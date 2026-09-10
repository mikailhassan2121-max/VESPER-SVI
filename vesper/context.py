"""Receipt-aware historical context shared by research and the live process."""
import json
from collections import deque
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from vesper.calendar import Calendar
from vesper.features import cutoff_rows, normalize_bars


class HistoricalContext:
    def __init__(self, max_sessions=65):
        self.sessions = deque()
        self.max_sessions = max_sessions

    def add(self, session, bars):
        current = cutoff_rows(bars, session.close + pd.Timedelta(seconds=2))
        current = current[(current.end >= session.open) & (current.end < session.close)]
        if any(saved.day == session.day for saved, _, _ in self.sessions):
            raise ValueError("Duplicate historical session")
        if current.empty:
            return
        current["weighted"] = current.vwap * current.volume
        grouped = current.groupby("ticker", sort=False)
        daily = grouped.agg(open=("open", "first"), close=("close", "last"), high=("high", "max"),
                            low=("low", "min"), volume=("volume", "sum"), weighted=("weighted", "sum"))
        daily["vwap"] = daily.weighted / daily.volume.replace(0, np.nan)
        daily = daily.drop(columns="weighted").reset_index()
        daily["end"] = pd.Timestamp(session.close)
        daily["available_at"] = pd.Timestamp(session.close) + pd.Timedelta(seconds=2)
        current["elapsed_second"] = ((current.available_at - session.open).dt.total_seconds()).apply(np.ceil).astype(int)
        curves = current.pivot_table(index="elapsed_second", columns="ticker", values="volume", aggfunc="sum", fill_value=0).cumsum()
        self.sessions.append((session, daily, curves.astype("float32")))
        # Keep a separate reservoir for short sessions rather than evicting their
        # scarce comparison days whenever another normal trading week completes.
        buckets = {}
        for saved in reversed(self.sessions):
            duration = saved[0].close - saved[0].open
            bucket = buckets.setdefault(duration, [])
            if len(bucket) < (self.max_sessions if duration.total_seconds() == 23400 else 20):
                bucket.append(saved)
        self.sessions = deque(sorted((saved for values in buckets.values() for saved in values), key=lambda x: x[0].day))

    def inputs(self, session, cutoff, splits=(), min_profile_sessions=20):
        """Use prior sessions of the same duration, at the same elapsed minute.

        Splits must have occurred by the prediction date. Never use a provider's
        cumulative adjustment factor that includes future actions.
        """
        elapsed = pd.Timestamp(cutoff) - session.open
        daily, volumes = [], []
        for prior, original, curve in self.sessions:
            if prior.day >= session.day:
                continue
            bars = original.copy()
            for action in splits:
                if str(prior.day) < action["execution_date"] <= str(session.day):
                    ratio = float(action["split_to"]) / float(action["split_from"])
                    if not np.isfinite(ratio) or ratio <= 0:
                        raise ValueError("Invalid split ratio")
                    mask = bars.ticker == action["ticker"]
                    bars.loc[mask, ["open", "high", "low", "close", "vwap"]] /= ratio
                    bars.loc[mask, "volume"] *= ratio
            daily.append(bars)
            if prior.close - prior.open == session.close - session.open:
                known = curve[curve.index <= elapsed.total_seconds()]
                if not known.empty:
                    values = known.iloc[-1].copy()
                    for action in splits:
                        if str(prior.day) < action["execution_date"] <= str(session.day) and action["ticker"] in values:
                            values[action["ticker"]] *= float(action["split_to"]) / float(action["split_from"])
                    volumes.append(values)
        profiles = {}
        if volumes:
            panel = pd.DataFrame(volumes).tail(20)
            means = panel.mean()
            profiles = means[panel.count() >= min_profile_sessions].to_dict()
        frame = pd.concat(daily, ignore_index=True) if daily else normalize_bars([], "")
        return frame, profiles


def load_history(directory, before, max_sessions=65):
    context = HistoricalContext(max_sessions)
    calendar = Calendar()
    candidates = [p for p in sorted((Path(directory) / "historical").glob("????-??-??"))
                  if p.name < str(before) and (p / "complete.json").exists()]
    buckets = {}
    for folder in reversed(candidates):
        prior = calendar.session(date.fromisoformat(folder.name))
        if prior is None:
            raise ValueError("Cached history has a non-session date")
        duration = prior.close-prior.open
        bucket = buckets.setdefault(duration, [])
        if len(bucket) < (max_sessions if duration.total_seconds() == 23400 else 20):
            bucket.append(folder)
    folders = sorted(folder for values in buckets.values() for folder in values)
    for folder in folders:
        session = calendar.session(date.fromisoformat(folder.name))
        if session is None:
            raise ValueError("Cached history has a non-session date")
        frames = []
        for path in (folder / "minutes").glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("source") != "massive" or payload.get("adjusted") is not False:
                raise ValueError("Unexpected historical provenance")
            frames.append(normalize_bars(payload["bars"], payload["ticker"], availability_lag_seconds=1))
        if frames:
            context.add(session, pd.concat(frames, ignore_index=True))
    return context


def dated_records(path, cutoff):
    """Optional audited context file: publication and validity are separate timestamps."""
    path = Path(path)
    if not path.exists():
        return []
    records = json.loads(path.read_text(encoding="utf-8"))
    result = []
    for record in records:
        if not record.get("source"):
            raise ValueError("Context record requires a source")
        times = [pd.Timestamp(record[key]) for key in ("available_at", "valid_from", "valid_until")]
        if any(t.tzinfo is None for t in times):
            raise ValueError("Context timestamps must be timezone-aware")
        available, start, end = times
        if available <= cutoff and start <= cutoff < end:
            result.append(record)
    return sorted(result, key=lambda row: pd.Timestamp(row["available_at"]))
