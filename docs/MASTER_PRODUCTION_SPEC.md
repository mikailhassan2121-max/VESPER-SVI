# VESPER — MASTER PRODUCTION BUILD PROMPT

You are Claude Code.

You are acting as the principal quantitative researcher, machine-learning engineer, market-data engineer, reliability engineer, and production owner for a completely new repository called:

# VESPER

Build it from scratch.

Do not assume or import any previous VESPER implementation.

---

# 1. WHAT VESPER IS

VESPER is a:

> REAL-TIME U.S. EQUITY CROSS-SECTIONAL NEXT-TRADING-DAY SIGNAL ENGINE.

Its job is to analyze the entire eligible U.S. stock universe before the market closes and identify the SINGLE stock with the strongest risk-adjusted probability of outperforming during the next trading session.

Default signal time:

```text
3:50 PM America/New_York
```

on normal U.S. trading days.

The basic trade concept is:

```text
~3:50 PM TODAY
↓
VESPER ANALYZES THE FULL MARKET
↓
SELECTS ONE BEST LONG CANDIDATE
↓
USER BUYS MANUALLY
↓
HOLD OVERNIGHT
↓
HOLD THROUGH NEXT TRADING SESSION
↓
EXIT NEAR NEXT SESSION'S CLOSE
```

VESPER is LONG-ONLY in v1.

No short selling.

No options.

No automatic brokerage execution.

---

# 2. EXACT FORECASTING TARGET

VESPER should NOT ambiguously predict:

> "stock will go up tomorrow."

Define an explicit target.

Primary target:

> Return from a realistic executable entry shortly after today's VESPER signal to a realistic executable exit near the following regular trading session's close.

Default modeling target:

```text
ENTRY:
approximately 15:50–15:52 ET on signal day

EXIT:
approximately 15:50–15:58 ET on next regular trading day
```

Define:

```text
R_next =
    ExitPrice_next_session
    /
    EntryPrice_signal_day
    - 1
```

Also calculate:

```text
ExcessReturn_vs_SPY
ExcessReturn_vs_sector
```

The goal is NOT necessarily to select the stock with the largest raw expected return if it has insane uncertainty.

The primary ranking objective should be approximately:

> highest credible risk-adjusted expected next-session excess return that remains realistically executable.

---

# 3. NO CLAIM OF CERTAINTY

VESPER cannot know with certainty which stock WILL perform best.

It must estimate:

```text
expected_return
expected_excess_return
probability_positive
probability_outperform_spy
probability_top_decile
probability_top_1_percent
expected_downside
prediction_uncertainty
```

Then rank the universe.

The VESPER winner means:

> highest-ranked opportunity according to the live model.

Never display:

```text
GUARANTEED WINNER
```

or claim certainty.

---

# 4. THE UNIVERSE IS NOT "MILLIONS OF U.S. STOCKS"

Do not fabricate universe size.

VESPER should dynamically identify the entire CURRENT ELIGIBLE U.S. STOCK UNIVERSE.

This will typically be thousands of securities, not millions.

Pull current reference data dynamically.

Do not maintain a manually typed ticker list.

Initially prioritize:

```text
NYSE
NASDAQ
NYSE American
other legitimate U.S. exchange-listed common stocks
```

Optionally support ADRs separately.

Do not include every random:

- ETF
- warrant
- right
- preferred stock
- unit
- bond
- OTC shell
- inactive ticker
- delisted stock

unless explicitly configured.

---

# 5. MANUAL SIGNALS ONLY

VESPER v1 does NOT automatically trade.

Forbidden:

```text
place_order
buy_stock
sell_stock
submit_order
cancel_order
modify_order
broker_execution
```

Do not merely hide automatic execution behind a disabled button.

Do not build brokerage order placement in v1.

VESPER analyzes and signals.

The user manually executes.

Add a static test verifying the application has no live order-execution path.

---

# 6. CORE OBJECTIVE

Every trading day VESPER should answer:

> Out of every sufficiently tradable U.S. stock available at approximately 3:50 PM, which ONE has the best credible probability distribution for return from now through the next trading day's close?

Then output:

```text
VESPER SIGNAL
BUY: XYZ
```

with the entire reasoning stack.

---

# 7. NO DEAD SIGNALER

VESPER cannot finish as a project that only:

- downloads data
- shows charts
- ranks historical stocks
- displays a dashboard
- says training
- says collecting samples
- says model unavailable
- runs a notebook
- has mock predictions

At approximately the target time on a real trading day it must process LIVE data and produce:

```text
TOP PICK
```

or:

```text
NO TRADE
```

from real production inputs.

NO TRADE is legitimate when the market offers no sufficiently strong candidate.

However the program must still show a changing live leaderboard.

Never manufacture a winner to satisfy validation.

---

# 8. RESEARCH CURRENT DATA APIS FIRST

Before implementation, research CURRENT official documentation.

Do not blindly implement endpoints from old tutorials.

Evaluate providers capable of supplying:

- ticker reference universe
- historical daily bars
- historical minute bars
- real-time minute aggregates
- preferably second aggregates
- NBBO quotes
- trades
- LULD status
- splits
- dividends
- ticker changes
- delistings
- corporate actions
- market status
- holidays
- news
- filings where useful
- fundamentals where useful

Potential providers include services such as:

```text
Massive
Databento
Alpaca market data
other legitimate professional providers
```

Choose the strongest practical provider architecture based on current APIs and available credentials.

Prefer one coherent primary source with fallback adapters rather than 15 fragile scrapers.

---

# 9. REAL-TIME DATA MEANS REAL-TIME

A 15-minute delayed feed is NOT acceptable for a 3:50 PM signal.

Detect provider entitlement.

Expose:

```text
REALTIME_FULL_MARKET
REALTIME_LIMITED
DELAYED
UNAVAILABLE
```

If the available data is delayed:

```text
LIVE SIGNALS DISABLED
```

with the exact reason.

Never label delayed data as live.

---

# 10. CONSOLIDATED MARKET DATA

Prefer full consolidated U.S. market data / SIP-quality coverage where available.

Do not unknowingly base the entire U.S. market ranking on one exchange's partial feed.

For shortlisted securities VESPER should ideally have:

```text
NBBO
trades
minute bars
volume
spread
bid size
ask size
```

---

# 11. WINDOWS-FIRST

Primary target:

```text
Windows 11
Python 3.12+
PowerShell
local machine
```

Create:

```text
SETUP_VESPER.ps1
RUN_VESPER.ps1
STOP_VESPER.ps1
CHECK_VESPER.ps1
TRAIN_VESPER.ps1
VALIDATE_LIVE.ps1
```

Dashboard:

```text
http://127.0.0.1:8787
```

Docker must not be mandatory.

---

# 12. STACK

Prefer:

```text
Python 3.12+
asyncio
aiohttp/httpx
websockets
FastAPI
Uvicorn
Pydantic v2
numpy
pandas/polars
scipy
scikit-learn
LightGBM
XGBoost and/or CatBoost where justified
Optuna only where appropriate
SQLite
DuckDB and/or Parquet for research datasets
structured logging
pytest
```

GPU should not be required.

Do not automatically build a giant neural network because it sounds sophisticated.

Tabular gradient-boosted models are strong candidates for this type of problem.

---

# 13. ARCHITECTURE

Suggested structure:

```text
VESPER/
│
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
│
├── SETUP_VESPER.ps1
├── RUN_VESPER.ps1
├── STOP_VESPER.ps1
├── CHECK_VESPER.ps1
├── TRAIN_VESPER.ps1
├── VALIDATE_LIVE.ps1
│
├── vesper/
│   ├── config.py
│   ├── clock.py
│   ├── models.py
│   ├── supervisor.py
│   │
│   ├── calendar/
│   │   ├── market_calendar.py
│   │   └── sessions.py
│   │
│   ├── universe/
│   │   ├── builder.py
│   │   ├── eligibility.py
│   │   ├── point_in_time.py
│   │   └── corporate_actions.py
│   │
│   ├── providers/
│   │   ├── primary.py
│   │   ├── websocket.py
│   │   ├── historical.py
│   │   ├── reference.py
│   │   ├── news.py
│   │   ├── filings.py
│   │   └── health.py
│   │
│   ├── features/
│   │   ├── daily.py
│   │   ├── intraday.py
│   │   ├── close_pressure.py
│   │   ├── momentum.py
│   │   ├── volume.py
│   │   ├── volatility.py
│   │   ├── microstructure.py
│   │   ├── relative_strength.py
│   │   ├── sector.py
│   │   ├── catalyst.py
│   │   ├── news.py
│   │   ├── market_regime.py
│   │   └── cross_sectional.py
│   │
│   ├── modeling/
│   │   ├── dataset.py
│   │   ├── labels.py
│   │   ├── ranking.py
│   │   ├── regression.py
│   │   ├── classifier.py
│   │   ├── gap_model.py
│   │   ├── nextday_model.py
│   │   ├── ensemble.py
│   │   ├── uncertainty.py
│   │   ├── calibration.py
│   │   └── artifacts.py
│   │
│   ├── ranking/
│   │   ├── coarse.py
│   │   ├── shortlist.py
│   │   ├── final_rank.py
│   │   └── decision.py
│   │
│   ├── risk/
│   │   ├── liquidity.py
│   │   ├── gap_risk.py
│   │   ├── sizing.py
│   │   └── vetoes.py
│   │
│   ├── signals/
│   │   ├── engine.py
│   │   ├── lifecycle.py
│   │   ├── monitoring.py
│   │   └── dedupe.py
│   │
│   ├── storage/
│   │   ├── database.py
│   │   ├── parquet.py
│   │   └── migrations.py
│   │
│   ├── analytics/
│   │   ├── backtest.py
│   │   ├── walkforward.py
│   │   ├── performance.py
│   │   └── attribution.py
│   │
│   ├── alerts/
│   │   ├── telegram.py
│   │   └── console.py
│   │
│   ├── api/
│   │   └── server.py
│   │
│   └── ui/
│       └── ...
│
├── models/
├── data/
├── logs/
└── tests/
```

Modify where appropriate.

---

# 14. MARKET CALENDAR FIRST

Never assume every weekday has a normal 4:00 PM close.

Support:

- weekends
- U.S. market holidays
- early-close sessions
- unusual closures

Define:

```text
signal_time =
    regular_session_close - 10 minutes
```

Therefore:

Normal session:

```text
4:00 PM close
→ 3:50 PM signal
```

Early close:

```text
1:00 PM close
→ 12:50 PM signal
```

Do NOT issue a 3:50 signal after an early-close market already closed.

---

# 15. NEXT TRADING DAY

Calculate next trading session from the actual exchange calendar.

Friday:

```text
next session = Monday
```

unless Monday is a holiday.

Never calculate:

```text
today + 1 calendar day
```

blindly.

---

# 16. POINT-IN-TIME UNIVERSE

This is mandatory.

Historical backtests must reconstruct which stocks actually existed and were eligible ON THAT HISTORICAL DATE.

Do NOT use today's ticker universe to test 2022.

That creates:

```text
SURVIVORSHIP BIAS
```

Include:

- delisted stocks
- historical ticker changes
- IPO dates
- merger exits
- splits
- corporate actions

when constructing historical samples.

---

# 17. CORPORATE ACTIONS

Correct prices/returns appropriately for:

```text
stock splits
reverse splits
dividends where relevant
ticker changes
mergers
spin-offs
```

Do not mistake a 10-for-1 split for a -90% crash.

Use point-in-time corporate-action information for historical training wherever possible.

---

# 18. DEFAULT LIVE ELIGIBILITY

Start from all active U.S. common stocks.

Apply reasonable tradability rules.

Suggested configurable defaults:

```text
MIN_PRICE = $2.00
MIN_MEDIAN_DOLLAR_VOLUME_20D = $10M
MAX_NBBO_SPREAD_BPS = 75
```

Also reject:

```text
OTC
inactive
halted
obvious shells
warrants
rights
units
preferred shares
broken reference data
```

Do NOT automatically require mega-cap status.

Small/mid-cap stocks may contain substantial edge.

---

# 19. LIQUIDITY TIERS

Instead of one crude liquidity filter classify:

```text
TIER_1
TIER_2
TIER_3
UNTRADEABLE
```

using:

- dollar volume
- spread
- quote depth
- price
- market cap where available
- trade frequency

Allow model confidence requirements to increase as liquidity decreases.

---

# 20. STAGED UNIVERSE PROCESSING

Do NOT wait until exactly 3:50 and then download the entire stock market.

Create a staged pipeline.

Example:

## BEFORE MARKET

Build today's eligible universe.

Calculate:

- daily features
- historical features
- fundamentals
- recent news context
- known events

## 3:00 PM

Calculate preliminary score for every eligible ticker.

## 3:30 PM

Produce top approximately:

```text
500
```

candidates.

## 3:40 PM

Increase high-frequency analysis on approximately:

```text
100–200
```

candidates.

## 3:47 PM

Produce approximately:

```text
TOP 25–50
```

## 3:49:45 PM

Run final features/model inference.

## ~3:50 PM

Issue final ranking and signal.

Numbers are configurable.

Optimize architecture based on actual feed capabilities.

---

# 21. WILDCARD MARKET STREAMS

If the data provider supports safe wildcard streaming of minute aggregates across all tickers, use it.

Do not create 8,000 individual HTTP polling loops.

Prefer:

```text
one/few efficient streams
↓
local aggregation
↓
cross-sectional state
```

Use backpressure and bounded queues.

---

# 22. INPUT CUTOFF

This is CRITICAL.

For a signal timestamp of:

```text
15:50:00
```

the model may ONLY consume information known before the configured prediction cutoff.

For example:

```text
FEATURE_CUTOFF = 15:49:59.999
```

Do not accidentally use:

- the completed 3:50–3:51 bar
- the 4 PM close
- news published at 3:53
- final daily volume
- next-day data

to create the 3:50 prediction.

---

# 23. PRIMARY LABEL

For historical training define an executable entry benchmark.

Avoid simply using:

```text
3:50 exact last trade
```

if that would be unrealistic.

Example:

```text
entry_price =
    conservative VWAP / midpoint / ask-aware estimate
    from approximately 15:50–15:51
```

Target exit:

```text
exit_price =
    conservative executable estimate
    near next session's close
```

Then:

```text
target_return =
    exit_price / entry_price - 1
```

---

# 24. EXCESS-RETURN LABEL

Also compute:

```text
stock_return - SPY_return
```

over exactly the same horizon.

Also:

```text
stock_return - sector_benchmark_return
```

This helps distinguish:

> good stock prediction

from:

> entire market went up 3%.

---

# 25. DECOMPOSE THE FORECAST

This is extremely important.

The next-session return can be decomposed:

```text
TODAY 3:50
→
NEXT SESSION OPEN
→
NEXT SESSION CLOSE
```

Build separate forecasts for:

# MODEL A — OVERNIGHT GAP

Predict:

```text
entry_to_next_open_return
```

# MODEL B — NEXT-DAY CONTINUATION

Predict:

```text
next_open_to_next_close_return
```

# MODEL C — TOTAL

Predict:

```text
entry_to_next_close_return
```

Then ensemble them.

Different information drives overnight gaps and next-day continuation.

---

# 26. OVERNIGHT GAP MODEL

Potential features:

- late-day momentum
- late-day volume
- closing pressure
- unusual volume
- recent news
- recent filings
- earnings timing
- sector momentum
- market momentum
- volatility
- short-term reversal
- gap history
- liquidity
- after-hours propensity
- event risk

Output:

```text
expected_gap
p_gap_positive
gap_downside_quantile
```

---

# 27. NEXT-DAY INTRADAY MODEL

Predict next regular-session movement after the open.

Potential drivers:

- persistent momentum
- relative strength
- institutional accumulation proxy
- close location
- volume profile
- multi-day momentum
- volatility regime
- mean reversion
- sector leadership
- previous overnight behavior
- catalyst persistence

Output:

```text
expected_open_to_close
p_open_to_close_positive
```

---

# 28. TOTAL RETURN MODEL

Directly model:

```text
3:50 today → next close
```

Do NOT solely sum Models A and B.

Train a direct total-horizon model as another ensemble component.

---

# 29. CROSS-SECTIONAL RANK MODEL

This should be a central VESPER component.

Every training day should be treated as a group.

For each date:

```text
stock_1
stock_2
stock_3
...
stock_N
```

The model learns:

> Which stocks are likely to rank highest relative to their peers tomorrow?

Evaluate ranking approaches such as:

```text
LightGBM LambdaRank
XGBoost ranking
other appropriate learning-to-rank algorithms
```

Ranking is often more aligned with VESPER's goal than predicting every stock's exact return independently.

---

# 30. REGRESSION MODEL

Also predict:

```text
expected_return
```

using gradient-boosted regression.

Prefer robust targets/losses.

Extreme single-stock returns should not completely distort the model.

Consider:

```text
Huber
quantile
winsorized target for some model components
```

but always preserve actual returns for final evaluation.

---

# 31. CLASSIFICATION MODEL

Predict:

```text
P(return > 0)
P(outperform SPY)
P(top decile)
P(top 5%)
P(top 1%)
```

These probabilities provide useful complementary information.

---

# 32. QUANTILE MODELS

Estimate:

```text
5th percentile
25th percentile
median
75th percentile
95th percentile
```

of likely return.

This provides an explicit risk distribution.

A ticker with:

```text
expected +4%
5th percentile -18%
```

is fundamentally different from:

```text
expected +3%
5th percentile -4%
```

---

# 33. MODEL ENSEMBLE

Combine:

```text
cross-sectional rank model
return regression
overnight gap model
next-day continuation model
classification
quantile forecasts
selected rule-based features
```

into:

```text
VESPER_EXPECTED_RETURN
VESPER_EXPECTED_EXCESS_RETURN
VESPER_CONFIDENCE
VESPER_SCORE
```

Do not simply average everything equally.

Use forward/walk-forward evidence to determine model weights.

---

# 34. DAILY PRICE FEATURES

Calculate features such as:

```text
return_1d
return_2d
return_3d
return_5d
return_10d
return_20d
return_60d
```

Also:

```text
distance_20d_high
distance_52w_high
distance_20d_low
trend_slope
moving_average_distances
```

Do not rely on generic RSI/MACD alone.

---

# 35. INTRADAY FEATURES

Use information available before 3:50.

Examples:

```text
return_open_to_now
return_30m
return_60m
return_120m

return_5m
return_10m
return_15m
```

Also:

```text
high_of_day_distance
low_of_day_distance
VWAP_distance
intraday_range_position
```

---

# 36. CLOSING PRESSURE

This is one of the most important VESPER feature families.

Calculate:

```text
return_3pm_to_now
return_330_to_now
return_340_to_now
return_345_to_now

late_day_velocity
late_day_acceleration
```

Measure whether buyers are persistently pushing the stock into the close.

---

# 37. CLOSE LOCATION VALUE

Calculate:

```text
CLV =
(close_so_far - low_today)
/
(high_today - low_today)
```

with appropriate edge-case handling.

Stocks finishing near highs under strong volume may behave differently from those fading into the close.

---

# 38. RELATIVE VOLUME

Calculate:

```text
RVOL
```

against the stock's historical volume profile AT THE SAME TIME OF DAY.

Do NOT compare 3:45 accumulated volume directly against average full-day volume without adjustment.

Build minute-of-day historical volume curves.

Examples:

```text
volume_so_far /
expected_volume_by_15:45

last_30m_volume /
historical_last_30m_volume
```

---

# 39. VOLUME ACCELERATION

Features:

```text
volume_5m
volume_15m
volume_30m

volume_acceleration
trade_count_acceleration
dollar_volume_acceleration
```

Late institutional participation may matter.

---

# 40. VWAP FEATURES

Calculate:

```text
price_vs_vwap
vwap_slope
time_above_vwap
late_reclaim_of_vwap
late_loss_of_vwap
```

---

# 41. MICROSTRUCTURE

For the final shortlist use:

```text
NBBO spread
bid size
ask size
quote imbalance
trade imbalance
trade frequency
average trade size
spread trend
```

Do not try to process full tick-level order flow for every ticker all day if it is computationally unnecessary.

Use detailed microstructure on the shortlist.

---

# 42. RELATIVE STRENGTH

Measure relative performance against:

```text
SPY
QQQ
IWM
sector ETF
industry peers
```

over:

```text
5m
15m
30m
60m
1d
5d
20d
```

Cross-sectional relative strength should be central.

---

# 43. SECTOR MOMENTUM

Create live sector state.

Features include:

```text
sector_return_today
sector_return_30m
sector_breadth
sector_volume
sector_relative_strength
```

A strong stock inside a collapsing sector is different from a leader inside the market's strongest group.

---

# 44. INDUSTRY PEER FEATURES

When reliable industry classifications exist:

```text
stock_return - industry_mean
stock_volume_z - industry_mean
stock_momentum_rank_within_industry
```

---

# 45. MARKET REGIME

Classify broad environment:

```text
RISK_ON
RISK_OFF
TREND_UP
TREND_DOWN
CHOP
HIGH_VOL
LOW_VOL
PANIC
RELIEF_RALLY
```

Use:

- SPY
- QQQ
- IWM
- market breadth
- realized volatility
- optionally VIX when available

The optimal overnight stock characteristics may differ by regime.

---

# 46. MARKET BREADTH

Calculate:

```text
advancers / decliners
% above VWAP
% positive on day
new highs / lows
cross-sectional dispersion
```

This also helps determine how hard it is for a single-stock signal to overcome market direction.

---

# 47. CROSS-SECTIONAL DISPERSION

Measure distribution of stock returns today.

High dispersion can create better stock-selection opportunities.

Low dispersion may mean broad beta dominates.

Use:

```text
std_cross_section_returns
interquartile_range
tail_dispersion
```

---

# 48. VOLATILITY FEATURES

For every stock:

```text
realized_vol_5d
realized_vol_20d
intraday_realized_vol
overnight_vol
ATR-like measures
gap_volatility
```

Normalize expected return by risk.

---

# 49. IDIOSYNCRATIC VOLATILITY

Estimate residual volatility after accounting for:

```text
market
sector
```

This helps distinguish stock-specific moves from broad market noise.

---

# 50. BETA

Estimate rolling:

```text
market beta
sector beta
```

Use them as features and for risk decomposition.

Do not assume a +3% forecast in a 3% market rally represents alpha.

---

# 51. NEWS

Incorporate news available BEFORE the cutoff.

Potential features:

```text
news_count_1h
news_count_6h
news_count_24h
sentiment
sentiment_change
source_quality
ticker_relevance
novelty
```

Do not let a generic sentiment API directly dictate the signal.

It is one feature family.

---

# 52. NEWS TIMESTAMPS

Strictly enforce:

```text
published_at <= prediction_cutoff
```

No backtest may use news that became available after the 3:50 signal.

Store original publication timestamps.

---

# 53. SEC FILINGS / CORPORATE EVENTS

Potentially incorporate recent:

```text
8-K
Form 4
major filings
offerings
merger announcements
material corporate events
```

only when timestamped point-in-time data is available.

---

# 54. EARNINGS

Earnings are extremely important.

Determine whether the company is expected to report:

```text
after today's close
before tomorrow's open
during tomorrow's session
```

A stock with earnings tonight is a binary-event trade, not a normal momentum trade.

Create:

```text
EARNINGS_RISK
```

feature.

---

# 55. EARNINGS DEFAULT

Do NOT automatically rank earnings stocks highly merely because their expected volatility is high.

Require directional evidence.

Potential policy:

```text
normal model
+
special earnings model
+
large uncertainty penalty
```

If the model cannot reliably estimate direction:

```text
CATALYST_RISK_VETO
```

or substantial penalty.

---

# 56. OTHER BINARY CATALYSTS

Flag:

- FDA decisions
- trial results
- lawsuits
- merger votes
- financing announcements
- known scheduled events
- shareholder votes

where data is legitimately available.

Do not unknowingly treat event gambling as normal overnight momentum.

---

# 57. DILUTION / OFFERING RISK

Particularly for smaller stocks, detect recent:

```text
ATM
secondary offering
convertible financing
shelf registration
```

where point-in-time filing/news data supports it.

This should influence downside risk.

---

# 58. GAP HISTORY

For each stock calculate historical tendencies:

```text
average overnight gap
positive gap frequency
gap after strong close
gap after unusual volume
gap after news
```

Use only prior samples.

---

# 59. CONTINUATION HISTORY

Calculate conditional historical behavior such as:

> After this stock closes in the top 10% of its daily range with RVOL > 2 and +5% daily return, what has next-day behavior historically looked like?

Do not use crude tiny-sample statistics without shrinkage.

---

# 60. FEATURE NORMALIZATION

Many features should be expressed cross-sectionally.

For each trading date calculate:

```text
percentile rank
z-score
robust z-score
sector-relative rank
```

Example:

A 3% daily return means different things when:

```text
market average = +0.2%
```

versus:

```text
market average = +5%
```

---

# 61. MISSING DATA

Do not silently fill all missing values with zero.

Differentiate:

```text
real zero
missing
not applicable
provider failure
```

Add missingness flags where useful.

---

# 62. DATA QUALITY

Detect:

```text
bad split adjustment
impossible price
zero/negative price
massive erroneous spike
duplicate bars
timestamp disorder
stale quote
crossed NBBO
missing bars
```

Bad data must not generate the top signal.

---

# 63. LOOKAHEAD LEAKAGE

Create explicit automated tests.

No feature for a historical 3:50 prediction may use data after that timestamp.

Examples of forbidden leakage:

```text
official daily close
full-day volume
next day's open
future news
future fundamentals revision
post-close filing
future index membership
```

This is one of the highest priority tests.

---

# 64. SURVIVORSHIP-BIAS TEST

Write a test proving historical universes include securities that subsequently:

```text
delisted
merged
bankrupted
changed ticker
```

when they were valid at the time.

---

# 65. TRAIN/VALIDATION SPLITS

Do NOT randomly shuffle daily market data into train/test.

Use time-ordered validation.

Example:

```text
TRAIN:
past period

VALIDATE:
following period

TEST:
later unseen period
```

Use walk-forward evaluation.

---

# 66. PURGED TIME SPLITS

Avoid overlap contamination where necessary.

Do not let labels whose holding horizon extends into the next session leak information across folds.

Use appropriate embargo/purge logic.

---

# 67. WALK-FORWARD TRAINING

Example:

```text
Train through month N
↓
Predict month N+1
↓
Advance
↓
Retrain
↓
Predict next unseen block
```

Every test prediction must come from a model trained only on earlier information.

---

# 68. DO NOT OPTIMIZE ONE BACKTEST

Claude must not tune parameters repeatedly against the final test period.

Maintain:

```text
TRAIN
VALIDATION
LOCKED TEST
FORWARD LIVE
```

The locked test should remain truly unseen until major model selection is complete.

---

# 69. REALISTIC TRANSACTION COSTS

VESPER enters shortly before the close.

Backtests must account for:

```text
spread
slippage
price impact
entry delay
exit spread
```

Do not pretend fills occur exactly at a bar's midpoint.

---

# 70. EXECUTABLE ENTRY

At live signal time calculate:

```text
bid
ask
spread_bps
depth
recent volume
expected slippage
```

Provide:

```text
CURRENT ASK
MAX ENTRY
```

If price explodes above MAX ENTRY after alert:

```text
DO NOT CHASE
```

---

# 71. SIGNAL-TO-ENTRY LATENCY

Record:

```text
feature_cutoff_time
inference_start
inference_end
alert_time
```

Target fast enough that the 3:50 signal remains useful.

The full-market heavy computation should already have been staged beforehand.

---

# 72. LIQUIDITY-AWARE EXPECTED RETURN

Compute:

```text
raw_expected_return
-
estimated_transaction_cost
=
net_expected_return
```

Ranking should use executable/net return.

---

# 73. GAP RISK

Because the position is held overnight, stop-loss orders cannot protect against overnight gaps.

Explicitly model:

```text
P(gap < -2%)
P(gap < -5%)
P(gap < -10%)
expected_shortfall
```

where data supports stable estimation.

---

# 74. PREDICTION UNCERTAINTY

Return:

```text
expected_return
prediction_interval
model_disagreement
uncertainty_score
```

A model consensus of:

```text
+2.8%
+2.6%
+3.1%
```

is different from:

```text
+8%
-1%
+5%
```

even if their average is positive.

---

# 75. MODEL AGREEMENT

Calculate agreement among:

```text
rank model
gap model
next-day model
total-return model
classifier
```

Use disagreement as a confidence penalty.

---

# 76. VESPER SCORE

Generate:

```text
0–100
```

using approximately:

```text
expected net return
expected excess return
top-decile probability
model agreement
liquidity
late-day momentum
relative strength
volume confirmation
catalyst quality
downside risk
uncertainty
market regime compatibility
```

Suggested:

```text
< 65      NO TRADE
65–74     WATCH
75–84     B
85–92     A
93–100    A+
```

These are starting values only.

Tune from genuine walk-forward/forward results.

---

# 77. TOP PICK DECISION

At signal time rank every eligible stock.

Select:

```text
RANK #1
```

but only issue an actionable BUY when minimum quality criteria are met.

Example:

```text
VESPER_SCORE >= configured minimum
expected_net_return > 0
expected_excess_return > 0
liquidity acceptable
uncertainty acceptable
no hard veto
```

Otherwise:

```text
VESPER: NO TRADE TODAY
```

---

# 78. NO FORCED DAILY TRADE

Do NOT lower standards merely because the user expects one signal every day.

Some days have no strong opportunity.

Still display:

```text
#1 candidate
#2 candidate
...
```

and explain why #1 failed the actionable threshold.

---

# 79. TOP-20 LEADERBOARD

At 3:50 show:

```text
RANK
TICKER
PRICE
EXPECTED RETURN
EXPECTED EXCESS
P(POSITIVE)
P(TOP 10%)
P(TOP 1%)
DOWNSIDE
VESPER SCORE
STATE
```

This proves VESPER genuinely scanned the market.

---

# 80. SINGLE ACTIONABLE SIGNAL

Even though the leaderboard contains many stocks:

Default actionable output is ONE stock.

Do not spray:

```text
BUY these 17 stocks
```

VESPER's identity is:

> Find today's highest-conviction next-session opportunity.

---

# 81. SIGNAL FORMAT

Example structure:

```text
====================================================
                 VESPER LIVE SIGNAL
====================================================

DATE:
SIGNAL TIME:

BUY: XYZ
COMPANY:

GRADE: A
VESPER SCORE: 88/100

CURRENT:
$...

ENTRY RANGE:
$... – $...

MAX ENTRY:
$...

PLANNED HOLD:
Through next trading session

PLANNED EXIT WINDOW:
~3:50–3:58 PM ET next trading day

EXPECTED RETURN:
+...%

EXPECTED EXCESS VS SPY:
+...%

PROBABILITY POSITIVE:
...%

PROBABILITY OUTPERFORM SPY:
...%

PROBABILITY TOP DECILE:
...%

PREDICTION RANGE:
5th percentile:
Median:
95th percentile:

EXPECTED OVERNIGHT GAP:
...

EXPECTED NEXT-DAY OPEN→CLOSE:
...

TODAY:
Return:
RVOL:
Late-day momentum:
VWAP:
Relative strength:

LIQUIDITY:
Spread:
Dollar volume:

CATALYST:
...

MARKET REGIME:
...

WHY VESPER PICKED IT:
1.
2.
3.
4.

KEY RISKS:
1.
2.
3.

INVALIDATION BEFORE CLOSE:
...

DATA AGE:
...

MODEL VERSION:
...

====================================================
```

---

# 82. SHORT EXPLANATION

Alongside quantitative details generate a concise human-readable thesis such as:

```text
XYZ ranks #1 out of 4,812 eligible stocks because it combines top-decile late-day relative strength, 2.7× time-adjusted volume, strong sector leadership, persistent trading above VWAP, positive recent catalyst sentiment, and agreement across four of five next-session models.
```

Do not generate vague AI prose unrelated to actual features.

---

# 83. REASON CODES

Machine-readable positives:

```text
LATE_DAY_ACCELERATION
HIGH_RVOL
SECTOR_LEADER
MARKET_RELATIVE_STRENGTH
VWAP_STRENGTH
CLOSING_PRESSURE
POSITIVE_CATALYST
MODEL_CONSENSUS
TOP_DECILE_PROBABILITY
LOW_RELATIVE_SPREAD
```

Risks:

```text
EARNINGS_BINARY_RISK
HIGH_GAP_RISK
WIDE_SPREAD
LOW_DEPTH
MODEL_DISAGREEMENT
EXTREME_VOLATILITY
NEGATIVE_RECENT_FILING
DILUTION_RISK
SECTOR_WEAKNESS
```

---

# 84. PRE-SIGNAL LIVE BOARD

Starting around 3:30 PM show changing candidates:

```text
VESPER PRE-CLOSE RANKING

1 NVDA    87
2 ABC     85
3 XYZ     81
...
```

This ranking should genuinely change with live data.

---

# 85. RANK STABILITY

Track:

```text
rank_330
rank_340
rank_345
rank_348
rank_349
rank_350
```

A stock that jumps from #800 to #1 in 30 seconds may be fundamentally different from a persistent #1.

Use:

```text
rank_stability
rank_velocity
```

as features/confidence signals.

---

# 86. LAST-MINUTE PUMP DETECTION

Avoid blindly buying a stock that spikes vertically at 3:49:50.

Detect:

```text
parabolic move
liquidity vacuum
spread expansion
single-print distortion
news spike
LULD risk
```

A late spike may be momentum or exhaustion.

Model it rather than automatically chasing.

---

# 87. LULD / HALT HANDLING

Monitor:

```text
limit up / limit down
trading halt
resume
```

Never issue a normal BUY signal for a currently halted stock.

Apply special handling for stocks near LULD boundaries.

---

# 88. MAX ENTRY

Calculate a price beyond which expected edge disappears.

If:

```text
current = 20.00
max entry = 20.18
```

and the stock immediately jumps to:

```text
20.50
```

signal:

```text
VESPER SIGNAL INVALIDATED — DO NOT CHASE
```

---

# 89. POST-SIGNAL MONITOR

From signal until the close, monitor the winner.

Possible states:

```text
ACTIVE
DO_NOT_CHASE
CANCELLED
CLOSE_CONFIRMED
```

Cancel only for legitimate major changes such as:

```text
severe adverse news
halt
massive reversal
spread explosion
provider failure
model score collapse
```

Do not flip every 5 seconds.

---

# 90. AFTER-HOURS MONITORING

After market close, continue tracking the selected stock.

Track:

```text
after-hours price
after-hours volume
news
filings
```

Do not pretend this information was available at the original signal time.

It is used for post-entry monitoring, not backfilled into the prediction.

---

# 91. NEXT-DAY MONITORING

During the following trading session track:

```text
current return
MFE
MAE
SPY-relative return
sector-relative return
```

Default thesis remains hold to next close.

---

# 92. EMERGENCY RISK ALERT

Although the normal plan is hold to next close, VESPER may issue:

```text
EMERGENCY RISK ALERT
```

for events such as:

```text
fraud announcement
bankruptcy
trading suspension
unexpected offering
catastrophic earnings surprise
major legal/regulatory event
model-breaking news
```

It remains signal-only.

The user decides whether to exit.

---

# 93. DEFAULT EXIT

Default:

```text
EXIT near next trading day's close
```

Suggested monitoring window:

```text
15:50–15:58 ET
```

Do not model an impossible exact 4:00:00 execution unless specifically using a closing-auction strategy.

---

# 94. POSITION SIZING

VESPER may suggest a maximum risk size.

It must not tell the user that a high-confidence model makes the trade safe.

Use:

```text
prediction uncertainty
overnight volatility
gap risk
liquidity
```

for sizing.

Conservative starting framework:

```text
LOW CONFIDENCE:
no trade

B:
small

A:
moderate

A+:
still capped
```

Never use extreme leverage.

---

# 95. SHADOW TRADE

Every actionable live signal automatically creates a PAPER shadow trade.

Record:

```text
signal
signal timestamp
entry estimate
actual model forecast
confidence
next open
next close
MFE
MAE
SPY return
stock return
net return estimate
```

This is essential for unbiased forward validation.

---

# 96. IMMUTABLE SIGNALS

Once VESPER issues:

```text
BUY XYZ
```

preserve the original signal.

Do not retrospectively edit:

```text
expected return
score
features
reasoning
```

after the outcome is known.

Store later updates as events.

---

# 97. PERFORMANCE

Track:

```text
signal count
win rate
average return
median return
average excess return
Sharpe-like statistics
Sortino-like statistics
max drawdown
profit factor
MFE
MAE
```

Most importantly:

```text
average next-day return of VESPER #1
```

versus:

```text
SPY
random eligible stock
equal-weight universe
top momentum baseline
simple close-to-close momentum baseline
```

---

# 98. RANKING QUALITY

Evaluate:

```text
Spearman rank correlation
information coefficient
precision@1
precision@5
NDCG
top-decile lift
top-1% lift
```

VESPER is fundamentally a ranking engine.

---

# 99. #1 PICK PERFORMANCE

Track separately:

```text
rank #1 return
rank #2 return
rank #3 return
top 5 equal weight
top 10 equal weight
```

This reveals whether the model is truly good at identifying a single winner or merely a useful basket.

---

# 100. CALIBRATION

If VESPER says:

```text
P(POSITIVE) = 70%
```

those predictions should eventually be positive roughly 70% of the time.

Track:

```text
Brier score
reliability
expected calibration error
```

Use Platt/isotonic calibration only when sufficient out-of-sample samples exist.

---

# 101. REGIME PERFORMANCE

Break performance down by:

```text
bull market
bear market
high volatility
low volatility
earnings season
Fed days
index rebalance days
Friday
Monday
month end
quarter end
```

Do not assume one model behaves equally well everywhere.

---

# 102. FEATURE IMPORTANCE

Record:

```text
global feature importance
per-signal SHAP values
```

where practical.

The displayed reasons for a signal should reflect actual model drivers.

Do not use SHAP as proof of causality.

---

# 103. MODEL DRIFT

Monitor:

```text
feature distribution drift
prediction distribution drift
performance drift
calibration drift
```

If the market changes substantially:

warn.

Do not silently keep using a model trained on obsolete relationships.

---

# 104. RETRAINING

Recommended framework:

```text
nightly:
update datasets and labels

weekly:
candidate retrain

periodically:
full walk-forward validation
```

Do not deploy a new model simply because in-sample metrics improved.

Require out-of-sample improvement.

---

# 105. MODEL REGISTRY

Save models with:

```text
model_id
trained_at
training_period
features
hyperparameters
validation_metrics
test_metrics
dataset fingerprint
git commit
```

Never silently overwrite the production model.

---

# 106. PRODUCTION MODEL PROMOTION

A candidate model becomes production only if it passes predefined gates.

Examples:

```text
rank IC not degraded
#1 return improves or remains acceptable
drawdown acceptable
calibration acceptable
enough samples
no leakage tests failing
```

---

# 107. BASELINES

Compare VESPER against simple baselines:

```text
highest daily return
highest 30m momentum
highest RVOL
highest close location
random liquid stock
SPY
```

If the sophisticated model cannot outperform trivial baselines out-of-sample, do not pretend it is useful.

---

# 108. NO OVERFITTING BY FEATURE EXPLOSION

Do not blindly create 20,000 technical indicators.

Every feature should have:

```text
definition
timestamp
economic rationale
availability
missingness behavior
```

Prefer a smaller robust feature set to garbage feature mining.

---

# 109. HISTORICAL DATASET

Build research rows approximately like:

```text
date
ticker
features_known_at_15_50
entry_price
next_open
next_close
target_return
target_excess_return
```

Each row must have a strict feature timestamp cutoff.

---

# 110. DATA STORAGE

Use efficient storage.

Suggested:

```text
Parquet
DuckDB
```

for large historical research datasets.

SQLite for:

```text
signals
state
provider health
model registry metadata
shadow positions
configuration state
```

---

# 111. RAW LIVE RECORDER

Record enough information around the closing window to debug signals.

For example:

```text
15:30 → 16:00
```

for relevant tickers.

Record:

```text
minute bars
quotes
trades/aggregates where practical
rankings
features
model outputs
```

---

# 112. DATA FRESHNESS

Track:

```text
latest_bar_age
latest_quote_age
latest_trade_age
news_update_age
```

A stale ticker cannot become the winner.

At signal time use strict freshness requirements.

---

# 113. PROVIDER HEALTH

States:

```text
HEALTHY
DEGRADED
STALE
DISCONNECTED
RECONNECTING
FAILED
```

Track:

```text
last_message
message_rate
latency
reconnect_count
errors
```

---

# 114. RECONNECTS

All WebSockets require:

```text
heartbeat
automatic reconnect
bounded exponential backoff
jitter
resubscribe
state restoration
```

Provider failure must not crash the entire process.

---

# 115. NO SILENT FALLBACK

If consolidated real-time data fails and VESPER falls back to something inferior, display:

```text
DEGRADED DATA
```

and increase uncertainty.

If the fallback is insufficient for a valid 3:50 ranking:

```text
ACTIONABLE SIGNALS DISABLED
```

---

# 116. BOUNDED QUEUES

Market-wide streams can be enormous.

Use:

```text
bounded queues
coalescing
batch processing
vectorized operations
```

Avoid unbounded RAM growth.

Monitor queue lag.

---

# 117. PERFORMANCE ENGINEERING

Do not loop through thousands of pandas DataFrames one ticker at a time at 3:49:59.

Use:

```text
Polars/vectorization
batch inference
cached historical features
incremental intraday features
```

Target final ranking inference within seconds.

---

# 118. PROCESS SUPERVISION

Supervise:

```text
market stream
universe builder
feature engine
ranker
news poller
database writer
Telegram
dashboard
```

One optional component failure should not kill everything.

Critical market-data failure should disable the signal.

---

# 119. HEARTBEATS

Detect frozen tasks.

Track heartbeat of every critical worker.

A process that is alive but hasn't processed a market update in 60 seconds should not be considered healthy.

---

# 120. SINGLE INSTANCE

Prevent five VESPER instances from accidentally sending five identical signals.

Use process locking.

---

# 121. CLEAN SHUTDOWN

CTRL+C and STOP_VESPER must:

```text
stop streams
flush data
save state
close DB
close HTTP sessions
release lock
```

---

# 122. CRASH RECOVERY

Test:

```text
start
receive market data
kill process
restart
```

VESPER must resume without:

- corrupt DB
- duplicate signal
- broken model state

---

# 123. TELEGRAM

Support alerts to the user's phone.

Environment:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Commands:

```text
/start
/help
/status
/health
/top
/signal
/performance
/why
/mute
/unmute
```

Telegram failure must not stop VESPER.

---

# 124. SIGNAL ALERT

At signal time send a concise Telegram alert:

```text
🦅 VESPER A SIGNAL

BUY: XYZ
Price: $42.17
Entry: $42.10–$42.30
Max: $42.38

Expected next-session return: +3.1%
P(positive): 71%
P(top decile): 83%

Score: 88/100
Rank: #1 of 4,921

Plan:
Hold through next trading session.
Target exit near tomorrow's close.

Why:
• extreme closing relative strength
• 2.8x RVOL
• strong sector
• model consensus

Dashboard:
...
```

Do not spam.

---

# 125. DASHBOARD

Keep it functional, not overly elaborate.

Main view:

# SYSTEM HEALTH

# CURRENT MARKET REGIME

# VESPER COUNTDOWN

```text
NEXT SIGNAL IN 00:07:18
```

# TOP 20 LIVE RANKING

# TODAY'S WINNER

# MODEL BREAKDOWN

# LIVE CHART

# RECENT SIGNALS

# FORWARD PERFORMANCE

# PROVIDER HEALTH

---

# 126. CONSOLE

Example:

```text
==========================================================
                         VESPER
             NEXT-SESSION EQUITY RANKER
==========================================================

MARKET               OPEN
NEXT CLOSE            16:00 ET
VESPER SIGNAL         15:50 ET

REALTIME DATA         HEALTHY
UNIVERSE              5,0XX
ELIGIBLE              4,8XX

MODEL                 vesper_xxx
MODEL STATUS          READY

LIVE RANKING          ACTIVE

#1 XYZ                89.2
#2 ABC                86.4
#3 DEF                83.7
==========================================================
```

---

# 127. TIMEZONE

Use:

```text
America/New_York
```

for exchange scheduling.

Store internal timestamps in UTC.

Respect DST automatically.

Do not hardcode UTC offsets.

---

# 128. STARTUP SELF-TEST

Before live operation verify:

```text
configuration PASS
clock PASS
market calendar PASS
reference data PASS
historical data PASS
real-time entitlement PASS
WebSocket PASS
universe PASS
production model PASS
feature schema PASS
database PASS
```

---

# 129. SIGNAL-DAY SELF-TEST

Before final signal verify:

```text
market actually open
regular session active
signal time correct
quotes fresh
bars fresh
universe complete enough
model loaded
feature coverage acceptable
ranker updated
```

If not:

```text
NO SIGNAL — SYSTEM INVALID
```

---

# 130. TESTS

Prioritize:

```text
calendar
early close
next-session calculation
point-in-time universe
split adjustments
ticker changes
delistings
feature cutoff
lookahead leakage
news timestamps
volume profile calculations
VWAP features
cross-sectional ranks
labels
entry cost
exit cost
ranking groups
walk-forward splits
purge/embargo
model loading
live feature equivalence
data freshness
halt handling
LULD handling
signal dedupe
restart recovery
```

Do not spend half the test suite on CSS.

---

# 131. LIVE / BACKTEST FEATURE PARITY

This is critical.

Historical feature code and production feature code must share the same core transformations wherever possible.

Do not create:

```text
research_features.py
```

and:

```text
live_features_completely_different.py
```

that silently disagree.

Write feature-parity tests.

---

# 132. REPLAY

Build:

```text
LIVE
REPLAY
BACKTEST
```

modes.

Replay a historical 3:30–4:00 window through the same ranking engine.

Never label replay data as LIVE.

---

# 133. LIVE VALIDATOR

Implement:

```text
python -m vesper validate-live
```

and:

```text
VALIDATE_LIVE.ps1
```

No mocks for production validation.

---

# 134. LIVE VALIDATION — MARKET STATUS

Confirm:

```text
current market status
today's session
today's close
calculated VESPER signal time
next trading session
```

---

# 135. LIVE VALIDATION — UNIVERSE

Retrieve the current universe.

Print:

```text
TOTAL ACTIVE STOCK REFERENCES:
ELIGIBLE COMMON STOCKS:
REJECTED:
```

with categories.

---

# 136. LIVE VALIDATION — REALTIME ENTITLEMENT

Prove the provider is delivering genuinely real-time data.

Do not merely connect successfully.

Inspect:

```text
provider timestamps
local timestamps
latency
feed type
```

If delayed:

FAIL.

---

# 137. LIVE VALIDATION — MARKET-WIDE DATA

Receive live updates for multiple current securities.

Prove changing:

```text
price
volume
timestamp
```

---

# 138. LIVE VALIDATION — QUOTES

For shortlisted securities obtain:

```text
bid
ask
spread
```

from real data.

---

# 139. LIVE VALIDATION — FEATURES

For at least several live stocks print:

```text
30m return
late-day return
RVOL
VWAP distance
relative strength
sector strength
volatility
```

from current data.

---

# 140. LIVE VALIDATION — MODEL

Run the real production model.

Print top 20 ranked candidates.

Do not use random scores.

---

# 141. LIVE VALIDATION — FINAL PICK

Print:

```text
VESPER CURRENT #1:
Ticker
Score
Expected return
P positive
P top decile
Entry
Max entry
```

If below action threshold:

```text
DECISION: NO TRADE
```

This is acceptable.

---

# 142. LIVE VALIDATION — DYNAMIC MOVEMENT

Prove the live rankings update over time.

Record multiple snapshots.

For example:

```text
15:45
15:47
15:49
15:50
```

when operating during the proper window.

Do not pass validation using one static REST snapshot.

---

# 143. OUTSIDE MARKET HOURS

If validation is run when the market is closed:

Do NOT fake live activity.

Instead validate everything legitimately possible and report:

```text
LIVE MARKET-MOVEMENT TEST:
PENDING NEXT OPEN SESSION
```

The application itself may not be called fully production-validated until a real open-session run succeeds.

---

# 144. NO FAKE VALIDATION

Forbidden:

```text
force_signal
random score
fake websocket
stored live sample presented as current
hardcoded AAPL
mock universe
threshold=0
future bar data
```

---

# 145. LIVE VALIDATION REPORT

Generate:

```text
LIVE_VALIDATION_REPORT.md
```

including:

```text
VESPER LIVE VALIDATION
======================

Market Calendar           PASS
Universe                  PASS
Real-Time Entitlement     PASS
Market-Wide Feed          PASS
Quote Feed                PASS
Feature Engine            PASS
Production Model          PASS
Ranking Engine            PASS
Risk Filters              PASS
Signal Engine             PASS
Persistence               PASS
Telegram                  PASS
Dashboard                 PASS

TOTAL ELIGIBLE:
...

CURRENT TOP 10:
...

CURRENT #1:
...

ACTIONABLE:
YES / NO

LIVE PIPELINE:
PASS / FAIL
```

---

# 146. WALK-FORWARD ACCEPTANCE REPORT

Create:

```text
MODEL_VALIDATION_REPORT.md
```

Include:

```text
training period
validation period
locked test period

#1 average return
#1 median return
#1 positive rate
#1 excess return

top-5 statistics
rank IC
max drawdown

SPY benchmark
momentum baseline
random baseline

transaction cost assumptions
number of sessions
number of signals
```

Never hide bad results.

---

# 147. MINIMUM EVIDENCE

Do not declare:

```text
VESPER IS PROFITABLE
```

from:

```text
8 test days
```

Report confidence intervals/sample size.

---

# 148. FORWARD MODE

From first launch onward automatically record each day's:

```text
3:50 universe
ranking
top candidate
decision
predictions
actual next-session outcome
```

This is the ultimate evaluation dataset.

---

# 149. DAILY REPORT

After the next session closes generate:

```text
VESPER RESULT

Yesterday's pick:
XYZ

Entry:
...

Exit:
...

Return:
...

SPY:
...

Excess:
...

Rank #1 outcome:
...

Forecast:
...

Error:
...
```

---

# 150. WHY DID IT LOSE?

For losing signals record an attribution report.

Examples:

```text
overnight catalyst
market reversal
sector reversal
late-day momentum failed
model overconfidence
unexpected dilution
execution/slippage
```

Do not automatically modify the model after one loss.

---

# 151. MODEL MONITORING

Track rolling:

```text
20-signal
50-signal
100-signal
```

performance.

Warn when:

```text
performance degrades
calibration worsens
rank IC collapses
```

---

# 152. KILL SWITCH

If forward performance becomes severely inconsistent with validation:

```text
LIVE ACTIONABLE SIGNALS PAUSED
```

while rankings continue.

Require objective criteria, not emotion.

---

# 153. SECURITY

Never commit:

```text
API keys
Telegram tokens
credentials
```

Use `.env`.

`.gitignore` secrets.

Do not print tokens in diagnostics.

---

# 154. README

Include:

# WHAT VESPER IS

# WHAT VESPER IS NOT

State prominently:

```text
VESPER DOES NOT PLACE TRADES.
```

Include:

```text
installation
data provider setup
real-time subscription requirements
training
running
Telegram
dashboard
live validation
signal interpretation
risk
troubleshooting
```

---

# 155. CRITICAL PRODUCT PRINCIPLE

Do not build VESPER around:

```text
RSI < 30
MACD crossover
moving-average crossover
```

and pretend it is an intelligent market-wide predictor.

Technical indicators may become minor features.

The core is:

```text
point-in-time market-wide dataset
+
cross-sectional ranking
+
late-day microstructure
+
relative strength
+
volume
+
catalysts
+
overnight gap model
+
next-day continuation model
+
uncertainty
+
realistic costs
```

---

# 156. SECOND CRITICAL PRINCIPLE

VESPER is not:

> Which stock looks strongest?

It is:

> Which stock has the highest credible expected return FROM THIS SPECIFIC ENTRY TIME THROUGH THE NEXT SESSION CLOSE, compared with every other currently tradable candidate?

That distinction must control the entire architecture.

---

# 157. THIRD CRITICAL PRINCIPLE

A stock's expected return is not enough.

VESPER should prefer:

```text
expected +3.0%
strong model agreement
good liquidity
manageable downside
```

over:

```text
expected +3.5%
extreme uncertainty
15% downside tail
wide spread
binary catalyst
```

unless forward evidence proves otherwise.

---

# 158. FOURTH CRITICAL PRINCIPLE

VESPER must never accidentally learn tomorrow.

Every feature must answer:

> Was this information genuinely available before the historical signal timestamp?

If not:

DELETE IT FROM THAT SAMPLE.

---

# 159. REQUIRED DELIVERABLES

Before completion the repository must include:

```text
dynamic full U.S. stock universe
point-in-time historical universe
corporate-action handling
market calendar
early closes
real-time full-market data
minute bars
NBBO data
historical data pipeline
news integration
feature engine
market regime engine
sector/relative-strength features
late-day features
volume-profile features
microstructure
overnight gap model
next-day model
total-return model
cross-sectional ranking model
classification models
quantile predictions
ensemble
uncertainty
liquidity model
signal ranking
one-stock final decision
max-entry calculation
shadow positions
forward validation
walk-forward testing
baseline comparison
Telegram
dashboard
logging
crash recovery
PowerShell scripts
live validation
tests
README
```

No critical TODO implementations.

---

# 160. FINAL REPORT

When finished provide:

```text
VESPER BUILD STATUS
===================

VERSION:
COMMIT:

TESTS:
X passed
X failed

DATA PROVIDER:
...

REAL-TIME FEED:
PASS / FAIL

POINT-IN-TIME UNIVERSE:
PASS / FAIL

LOOKAHEAD TESTS:
PASS / FAIL

SURVIVORSHIP-BIAS TEST:
PASS / FAIL

MODEL:
...

TRAIN PERIOD:
...

VALIDATION PERIOD:
...

LOCKED TEST:
...

TEST #1 PICK RESULTS:
Average return:
Median:
Positive rate:
Excess vs SPY:
Max drawdown:

BASELINES:
...

LIVE UNIVERSE:
...

ELIGIBLE:
...

LIVE RANKING:
PASS / FAIL

CURRENT #1:
...

CURRENT DECISION:
BUY / NO TRADE

TELEGRAM:
PASS / FAIL

DASHBOARD:
...

ORDER EXECUTION ABSENT:
PASS / FAIL

KNOWN LIMITATIONS:
...

RUN:
...
```

Never hide failures.

---

# 161. FINAL COMMAND

Start from a clean repository.

Research current official market-data APIs.

Build the full point-in-time dataset.

Build the historical feature pipeline.

Build the live market-wide feature pipeline.

Ensure they match.

Train cross-sectional models using strict chronological walk-forward evaluation.

Prevent lookahead.

Prevent survivorship bias.

Model the overnight gap separately from the next-day session.

Include late-day price, relative-strength, volume, liquidity, news, market-regime, and catalyst information.

Build the ensemble.

Build the full-market staged ranking engine.

Connect REAL production market data.

Run the live universe.

Run the live ranking.

At approximately ten minutes before the current regular-session close, rank every eligible U.S. stock.

Select exactly ONE winner if it satisfies the required quality thresholds.

Send the real signal.

Track it through the next session.

Record the result.

Do not stop at scaffolding.

Do not stop at training notebooks.

Do not stop at historical backtests.

Do not stop at a dashboard.

Do not use delayed data and label it live.

Do not fabricate a signal.

Do not claim profitability without evidence.

Build the real VESPER.