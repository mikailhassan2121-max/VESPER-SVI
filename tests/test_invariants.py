import ast
import sqlite3
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from vesper.calendar import NY, Calendar
from vesper.config import Settings
from vesper.decision import decide
from vesper.features import cutoff_rows, intraday, normalize_bars
from vesper.modeling import purged_folds
from vesper.provider import Massive, ProviderError, timestamp_ms
from vesper.storage import Store
from vesper.universe import reference_universe, split_return


def test_early_close():
    session = Calendar().session(date(2026, 11, 27))
    assert session.close.astimezone(NY).hour == 13
    assert session.signal.astimezone(NY).strftime("%H:%M") == "12:50"


def test_holiday_and_next_session():
    calendar = Calendar()
    assert calendar.session(date(2026, 9, 7)) is None
    assert calendar.session(date(2026, 9, 4)).next_day == date(2026, 9, 8)


def test_dst():
    calendar = Calendar()
    assert calendar.session(date(2026, 3, 6)).signal.hour == 20
    assert calendar.session(date(2026, 3, 9)).signal.hour == 19


def bars():
    start = pd.Timestamp("2026-09-04T19:00:00Z")
    return normalize_bars([{"t": int((start + pd.Timedelta(minutes=i)).timestamp()*1000),
                            "o": 10+i/100, "h": 11, "l": 9, "c": 10+i/100,
                            "v": 100, "vw": 10+i/100} for i in range(60)], "TEST")


def test_future_bar_and_late_arrival_excluded():
    frame = bars()
    cutoff = pd.Timestamp("2026-09-04T19:49:59.999999Z")
    original = intraday(frame, cutoff, pd.Timestamp("2026-09-04T13:30Z"))
    frame.loc[frame.end > cutoff, "close"] = 900
    assert original.equals(intraday(frame, cutoff, pd.Timestamp("2026-09-04T13:30Z")))
    frame.loc[0, "available_at"] = cutoff + pd.Timedelta(seconds=1)
    assert len(cutoff_rows(frame, cutoff)) == 49


def test_availability_required():
    with pytest.raises(ValueError):
        cutoff_rows(bars().drop(columns="available_at"), pd.Timestamp("2026-09-04T20:00Z"))


def test_duplicate_correction_keeps_last_known_version():
    frame = bars().iloc[:2].copy()
    duplicate = frame.iloc[[0]].copy()
    duplicate["close"] = 11
    known = cutoff_rows(pd.concat([frame, duplicate]), pd.Timestamp("2026-09-04T20:00Z"))
    assert len(known) == 2
    assert known.iloc[0].close == 11


def test_split_and_dividend_return():
    assert split_return(100, 10, 10) == 0
    assert split_return(100, 99, 1, 1) == 0
    assert split_return(10, 100, .1) == 0


def test_historical_reference_does_not_filter_by_current_ticker():
    historical = [{"ticker": "OLD", "active": True, "market": "stocks", "locale": "us",
                   "type": "CS", "primary_exchange": "XNYS"}]
    universe, _ = reference_universe(historical)
    assert "OLD" in universe
    # The caller must request the historical date; current inactive status is not substituted.
    current = [historical[0] | {"active": False}]
    assert not reference_universe(current)[0]


@pytest.mark.parametrize("kind", ["ETF", "WARRANT", "PFD", "UNIT"])
def test_noncommon_rejected(kind):
    row = {"ticker": "X", "active": True, "market": "stocks", "locale": "us",
           "type": kind, "primary_exchange": "XNYS"}
    assert not reference_universe([row])[0]


def test_restart_dedupe_and_immutability(tmp_path):
    path = tmp_path / "state.sqlite"
    store = Store(path)
    assert store.signal("2026-09-04", "LIVE", {"winner": "X"})
    store.close()
    store = Store(path)
    assert not store.signal("2026-09-04", "LIVE", {"winner": "Y"})
    assert store.recent() == [{"winner": "X"}]
    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute("UPDATE signals SET payload='{}'")
    store.close()


def context():
    return {"mode": "LIVE", "entitlement": "REALTIME_FULL_MARKET", "model_production": True,
            "coverage": 1, "signal_window": True}


def candidate():
    return pd.DataFrame([dict(ticker="TEST", score=90, expected_return=.04, expected_excess=.03,
                             uncertainty=.03, q05=-.03, ask=10.01, bid=10, quote_age=1, bar_age=30,
                             median_dollar_volume=20_000_000, bid_size=100, ask_size=100,
                             halted=False, binary_event=False, luld_risk=False)])


@pytest.mark.parametrize("field,value", [("entitlement", "DELAYED"), ("mode", "REPLAY"),
                                        ("model_production", False), ("coverage", .5), ("signal_window", False)])
def test_invalid_system_cannot_buy(field, value):
    assert decide(candidate(), context() | {field: value}, Settings())["decision"].startswith("NO SIGNAL")


@pytest.mark.parametrize("field,value", [("quote_age", 10), ("quote_age", -1), ("bar_age", 200),
                                        ("ask", 9), ("bid", np.nan), ("halted", True),
                                        ("binary_event", True), ("luld_risk", True)])
def test_risk_veto(field, value):
    frame = candidate()
    frame.loc[0, field] = value
    assert decide(frame, context(), Settings())["decision"] != "BUY"


def test_valid_candidate_max_entry():
    outcome = decide(candidate(), context(), Settings())
    assert outcome["decision"] == "BUY"
    assert outcome["max_entry"] > outcome["entry"]


def test_purging_label_overlap():
    days = pd.date_range("2020-01-01", periods=20, tz="UTC")
    frame = pd.DataFrame({"session": days.date.astype(str), "cutoff": days,
                          "label_end": days + pd.Timedelta(days=3)})
    for training, validation in purged_folds(frame, min_train=5, validation_sessions=3):
        assert training.label_end.max() < validation.cutoff.min()
        assert training.session.max() < validation.session.min()


@pytest.mark.parametrize("value", [1788551400000, 1788551400000000, 1788551400000000000])
def test_provider_timestamp_units(value):
    assert timestamp_ms(value) == 1788551400000


async def test_pagination_never_leaks_key_to_other_host():
    provider = Massive("not-a-real-key")
    try:
        with pytest.raises(ProviderError):
            await provider.get("https://example.com/steal")
    finally:
        await provider.close()


def test_no_order_execution_path():
    forbidden = {"place_order", "buy_stock", "sell_stock", "submit_order", "cancel_order",
                 "modify_order", "broker_execution"}
    for path in (Path(__file__).parents[1] / "vesper").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Name)):
                assert getattr(node, "name", getattr(node, "id", "")) not in forbidden
            if isinstance(node, ast.Attribute):
                assert node.attr not in forbidden
