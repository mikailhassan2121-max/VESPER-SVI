"""Execution-time evidence is kept separate from prediction-time features."""
import numpy as np
import pandas as pd

from vesper.provider import timestamp_ms


def enrich_candidates(frame, quotes, luld, risk_records, now, max_status_age=60, trades=None):
    out = frame.copy()
    records = {}
    for record in risk_records:
        records.setdefault(record["ticker"], []).append(record)
    for column in ("ask", "bid", "bid_size", "ask_size", "quote_age", "bar_age"):
        out[column] = np.nan
    out["halted"] = pd.Series(None, index=out.index, dtype=object)
    out["binary_event"] = pd.Series(None, index=out.index, dtype=object)
    out["luld_risk"] = pd.Series(None, index=out.index, dtype=object)
    for index, row in out.iterrows():
        ticker = row.ticker
        if pd.notna(row.get("last_bar")):
            out.loc[index, "bar_age"] = (now - pd.Timestamp(row.last_bar)).total_seconds()
        quote = quotes.get(ticker)
        if quote:
            received = pd.Timestamp(quote["received_at"])
            age = now.timestamp() - timestamp_ms(quote["t"]) / 1000
            if received <= now:
                out.loc[index, ["ask", "bid", "bid_size", "ask_size", "quote_age"]] = [
                    quote["ap"], quote["bp"], quote["bs"], quote["as"], age]
        statuses = records.get(ticker, [])
        trade = (trades or {}).get(ticker)
        if trade and quote and pd.Timestamp(trade["received_at"]) <= now:
            trade_age = now.timestamp()-timestamp_ms(trade["t"])/1000
            if 0 <= trade_age <= 3 and float(trade.get("p", 0)) > 0 and 0 <= out.at[index, "quote_age"] <= 3:
                out.at[index, "halted"] = False
        for key in ("halted", "binary_event"):
            evidence = [status[key] for status in statuses
                        if isinstance(status.get(key), bool) and
                        0 <= (now-pd.Timestamp(status["available_at"])).total_seconds() <= max_status_age]
            if evidence:
                # A fresh all-clear from another source cannot erase a known risk.
                out.at[index, key] = any(evidence)
        band = luld.get(ticker)
        if band and pd.Timestamp(band["received_at"]) <= now:
            age = now.timestamp() - timestamp_ms(band["t"]) / 1000
            if 0 <= age <= max_status_age and quote and 0 < band["l"] < band["h"]:
                out.at[index, "luld_risk"] = bool(quote["ap"] >= band["h"] * .995 or
                                                  quote["bp"] <= band["l"] * 1.005)
            # A known halt veto remains useful even without complete exchange-wide coverage.
            if 17 in band.get("i", []):
                out.at[index, "halted"] = True
    return out
