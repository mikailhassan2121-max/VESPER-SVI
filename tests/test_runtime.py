from datetime import date

import pandas as pd

from vesper.calendar import Calendar
from vesper.config import Settings
from vesper.market_state import enrich_candidates
from vesper.runtime import Runtime


async def test_missing_model_and_feed_still_record_daily_invalid_decision(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", model_dir=tmp_path / "models", MASSIVE_API_KEY="")
    runtime = Runtime(settings)
    session = Calendar().session(date(2026, 9, 4))
    try:
        await runtime.rank_once(session.signal)
        await runtime.rank_once(session.signal+pd.Timedelta(seconds=1))
        signals = runtime.store.recent()
        assert len(signals) == 1
        assert signals[0]["decision"] == "NO SIGNAL — SYSTEM INVALID"
        assert "PRODUCTION_MODEL_UNAVAILABLE" in signals[0]["reasons"]
    finally:
        await runtime.close()


def test_quote_enrichment_preserves_unknown_risks():
    now = pd.Timestamp("2026-09-04T19:50Z")
    frame = pd.DataFrame([{"ticker": "TEST", "last_bar": now-pd.Timedelta(seconds=60)}])
    quote = {"ap": 10.01, "bp": 10, "bs": 10, "as": 20,
             "t": int((now-pd.Timedelta(seconds=1)).timestamp()*1000), "received_at": now.isoformat()}
    enriched = enrich_candidates(frame, {"TEST": quote}, {}, [], now)
    assert enriched.iloc[0].quote_age == 1
    assert enriched.iloc[0].bar_age == 60
    assert pd.isna(enriched.iloc[0].halted)
    assert pd.isna(enriched.iloc[0].binary_event)
    assert pd.isna(enriched.iloc[0].luld_risk)


def test_stale_risk_record_cannot_clear_veto():
    now = pd.Timestamp("2026-09-04T19:50Z")
    frame = pd.DataFrame([{"ticker": "TEST", "last_bar": now}])
    risk = [{"ticker": "TEST", "halted": False, "binary_event": False,
             "available_at": (now-pd.Timedelta(minutes=5)).isoformat()}]
    enriched = enrich_candidates(frame, {}, {}, risk, now)
    assert pd.isna(enriched.iloc[0].halted)


async def test_post_cutoff_correction_keeps_original_prediction_input(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", model_dir=tmp_path / "models", MASSIVE_API_KEY="")
    runtime = Runtime(settings)
    cutoff = pd.Timestamp("2026-09-04T19:50Z")
    end = cutoff-pd.Timedelta(minutes=1)
    try:
        for i in range(20):
            runtime.keep_bar("TEST", {"end": end, "available_at": cutoff-pd.Timedelta(seconds=20-i), "close": i}, cutoff)
        runtime.keep_bar("TEST", {"end": end, "available_at": cutoff+pd.Timedelta(seconds=1), "close": 999}, cutoff)
        versions = runtime.bars["TEST"][end]
        assert len(versions) == 2
        assert [v["close"] for v in versions if v["available_at"] <= cutoff] == [19]
    finally:
        await runtime.close()
