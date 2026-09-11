# VESPER SVI

**VESPER DOES NOT PLACE TRADES.** It is intended to rank eligible U.S. common stocks for a manual entry shortly after ten minutes before the regular close, with exit near the next session's close.

**Status: incomplete engineering build, not production-ready.** No real-data model has been trained, no live full-market validation has passed, and no profitability claim is made. The current implementation deliberately disables actionable live signals. This is not yet the complete system requested in the master specification. See [BUILD_STATUS.md](BUILD_STATUS.md) for the exact remaining work.

## Windows setup

Python 3.14 is the tested setup; PowerShell, no Docker or GPU required. `requirements-tested.txt` pins the verified dependency versions.

```powershell
.\SETUP_VESPER.ps1
# Edit .env locally; never commit your API key.
.\CHECK_VESPER.ps1
.\RUN_VESPER.ps1
```

Dashboard: http://127.0.0.1:8787. Stop with CTRL+C or `STOP_VESPER.ps1`.

The dashboard distinguishes observed momentum from model forecasts. With no production model, it cannot display model probabilities or a winner. Reference data, model status, feed status, and missing coverage remain visible.

## Market data

The initial adapter uses Massive's read-only REST and real-time stock WebSocket APIs. Set `MASSIVE_API_KEY` in `.env`. Paid real-time consolidated stock entitlement, historical minute access, reference data, corporate actions, and quote access are needed. Authentication is not treated as proof of full-market coverage. No delayed-feed fallback is used.

Massive is the selected primary provider: one API key covers its stock endpoints. The earnings veto additionally requires access to its Benzinga earnings endpoint. Free access is useful for limited research, but does not establish consolidated real-time entitlement or the complete historical/event evidence required here. No subscription has been purchased. See [provider research](docs/PROVIDER_RESEARCH.md). Never paste credentials into a task or diagnostics.

## Historical acquisition and research

```powershell
.\.venv\Scripts\python.exe -m vesper download --start 2022-01-03 --end 2025-12-31
.\.venv\Scripts\python.exe -m vesper build-dataset --output data/research.parquet
.\TRAIN_VESPER.ps1 -Dataset data/research.parquet -LockedStart 2025-07-01
```

These commands require a suitable subscription and substantial storage/time. Acquisition requests the reference universe on each historical date, paginates, caches raw responses, and resumes completed ticker files. It records missing outcomes explicitly. Missing delisting/merger outcomes block dataset export rather than silently removing failed securities.

The compiler accepts point-in-time sector mappings from `data/context/sectors.json` and constructs an equal-weight sector-peer benchmark. Actual mappings and complete event/revision provenance have not been supplied. Its output remains **research-only** until these inputs are reconciled. Do not replace missing sector returns with fabricated zeros to pass validation. Historical volume profiles use prior sessions of the same duration at the same elapsed time; sparse early-close history remains unavailable instead of borrowing normal-session totals.

Training implements separate gap, next-day, direct-return and excess-return models; LambdaRank; binary classifiers; quantile models; purged chronological folds; out-of-fold ensemble weighting and sigmoid calibration; and a locked holdout. At least 252 training, 63 validation, embargo, and 63 locked-test sessions are needed. The registry reserves locked date intervals before evaluation and refuses overlapping reuse, including with changed data. Saved models are candidates, not silently promoted. Production promotion is explicit: `python -m vesper promote --model-id <candidate-id> --audit <audit.json>`. It checks locked-test performance, baseline and block-bootstrap confidence evidence, calibration, dataset identity, and all provenance/parity attestations before atomically selecting an immutable candidate. See `docs/PRODUCTION_OPERATIONS.md`. There is no promoted artifact in this checkout.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\VALIDATE_LIVE.ps1
```

`LIVE_VALIDATION_REPORT.md` reports actual evidence. Missing keys and a closed market never produce a pass. The validator observes the running local application without opening a competing feed. It requires an open session, fresh runtime, clock evidence, full coverage, quotes, promoted model, feature coverage, changing model snapshots, healthy workers, and a current-session persisted valid decision. Start VESPER first and validate through the real signal window. Missing evidence fails the check. Configured Telegram additionally requires successful delivery evidence. `MODEL_VALIDATION_REPORT.md` is produced by training, never populated with invented results.

## Signal interpretation and risk

BUY, NO TRADE, and NO SIGNAL — SYSTEM INVALID are different outcomes. NO TRADE is reserved for valid inputs with inadequate opportunity. Missing models, delayed data, inadequate universe coverage, or incorrect scheduling invalidate the system. Overnight gaps can exceed any planned loss; model probabilities are uncertain; production artifacts must include calibration, whose real-data quality still needs evaluation. A displayed score is not a probability.

## Troubleshooting

- Missing credentials: configure the key locally in `.env`.
- Subscription rejection: verify reference/minute/quote/full-market entitlement with the provider.
- Model unavailable: training and independent promotion evidence are required; there is no substitute model.
- No live movement: run during a real open session; weekends and exchange holidays are closed.
- Unresolved historical outcomes: reconcile corporate actions and symbol identity; do not drop the affected names.
- Port already in use: stop the existing VESPER instance. SQLite and process locking prevent duplicate local instances sharing the same data directory.

## Telegram and paper outcomes

Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` locally to enable optional delivery and commands. Only the configured chat receives replies. `/status`, `/health`, `/top`, `/signal`, `/performance`, `/why`, `/mute`, `/unmute`, `/start`, and `/help` are supported. Signal and outbox creation are atomic. Expired alerts are not sent; unknown delivery after a timeout or process interruption is not retried automatically. This avoids duplicate instructions but can require manual delivery investigation. No real delivery has been validated.

BUY decisions create immutable paper records. After the following close, the worker resolves conservative execution-window benchmarks and writes `data/results/`. These are not actual fills. A benchmark entry above max-entry is flagged and still retained for unbiased forecast analysis. Missing execution windows or corporate-action data leave an unresolved outcome rather than a fabricated return.

## Replay and context inputs

```powershell
.\.venv\Scripts\python.exe -m vesper export-replay --session 2026-09-04 --output data/recording.jsonl
.\.venv\Scripts\python.exe -m vesper replay --session 2026-09-04 --recording data/recording.jsonl --output data/replay-results.jsonl
```

Use a date actually recorded by your instance. Optional `--model models/<candidate-id>` enables candidate inference during replay. Replay writes to `replay.sqlite`, never the live signal database, and does not start stream, Telegram or backfill workers. Morning aggregates and REST warmup bars are retained with receipt timestamps to reproduce partial-session startup.

Optional `data/context/sectors.json`, `splits.json`, and `risk.json` are JSON arrays from an audited provider ingestion process. Every record needs `source`, timezone-aware `available_at`, `valid_from`, and exclusive `valid_until`. Sector records add `ticker` and `sector`; split records add `ticker`, `execution_date`, `split_from`, and `split_to`; risk records add `ticker`, boolean `halted`, and boolean `binary_event`. Risk evidence expires after 60 seconds. Absence of a file is missing evidence, never an all-clear. These file contracts are integration boundaries; authoritative data acquisition remains unfinished.

## Operating controls

`python -m vesper pause --reason "reason"` persistently blocks new signals. `python -m vesper resume --reason "review outcome"` records a manual review and clears the pause; all other gates still apply. Automatic pauses trigger on the configured forward drawdown limit or negative mean return and SPY excess over 20 completed outcomes. A reviewed set of outcomes is not repeatedly paused until another outcome arrives.

Raw market recordings expire after 90 days by default (`VESPER_RAW_RETENTION_DAYS`); signals, outcomes, and audit events remain. Export recordings needed for long-term replay before retention expires. The dashboard includes recorded price charts, saved decisions, model breakdown, position monitoring and forward summaries. Missing quotes and model forecasts remain visibly unavailable.
