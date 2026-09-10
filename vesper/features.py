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
    frame = frame[frame.end >= session_open]
    records = []
    for ticker, bars in frame.groupby("ticker", sort=False):
        if bars.iloc[0].end >= pd.Timestamp(session_open) + pd.Timedelta(minutes=1):
            # A stream started late cannot redefine the regular-session opening price.
            continue
        if (bars[["open", "high", "low", "close", "vwap"]] <= 0).any().any():
            continue
        if (bars.volume < 0).any() or (bars.high < bars.low).any() or bars.volume.sum() <= 0:
            continue
        last = bars.iloc[-1]
        total_volume = bars.volume.sum()
        vwap = (bars.vwap * bars.volume).sum() / total_volume
        high, low = bars.high.max(), bars.low.min()
        row = {"ticker": ticker, "price": last.close, "last_bar": last.end,
               "return_open": last.close / bars.iloc[0].open - 1,
               "vwap_distance": last.close / vwap - 1,
               "range_position": (last.close - low) / (high - low) if high > low else .5,
               "intraday_vol": np.log(bars.close).diff().std(), "volume_so_far": total_volume}
        for minutes in (5, 15, 30, 60):
            prior = bars[bars.end <= pd.Timestamp(cutoff) - pd.Timedelta(minutes=minutes)]
            row[f"return_{minutes}m"] = last.close / prior.iloc[-1].close - 1 if len(prior) else np.nan
        row["late_velocity"] = row["return_5m"] - row["return_15m"] / 3
        recent = bars[bars.end > pd.Timestamp(cutoff) - pd.Timedelta(minutes=5)].volume.sum()
        previous = bars[(bars.end <= pd.Timestamp(cutoff) - pd.Timedelta(minutes=5)) &
                        (bars.end > pd.Timestamp(cutoff) - pd.Timedelta(minutes=10))].volume.sum()
        row["volume_acceleration"] = recent / previous if previous > 0 else np.nan
        records.append(row)
    return pd.DataFrame(records)


def daily_features(frame, cutoff):
    frame = cutoff_rows(frame, cutoff)
    records = []
    for ticker, bars in frame.groupby("ticker"):
        row = {"ticker": ticker}
        for days in (1, 5, 20):
            row[f"return_{days}d"] = bars.close.iloc[-1] / bars.close.iloc[-days-1] - 1 if len(bars) > days else np.nan
        row["vol_20d"] = bars.close.pct_change().tail(20).std()
        row["median_dollar_volume"] = (bars.close * bars.volume).tail(20).median() if len(bars) >= 20 else np.nan
        records.append(row)
    return pd.DataFrame(records)


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
