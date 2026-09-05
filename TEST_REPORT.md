# Engineering verification — 2026-09-05

- Full suite: 38 passed before conservative entry-window tightening.
- Full suite after tightening: 37 passed, 1 failed because an empty frame needed an explicit unresolved-window guard.
- After fixing that guard: all 3 label tests passed; the other 35 tests were unchanged and had passed in the preceding full run.
- Final status: all 38 tests verified passing, no outstanding test failures.
- Ruff static checks: passed.
- Startup self-check: configuration, exchange calendar, SQLite passed. Credentials absent.
- Dashboard: HTTP startup and safe missing-credential state passed via FastAPI integration test.
- Live validator: FAIL / NOT PROVEN; missing API key; market movement pending next open session.

Coverage includes holidays, early closes, DST, point-in-time reference filtering, noncommon-stock rejection, future-data cutoff, delayed availability, duplicate bars, split/dividend math, conservative entry/exit labels, missing execution windows, purged folds, candidate model save/load and tamper detection, signal immutability and restart dedupe, stale/crossed quotes, halt/event/LULD vetoes, timestamp-unit normalization, foreign pagination rejection, and a static prohibited execution-path check.

Limitations: synthetic unit fixtures do not prove actual survivorship-bias elimination, live feature parity, full market coverage, real-world latency, strategy profitability, or process-kill recovery. Two upstream Starlette/AnyIO test-client deprecation warnings remain. The source-level prohibited-name check is a regression guard, not a formal proof of every possible network behavior.
