# COINPILOT AI v1.5 — Market Pulse & Exit Alerts

## What's new
- Market Pulse now displays up to 15 selected USDT Spot candidates in a clearer three-column dashboard.
- Open virtual holdings are highlighted in teal/green and remain highlighted across app refreshes using the SQLite trade ledger.
- When a held coin receives a confirmed bearish signal, its card pulses/blinks red with **SELL / EXIT NOW**. For a coin not held, the same bearish signal is labelled **BEARISH WATCH**, not a Spot sell order.
- Added a one-click **$100 PAPER BUY** button for qualified BUY setups on Market Pulse. It creates a virtual trade only and stores the original quantity/entry fee so the staged exit manager can track it.
- Added plain-English explanations for Trend Rider, Momentum Hunter and Breakout Scanner.
- Clarified the agreed paper exit plan: sell 50% at +2R, 25% at +4R, final 25% at +5R; initial stop at -1R; after +2R move stop to break-even; after +4R move stop to +2R.
- Updated dashboard cards, colours, borders and typography for a more professional terminal feel.

## Important trading notes
- R means the original entry-to-initial-stop distance. It does not mean 2x or 5x the coin price.
- 1% is planned account risk at the initial stop, not a guaranteed maximum loss. Gaps, slippage, fees and execution can change outcomes.
- Rule scores are confluence scores, not probabilities of profit. No strategy or win rate is guaranteed.
- This release remains paper-only. It does not submit Binance orders or require API keys.

## Upgrade
1. Stop any running COINPILOT window.
2. Extract this ZIP into a new folder.
3. Copy the existing `data` folder from your previous installation into the new folder. Do not delete or overwrite your existing database.
4. Run `START_COINPILOT.bat`.
