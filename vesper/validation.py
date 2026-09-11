"""Observe the running pipeline; never open a competing feed or send a test alert."""
import asyncio
import json
from pathlib import Path

import httpx
import pandas as pd

from vesper.calendar import NY, Calendar, utcnow


def evaluate(snapshot, signals, now, settings):
    session = Calendar().session(now.astimezone(NY).date())
    updated = pd.Timestamp(snapshot.get("updated_at"))
    fresh = not pd.isna(updated) and updated.tzinfo is not None and 0 <= (now-updated).total_seconds() <= 15
    opened = bool(session and session.open <= now < session.close and snapshot.get("market") == "OPEN")
    feed = snapshot.get("feed_evidence", {})
    model = snapshot.get("model", {})
    valid_signals = [row for row in signals if session and row.get("session") == str(session.day)
                     and row.get("decision") in {"BUY", "NO TRADE"}
                     and row.get("context", {}).get("mode") == "LIVE"
                     and row.get("context", {}).get("signal_window")
                     and row.get("model") == model.get("model_id")
                     and not row.get("context", {}).get("failures")]
    checks = {
        "Open Session": opened,
        "Runtime Freshness": fresh and snapshot.get("mode") == "LIVE",
        "Clock": snapshot.get("clock", {}).get("valid") is True,
        "Universe": snapshot.get("universe", 0) >= 100,
        "Real-Time Entitlement": feed.get("entitlement") == "REALTIME_FULL_MARKET",
        "Market-Wide Feed": feed.get("stream_coverage", 0) >= settings.min_coverage and feed.get("moving_tickers", 0) >= 5,
        "Quote Feed": feed.get("fresh_quote_tickers", 0) >= 5,
        "Production Model": model.get("status") == "PRODUCTION" and bool(model.get("model_id")),
        "Feature Engine": snapshot.get("coverage", 0) >= settings.min_coverage,
        "Ranking Engine": snapshot.get("leaderboard_label") == "MODEL RANKING" and bool(snapshot.get("leaderboard")),
        "Workers": not snapshot.get("failures") and not snapshot.get("pipeline_failures"),
        "Signal and Persistence": bool(valid_signals),
        "Risk Filters": bool(valid_signals),
    }
    report = {key: "PASS" if value else "NOT PROVEN" for key, value in checks.items()}
    if not opened:
        report["Open Session"] = "PENDING OPEN SESSION"
    telegram_required = bool(settings.telegram_bot_token.get_secret_value() and settings.telegram_chat_id)
    report["Telegram"] = ("PASS" if snapshot.get("telegram") == "HEALTHY" else "NOT PROVEN") if telegram_required else "NOT CONFIGURED (OPTIONAL)"
    report["LIVE PIPELINE"] = "PASS" if all(checks.values()) and (not telegram_required or report["Telegram"] == "PASS") else "FAIL"
    return report


async def validate_live(settings, seconds=120):
    deadline = asyncio.get_running_loop().time()+seconds
    observations = []
    rankings = set()
    snapshot, signals = {}, []
    dashboard = False
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8787", timeout=5, trust_env=False) as client:
        while True:
            now = utcnow()
            try:
                response = await client.get("/api/status")
                response.raise_for_status()
                snapshot = response.json()
                response = await client.get("/api/signals")
                response.raise_for_status()
                signals = response.json()
                dashboard = (await client.get("/")).status_code == 200
                report = evaluate(snapshot, signals, now, settings)
                ranking = [{key: row.get(key) for key in ("ticker", "price", "expected_return", "score", "return_30m", "rvol")}
                           for row in snapshot.get("leaderboard", [])[:20]]
                if snapshot.get("leaderboard_label") == "MODEL RANKING" and ranking:
                    rankings.add(json.dumps(ranking, sort_keys=True, allow_nan=False))
                observations.append({"at": now.isoformat(), "updated_at": snapshot.get("updated_at"),
                                     "checks": report.copy(), "ranking": ranking})
            except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
                report = evaluate({}, [], now, settings)
                observations.append({"at": now.isoformat(), "error": type(exc).__name__})
                break
            if (report["LIVE PIPELINE"] == "PASS" and len(rankings) >= 2) or asyncio.get_running_loop().time() >= deadline:
                break
            if not Calendar().session(now.astimezone(NY).date()) or snapshot.get("market") == "CLOSED":
                break
            await asyncio.sleep(min(5, max(.01, deadline-asyncio.get_running_loop().time())))
    report["Dashboard"] = "PASS" if dashboard else "NOT PROVEN"
    report["Dynamic Ranking"] = "PASS" if len(rankings) >= 2 else "NOT PROVEN"
    if not dashboard or len(rankings) < 2:
        report["LIVE PIPELINE"] = "FAIL"
    evidence = {"checked_at": utcnow().isoformat(), "observations": observations,
                "runtime": snapshot, "signal_sessions": [row.get("session") for row in signals],
                "scope": "Current running application and current-session persisted decision; no synthetic data or messages"}
    body = "# VESPER live validation\n\nStart VESPER before running this check. Full acceptance requires observing the real signal session.\n\n"
    body += "| Check | Result |\n|---|---|\n"+"\n".join(f"| {key} | {value} |" for key, value in report.items())
    body += "\n\n## Evidence\n\n```json\n"+json.dumps(evidence, indent=2, allow_nan=False)+"\n```\n"
    Path("LIVE_VALIDATION_REPORT.md").write_text(body, encoding="utf-8")
    destination = settings.data_dir / "live-validation.json"
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps({"checks": report, "evidence": evidence}, allow_nan=False), encoding="utf-8")
    temporary.replace(destination)
    return report, evidence
