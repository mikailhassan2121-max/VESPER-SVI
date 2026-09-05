from datetime import date

import pandas as pd
import pytest

from vesper.calendar import Calendar
from vesper.features import normalize_bars
from vesper.labels import executable_vwap, labels


def test_execution_costs_are_conservative():
    start = pd.Timestamp("2026-09-04T19:50Z")
    frame = normalize_bars([{"t": int(start.timestamp()*1000), "o": 10, "h": 10, "l": 10,
                            "c": 10, "v": 1000, "vw": 10}], "TEST")
    end = start + pd.Timedelta(minutes=2)
    assert executable_vwap(frame, start, end, "entry") > 10
    assert executable_vwap(frame, start, end, "exit") < 10


def test_missing_exit_is_unresolved_not_zero():
    session = Calendar().session(date(2026, 9, 4))
    with pytest.raises(ValueError, match="UNRESOLVED"):
        labels(normalize_bars([], "TEST"), session, {})


def test_split_horizon_label():
    session = Calendar().session(date(2026, 9, 4))
    records = []
    for time, price in [(session.signal + pd.Timedelta(minutes=1), 100), (session.next_open, 10),
                        (session.next_close-pd.Timedelta(minutes=9), 10)]:
        records.append({"t": int(time.timestamp()*1000), "o": price, "h": price, "l": price,
                        "c": price, "v": 1000, "vw": price})
    result = labels(normalize_bars(records, "TEST"), session,
                    {"splits": [{"execution_date": "2026-09-08", "split_from": 1, "split_to": 10}]},
                    spread_bps=0, slippage_bps=0)
    assert result["target_return"] == pytest.approx(0)
    assert result["target_gap"] == pytest.approx(0)
