# COINPILOT AI v1.2 — Binance REST endpoint fix

## Changes
- Public REST market-data requests now use `https://data-api.binance.vision`, which was reachable in the user's local connectivity test (HTTP 200, `{}`).
- SQLite database parent directory is created automatically before opening the database.
- Staged exit configuration remains: sell 50% at +2R, 25% at +4R, final 25% at +5R; stop ladder -1R → break-even → +2R.
- Planned account risk remains 1%; 70% win rate remains a research objective, not a guarantee.
- No live order placement or API-key trading is enabled.

## Verification performed
- Python AST parse and bytecode compilation passed.
- The package archive will be checked for integrity.
- The user's successful endpoint test validates the alternative ping endpoint, but full ticker, kline, historical backtest and paper-trading behavior must still be tested in the installed app.

## Limitations
- The WebSocket stream still uses Binance's standard stream host; if it is unreachable, the app should use the REST fallback.
- The app refreshes periodically; it is not an always-on exchange-side stop manager.
- Backtest and paper outcomes are simulations and do not guarantee real execution prices or results.
