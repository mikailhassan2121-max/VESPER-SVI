"""Shared historical/live transformations; all timestamps are UTC and availability-aware."""
import numpy as np
import pandas as pd

FEATURES = ["return_open", "return_5m", "return_15m", "return_30m", "return_60m",
            "late_velocity", "vwap_distance", "range_position", "intraday_vol", "rvol",
            "volume_acceleration", "return_1d", "return_5d", "return_20d", "vol_20d",
            "median_dollar_volume", "relative_30m", "sector_relative", "market_breadth",
            "dispersion", "momentum_percentile", "rvol_percentile", "news_count", "news_missing"]


def cutoff_rows(frame, cutoff):
    if frame.empty:
        return frame.copy()
    cutoff = pd.Timestamp(cutoff)
    if cutoff.tzinfo is None:
        raise ValueError("Timezone required")
    for column in ("end", "available_at"):
        if column not in frame:
            raise ValueError(f"Missing availability column: {column}")
    result = frame[(frame.end <= cutoff) & (frame.available_at <= cutoff)].copy()
    return result.sort_values(["end", "available_at"], kind="stable").drop_duplicates(["ticker", "end"], keep="last")


def intraday(frame, cutoff, session_open):
    frame = cutoff_rows(frame, cutoff)
    frame = frame[frame.end >= session_open].copy()
    if frame.empty:
        return pd.DataFrame()
    prices = frame[["open", "high", "low", "close", "vwap"]]
    frame["invalid"] = (~np.isfinite(prices).all(axis=1) | (prices <= 0).any(axis=1) |
                        ~np.isfinite(frame.volume) | (frame.volume < 0) | (frame.high < frame.low))
    frame["weighted"] = frame.vwap*frame.volume
    frame["log_return"] = np.log(frame.close.where(frame.close > 0)).groupby(frame.ticker).diff()
    grouped = frame.groupby("ticker", sort=False)
    first, last = grouped.first(), grouped.last()
    totals = grouped.volume.sum()
    valid = (first.end < pd.Timestamp(session_open)+pd.Timedelta(minutes=1)) & ~grouped.invalid.any() & (totals > 0)
    out = pd.DataFrame(index=first.index)
    out["price"], out["last_bar"] = last.close, last.end
    out["return_open"] = last.close/first.open-1
    out["vwap_distance"] = last.close/(grouped.weighted.sum()/totals)-1
    high, low = grouped.high.max(), grouped.low.min()
    out["range_position"] = ((last.close-low)/(high-low)).where(high > low, .5)
    out["intraday_vol"] = grouped.log_return.std()
    out["volume_so_far"] = totals
    for minutes in (5, 15, 30, 60):
        prior = frame[frame.end <= pd.Timestamp(cutoff)-pd.Timedelta(minutes=minutes)].groupby("ticker").close.last()
        out[f"return_{minutes}m"] = last.close/prior-1
    out["late_velocity"] = out.return_5m-out.return_15m/3
    recent = frame[frame.end > pd.Timestamp(cutoff)-pd.Timedelta(minutes=5)].groupby("ticker").volume.sum()
    previous = frame[(frame.end <= pd.Timestamp(cutoff)-pd.Timedelta(minutes=5)) &
                     (frame.end > pd.Timestamp(cutoff)-pd.Timedelta(minutes=10))].groupby("ticker").volume.sum()
    out["volume_acceleration"] = recent.reindex(out.index, fill_value=0)/previous.where(previous > 0)
    return out[valid].reset_index()


def daily_features(frame, cutoff):
    frame = cutoff_rows(frame, cutoff).copy()
    if frame.empty:
        return pd.DataFrame()
    grouped = frame.groupby("ticker", sort=False)
    out = pd.DataFrame(index=grouped.size().index)
    last = grouped.close.last()
    for days in (1, 5, 20):
        frame[f"lag_{days}"] = grouped.close.shift(days)
        prior = frame.groupby("ticker").tail(1).set_index("ticker")[f"lag_{days}"]
        out[f"return_{days}d"] = last/prior-1
    frame["daily_return"] = grouped.close.pct_change(fill_method=None)
    frame["dollar_volume"] = frame.close*frame.volume
    recent = frame.groupby("ticker").tail(20).groupby("ticker")
    out["vol_20d"] = recent.daily_return.std()
    out["median_dollar_volume"] = recent.dollar_volume.median().where(grouped.size() >= 20)
    return out.reset_index()


def build_features(minutes, daily, profiles, cutoff, session_open, sectors=None, news=None):
    result = intraday(minutes, cutoff, session_open)
    if result.empty:
        return result
    historical = daily_features(daily, session_open - pd.Timedelta(microseconds=1))
    if historical.empty:
        for col in ("return_1d", "return_5d", "return_20d", "vol_20d", "median_dollar_volume"):
            result[col] = np.nan
    else:
        result = result.merge(historical, on="ticker", how="left", validate="one_to_one")
    result["rvol"] = result.volume_so_far / result.ticker.map(profiles).replace(0, np.nan)
    benchmark = result.loc[result.ticker == "SPY", "return_30m"]
    result["relative_30m"] = result.return_30m - (benchmark.iloc[0] if len(benchmark) else np.nan)
    result["sector"] = result.ticker.map(sectors or {})
    result["sector_relative"] = result.return_30m - result.groupby("sector").return_30m.transform("mean")
    result["market_breadth"] = (result.return_open > 0).mean()
    result["dispersion"] = result.return_open.std()
    result["momentum_percentile"] = result.return_30m.rank(pct=True)
    result["rvol_percentile"] = result.rvol.rank(pct=True)
    result["news_missing"] = float(news is None)
    result["news_count"] = np.nan if news is None else 0.0
    if news is not None:
        counts = {}
        for article in news:
            if (pd.Timestamp(article["published_utc"]) <= cutoff and
                    pd.Timestamp(article["available_at"]) <= cutoff):
                for ticker in article.get("tickers", []):
                    counts[ticker] = counts.get(ticker, 0) + 1
        result["news_count"] = result.ticker.map(counts).fillna(0)
    return result


def normalize_bars(raw, ticker, availability_lag_seconds=0):
    """Historical bars use declared latency, not today's retrieval timestamp.

    Historical revised aggregates cannot prove original publication availability;
    dataset provenance must disclose this limitation before model promotion.
    """
    if not raw:
        return pd.DataFrame(columns=["ticker", "end", "available_at", "open", "high", "low", "close", "volume", "vwap"])
    out = pd.DataFrame(raw).rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume", "vw": "vwap"})
    out["ticker"] = ticker
    out["end"] = pd.to_datetime(out.t, unit="ms", utc=True) + pd.Timedelta(minutes=1) - pd.Timedelta(milliseconds=1)
    out["available_at"] = out.end + pd.Timedelta(seconds=availability_lag_seconds)
    return out
