import json
from datetime import date
from pathlib import Path

import pandas as pd

from vesper.calendar import Calendar
from vesper.context import HistoricalContext, dated_records
from vesper.features import build_features, normalize_bars
from vesper.labels import labels


def build_dataset(directory, output):
    """Compile cached market-wide sessions without silently discarding missing outcomes.

    An unresolved eligible outcome blocks export. This intentionally requires reconciliation
    of delistings/mergers instead of teaching only from the surviving securities.
    """
    calendar = Calendar()
    history = HistoricalContext()
    samples, unresolved = [], []
    folders = sorted((Path(directory) / "historical").glob("????-??-??"))
    for folder in folders:
        if not (folder / "complete.json").exists():
            raise ValueError(f"Incomplete acquisition: {folder.name}")
        session = calendar.session(date.fromisoformat(folder.name))
        universe = json.loads((folder / "universe.json").read_text())["eligible"]
        minute_frames, targets, actions = [], {}, []
        for path in (folder / "minutes").glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            ticker = payload["ticker"]
            bars = normalize_bars(payload["bars"], ticker, availability_lag_seconds=1)
            if bars.empty:
                unresolved.append({"session": folder.name, "ticker": ticker, "reason": "NO_BARS"})
                continue
            current = bars[(bars.end >= session.open) & (bars.end < session.close)]
            minute_frames.append(current)
            actions.extend(payload["actions"].get("splits", []))
            try:
                targets[ticker] = labels(bars, session, payload["actions"])
            except (ValueError, KeyError) as exc:
                unresolved.append({"session": folder.name, "ticker": ticker, "reason": str(exc)})
        if minute_frames:
            daily, expected = history.inputs(session, session.cutoff, actions)
            records = dated_records(Path(directory) / "context" / "sectors.json", session.cutoff)
            sectors = {row["ticker"]: row["sector"] for row in records}
            sector_returns = {}
            for ticker, target in targets.items():
                if ticker in sectors and ticker in universe:
                    sector_returns.setdefault(sectors[ticker], []).append(target["target_return"])
            features = build_features(pd.concat(minute_frames), daily, expected,
                                      session.cutoff, session.open, sectors=sectors)
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
                        "sector_return": (sum(sector_returns[sectors[ticker]]) / len(sector_returns[sectors[ticker]]))
                            if ticker in sectors and sectors[ticker] in sector_returns else float("nan"),
                        "sector_benchmark": "equal_weight_point_in_time_sector_peers",
                        "pit_universe": True, "source": "massive"})
            history.add(session, pd.concat(minute_frames, ignore_index=True))
    report_path = Path(output).with_suffix(".audit.json")
    audit = {"sessions": len(folders), "rows": len(samples), "unresolved": unresolved,
             "production_ready": False, "limitations": ["Historical revisions are not original publication snapshots",
                 "Point-in-time sector mappings required", "Historical NBBO costs use explicit conservative assumptions",
                 "Historical news/catalyst coverage not integrated"]}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    if unresolved:
        raise ValueError(f"{len(unresolved)} unresolved outcomes; inspect {report_path}")
    if not samples:
        raise ValueError("No research samples; acquire more than 20 prior sessions")
    pd.DataFrame(samples).to_parquet(output, index=False)
    return audit
