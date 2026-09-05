import json
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

import pandas as pd

from vesper.calendar import Calendar
from vesper.features import build_features, normalize_bars
from vesper.labels import labels


def build_dataset(directory, output):
    """Compile cached market-wide sessions without silently discarding missing outcomes.

    An unresolved eligible outcome blocks export. This intentionally requires reconciliation
    of delistings/mergers instead of teaching only from the surviving securities.
    """
    calendar = Calendar()
    previous_daily = deque(maxlen=65)
    profiles = defaultdict(lambda: deque(maxlen=20))
    samples, unresolved = [], []
    folders = sorted((Path(directory) / "historical").glob("????-??-??"))
    for folder in folders:
        if not (folder / "complete.json").exists():
            raise ValueError(f"Incomplete acquisition: {folder.name}")
        session = calendar.session(date.fromisoformat(folder.name))
        universe = json.loads((folder / "universe.json").read_text())["eligible"]
        minute_frames, targets, current_daily, volumes = [], {}, [], {}
        for path in (folder / "minutes").glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            ticker = payload["ticker"]
            bars = normalize_bars(payload["bars"], ticker, availability_lag_seconds=1)
            if bars.empty:
                unresolved.append({"session": folder.name, "ticker": ticker, "reason": "NO_BARS"})
                continue
            current = bars[(bars.end >= session.open) & (bars.end < session.close)]
            minute_frames.append(current)
            # Raw price history across a split must be normalized to the current share basis.
            for action in payload["actions"].get("splits", []):
                if action["execution_date"] == folder.name:
                    ratio = action["split_to"] / action["split_from"]
                    for daily_frame in previous_daily:
                        mask = daily_frame.ticker == ticker
                        daily_frame.loc[mask, ["open", "high", "low", "close", "vwap"]] /= ratio
                        daily_frame.loc[mask, "volume"] *= ratio
                    profiles[ticker] = deque([v * ratio for v in profiles[ticker]], maxlen=20)
            try:
                targets[ticker] = labels(bars, session, payload["actions"])
            except (ValueError, KeyError) as exc:
                unresolved.append({"session": folder.name, "ticker": ticker, "reason": str(exc)})
            if not current.empty:
                current_daily.append({"ticker": ticker, "end": pd.Timestamp(session.close),
                                      "available_at": pd.Timestamp(session.close) + pd.Timedelta(seconds=1),
                                      "open": current.iloc[0].open, "close": current.iloc[-1].close,
                                      "high": current.high.max(), "low": current.low.min(),
                                      "volume": current.volume.sum(), "vwap": current.vwap.mean()})
                volumes[ticker] = current[current.end <= session.cutoff].volume.sum()
        if minute_frames and previous_daily:
            expected = {t: sum(v) / len(v) for t, v in profiles.items() if len(v) >= 20}
            features = build_features(pd.concat(minute_frames), pd.concat(previous_daily), expected,
                                      session.cutoff, session.open)
            if not features.empty and "SPY" in targets:
                for row in features.to_dict("records"):
                    ticker = row["ticker"]
                    if ticker not in universe or ticker not in targets:
                        continue
                    # Research eligibility uses only history before this signal.
                    if row["price"] < 2 or pd.isna(row["median_dollar_volume"]) or row["median_dollar_volume"] < 10_000_000:
                        continue
                    samples.append(row | targets[ticker] | {"session": folder.name, "cutoff": session.cutoff,
                        "feature_available_at": session.cutoff, "spy_return": targets["SPY"]["target_return"],
                        "sector_return": float("nan"), "pit_universe": True, "source": "massive"})
        if current_daily:
            previous_daily.append(pd.DataFrame(current_daily))
        for ticker, volume in volumes.items():
            profiles[ticker].append(volume)
    report_path = Path(output).with_suffix(".audit.json")
    audit = {"sessions": len(folders), "rows": len(samples), "unresolved": unresolved,
             "production_ready": False, "limitations": ["Historical revisions are not original publication snapshots",
                 "Point-in-time sector mappings required", "Historical NBBO costs use explicit conservative assumptions",
                 "Historical news/catalyst coverage not integrated", "Early-close volume profiles require matched session lengths"]}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    if unresolved:
        raise ValueError(f"{len(unresolved)} unresolved outcomes; inspect {report_path}")
    if not samples:
        raise ValueError("No research samples; acquire more than 20 prior sessions")
    pd.DataFrame(samples).to_parquet(output, index=False)
    return audit
