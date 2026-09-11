# VESPER live validation

Start VESPER before running this check. Full acceptance requires observing the real signal session.

| Check | Result |
|---|---|
| Open Session | PENDING OPEN SESSION |
| Runtime Freshness | PASS |
| Clock | NOT PROVEN |
| Universe | NOT PROVEN |
| Real-Time Entitlement | NOT PROVEN |
| Market-Wide Feed | NOT PROVEN |
| Quote Feed | NOT PROVEN |
| Production Model | NOT PROVEN |
| Feature Engine | NOT PROVEN |
| Ranking Engine | NOT PROVEN |
| Workers | NOT PROVEN |
| Signal and Persistence | NOT PROVEN |
| Telegram | NOT CONFIGURED (OPTIONAL) |
| LIVE PIPELINE | FAIL |
| Dashboard | PASS |

## Evidence

```json
{
  "checked_at": "2026-09-11T01:46:48.110214+00:00",
  "observations": [
    {
      "at": "2026-09-11T01:46:47.761575+00:00",
      "checks": {
        "Open Session": "PENDING OPEN SESSION",
        "Runtime Freshness": "PASS",
        "Clock": "NOT PROVEN",
        "Universe": "NOT PROVEN",
        "Real-Time Entitlement": "NOT PROVEN",
        "Market-Wide Feed": "NOT PROVEN",
        "Quote Feed": "NOT PROVEN",
        "Production Model": "NOT PROVEN",
        "Feature Engine": "NOT PROVEN",
        "Ranking Engine": "NOT PROVEN",
        "Workers": "NOT PROVEN",
        "Signal and Persistence": "NOT PROVEN",
        "Telegram": "NOT CONFIGURED (OPTIONAL)",
        "LIVE PIPELINE": "FAIL",
        "Dashboard": "PASS"
      }
    }
  ],
  "runtime": {
    "mode": "LIVE",
    "decision": "NO SIGNAL \u2014 SYSTEM INVALID",
    "failures": [
      "PRODUCTION_MODEL_UNAVAILABLE",
      "REFERENCE_ProviderError",
      "NEWS_ProviderError",
      "MARKET_STATUS_ProviderError",
      "EARNINGS_ProviderError"
    ],
    "leaderboard": [],
    "production_validated": false,
    "universe": 0,
    "model": {
      "status": "UNAVAILABLE"
    },
    "forward": {
      "completed": 0,
      "kind": "FORWARD_BENCHMARKS_NOT_ACTUAL_FILLS",
      "windows": {}
    },
    "pause": null,
    "positions": [],
    "updated_at": "2026-09-11T01:46:42.823299+00:00",
    "provider": {
      "state": "FAILED",
      "entitlement": "UNAVAILABLE",
      "reconnects": 0,
      "last_message": null,
      "messages": 0,
      "error": "MASSIVE_API_KEY is not configured"
    },
    "queue_size": 0,
    "next_signal": "2026-09-11T19:50:00+00:00",
    "telegram": "NOT_CONFIGURED",
    "market": "CLOSED"
  },
  "signal_sessions": [],
  "scope": "Current running application and current-session persisted decision; no synthetic data or messages"
}
```
