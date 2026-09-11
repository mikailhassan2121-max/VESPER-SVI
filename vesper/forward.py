"""Immutable forward benchmark outcomes, never represented as brokerage fills."""
import json
from datetime import date

import numpy as np
import pandas as pd

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
    normalized = normalize_bars(stock_bars, ticker)
    stock = labels(normalized, session, stock_actions,
                   slippage_bps=settings.slippage_bps_each_side)
    spy = labels(normalize_bars(spy_bars, "SPY"), session, spy_actions,
                 slippage_bps=settings.slippage_bps_each_side)
    return {"recorded_at": utcnow().isoformat(), "kind": "EXECUTION_WINDOW_BENCHMARK_NOT_ACTUAL_FILL",
            "return": stock["target_net_return"], "spy_return": spy["target_net_return"],
            "excess_return": stock["target_net_return"]-spy["target_net_return"],
            "entry": stock["entry_price"], "exit": stock["exit_price"],
            "entry_time": stock["entry_time"].isoformat(), "exit_time": stock["label_end"].isoformat(),
            "within_max_entry": stock["entry_price"] <= position["signal"]["max_entry"],
            "forecast": position["signal"]["expected_return"],
            "forecast_error": stock["target_return"]-position["signal"]["expected_return"],
            "gap_return": stock["target_gap"], "intraday_return": stock["target_intraday"],
            "cost": stock["cost"],
            "loss_attribution": ("COSTS_DOMINATED" if stock["target_return"] >= 0 else
                                 "OVERNIGHT_COMPONENT" if stock["target_gap"] < stock["target_intraday"] else
                                 "INTRADAY_COMPONENT") if stock["target_net_return"] < 0 else "NOT_APPLICABLE",
            "attribution_scope": "Return decomposition; not a causal news explanation",
            **excursions(normalized, session, stock_actions, stock["entry_price"])}


def excursions(bars, session, actions, entry):
    start = bars.end-pd.Timedelta(minutes=1)+pd.Timedelta(milliseconds=1)
    first = (start >= session.signal+pd.Timedelta(minutes=1)) & (bars.end < session.close)
    second = (start >= session.next_open) & (bars.end < session.next_close-pd.Timedelta(minutes=2))
    path = bars[first | second].copy()
    ratio, cash = 1., 0.
    for action in actions.get("splits", []):
        if str(session.day) < action["execution_date"] <= str(session.next_day):
            ratio *= action["split_to"]/action["split_from"]
    for action in actions.get("dividends", []):
        if str(session.day) < action["ex_dividend_date"] <= str(session.next_day):
            cash += action["cash_amount"]
    later = path.end >= session.next_open
    for column in ("high", "low"):
        path.loc[later, column] = path.loc[later, column]*ratio+cash
    return {"mfe": float(path.high.max()/entry-1), "mae": float(path.low.min()/entry-1),
            "excursion_kind": "REGULAR_SESSION_MINUTE_BAR_BOUNDS_NOT_ACTUAL_FILL_PATH"}


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
    values = [row["outcome"]["return"] for row in ordered]
    if values:
        wealth = np.cumprod(1+np.asarray(values))
        summary["max_drawdown"] = float(np.min(wealth/np.maximum.accumulate(np.r_[1, wealth])[1:]-1))
    return summary


def performance_pause(summary, drawdown_limit=.15):
    reasons = []
    if summary.get("max_drawdown", 0) <= -drawdown_limit:
        reasons.append("FORWARD_DRAWDOWN_LIMIT")
    recent = summary.get("windows", {}).get("20", {})
    if recent and recent["mean_return"] < 0 and recent["mean_excess"] < 0:
        reasons.append("NEGATIVE_20_SESSION_RETURN_AND_EXCESS")
    return reasons


def write_result(directory, position, outcome):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{position['session']}.json"
    # The SQLite outcome is canonical. An interrupted file write can be regenerated.
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps({"session": position["session"], "ticker": position["signal"]["winner"],
                                "outcome": outcome}, indent=2, allow_nan=False), encoding="utf-8")
    temp.replace(path)
