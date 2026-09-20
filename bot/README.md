# Silver Bullet v3 — Paper Trading Bot

Automates the v3 spec on your IBKR **paper** account (DUT146048) using ETF
proxies while futures permissions are pending: SPY stands in for ES, QQQ for
NQ. The detection code is a verified line-for-line port of the backtest
engine (53/53 historical trades reproduced exactly).

## What it trades

| Proxy | Window (ET)            | Target | Notes                      |
|-------|------------------------|--------|----------------------------|
| SPY   | London 3:00–4:00a      | 2R     | pre-market — see caveats   |
| SPY   | NYMEX open 9:00–10:00a | 1R     | first 30 min is pre-market |
| QQQ   | Midday 12:00–1:00p     | 1R     |                            |
| SPY   | Pre-settle 1:30–2:30p  | 1R     |                            |

One trade max per window per day. Sweep of the prior 2h extreme → fair value
gap with displacement → limit at the gap edge, stop beyond the sweep, R
target, 2-hour time exit. Weekends skipped.

## One-time setup (~15 minutes)

1. **Install IB Gateway** (lighter than TWS): ibkr.com → Trading → API
   Software → IB Gateway → download the macOS "stable" build and install.
2. **Log in to Gateway** choosing **IB API** mode and **Paper Trading**,
   username `vmkosj470`. The title bar must say *Simulated Trading*.
3. **Enable the API**: Gateway → Configure → Settings → API → Settings:
   - check "Enable ActiveX and Socket Clients"
   - socket port **4002**
   - UNCHECK "Read-Only API" (the bot must place paper orders)
   - add `127.0.0.1` to Trusted IPs
4. **Install the Python library**: open Terminal and run
   `pip3 install ib_async`

## Running it

From Terminal, in this folder:

    python3 sb_paper_bot.py --dry-run    # first day: signals only, no orders
    python3 sb_paper_bot.py              # live paper trading

Leave it running in a Terminal window with Gateway open. It sleeps between
windows and polls every 20 seconds during them. Everything it does is echoed
to the window, appended to `sb_bot.log`, and each signal/trade is written to
`sb_bot_journal.csv`.

**Recommended first step:** run `--dry-run` for a day or two and compare its
logged signals against the site's blotter before letting it place orders.

## Stopping it

- `Ctrl-C` in the Terminal window, or
- create an empty file named `STOP` in this folder (`touch STOP`) — the bot
  flattens all positions, cancels all orders, and exits. Delete the file
  before restarting.

## Built-in guardrails

- **Paper-only lock**: exits immediately unless every account starts with
  `DU`. Only connects to paper API ports (4002/7497), never live ports.
- **Risk per trade**: $1,000 (0.1% of the $1M sim account) — `RISK_DOLLARS`
  at the top of the script.
- **Daily cutoff**: stops trading and flattens at −$2,000 realized on the day
  (`MAX_DAILY_LOSS`).
- **Position cap**: $400k notional per trade (`MAX_POSITION_VALUE`).

## Caveats

- **Your Mac must be awake** with Gateway running, or a window simply doesn't
  trade. System Settings → prevent sleep, or use the `caffeinate` command.
- **Gateway auto-logoff**: by default it restarts nightly (Configure →
  Settings → Lock and Exit). Set auto-restart so the 3 a.m. London window
  isn't missed.
- **London window is pre-market** for SPY: spreads are wider and the paper
  fill simulator is optimistic there. Treat London results with extra
  skepticism.
- **One session rule**: Gateway's paper login and the Client Portal paper
  login share credentials — logging into the portal while the bot runs will
  disconnect Gateway. Check positions on the site/TWS mobile instead, or
  accept the reconnect.
- **Proxy drift**: SPY/QQQ track ES/NQ closely but not perfectly (dividends,
  cash-session gaps). When futures permissions come through, switch to MES /
  MNQ micros and retire the proxies.
- This validates the **algorithm**. The walk-forward verdict it's built on is
  +2.87R over 16 trades — thin and front-loaded. Paper is exactly where this
  belongs.
