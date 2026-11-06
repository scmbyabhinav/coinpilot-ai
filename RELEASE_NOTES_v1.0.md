# COINPILOT AI v1.0 — Strategy Research Configuration

## Research defaults
- Planned account risk per trade: **1.0%** of simulated account equity.
- Reward-to-risk target: **5:1 (5R)**.
- Win-rate objective: **70%**, treated strictly as a research benchmark, never a promise or calibrated probability.
- Execution: Binance Spot decision support only; virtual paper trading and manual review. No live API orders.

## Changes
- Trade Desk now defaults to a 5R target and 1% planned risk.
- Backtesting Lab sizes spot positions from planned cash risk and stop distance, capped by available cash (no leverage).
- Backtest take-profit distance is calculated as five times the selected stop distance.
- Backtest results explicitly compare the observed win rate with the 70% research objective.
- Settings documents the research protocol and backtest → paper-trade → manual real-trade sequence.

## Required validation before any real execution
1. Run the historical backtest on multiple liquid pairs and timeframes.
2. Review trade count, win rate, average win/loss, expectancy, profit factor, drawdown, fees and slippage sensitivity.
3. Repeat on unseen periods and different market regimes; do not tune rules solely to hit 70%.
4. Paper trade the same setup for a meaningful sample and compare fills with the backtest.
5. Only then consider a separately reviewed manual Spot trade. Real execution remains the user's independent action.

## Important limitations
- The 70% win rate and 5R target may not be simultaneously achievable. A high reward-to-risk target can materially reduce hit rate.
- The backtest remains a simplified candle simulation; it does not fully model spread, order-book depth, latency, partial fills, market impact, taxes or stop slippage.
- Planned 1% risk is not a guaranteed maximum realized loss. Gaps, slippage and fees can increase losses.
- This release has been syntax-checked, but no live Binance backtest or profitability claim is made in this packaging step.
