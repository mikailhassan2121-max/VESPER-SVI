import math

import pandas as pd


def decide(ranked, context, settings):
    invalid = list(context.get("failures", []))
    if context.get("mode") != "LIVE":
        invalid.append("NON_LIVE_MODE")
    if context.get("entitlement") != "REALTIME_FULL_MARKET":
        invalid.append("FULL_MARKET_REALTIME_UNPROVEN")
    if not context.get("model_production"):
        invalid.append("PRODUCTION_MODEL_UNAVAILABLE")
    if context.get("coverage", 0) < settings.min_coverage:
        invalid.append("UNIVERSE_COVERAGE_INCOMPLETE")
    if not context.get("signal_window"):
        invalid.append("OUTSIDE_SIGNAL_WINDOW")
    if context.get("paused", False):
        invalid.append("FORWARD_PERFORMANCE_PAUSE")
    if invalid:
        return {"decision": "NO SIGNAL — SYSTEM INVALID", "reasons": sorted(set(invalid)), "winner": None}
    if ranked.empty:
        return {"decision": "NO TRADE", "reasons": ["NO_ELIGIBLE_CANDIDATES"], "winner": None}
    row = ranked.iloc[0]
    reasons = []
    for name in ("score", "expected_return", "expected_excess", "uncertainty", "q05", "ask", "bid",
                 "quote_age", "bar_age", "median_dollar_volume", "bid_size", "ask_size"):
        try:
            valid = name in row and math.isfinite(float(row[name]))
        except (TypeError, ValueError):
            valid = False
        if not valid:
            reasons.append("MISSING_OR_INVALID_" + name.upper())
    if reasons:
        return {"decision": "NO SIGNAL — SYSTEM INVALID", "reasons": reasons, "winner": None, "candidate": row.ticker}
    if min(row.ask, row.bid) <= 0:
        return {"decision": "NO SIGNAL — SYSTEM INVALID", "reasons": ["INVALID_QUOTE_PRICE"], "winner": None, "candidate": row.ticker}
    spread = (row.ask - row.bid) / ((row.ask + row.bid) / 2) * 10000
    half_spread = spread / 20000
    slip = settings.slippage_bps_each_side / 10000
    midpoint = (row.ask+row.bid)/2
    expected_exit = midpoint*(1+row.expected_return)*(1-half_spread-slip)
    estimated_entry = row.ask*(1+slip)
    net_return = expected_exit/estimated_entry-1
    cost = row.expected_return-net_return
    checks = {"LOW_SCORE": row.score < settings.min_score,
              "NO_NET_EDGE": net_return <= settings.min_net_return,
              "NO_EXCESS_EDGE": row.expected_excess - cost <= 0,
              "DOWNSIDE": row.q05 < -settings.max_downside,
              "CROSSED_QUOTE": spread < 0,
              "WIDE_QUOTE": spread > settings.max_spread_bps,
              "STALE_QUOTE": not 0 <= row.quote_age <= settings.max_quote_age,
              "STALE_BAR": not 0 <= row.bar_age <= settings.max_bar_age,
              "LOW_LIQUIDITY": row.median_dollar_volume < settings.min_dollar_volume,
              "LOW_PRICE": row.bid < settings.min_price,
              "NO_DEPTH": min(row.bid_size, row.ask_size) <= 0,
              "HALT_STATUS_UNKNOWN": pd.isna(row.get("halted")),
              "HALTED": not pd.isna(row.get("halted")) and bool(row.get("halted")),
              "CATALYST_STATUS_UNKNOWN": pd.isna(row.get("binary_event")),
              "BINARY_EVENT": not pd.isna(row.get("binary_event")) and bool(row.get("binary_event")),
              "LULD_STATUS_UNKNOWN": pd.isna(row.get("luld_risk")),
              "LULD_RISK": not pd.isna(row.get("luld_risk")) and bool(row.get("luld_risk"))}
    reasons.extend(name for name, fails in checks.items() if fails)
    if reasons:
        missing = {"HALT_STATUS_UNKNOWN", "CATALYST_STATUS_UNKNOWN", "LULD_STATUS_UNKNOWN",
                   "STALE_QUOTE", "STALE_BAR", "CROSSED_QUOTE"}
        outcome = "NO SIGNAL — SYSTEM INVALID" if missing.intersection(reasons) else "NO TRADE"
        return {"decision": outcome, "reasons": reasons, "candidate": row.ticker, "winner": None}
    max_entry = expected_exit / ((1+slip)*(1+settings.min_net_return))
    return {"decision": "BUY", "winner": row.ticker, "entry": float(row.ask), "max_entry": float(max_entry),
            "expected_return": float(row.expected_return), "expected_net_return": float(net_return),
            "score": float(row.score), "reasons": []}


def rank_predictions(frame, slippage_bps=10):
    out = frame.copy()
    out["net_utility"] = out.expected_excess - 2 * slippage_bps / 10000 - .1 * out.uncertainty
    # Score is a monotone utility transform, explicitly not a calibrated probability.
    out["score"] = (50 + out.net_utility * 1000).clip(0, 100)
    return out.sort_values(["net_utility", "ranking_prediction", "ticker"], ascending=[False, False, True])
