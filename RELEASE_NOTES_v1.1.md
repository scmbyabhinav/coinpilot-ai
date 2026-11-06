# COINPILOT AI v1.1 — Staged Exit Research

## Strategy configuration
- Planned account risk: 1% per trade (position size is risk-distance based and cash-capped).
- Initial stop: -1R.
- Profit-taking: sell 50% of original quantity at +2R, 25% at +4R, and final 25% at +5R.
- Stop ladder: after +2R, move remaining stop to entry; after +4R, move remaining stop to +2R.
- Research objective: 70% winning trades; explicitly not guaranteed.
- Binance Spot only; no leverage; no live order placement.

## Implemented
- Additive SQLite migration for initial quantity, exit stage, partial realized P&L, and remaining entry fee.
- Shared staged-exit processor for the automatic paper engine and manual virtual-trading desk.
- Backtesting Lab models staged exits and stop ladder; if the initial stop and +2R occur in the same OHLC candle, it assumes the stop first.
- Manual paper trade sizing uses planned account risk and user-entered maximum position budget.
- Auto paper engine uses 1% planned equity risk and a 2% initial stop distance, cash-capped.
- Existing records are preserved by additive schema migration.

## Important limitations
- Paper monitoring executes when the app refreshes / the relevant page is active; it is not an always-on exchange stop order.
- OHLC backtests cannot know the true intrabar path. Conservative assumptions reduce but do not eliminate bias.
- Fees are modeled; spread, slippage, tax, partial-fill mechanics, latency, and exchange outages may differ materially.
- Stop losses do not guarantee exact realized loss.
- No live Binance trading or API key storage is implemented.
- No profitability or 70% win rate is claimed. Backtest across multiple symbols and out-of-sample periods, then paper trade before considering any real manual trade.
