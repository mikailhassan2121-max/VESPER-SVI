# Engineering verification — 2026-09-10

- Final local suite: **64 passed, 0 failed**, 6.03 seconds, Windows / Python 3.14.
- Ruff and Python compilation passed; dependency consistency check passed.
- Two upstream Starlette/AnyIO test-client deprecation warnings remain.
- Forced child-process termination: committed SQLite decision survives, duplicate creation is refused, integrity check passes, interrupted sending becomes UNKNOWN and is not retried.
- Browser verification: running dashboard loads its missing-key/model state, readiness reasons, empty forecast/history panels and provider status without invented market data.
- Running-application validation: dashboard and runtime freshness pass; market closed, API key absent, no production model; **LIVE PIPELINE FAIL**. See LIVE_VALIDATION_REPORT.md.
- Vectorized daily/intraday calculations match the previous implementation on a 100-symbol synthetic fixture. Synthetic 4,000-stock / 1,520,000-row intraday timing: **2.227 seconds**. This measures transformation time only, not full pipeline or feed latency.

Regression coverage includes session calendars, cutoffs and revisions, point-in-time reference filtering, corporate actions and gross/net cost decomposition, conservative execution windows, purge/holdout reservation, calibration, artifact integrity, production evidence rejection, immutable persistence, outbox recovery, stale quotes and independent risk records, clock drift, broad stream evidence, raw retention, performance pause rules, and prevention of realized-cost ranking leakage.

No real-data profitability, terminal-outcome reconciliation, all-event coverage, full-context replay parity, actual Telegram delivery, or open-session production acceptance is established. GitHub workflow results must be checked separately; local passing tests do not imply a remote CI pass.
