# Engineering verification — 2026-09-10

- Final full suite: **54 passed, 0 failed**, 16.60 seconds on Windows / Python 3.14.
- Two upstream Starlette/AnyIO test-client deprecation warnings remain.
- A sandboxed run could not access pytest's temporary directory; the successful final run used the approved environment. No test failures remain.
- Ruff static checks: passed.
- Startup self-check: configuration, exchange calendar, SQLite passed. Credentials absent.
- Dashboard: HTTP startup and safe missing-credential state passed via FastAPI integration test.
- Live validator: FAIL / NOT PROVEN; missing API key; market movement pending next open session.

Coverage includes holidays, early closes, DST, point-in-time reference filtering, noncommon-stock rejection, future-data cutoff, delayed availability, duplicate bars, split/dividend math, conservative entry/exit labels, missing execution windows, purged folds, candidate model save/load and tamper detection, signal immutability and restart dedupe, stale/crossed quotes, halt/event/LULD vetoes, timestamp-unit normalization, foreign pagination rejection, and a static prohibited execution-path check.

Continuation coverage adds matched time-of-day volume profiles, early-close separation, repeated split-context evaluation without mutation, dated context availability, signal-time invalid-state persistence, NBBO enrichment with unknown/stale risk evidence, post-cutoff correction retention, offline replay isolation, receipt-order export, overlapping holdout refusal, sigmoid calibration/class-support checks, atomic signal/outbox/shadow creation, immutable outcomes, delivery acknowledgement and ambiguous-timeout recovery. Telegram transport is mocked only in unit tests; no real phone delivery is claimed.

Limitations: synthetic unit fixtures do not prove actual survivorship-bias elimination, live feature parity, full market coverage, real-world latency, strategy profitability, or process-kill recovery. Two upstream Starlette/AnyIO test-client deprecation warnings remain. The source-level prohibited-name check is a regression guard, not a formal proof of every possible network behavior.
