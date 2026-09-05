# Provider research — 2026-09-05

Official documentation checked before implementation. No subscription was purchased and no credentials were supplied.

| Provider | Relevant capabilities | Decision |
|---|---|---|
| Massive | Date-specific ticker reference, historical bars, wildcard minute stream, quotes, corporate actions, news | Provisional primary adapter; entitlement still unverified |
| Databento | Historical/live feeds plus security master and corporate-action products | Candidate supplement for security identity and action reconciliation; no adapter implemented |
| Alpaca market data | IEX and consolidated SIP feeds | Possible fallback adapter; IEX alone does not meet full-market requirements |

## Sources and implementation implications

- [Massive ticker reference](https://massive.com/docs/rest/stocks/tickers/all-tickers): date and active filters refer to the queried historical date; paginate all responses. A current-only ticker list must never drive a historical backtest.
- [Massive minute stream](https://massive.com/docs/websocket/stocks/aggregates-per-minute): wildcard subscriptions are supported. Some plans are delayed; authentication alone is insufficient evidence of real-time entitlement.
- [Massive quotes](https://massive.com/docs/websocket/stocks/quotes): shortlist quote access is needed for spread/depth validation.
- [Massive custom bars](https://massive.com/docs/rest/stocks/aggregates/custom-bars): retain unadjusted raw values and apply dated actions explicitly.
- [Current split API](https://massive.com/docs/rest/stocks/corporate-actions/splits) and [dividend API](https://massive.com/docs/rest/stocks/corporate-actions/dividends): use `/stocks/v1/splits` and `/stocks/v1/dividends`, not the deprecated v3 routes.
- [Massive LULD](https://massive.com/docs/websocket/stocks/luld): halt/resume indicators are only supplied for Nasdaq listings. This feed alone does not prove all-exchange halt coverage. Documentation also shows inconsistent timestamp units between prose and examples; normalize magnitude and validate freshness.
- [Databento security master](https://databento.com/security-master) and [documentation](https://databento.com/docs): investigate licensed historical identity and action coverage before accepting survivorship-bias claims.
- [Alpaca feed documentation](https://docs.alpaca.markets/us/docs/real-time-stock-pricing-data) and [FAQ](https://docs.alpaca.markets/us/docs/market-data-faq): distinguish IEX, SIP and delayed SIP explicitly.
- [Exchange calendar implementation](https://github.com/gerrymanoim/exchange_calendars): use session opens/closes and next-session lookup; unexpected future exchange closures still require an operational override and official market-status reconciliation.

Historical REST retrieval is not proof that every revision was available at the original signal time. Keep this limitation explicit; raw live recordings can establish actual receipt timestamps going forward.
