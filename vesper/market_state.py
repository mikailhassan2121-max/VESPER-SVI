"""Execution-time evidence is kept separate from prediction-time features."""
import numpy as np
import pandas as pd

from vesper.provider import timestamp_ms


def enrich_candidates(frame, quotes, luld, risk_records, now, max_status_age=60):
    out = frame.copy()
    records = {row["ticker"]: row for row in risk_records}
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
        status = records.get(ticker)
        if status and 0 <= (now - pd.Timestamp(status["available_at"])).total_seconds() <= max_status_age:
            for key in ("halted", "binary_event"):
                if isinstance(status.get(key), bool):
                    out.at[index, key] = status[key]
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
