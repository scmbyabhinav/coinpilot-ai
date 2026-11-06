# COINPILOT AI v1.4 — Dynamic Top 15 Scanner (Paper Only)

## Changes
- Adds a dynamic Binance USDT Spot candidate universe, ranked by 24-hour quote volume.
- Filters for active Spot-tradable markets, removes stablecoin and leveraged-token bases, applies a configurable liquidity floor ($2M/$5M/$10M/$25M), and excludes pairs with spreads above 0.50%.
- Refreshes the candidate universe every five minutes and shows the current Top 15 list in the sidebar workspace.
- Retains a manual-watchlist option and a core eight-pair fallback if Binance market-data requests fail.
- Blocks signal generation when the latest closed candle is materially stale (more than 2.5 timeframe lengths old).
- Enables SQLite WAL mode and a 30-second busy timeout to reduce transient database-lock errors.

## Data source
Uses Binance public market-data-only REST endpoints on `https://data-api.binance.vision`; no API key is required and no account/order endpoints are used.

## Safety
- Candidate ranking is a liquidity filter, not a prediction of which coins will be profitable.
- The signal score is not a win probability. No 70% win rate or profit is promised.
- Paper-only; no real orders or API credentials. Keep testing with fees, slippage and out-of-sample data.
