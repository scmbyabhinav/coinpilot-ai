# COINPILOT AI

A Windows-first, local Streamlit application for Binance Spot market scanning and **paper trading only**.

> **Risk notice:** COINPILOT is an experimental research tool, not financial advice. Signals and confluence scores are not probabilities of profit. No strategy or win rate is guaranteed. This release does not place real Binance orders.

## Current release

**v1.5 — Market Pulse & Exit Alerts**

- Dynamic Binance USDT Spot candidate selection using public market data.
- Market Pulse cards distinguish BUY, WAIT and bearish-watch conditions.
- Open paper holdings remain highlighted; held positions with bearish exit conditions receive a visible SELL / EXIT alert.
- Paper BUY workflow and staged exit management.
- SQLite-backed local paper-trade history.
- Plain-English explanations for Trend Rider, Momentum Hunter and Breakout Scanner.

## Windows setup

1. Install Python 3.11 or newer.
2. Download or clone this repository.
3. Open the project folder in Windows Explorer.
4. Double-click `START_COINPILOT.bat`.
5. The launcher creates a virtual environment, installs requirements and starts Streamlit.
6. Open the localhost URL printed in the terminal.

Alternatively:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Local data and privacy

The application creates `data/coinpilot.db` locally. This database may contain paper-trading activity and settings. **Do not commit it.** The repository ignore rules exclude local databases, environment files, logs, backups and virtual environments.

This version uses public market data and does not require Binance API keys. Never put API credentials, passwords, recovery codes or personal trading records in source control.

## Paper exit framework

The configured plan uses R-multiples based on the original entry-to-stop distance:

- Initial stop: -1R.
- At +2R: close 50% of the original position; move stop to break-even.
- At +4R: close another 25%; move stop to +2R.
- At +5R: close the remaining 25%.

These are simulated rules. Fees, slippage, gaps, data quality and execution assumptions can materially change results. A planned 1% account risk is not a guaranteed maximum loss.

## Project roadmap

- Daily trade ledger with linked partial exits and realised P&L.
- Daily/weekly/monthly performance summaries.
- CSV and Excel exports.
- Equity curve, drawdown, profit factor and strategy-level validation.
- Automated tests and release checks.

## Development

Use feature branches and pull requests. Keep `main` as the stable branch. Validate changes with:

```powershell
python -m compileall -q .
python -m pip check
```

## Disclaimer

For educational and research use only. Cryptocurrency markets are volatile. Paper performance does not guarantee live performance. Do not use borrowed money or funds needed for essential expenses.
