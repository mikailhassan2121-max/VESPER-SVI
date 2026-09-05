# VESPER build status

Version: 0.1.0 engineering build. **Incomplete; not production-ready.**

Validation on Windows / Python 3.14: all 38 tests verified passing, including a targeted rerun after the final entry-window fix; see TEST_REPORT.md. Static checks passed. Two upstream test-client deprecation warnings were observed. Unit fixtures are synthetic and do not establish real-data model performance.

## Implemented

- Windows environment and six launch/check/train/validation/shutdown scripts.
- Exchange sessions, holidays, DST, early closes, next-session horizon.
- Read-only Massive REST pagination, dated reference acquisition, raw unadjusted historical download, corporate-action endpoints, news endpoint.
- Bounded stream queue, reconnect/backoff, authentication, market aggregate consumption, shortlist subscription interface.
- Shared availability-cutoff transformations, intraday/daily/cross-sectional features, conservative execution-window labels, simple split/dividend accounting.
- Research compiler with explicit unresolved-outcome audit and export refusal.
- Candidate LightGBM regression, classification, ranking and quantile model code; chronological purging, held-out evaluation, fingerprinted artifacts.
- Decision gates, SQLite immutable records, deduplication, process lock, loopback dashboard, honest partial live validator.

## Required before completion

1. Confirm provider subscription and supply credentials locally; verify real-time full-market and quote entitlement.
2. Complete and audit historical identity continuity, merger/delisting terminal outcomes, point-in-time sector/event/news/fundamental inputs, revision provenance and early-close volume-profile matching.
3. Integrate cached daily/profile/sector/news features into the running live engine. Current runtime containers are unpopulated. Complete vectorized staged inference and feature coverage checks.
4. Connect NBBO/depth and authoritative halt/catalyst status to final candidate checks. Current runtime does not enrich ranked rows with these values. Full-market entitlement is never promoted from partial observations yet.
5. Complete calibrated ensemble selection, executable-cost parity, model promotion gates, truly locked test reuse protection and baseline/regime/confidence-interval reporting.
6. Implement Telegram commands/delivery, immutable alert outbox, shadow-position outcome tracking, post-signal monitoring, daily attribution, performance drift and kill switch.
7. Complete replay/backtest CLI modes, raw-data retention policy, clock-drift detection, market-status overrides, critical worker watchdog and crash-injection integration tests.
8. Train on real historical data, inspect locked test results honestly, then complete real open-session pipeline validation. No trained artifact or current top pick exists.

The initial code is committed for review and continuation, not as fulfillment of the full 161-section production specification. The absence of credentials is not the only remaining limitation.
