# TFSA Stock and ETF Dashboard MVP

A local-first personal investing research dashboard for Canadian TFSA long-term investing. The MVP uses mock market data, JSON storage, and rule-based scoring so it runs without API keys or package installs.

This app does not place trades, connect to a brokerage, or automate trading. It only supports research, watchlist analysis, manual transaction tracking, portfolio review, suggested allocations, exports, and reports.

> **Demo data:** the JSON files under `data/` contain sample data for demonstration. They are not real holdings or transactions.

## What Is Included

- Five dashboard views:
  - Recommendation Dashboard
  - Weekly Picks
  - Watchlist Detail
  - Portfolio / Holdings
  - Settings
- Mock market data with deterministic fallback values
- Manual watchlist add/remove and notes
- Manual buy/sell transaction ledger
- Holdings calculated from transactions
- Average cost, current value, portfolio weight, realized/unrealized gain/loss
- Rule-based stock and ETF scoring
- Weekly investment allocation suggestions
- Current holding context for already-held recommendations
- Optional target allocation mode
- Plan B allocation only when a ticker is manually skipped or explicitly excluded
- Copy-to-LLM exports
- JSON storage under `data/`
- Optional provider placeholders for yfinance, news APIs, and LLM mode
- Manual weekly analysis script
- GitHub Actions weekly workflow scaffold

## Run Locally

```bash
python3 backend/server.py
```

Then open:

```text
http://127.0.0.1:8000
```

The backend is implemented with Python's standard library. No API keys are required.

## Desktop Startup Shortcut

A macOS shortcut named `Start Stock App.command` can be placed on your Desktop. Double-click it to open Terminal, start the app, and open the local dashboard URL in your default browser.

For this MVP, the detected startup command is:

```bash
python3 -B backend/server.py
```

The detected local URL is:

```text
http://127.0.0.1:8000
```

To stop the app, click the Terminal window and press `Control + C`. The Terminal window stays open so you can read any errors.

If the browser does not open automatically, copy the local URL shown in Terminal and paste it into your browser manually.

## Add Tickers

Open `Watchlist Detail`, enter a supported ticker, and click `Add`. The MVP supports:

- U.S.-listed stocks, such as `NVDA`, `MSFT`, `GOOGL`, `AAPL`
- U.S.-listed ETFs, such as `QQQ`, `SMH`, `VOO`, `VTI`
- Canada-listed CAD-traded ETFs ending in `.TO`, such as `VFV.TO`, `XQQ.TO`, `TEC.TO`

Unsupported assets such as CDRs, crypto, forex, options, futures, China A-shares, and Hong Kong stocks are intentionally out of scope.

## Record Transactions

Open `Portfolio / Holdings`, enter:

- ticker
- action: Buy or Sell
- shares
- price
- currency
- date
- notes

The app stores every transaction in `data/transactions.json`. It never overwrites history unless you explicitly edit or delete a ledger row.

## Holdings Calculation

Holdings are calculated from the transaction ledger:

- buys increase shares and cost basis
- sells reduce shares using average cost
- realized gain/loss is calculated when sells occur
- current value uses the latest available mock market price
- U.S. tickers are converted to CAD portfolio value using the configured mock FX rate
- portfolio weight is based on CAD-converted market value

## Portfolio Weight

By default, portfolio weight is shown as information only. A ticker can still be recommended when it already represents a large part of the portfolio if the score and rule-based opportunity are attractive.

Target allocation mode is optional and off by default. If enabled in `Settings`, the app can show target allocation fields and above/below-target context.

## Plan B Allocation

Plan B is not generated just because a position has a high portfolio weight. It appears when you manually click `Skip` on a recommendation or when an explicit setting/rule excludes a ticker.

1. core ETFs
2. CAD-traded ETFs when preferred
3. ETFs already eligible under current settings
4. eligible watchlist tickers
5. cash reserve when there is no suitable alternative

Plan B is shown alongside the main recommendation when active. It does not replace it.

## Optional API Keys Later

Copy `.env.example` to `.env` later if you enable optional providers:

```bash
cp .env.example .env
```

All API keys are optional. The MVP runs normally without them.

## Run Weekly Analysis Manually

```bash
python3 scripts/run_weekly_analysis.py
```

This refreshes:

- `data/weekly_picks.json`
- `data/watchlist_analysis.json`
- `data/holdings.json`
- `data/recommendation_snapshot.json`
- `reports/YYYY-MM-DD-weekly-report.md`

## Enable GitHub Actions Later

The workflow is in `.github/workflows/weekly-analysis.yml`.

After pushing this project to GitHub, enable Actions and run `Weekly TFSA Analysis` manually or keep the weekly schedule. It works with mock/yfinance-compatible rule-based analysis and does not require API keys.

## Disclaimer

This project is for personal research and educational use only. It does not provide financial advice and does not predict exact market tops or bottoms. Use brokerage tools and professional advice before making investment decisions.
