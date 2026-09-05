import asyncio
from pathlib import Path

from vesper.calendar import NY, Calendar, utcnow
from vesper.provider import Massive, timestamp_ms
from vesper.universe import reference_universe


async def validate_live(settings, seconds=120):
    now = utcnow()
    calendar = Calendar()
    session = calendar.session(now.astimezone(NY).date())
    report = {"Market Calendar": "PASS", "Universe": "NOT TESTED", "Real-Time Entitlement": "NOT PROVEN",
              "Market-Wide Feed": "NOT PROVEN", "Quote Feed": "NOT PROVEN", "Production Model": "NOT PROVEN",
              "Feature Engine": "NOT PROVEN", "Ranking Engine": "NOT PROVEN", "Risk Filters": "NOT PROVEN",
              "Signal Engine": "NOT PROVEN", "Persistence": "NOT PROVEN", "Telegram": "NOT CONFIGURED",
              "Dashboard": "NOT TESTED", "LIVE PIPELINE": "FAIL"}
    evidence = {"checked_at": now.isoformat(), "session": str(session.day) if session else None,
                "signal_time": session.signal.isoformat() if session else None,
                "close": session.close.isoformat() if session else None,
                "next_session": str(session.next_day) if session else str(calendar.upcoming(now).day)}
    if not session or not session.open <= now < session.close:
        report["Market-Wide Feed"] = "PENDING NEXT OPEN SESSION"
    provider = Massive(settings.massive_api_key.get_secret_value())
    task = None
    try:
        records = await provider.references(now.astimezone(NY).date())
        universe, rejected = reference_universe(records)
        report["Universe"] = "PASS" if universe else "FAIL"
        evidence.update(total_references=len(records), eligible=len(universe), rejected=rejected)
        if not session or not session.open <= now < session.close:
            report["Market-Wide Feed"] = "PENDING NEXT OPEN SESSION"
        else:
            queue = asyncio.Queue(maxsize=settings.queue_size)
            task = asyncio.create_task(provider.stream(queue))
            deadline = asyncio.get_running_loop().time() + seconds
            snapshots, latencies, quotes = {}, [], set()
            while asyncio.get_running_loop().time() < deadline:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=min(5, max(.1, deadline-asyncio.get_running_loop().time())))
                except TimeoutError:
                    continue
                ticker = event.get("sym")
                if event.get("ev") == "AM" and ticker in universe:
                    snapshots.setdefault(ticker, set()).add((event["e"], event["c"], event["v"]))
                    latencies.append(utcnow().timestamp() - timestamp_ms(event["e"]) / 1000)
                    if len(snapshots) <= 20:
                        await provider.shortlist(list(snapshots))
                elif event.get("ev") == "Q" and event.get("ap", 0) >= event.get("bp", 0) > 0:
                    if 0 <= utcnow().timestamp() - timestamp_ms(event["t"]) / 1000 <= settings.max_quote_age:
                        quotes.add(ticker)
                queue.task_done()
            changed = sum(len(values) >= 2 for values in snapshots.values())
            evidence.update(received_tickers=len(snapshots), multiple_snapshots=changed, fresh_quote_tickers=len(quotes),
                            min_latency=min(latencies) if latencies else None,
                            max_latency=max(latencies) if latencies else None)
            if changed >= 5:
                report["Market-Wide Feed"] = "MOVEMENT OBSERVED; FULL COVERAGE NOT YET PROVEN"
            if len(quotes) >= 5:
                report["Quote Feed"] = "PASS"
            if latencies and min(latencies) >= 0 and max(latencies) <= settings.max_bar_age:
                report["Real-Time Entitlement"] = "FRESH DATA OBSERVED; FULL COVERAGE NOT YET PROVEN"
    except Exception as exc:
        evidence["error"] = str(exc) if type(exc).__name__ == "ProviderError" else type(exc).__name__
        report["Universe"] = "FAIL"
    finally:
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await provider.close()
    import json
    body = "# VESPER live validation\n\nNo fabricated data. An offline test pass does not establish live readiness.\n\n"
    body += "| Check | Result |\n|---|---|\n" + "\n".join(f"| {key} | {value} |" for key, value in report.items())
    body += "\n\n## Evidence\n\n```json\n" + json.dumps(evidence, indent=2) + "\n```\n"
    Path("LIVE_VALIDATION_REPORT.md").write_text(body, encoding="utf-8")
    return report, evidence
