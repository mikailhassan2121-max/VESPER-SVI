from datetime import date

import pandas as pd
import pytest

from vesper.calendar import Calendar
from vesper.context import HistoricalContext, dated_records
from vesper.features import normalize_bars


def minutes(session, volume=100):
    return normalize_bars([{"t": int((session.open+pd.Timedelta(minutes=i)).timestamp()*1000),
                            "o": 10., "h": 10., "l": 10., "c": 10., "vw": 10., "v": volume}
                           for i in range(int((session.close-session.open).total_seconds()/60))], "TEST", 1)


def test_profile_matches_elapsed_minute_and_excludes_future_sessions():
    calendar = Calendar()
    prior = calendar.session(date(2026, 9, 3))
    current = calendar.session(date(2026, 9, 4))
    future = calendar.session(date(2026, 9, 8))
    history = HistoricalContext()
    history.add(prior, minutes(prior))
    history.add(future, minutes(future, 99999))
    daily, profile = history.inputs(current, current.open+pd.Timedelta(minutes=30), min_profile_sessions=1)
    assert profile["TEST"] == 2900
    assert daily.close.to_list() == [10]
    assert daily.volume.to_list() == [39000]


def test_early_close_does_not_use_normal_session_profile():
    calendar = Calendar()
    prior = calendar.session(date(2026, 11, 25))
    early = calendar.session(date(2026, 11, 27))
    history = HistoricalContext()
    history.add(prior, minutes(prior))
    daily, profile = history.inputs(early, early.cutoff, min_profile_sessions=1)
    assert len(daily) == 1
    assert profile == {}


def test_split_context_is_repeatable_and_does_not_mutate_raw_history():
    calendar = Calendar()
    prior = calendar.session(date(2026, 9, 3))
    current = calendar.session(date(2026, 9, 4))
    history = HistoricalContext()
    history.add(prior, minutes(prior))
    splits = [{"ticker": "TEST", "execution_date": "2026-09-04", "split_to": 10, "split_from": 1},
              {"ticker": "TEST", "execution_date": "2026-09-08", "split_to": 100, "split_from": 1}]
    first, volume = history.inputs(current, current.cutoff, splits, min_profile_sessions=1)
    second, _ = history.inputs(current, current.cutoff, splits, min_profile_sessions=1)
    assert first.equals(second)
    assert first.close.iloc[0] == 1
    original, _ = history.inputs(current, current.cutoff, min_profile_sessions=1)
    assert original.close.iloc[0] == 10
    assert volume["TEST"] > 300000


def test_context_records_require_prior_availability(tmp_path):
    import json
    path = tmp_path / "sector.json"
    row = {"source": "unit-test", "ticker": "TEST", "sector": "test",
           "available_at": "2026-09-04T19:51Z", "valid_from": "2026-01-01T00:00Z",
           "valid_until": "2027-01-01T00:00Z"}
    path.write_text(json.dumps([row]))
    assert dated_records(path, pd.Timestamp("2026-09-04T19:50Z")) == []
    row["available_at"] = "2026-09-04T19:49Z"
    path.write_text(json.dumps([row]))
    assert len(dated_records(path, pd.Timestamp("2026-09-04T19:50Z"))) == 1
    row["available_at"] = "2026-09-04T19:49"
    path.write_text(json.dumps([row]))
    with pytest.raises(ValueError, match="timezone"):
        dated_records(path, pd.Timestamp("2026-09-04T19:50Z"))
