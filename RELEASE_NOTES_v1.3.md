# COINPILOT AI v1.3 — Auto Paper Trading Desk

## What changed
- Refreshed dashboard styling with stronger contrast, saturated blue/purple accents and clearer metric cards.
- Rebuilt Auto Paper Engine page as an automated paper-trading cockpit with $1,000 virtual starting-equity context.
- Added live open-position table with BUY status, entry, live price, stop, final target and unrealized P&L.
- Added closed trade results table showing BUY-to-SELL outcome, entry, exit, net P&L, timestamps and exit reason.
- Added recent automated BUY/SELL activity table and CSV export for closed automated trades.
- Auto paper position notional cap defaults to $1,000; quantity is sized from 1% planned account risk and the configured 2% initial stop, subject to available virtual cash.
- Automated engine can close remaining long quantity on a confirmed bearish SELL signal, or via the staged exit / stop ladder.
- Staged profit taking remains 50% at +2R, 25% at +4R, and final 25% at +5R. Stop ladder remains initial -1R, then break-even, then +2R.
- Daily realized-loss pause defaults to $25; maximum simultaneous positions defaults to 3.
- REST market data continues to use `https://data-api.binance.vision`.

## How to run
- Start the app with the existing virtual environment.
- Select **Auto Paper Engine** in the sidebar.
- Enable automatic paper trading and click **Save settings and apply**.
- Keep the app open and keep the Auto Paper Engine page selected. The page refreshes every 15 seconds and runs one simulation cycle per refresh.

## Safety and limitations
- Paper-only: no Binance account credentials or real order execution.
- The engine only operates while the app is open and the Auto Paper Engine page is selected; it is not a Windows service.
- Starting virtual equity is $1,000 for a fresh database. Existing local databases and trade history are preserved.
- 1% is planned risk sizing, not a guarantee of exact realized loss. Simulated fills, fees and market prices are approximate.
- The 70% win rate remains a research objective, not a guarantee. No profitability claim is made.
- Backtest, out-of-sample and paper-trading results must be evaluated before considering any real-money use.
