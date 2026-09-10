"""Immutable forward benchmark outcomes, never represented as brokerage fills."""
import json
from datetime import date

from vesper.calendar import Calendar, utcnow
from vesper.features import normalize_bars
from vesper.labels import labels


async def resolve_shadow(provider, position, settings):
    session = Calendar().session(date.fromisoformat(position["session"]))
    if session is None or utcnow() < session.next_close:
        return None
    ticker = position["signal"]["winner"]
    stock_bars = await provider.bars(ticker, session.day, session.next_day)
    spy_bars = await provider.bars("SPY", session.day, session.next_day)
    stock_actions = await provider.actions(ticker)
    spy_actions = await provider.actions("SPY")
    stock = labels(normalize_bars(stock_bars, ticker), session, stock_actions,
                   slippage_bps=settings.slippage_bps_each_side)
    spy = labels(normalize_bars(spy_bars, "SPY"), session, spy_actions,
                 slippage_bps=settings.slippage_bps_each_side)
    return {"recorded_at": utcnow().isoformat(), "kind": "EXECUTION_WINDOW_BENCHMARK_NOT_ACTUAL_FILL",
            "return": stock["target_return"], "spy_return": spy["target_return"],
            "excess_return": stock["target_return"]-spy["target_return"],
            "entry": stock["entry_price"], "exit": stock["exit_price"],
            "entry_time": stock["entry_time"].isoformat(), "exit_time": stock["label_end"].isoformat(),
            "within_max_entry": stock["entry_price"] <= position["signal"]["max_entry"],
            "forecast": position["signal"]["expected_return"],
            "forecast_error": stock["target_return"]-position["signal"]["expected_return"],
            "loss_attribution": "UNATTRIBUTED" if stock["target_return"] < 0 else "NOT_APPLICABLE"}


def forward_summary(positions):
    ordered = sorted(positions, key=lambda row: row["session"])
    summary = {"completed": len(ordered), "kind": "FORWARD_BENCHMARKS_NOT_ACTUAL_FILLS", "windows": {}}
    for count in (20, 50, 100):
        rows = ordered[-count:]
        if len(rows) < count:
            continue
        values = [row["outcome"]["return"] for row in rows]
        summary["windows"][str(count)] = {"mean_return": sum(values)/count,
            "positive_rate": sum(value > 0 for value in values)/count,
            "mean_excess": sum(row["outcome"]["excess_return"] for row in rows)/count}
    return summary


def write_result(directory, position, outcome):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{position['session']}.json"
    # The SQLite outcome is canonical. An interrupted file write can be regenerated.
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps({"session": position["session"], "ticker": position["signal"]["winner"],
                                "outcome": outcome}, indent=2, allow_nan=False), encoding="utf-8")
    temp.replace(path)
