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
- Decision gates, SQLite immutable records, deduplication, process lock, loopback dashboard, runtime-based live validator.
- Shared cached historical context, matched-duration/time-of-day volume profiles, historical split basis, timestamped sector-context input and peer benchmarks.
- Live history warmup/backfill, receipt-aware news polling, NBBO/depth enrichment, optional dated risk-context input, stale-worker/queue checks and invalid-session decision persistence.
- Cutoff-preserving bar revisions, batched recordings, export/replay CLI with separate storage and no live network workers.
- Chronological out-of-fold sigmoid calibration and one-use, nonoverlapping locked-test reservation registry.
- Durable Telegram outbox, command polling restricted to the configured chat, mute state, expiration and uncertain-delivery handling. No real Telegram delivery has been tested.
- Atomic paper-position creation, immutable next-session execution-window benchmark outcomes, result files and rolling 20/50/100 benchmark summaries.

## Additional hardening completed

- Explicit gross forecast/net execution-cost contract, exact dividend/gap decomposition, and exclusion of realized future costs from historical ranking selection.
- Audited model promotion with atomic production pointer, fingerprints, calibration checks, locked baseline gates and five-session block-bootstrap confidence intervals.
- Provider clock/market-status polling, stream-only coverage/movement proof, earnings veto adapter and conservative merging of independent risk records. Earnings-calendar absence never clears other binary-event risks.
- Runtime-based live acceptance report, actual snapshot evidence, changing rankings and persisted signal verification. No hardcoded acceptance and no competing stream.
- Vectorized feature transformations: parity checked against the previous calculations; 4,000 synthetic stocks / 1.52 million minute rows processed in 2.227 seconds locally. This is not a live latency claim.
- Persistent manual/automatic pauses, raw-feed retention, observed paper-position monitoring, regular-session bar-bound MFE/MAE and descriptive loss-component accounting.
- Expanded dashboard; tested forced-process termination recovery; pinned tested dependencies and automated Windows/Linux verification workflow.

## Required before completion

1. Configure a real Massive API key locally and verify the actual subscription covers consolidated real-time stocks, quotes, historical minute data and earnings. No account/subscription purchase was made.
2. Acquire and audit historical identity continuity, merger/delisting terminal outcomes, original revision availability, point-in-time sector/event/news/fundamental inputs and split context. Supplied historical revisions alone cannot establish what was originally known.
3. Complete authoritative all-binary-event and exchange-wide halt coverage; recent trades and Nasdaq LULD events are bounded observations. Earnings vetoes alone cannot prove all-clear. Unknown candidate evidence invalidates a signal.
4. Complete the full specification's advanced feature set, execution-policy backtest CLI with archived quote/risk evidence, regime diagnostics and complete live/replay context parity. Existing training metrics evaluate rankings, not a complete historical simulation of all live decision gates.
5. Train on actual historical data, examine untouched test performance and calibration, reconcile provenance and execution parity, and promote only if the evidence supports it. No trained artifact exists here.
6. Run real open-session acceptance and real Telegram delivery if configured; validate the full-volume system, complete after-hours catalyst coverage and long-running operational behavior. The current closed-session check fails correctly.

This is still an incomplete implementation of the 161-section specification. Missing credentials are not the only remaining limitation. The release gates prevent treating engineering tests or synthetic timing fixtures as production evidence.
