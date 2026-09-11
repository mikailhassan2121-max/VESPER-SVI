import copy
from datetime import date

import pandas as pd
import pytest

from vesper.calendar import Calendar
from vesper.config import Settings
from vesper.features import normalize_bars
from vesper.labels import labels
from vesper.market_state import enrich_candidates
from vesper.readiness import clock_check, feed_evidence
from vesper.registry import REQUIRED_AUDITS, candidate_path, promotion_failures
from vesper.validation import evaluate


def test_gross_net_and_dividend_decomposition():
    session = Calendar().session(date(2026, 9, 4))
    raw = [{"t": int(time.timestamp()*1000), "o": price, "h": price, "l": price,
            "c": price, "v": 1000, "vw": price}
           for time, price in [(session.signal+pd.Timedelta(minutes=1), 100),
                               (session.next_open, 99), (session.next_close-pd.Timedelta(minutes=9), 101)]]
    result = labels(normalize_bars(raw, "TEST"), session,
                    {"dividends": [{"ex_dividend_date": str(session.next_day), "cash_amount": 1}]})
    assert result["target_return"] == pytest.approx(.02)
    assert result["target_net_return"] == pytest.approx(result["target_return"]-result["cost"])
    assert result["cost"] > 0
    assert (1+result["target_gap"])*(1+result["target_intraday"])-1 == pytest.approx(result["target_return"])


def test_risk_records_do_not_refresh_or_erase_other_evidence():
    now = pd.Timestamp("2026-09-04T19:50Z")
    frame = pd.DataFrame({"ticker": ["TEST"]})
    records = [{"ticker": "TEST", "available_at": (now-pd.Timedelta(minutes=5)).isoformat(), "halted": False},
               {"ticker": "TEST", "available_at": now.isoformat(), "binary_event": True},
               {"ticker": "TEST", "available_at": now.isoformat(), "binary_event": False}]
    result = enrich_candidates(frame, {}, {}, records, now).iloc[0]
    assert pd.isna(result.halted)
    assert result.binary_event is True


def test_clock_rejects_offset_and_slow_request():
    now = pd.Timestamp("2026-09-04T19:50Z")
    assert clock_check({"serverTime": now.isoformat()}, now, now)["valid"]
    assert not clock_check({"serverTime": now.isoformat()}, now, now+pd.Timedelta(seconds=5))["valid"]
    assert not clock_check({"serverTime": (now+pd.Timedelta(seconds=10)).isoformat()}, now, now)["valid"]
    with pytest.raises(ValueError):
        clock_check({"serverTime": "2026-09-04T19:50"}, now, now)


def test_full_feed_requires_fresh_broad_movement_and_quotes():
    now = pd.Timestamp("2026-09-04T19:50Z")
    tickers = {f"TEST{i}" for i in range(100)}
    bars = {t: [{"e": int((now-pd.Timedelta(seconds=s)).timestamp()*1000)} for s in [1, 61]] for t in tickers}
    quotes = {t: {"t": int(now.timestamp()*1000), "ap": 101, "bp": 100} for t in sorted(tickers)[:5]}
    health = {"state": "HEALTHY", "entitlement": "REALTIME_FULL_MARKET"}
    assert feed_evidence(health, bars, quotes, tickers, now, Settings())["entitlement"] == "REALTIME_FULL_MARKET"
    assert feed_evidence(health, {}, quotes, tickers, now, Settings())["entitlement"] != "REALTIME_FULL_MARKET"
    assert feed_evidence(health, bars, {}, tickers, now, Settings())["entitlement"] != "REALTIME_FULL_MARKET"
    assert feed_evidence(health, bars, quotes, tickers, now+pd.Timedelta(minutes=2), Settings())["entitlement"] != "REALTIME_FULL_MARKET"


def test_promotion_rejects_incomplete_or_negative_evidence(tmp_path):
    metadata = {"dataset_sha256": "fixture", "forecast_basis": "GROSS_RETURN_MINUS_EXECUTION_COST",
                "calibration": {name: {"slope": 1., "intercept": 0.} for name in ["positive", "outperform", "top_decile", "top_one"]},
                "locked_test": {"sessions": 63, "excess_vs_spy": .01, "rank_ic": .1,
                    "max_drawdown": -.1, "brier": .2, "mean_ci95_block": [.001, .02],
                    "excess_ci95_block": [.001, .01], "mean": .01, "momentum_mean": .005}}
    audit = {"dataset_sha256": "fixture", "checks": {name: {"status": "PASS", "evidence": "UNIT FIXTURE ONLY"} for name in REQUIRED_AUDITS}}
    assert not promotion_failures(metadata, audit)
    altered = copy.deepcopy(metadata)
    altered["locked_test"]["excess_ci95_block"][0] = -.001
    assert promotion_failures(altered, audit)
    assert promotion_failures(metadata, {})
    for name in ["..", "../outside", "C:outside"]:
        with pytest.raises(ValueError):
            candidate_path(tmp_path, name)


def test_validator_missing_application_never_passes():
    result = evaluate({}, [], pd.Timestamp("2026-09-04T19:50Z"), Settings())
    assert result["LIVE PIPELINE"] == "FAIL"
    assert result["Runtime Freshness"] == "NOT PROVEN"
