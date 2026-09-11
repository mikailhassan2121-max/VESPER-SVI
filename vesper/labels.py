from datetime import timedelta

import pandas as pd

from vesper.universe import split_return


def executable_vwap(bars, start, end, side, spread_bps=20, slippage_bps=10):
    if side not in {"entry", "exit"}:
        raise ValueError("Unknown benchmark side")
    if bars.empty:
        raise ValueError("UNRESOLVED_EXECUTION_WINDOW")
    # A full-minute VWAP cannot represent an entry after that minute has already begun.
    bar_start = bars.end - pd.Timedelta(minutes=1) + pd.Timedelta(milliseconds=1)
    window = bars[(bar_start >= start) & (bars.end < end)]
    if window.empty or window.volume.sum() <= 0:
        raise ValueError("UNRESOLVED_EXECUTION_WINDOW")
    mid = (window.vwap * window.volume).sum() / window.volume.sum()
    adjustment = (spread_bps / 2 + slippage_bps) / 10000
    return float(mid * (1 + adjustment if side == "entry" else 1 - adjustment))


def labels(bars, session, actions, spread_bps=20, slippage_bps=10):
    entry_time = session.signal + timedelta(seconds=15)
    exit_start = session.next_close - timedelta(minutes=10)
    exit_end = session.next_close - timedelta(minutes=2)
    entry = executable_vwap(bars, entry_time, session.signal + timedelta(minutes=2), "entry", spread_bps, slippage_bps)
    exit_price = executable_vwap(bars, exit_start, exit_end, "exit", spread_bps, slippage_bps)
    entry_mid = executable_vwap(bars, entry_time, session.signal + timedelta(minutes=2), "entry", 0, 0)
    exit_mid = executable_vwap(bars, exit_start, exit_end, "exit", 0, 0)
    opening = bars[(bars.end >= session.next_open) & (bars.end < session.next_open + timedelta(minutes=2))]
    if opening.empty:
        raise ValueError("UNRESOLVED_NEXT_OPEN")
    next_open = float(opening.iloc[0].open)
    ratio, cash = 1.0, 0.0
    for action in actions.get("splits", []):
        if str(session.day) < action["execution_date"] <= str(session.next_day):
            ratio *= action["split_to"] / action["split_from"]
    for action in actions.get("dividends", []):
        if str(session.day) < action["ex_dividend_date"] <= str(session.next_day):
            if ratio != 1:
                raise ValueError("RECONCILE_SIMULTANEOUS_SPLIT_AND_DIVIDEND")
            cash += action["cash_amount"]
    gross = split_return(entry_mid, exit_mid, ratio, cash)
    net = split_return(entry, exit_price, ratio, cash)
    return {"entry_time": pd.Timestamp(entry_time), "label_end": pd.Timestamp(exit_end),
            "entry_price": entry, "exit_price": exit_price, "next_open": next_open,
            "target_return": gross, "target_net_return": net,
            "target_gap": split_return(entry_mid, next_open, ratio, cash),
            "target_intraday": (exit_mid*ratio+cash) / (next_open*ratio+cash) - 1,
            "cost": gross-net, "forecast_basis": "GROSS_RETURN_MINUS_EXECUTION_COST",
            "spread_bps_assumption": spread_bps, "slippage_bps_assumption": slippage_bps}
