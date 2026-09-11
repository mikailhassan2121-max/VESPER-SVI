"""Live readiness requires current, independently observable evidence."""
import pandas as pd

from vesper.provider import timestamp_ms


def clock_check(status, request_start, received):
    server = pd.Timestamp(status["serverTime"])
    if server.tzinfo is None:
        raise ValueError("Provider clock lacks timezone")
    rtt = (received-request_start).total_seconds()
    midpoint = request_start+(received-request_start)/2
    offset = (server-midpoint).total_seconds()
    return {"offset_seconds": offset, "roundtrip_seconds": rtt,
            "valid": 0 <= rtt <= 2 and abs(offset) <= 2}


def feed_evidence(health, stream_bars, quotes, eligible, now, settings):
    current = []
    moving = 0
    for ticker in eligible:
        events = stream_bars.get(ticker, [])
        fresh = [e for e in events if 0 <= now.timestamp()-timestamp_ms(e["e"])/1000 <= settings.max_bar_age]
        if fresh:
            current.append(ticker)
        if len({e["e"] for e in fresh}) >= 2:
            moving += 1
    coverage = len(current)/len(eligible) if eligible else 0
    fresh_quotes = sum(1 for ticker, quote in quotes.items() if ticker in eligible and
                       0 <= now.timestamp()-timestamp_ms(quote["t"])/1000 <= settings.max_quote_age and
                       quote.get("ap", 0) >= quote.get("bp", 0) > 0)
    full = health["state"] == "HEALTHY" and len(eligible) >= 100 and coverage >= settings.min_coverage and moving >= 5 and fresh_quotes >= 5
    state = "REALTIME_FULL_MARKET" if full else health.get("entitlement", "UNAVAILABLE")
    if state == "REALTIME_FULL_MARKET" and not full:
        state = "REALTIME_LIMITED"
    return {"entitlement": state, "stream_coverage": coverage, "moving_tickers": moving,
            "fresh_quote_tickers": fresh_quotes, "eligible": len(eligible)}
