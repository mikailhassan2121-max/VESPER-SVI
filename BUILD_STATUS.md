# VESPER build status

Version: 0.1.0 engineering build. **Incomplete; not production-ready.**

Validation on Windows / Python 3.14: see TEST_REPORT.md for the current suite. Unit fixtures are synthetic and do not establish real-data model performance.

## Implemented

- Windows environment and six launch/check/train/validation/shutdown scripts.
- Exchange sessions, holidays, DST, early closes, next-session horizon.
- Read-only Massive REST pagination, dated reference acquisition, raw unadjusted historical download, corporate-action endpoints, news endpoint.
- Bounded stream queue, reconnect/backoff, authentication, market aggregate consumption, shortlist subscription interface.
- Shared availability-cutoff transformations, intraday/daily/cross-sectional features, conservative execution-window labels, simple split/dividend accounting.
- Research compiler with explicit unresolved-outcome audit and export refusal.
- Candidate LightGBM regression, classification, ranking and quantile model code; chronological purging, held-out evaluation, fingerprinted artifacts.
- Decision gates, SQLite immutable records, deduplication, process lock, loopback dashboard, honest partial live validator.
- Shared cached historical context, matched-duration/time-of-day volume profiles, historical split basis, timestamped sector-context input and peer benchmarks.
- Live history warmup/backfill, receipt-aware news polling, NBBO/depth enrichment, optional dated risk-context input, stale-worker/queue checks and invalid-session decision persistence.
- Cutoff-preserving bar revisions, batched recordings, export/replay CLI with separate storage and no live network workers.
- Chronological out-of-fold sigmoid calibration and one-use, nonoverlapping locked-test reservation registry.
- Durable Telegram outbox, command polling restricted to the configured chat, mute state, expiration and uncertain-delivery handling. No real Telegram delivery has been tested.
- Atomic paper-position creation, immutable next-session execution-window benchmark outcomes, result files and rolling 20/50/100 benchmark summaries.

## Required before completion

1. Confirm provider subscription and supply credentials locally; verify real-time full-market and quote entitlement.
2. Complete and audit historical identity continuity, merger/delisting terminal outcomes, point-in-time sector/event/news/fundamental inputs, revision provenance and early-close volume-profile matching.
3. Supply actual context datasets and benchmark full-universe staged inference latency. Audit feature coverage, original historical revisions and split-context completeness. The runtime wiring exists but has not been tested with real market-wide inputs.
4. Connect authoritative halt/catalyst sources instead of relying on optional audited context files. Full-market entitlement is not yet promoted from partial observations. No complete live acceptance gate exists.
5. Complete executable-cost parity, production-model promotion, ensemble/baseline/regime/confidence-interval reporting and real calibration evaluation.
6. Validate real Telegram delivery; add post-signal/after-hours risk monitoring, MFE/MAE, loss attribution, performance drift and kill switch. Current forward results are bar-window benchmarks, not actual fills; unresolved outcomes remain pending.
7. Complete backtest CLI mode, raw-data retention, clock-drift detection, market-status overrides and process-kill integration tests. Replay and basic stale-consumer/backlog checks exist; production resilience is not established.
8. Train on real historical data, inspect locked test results honestly, then complete real open-session pipeline validation. No trained artifact or current top pick exists.

The initial code is committed for review and continuation, not as fulfillment of the full 161-section production specification. The absence of credentials is not the only remaining limitation.
