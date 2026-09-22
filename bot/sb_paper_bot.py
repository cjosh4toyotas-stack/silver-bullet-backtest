#!/usr/bin/env python3
"""
Silver Bullet v4 — automated PAPER trading bot (SPY/QQQ proxies).

v4 (tuned 2026-09-22 on ES/NQ 5-min data, Jun 9 - Aug 31 train,
Sep 1-22 holdout; v3 stays the spec for real futures):

    SPY (proxy for ES):  London 3-4a ET        .. 3R, stop at sweep, 2h hold
                         NYMEX open 9-10a      .. 3R, stop at sweep, 1h hold,
                                                  breakeven at +1R, stop cap 0.15%
                         Pre-settle 1:30-2:30p .. 3R, stop at GAP edge, 3h hold
    QQQ (proxy for NQ):  Midday 12-1p ET       .. v3 kept (1R, sweep, 2h) -
                                                  tuned params lost the holdout
    CL: not traded (no profitable configuration in the data)

Detection logic is a line-for-line port of update.py rules v1.1
(sweep of prior 2h extreme -> FVG with displacement -> limit at gap edge,
stop beyond sweep or gap edge, R-multiple target, time exit, one
trade per window).

SAFETY:
  * Refuses to run unless every managed account starts with "DU" (paper).
  * Connects only to paper API ports (4002 IB Gateway paper, 7497 TWS paper).
  * One trade per window per day. Daily loss cutoff. Kill switch file.
  * --dry-run mode logs setups without sending any order.

Run:  python3 sb_paper_bot.py            (live paper trading)
      python3 sb_paper_bot.py --dry-run  (signals only, no orders)
Stop: create a file named STOP next to this script (flattens + exits),
      or Ctrl-C.
"""

import csv
import os
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

try:
    from ib_async import IB, Stock, LimitOrder, StopOrder, MarketOrder, util
except ImportError:
    try:
        from ib_insync import IB, Stock, LimitOrder, StopOrder, MarketOrder, util
    except ImportError:
        sys.exit("Install the API library first:  pip3 install ib_async")

NY = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------- configuration ----------------
PAPER_PORTS = [4002, 7497]        # IB Gateway paper, TWS paper. NEVER 4001/7496.
CLIENT_ID = 7
RISK_DOLLARS = 1000.0             # $ risked per trade (0.1% of the $1M sim account)
MAX_DAILY_LOSS = 2000.0           # stop trading for the day at -$2,000 realized
WEEK_LOSS_HALT = 5000.0           # circuit breaker: halt if last 7 days <= -$5,000
TOTAL_LOSS_HALT = 10000.0         # circuit breaker: halt if all-time <= -$10,000

# Tiered drawdown breakers (fire on actual P&L, % of account equity):
#   daily DD > 2%  -> all position sizes cut 50% for the rest of the day
#   daily DD > 3%  -> close ALL, halt rest of day
#   weekly DD > 5% -> sizes cut 50% for the rest of the ISO week
#   weekly DD > 7% -> close ALL, halt rest of week
#   peak DD > 10%  -> halt ALL trading; a "halted" row is written to the
#                     journal and trading stays halted until that row is
#                     manually deleted from data/bot_journal.csv
DAILY_DD_REDUCE, DAILY_DD_HALT = 0.02, 0.03
WEEK_DD_REDUCE, WEEK_DD_HALT = 0.05, 0.07
PEAK_DD_HALT = 0.10
MAX_RISK_PCT = 0.01               # hard cap: risk per trade <= 1% of equity
MAX_POSITION_VALUE = 400_000.0    # sanity cap on notional per trade
POLL_SECONDS = 20
KILL_FILE = os.path.join(HERE, "STOP")
JOURNAL = os.path.join(HERE, "sb_bot_journal.csv")

# Strategy constants — must match update.py rules v1.1
LOOKBACK = 24            # bars (2h of 5-min) for the sweep reference extreme
MAX_HOLD = 24            # bars (2h) default max hold after fill
TICK = 0.01              # ETF tick

def min_gap(p):  return max(0.01, p * 1.7e-5)    # relative thresholds, as ES/CL
def max_stop(p): return p * 0.002

# v4 legs. Each dict: window start in minutes after NY midnight, target R,
# stop_mode ("sweep" = beyond the sweep extreme, "gap" = beyond the far gap
# edge), max_hold in 5-min bars, breakeven (move stop to entry once +1R
# trades), stop_frac (max stop distance as fraction of price).
LEGS = [
    {"sym": "SPY", "window": "London 3-4a",           "wmin": 180,
     "target_r": 3.0, "stop_mode": "sweep", "max_hold": 24,
     "breakeven": False, "stop_frac": 0.002},
    {"sym": "SPY", "window": "NYMEX open 9-10a",      "wmin": 540,
     "target_r": 3.0, "stop_mode": "sweep", "max_hold": 12,
     "breakeven": True,  "stop_frac": 0.0015},
    {"sym": "QQQ", "window": "Midday 12-1p",          "wmin": 720,
     "target_r": 1.0, "stop_mode": "sweep", "max_hold": 24,
     "breakeven": False, "stop_frac": 0.002},   # v3 kept: beat tuned on holdout
    {"sym": "SPY", "window": "Pre-settle 1:30-2:30p", "wmin": 810,
     "target_r": 3.0, "stop_mode": "gap",   "max_hold": 36,
     "breakeven": False, "stop_frac": 0.002},
]
PROXY_OF = {"SPY": "ES", "QQQ": "NQ"}

# Cloud "block" mode: GitHub Actions runs one block per job. SB_BLOCK env
# selects the legs and sets a hard end-of-block flatten. (minutes after NY
# midnight: start, end, window names)
BLOCKS = {
    "london":    (145, 370, ["London 3-4a"]),
    "morning":   (505, 688, ["NYMEX open 9-10a"]),
    "afternoon": (689, 995, ["Midday 12-1p", "Pre-settle 1:30-2:30p"]),
}

# ---------------- detection (ported verbatim from update.py) ----------------

def find_sweep(bars, i0, i1):
    for i in range(max(i0, LOOKBACK), i1):
        window = bars[i - LOOKBACK:i]
        ref_low = min(b["l"] for b in window)
        ref_high = max(b["h"] for b in window)
        b = bars[i]
        if b["l"] < ref_low and b["c"] > ref_low:
            return i, "bull", b["l"]
        if b["h"] > ref_high and b["c"] < ref_high:
            return i, "bear", b["h"]
    return None


def find_fvg(bars, start, end, bias, min_gap_fn):
    for k in range(max(start, 2), end):
        c1, c2, c3 = bars[k - 2], bars[k - 1], bars[k]
        gap_min = min_gap_fn(c2["c"])
        if bias == "bull" and c3["l"] - c1["h"] >= gap_min and c2["c"] > c2["o"]:
            return k, c1["h"], c3["l"]
        if bias == "bear" and c1["l"] - c3["h"] >= gap_min and c2["c"] < c2["o"]:
            return k, c1["l"], c3["h"]
    return None


def detect_setup(bars, day, wmin, target_r,
                 tick=TICK, min_gap_fn=min_gap, max_stop_fn=max_stop,
                 stop_mode="sweep"):
    """Given completed 5-min bars (dicts with ny/o/h/l/c), return the setup
    for `day`'s window starting at `wmin` minutes after NY midnight, or None.
    Identical decision path to update.py run_backtest up to order placement.
    stop_mode "sweep" places the stop beyond the sweep extreme (v3);
    "gap" places it beyond the far gap edge (v4 pre-settle leg)."""
    wopen = datetime(day.year, day.month, day.day, tzinfo=NY) + timedelta(minutes=wmin)
    wclose = wopen + timedelta(hours=1)
    scan_start = wopen - timedelta(minutes=30)
    idx = [i for i, b in enumerate(bars) if scan_start <= b["ny"] < wclose]
    if not idx:
        return None
    i0, i1 = idx[0], idx[-1] + 1
    win_idx = [i for i in idx if bars[i]["ny"] >= wopen]
    if len(win_idx) < 4:
        return None
    sw = find_sweep(bars, i0, i1)
    if not sw:
        return None
    si, bias, sweep_ext = sw
    fvg = find_fvg(bars, max(si + 1, win_idx[0]), i1, bias, min_gap_fn)
    if not fvg:
        return None
    fi, gfar, gnear = fvg
    entry = gnear
    if stop_mode == "gap":
        stop = gfar - tick if bias == "bull" else gfar + tick
    else:
        stop = sweep_ext - tick if bias == "bull" else sweep_ext + tick
    if bias == "bull" and stop >= entry:
        return None
    if bias == "bear" and stop <= entry:
        return None
    risk = abs(entry - stop)
    if risk <= 0 or risk > max_stop_fn(entry):
        return None
    tgt = entry + target_r * risk if bias == "bull" else entry - target_r * risk
    return {
        "bias": bias, "entry": round(entry, 2), "stop": round(stop, 2),
        "target": round(tgt, 2), "risk": risk,
        "sweep_time": bars[si]["ny"], "fvg_time": bars[fi]["ny"],
        "wopen": wopen, "wclose": wclose,
    }


# ---------------- live plumbing ----------------

def log(msg):
    line = f"[{datetime.now(NY):%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(os.path.join(HERE, "sb_bot.log"), "a") as f:
        f.write(line + "\n")


def journal_row(row):
    new = not os.path.exists(JOURNAL)
    with open(JOURNAL, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "date", "proxy", "market", "window", "bias", "qty", "entry",
            "stop", "target", "exit", "outcome", "pts", "r", "dollars"])
        if new:
            w.writeheader()
        w.writerow(row)


def record_close(m, entry_px, exit_px, outcome):
    """Journal a completed trade with realized numbers."""
    sign = 1 if m["side"] == "BUY" else -1
    pts = (exit_px - entry_px) * sign
    dollars = pts * m["qty"]
    r = pts / m["risk"] if m["risk"] else 0.0
    journal_row({
        "date": str(datetime.now(NY).date()), "proxy": m["symbol"],
        "market": PROXY_OF[m["symbol"]], "window": m["window"],
        "bias": "bull" if m["side"] == "BUY" else "bear", "qty": m["qty"],
        "entry": round(entry_px, 2), "stop": "", "target": "",
        "exit": round(exit_px, 2), "outcome": outcome,
        "pts": round(pts, 2), "r": round(r, 2), "dollars": round(dollars, 2)})
    log(f"CLOSED {m['symbol']} {m['window']} {outcome} {pts:+.2f} pts "
        f"({r:+.2f}R, ${dollars:+.0f})")


def journal_rows():
    """All journal rows, local + the repo copy cloud runs commit, deduped."""
    rows, seen = [], set()
    repo_journal = os.path.join(os.path.dirname(HERE), "data", "bot_journal.csv")
    for p in (JOURNAL, repo_journal):
        if os.path.exists(p):
            with open(p) as f:
                for r in csv.DictReader(f):
                    key = tuple(sorted(r.items()))
                    if key not in seen:
                        seen.add(key)
                        rows.append(r)
    return rows


def _dollars(r):
    try:
        return float(r.get("dollars") or 0)
    except ValueError:
        return 0.0


def log_breaker(kind, detail, equity, closed_positions, halt_row=False):
    """Log every trigger: breaker type, actual DD, equity, positions closed."""
    log(f"BREAKER {kind}: {detail} · equity ${equity:,.0f} · "
        f"positions closed: {closed_positions}")
    if halt_row:
        # a 'halted' row persists via the journal commit; deleting it from
        # data/bot_journal.csv is the manual reset the peak breaker requires
        already = any(r.get("outcome") == "halted" and r.get("window") == kind
                      for r in journal_rows())
        if not already:
            journal_row({"date": str(datetime.now(NY).date()), "proxy": "-",
                         "market": "-", "window": kind, "bias": "-", "qty": "",
                         "entry": "", "stop": "", "target": "", "exit": "",
                         "outcome": "halted", "pts": "", "r": "", "dollars": ""})


def risk_state(equity, intraday_pnl=0.0):
    """Evaluate the tiered breakers. Returns (halt_reason|None, size_factor)."""
    rows = [r for r in journal_rows() if r.get("outcome") not in
            (None, "", "signal", "halted")]
    today = datetime.now(NY).date()
    iso = today.isocalendar()

    if any(r.get("outcome") == "halted" and str(r.get("window", "")).startswith("PEAK")
           for r in journal_rows()):
        return ("PEAK-DD lock present in journal — manual deletion required "
                "to resume"), 0.0

    day_pnl = sum(_dollars(r) for r in rows if r.get("date") == str(today))
    day_pnl = min(day_pnl, day_pnl + intraday_pnl)  # include live fills if worse
    week_pnl = 0.0
    cum, peak, by_date = 0.0, 0.0, sorted(rows, key=lambda r: r.get("date") or "")
    for r in by_date:
        cum += _dollars(r)
        peak = max(peak, cum)
        d = r.get("date") or ""
        try:
            dt = datetime.strptime(d, "%Y-%m-%d").date()
            if dt.isocalendar()[:2] == iso[:2]:
                week_pnl += _dollars(r)
        except ValueError:
            pass
    peak_dd = (peak - cum) / equity if equity else 0.0
    day_dd = max(0.0, -day_pnl) / equity if equity else 0.0
    week_dd = max(0.0, -week_pnl) / equity if equity else 0.0

    if peak_dd > PEAK_DD_HALT:
        return f"peak drawdown {peak_dd*100:.1f}% > {PEAK_DD_HALT*100:.0f}%", 0.0
    if week_dd > WEEK_DD_HALT:
        return f"weekly drawdown {week_dd*100:.1f}% > {WEEK_DD_HALT*100:.0f}%", 0.0
    if day_dd > DAILY_DD_HALT:
        return f"daily drawdown {day_dd*100:.1f}% > {DAILY_DD_HALT*100:.0f}%", 0.0
    factor = 1.0
    if day_dd > DAILY_DD_REDUCE or week_dd > WEEK_DD_REDUCE:
        factor = 0.5
    return None, factor


def circuit_breaker_reason():
    """Cumulative kill switch: reads the full journal history (local + the
    repo copy that cloud runs commit) and halts on sustained losses. Trips
    without any manual monitoring; resets only by editing the limits or the
    journal, which is deliberate."""
    closed = [r for r in journal_rows()
              if r.get("outcome") not in (None, "", "signal", "halted")]
    total = sum(_dollars(r) for r in closed)
    cutoff = str((datetime.now(NY) - timedelta(days=7)).date())
    recent = sum(_dollars(r) for r in closed if (r.get("date") or "") >= cutoff)
    if recent <= -WEEK_LOSS_HALT:
        return f"7-day realized PnL ${recent:,.0f} breached -${WEEK_LOSS_HALT:,.0f}"
    if total <= -TOTAL_LOSS_HALT:
        return f"all-time realized PnL ${total:,.0f} breached -${TOTAL_LOSS_HALT:,.0f}"
    return None


def fetch_bars(ib, contract):
    """Completed 5-min bars for today + yesterday, NY timestamps."""
    raw = ib.reqHistoricalData(
        contract, endDateTime="", durationStr="2 D", barSizeSetting="5 mins",
        whatToShow="TRADES", useRTH=False, formatDate=2)
    bars = []
    for b in raw:
        t = b.date if isinstance(b.date, datetime) else None
        if t is None:
            continue
        bars.append({"ny": t.astimezone(NY), "o": b.open, "h": b.high,
                     "l": b.low, "c": b.close})
    # drop the still-forming bar
    now = datetime.now(NY)
    if bars and bars[-1]["ny"] + timedelta(minutes=5) > now:
        bars.pop()
    return bars


def kill_requested():
    return os.path.exists(KILL_FILE)


def flatten_all(ib):
    for tr in list(ib.openTrades()):
        ib.cancelOrder(tr.order)
    ib.sleep(1)
    for pos in ib.positions():
        if pos.position == 0:
            continue
        c = pos.contract
        c.exchange = "SMART"
        action = "SELL" if pos.position > 0 else "BUY"
        o = MarketOrder(action, abs(pos.position))
        o.outsideRth = True
        ib.placeOrder(c, o)
        log(f"FLATTEN {action} {abs(pos.position)} {c.symbol}")
    ib.sleep(2)


def realized_pnl_today(fills):
    """Realized $ from this bot's fills today (FIFO per symbol)."""
    from collections import deque
    lots, pnl = {}, 0.0
    for f in sorted(fills, key=lambda f: f.time):
        sym = f.contract.symbol
        q = f.execution.shares * (1 if f.execution.side == "BOT" else -1)
        px = f.execution.price
        dq = lots.setdefault(sym, deque())
        while q != 0:
            if not dq or (dq[0][0] > 0) == (q > 0):
                dq.append((q, px)); break
            oq, opx = dq.popleft()
            m = min(abs(q), abs(oq))
            pnl += m * (px - opx) * (1 if oq > 0 else -1)
            oq += m * (1 if q > 0 else -1)
            q -= m * (1 if q > 0 else -1)
            if oq != 0:
                dq.appendleft((oq, opx))
    return pnl


def place_bracket(ib, contract, setup, target_r, equity=1_000_000.0, size_factor=1.0):
    risk = setup["risk"]
    # every position has a stop by construction (bracket); risk is capped at
    # the smaller of RISK_DOLLARS and 1% of account equity, then scaled by
    # any breaker-imposed size reduction
    risk_budget = min(RISK_DOLLARS, MAX_RISK_PCT * equity) * size_factor
    qty = int(risk_budget / risk)
    if size_factor < 1.0:
        log(f"size reduced x{size_factor} by drawdown breaker")
    if qty < 1:
        log("qty < 1 — risk too wide for the risk budget, skipping")
        return None
    if qty * setup["entry"] > MAX_POSITION_VALUE:
        qty = int(MAX_POSITION_VALUE / setup["entry"])
        log(f"qty capped by MAX_POSITION_VALUE to {qty}")
    side = "BUY" if setup["bias"] == "bull" else "SELL"
    exit_side = "SELL" if side == "BUY" else "BUY"

    parent = LimitOrder(side, qty, setup["entry"])
    parent.orderId = ib.client.getReqId()
    parent.outsideRth = True
    parent.transmit = False

    tp = LimitOrder(exit_side, qty, setup["target"])
    tp.orderId = ib.client.getReqId()
    tp.parentId = parent.orderId
    tp.outsideRth = True
    tp.transmit = False

    sl = StopOrder(exit_side, qty, setup["stop"])
    sl.orderId = ib.client.getReqId()
    sl.parentId = parent.orderId
    sl.outsideRth = True
    sl.triggerMethod = 7          # last price, so stops work pre-market
    sl.transmit = True            # transmits the whole chain

    ib.placeOrder(contract, parent)
    ib.placeOrder(contract, tp)
    trade_sl = ib.placeOrder(contract, sl)
    log(f"BRACKET {side} {qty} {contract.symbol} @ {setup['entry']} "
        f"stop {setup['stop']} target {setup['target']} ({target_r}R)")
    return {"parent_id": parent.orderId, "qty": qty, "side": side,
            "tp_id": tp.orderId, "sl_id": sl.orderId,
            "risk": risk, "entry_px": setup["entry"]}


def main():
    dry = "--dry-run" in sys.argv
    block = os.environ.get("SB_BLOCK", "").strip().lower() or None
    legs = LEGS
    block_end = None
    if block:
        if block not in BLOCKS:
            sys.exit(f"Unknown SB_BLOCK {block!r}; use one of {sorted(BLOCKS)}")
        b0, b1, wnames = BLOCKS[block]
        legs = [l for l in LEGS if l["window"] in wnames]
        now = datetime.now(NY)
        block_end = (datetime(now.year, now.month, now.day, tzinfo=NY)
                     + timedelta(minutes=b1))
        if now >= block_end:
            log(f"Block {block} already over — nothing to do.")
            return
    reason = circuit_breaker_reason()
    if reason:
        log(f"CIRCUIT BREAKER TRIPPED: {reason}. Trading halted — no orders "
            f"will be placed until the limits in this script are raised or "
            f"the journal is reviewed. This is deliberate.")
        return

    ib = IB()
    # Gateway's port opens before its IBKR login finishes, so keep knocking:
    # up to ~6 minutes of retries before giving up.
    last_err = None
    for attempt in range(24):
        for port in PAPER_PORTS:
            try:
                ib.connect("127.0.0.1", port, clientId=CLIENT_ID, timeout=15)
                break
            except Exception as e:
                last_err = e
        if ib.isConnected():
            break
        if attempt % 3 == 0:
            log(f"waiting for gateway API (attempt {attempt + 1}/24): {last_err}")
        time.sleep(10)
    if not ib.isConnected():
        sys.exit("Could not connect after ~6 min. Is IB Gateway (paper) or TWS "
                 "(paper) running with API enabled on port 4002/7497? "
                 "If this is a cloud run, the gateway login may have failed - "
                 "check credentials/2FA on the paper account.")

    accounts = ib.managedAccounts()
    if not accounts or not all(a.startswith("DU") for a in accounts):
        ib.disconnect()
        sys.exit(f"SAFETY STOP: non-paper account detected ({accounts}). "
                 "This bot only ever runs against DU* paper accounts.")
    log(f"Connected. Paper account(s): {accounts}. "
        f"Mode: {'DRY RUN — no orders' if dry else 'LIVE PAPER'}"
        + (f". Block: {block} (ends {block_end:%H:%M} ET)" if block else ""))
    ib.reqMarketDataType(1)

    equity = 1_000_000.0
    try:
        for row in ib.accountSummary():
            if row.tag == "NetLiquidation":
                equity = float(row.value)
                break
        log(f"Account equity: ${equity:,.0f}")
    except Exception as e:
        log(f"equity fetch failed ({e}) — using ${equity:,.0f}")
    try:
        # picked up by the workflow and shown on the IBKR page
        with open(os.path.join(HERE, "sb_equity.txt"), "w") as f:
            f.write(f"{equity:.2f}")
    except OSError as e:
        log(f"equity file write failed: {e}")

    contracts = {}
    tickers = {}
    for sym in {l["sym"] for l in legs}:
        c = Stock(sym, "SMART", "USD", primaryExchange="ARCA")
        ib.qualifyContracts(c)
        contracts[sym] = c
        tickers[sym] = ib.reqMktData(c, "", False, False)

    done = {}       # (date, window name) -> True once traded/attempted
    open_mgmt = []  # [{trade info for time-exit management}]
    halted_day = None

    while True:
        if kill_requested():
            log("Kill switch found — flattening and exiting.")
            if not dry:
                flatten_all(ib)
            break
        now = datetime.now(NY)
        today = now.date()

        if block_end and now >= block_end:
            log(f"Block {block} over — flattening and exiting.")
            if not dry:
                flatten_all(ib)
            break

        # risk layer: fixed daily cutoff + tiered drawdown breakers
        intraday = 0.0
        if not dry:
            intraday = realized_pnl_today([f for f in ib.fills()
                                           if f.time.astimezone(NY).date() == today])
            if intraday <= -MAX_DAILY_LOSS and halted_day != today:
                log(f"DAILY LOSS CUTOFF hit ({intraday:.0f}) — flattening, done for today.")
                flatten_all(ib)
                halted_day = today
        halt_reason, size_factor = risk_state(equity, intraday)
        if halt_reason:
            npos = sum(1 for p in ib.positions() if p.position)
            if not dry:
                flatten_all(ib)
            lower = halt_reason.lower()
            if "peak" in lower:
                log_breaker("PEAK-DD >10% HALT", halt_reason, equity, npos,
                            halt_row=not dry)
                log("Trading halted until the PEAK-DD 'halted' row is manually "
                    "deleted from data/bot_journal.csv.")
                break
            if "week" in lower:
                log_breaker("WEEK-DD HALT", halt_reason, equity, npos)
                log("Halted for the rest of the ISO week.")
                break
            log_breaker("DAY-DD HALT", halt_reason, equity, npos)
            halted_day = today

        # manage open trades: cancel unfilled at window close, time-exit at 2h
        for m in list(open_mgmt):
            tr = next((t for t in ib.trades()
                       if t.order.orderId == m["parent_id"]), None)
            if tr is None:
                open_mgmt.remove(m); continue
            status = tr.orderStatus.status
            if status in ("Cancelled", "ApiCancelled", "Inactive"):
                open_mgmt.remove(m); continue
            filled = tr.orderStatus.filled or 0
            if filled == 0 and now >= m["wclose"]:
                ib.cancelOrder(tr.order)
                log(f"Window over, entry unfilled — cancelled {m['symbol']} {m['window']}")
                open_mgmt.remove(m); continue
            if filled > 0 and m.get("fill_time") is None:
                m["fill_time"] = now
                log(f"FILLED {m['symbol']} {m['window']} x{filled}")
            if not m.get("fill_time"):
                continue
            entry_px = tr.orderStatus.avgFillPrice or m["entry_px"]
            # time-exit market order resolving?
            ct = m.get("closing")
            if ct is not None:
                if ct.orderStatus.status == "Filled":
                    record_close(m, entry_px, ct.orderStatus.avgFillPrice, "time")
                    open_mgmt.remove(m)
                continue
            # closed by the bracket?
            done_close = False
            for oid, oc in ((m["tp_id"], "target"), (m["sl_id"], "stop")):
                t2 = next((t for t in ib.trades()
                           if t.order.orderId == oid), None)
                if t2 and t2.orderStatus.status == "Filled":
                    record_close(m, entry_px, t2.orderStatus.avgFillPrice, oc)
                    open_mgmt.remove(m)
                    done_close = True
                    break
            if done_close:
                continue
            # v4 breakeven: once price trades +1R in our favor, move the
            # resting stop to entry (engine arms it and applies from then on)
            if m.get("breakeven") and not m.get("be_armed"):
                tk = tickers.get(m["symbol"])
                px = None
                if tk is not None:
                    for cand in (tk.last, tk.close):
                        if cand and cand > 0:
                            px = cand
                            break
                if px is not None:
                    up = m["side"] == "BUY"
                    trig = (m["entry_px"] + m["risk"] if up
                            else m["entry_px"] - m["risk"])
                    if (px >= trig) if up else (px <= trig):
                        t2 = next((t for t in ib.openTrades()
                                   if t.order.orderId == m["sl_id"]), None)
                        if t2 is not None:
                            t2.order.auxPrice = round(m["entry_px"], 2)
                            ib.placeOrder(contracts[m["symbol"]], t2.order)
                            m["be_armed"] = True
                            log(f"BREAKEVEN {m['symbol']} {m['window']}: "
                                f"stop moved to entry {m['entry_px']}")
            if now >= m["fill_time"] + timedelta(
                    minutes=5 * m.get("max_hold", MAX_HOLD)):
                pos = next((p for p in ib.positions()
                            if p.contract.symbol == m["symbol"] and p.position != 0), None)
                if pos:
                    for t2 in ib.openTrades():
                        if t2.order.orderId in (m["tp_id"], m["sl_id"]):
                            ib.cancelOrder(t2.order)
                    ib.sleep(1)
                    c = contracts[m["symbol"]]
                    o = MarketOrder("SELL" if pos.position > 0 else "BUY",
                                    abs(pos.position))
                    o.outsideRth = True
                    m["closing"] = ib.placeOrder(c, o)
                    log(f"TIME EXIT {m['symbol']} {m['window']} after "
                        f"{m.get('max_hold', MAX_HOLD) * 5} min")
                else:
                    open_mgmt.remove(m)

        # scan active windows
        if halted_day != today:
            for leg in legs:
                sym, wname = leg["sym"], leg["window"]
                wmin, target_r = leg["wmin"], leg["target_r"]
                key = (str(today), wname)
                if key in done:
                    continue
                wopen = datetime(today.year, today.month, today.day,
                                 tzinfo=NY) + timedelta(minutes=wmin)
                scan_start = wopen - timedelta(minutes=30)
                wclose = wopen + timedelta(hours=1)
                if not (scan_start <= now < wclose) or now.weekday() >= 5:
                    continue
                try:
                    bars = fetch_bars(ib, contracts[sym])
                except Exception as e:
                    log(f"bar fetch failed for {sym}: {e}")
                    continue
                sf = leg["stop_frac"]
                setup = detect_setup(bars, today, wmin, target_r,
                                     max_stop_fn=lambda p, _sf=sf: p * _sf,
                                     stop_mode=leg["stop_mode"])
                if not setup:
                    continue
                done[key] = True
                log(f"SETUP {sym} {wname}: {setup['bias']} entry {setup['entry']} "
                    f"stop {setup['stop']} target {setup['target']} "
                    f"(sweep {setup['sweep_time']:%H:%M}, fvg {setup['fvg_time']:%H:%M})")
                journal_row({
                    "date": str(today), "proxy": sym, "market": PROXY_OF[sym],
                    "window": wname, "bias": setup["bias"], "qty": "",
                    "entry": setup["entry"], "stop": setup["stop"],
                    "target": setup["target"], "exit": "", "outcome": "signal",
                    "pts": "", "r": "", "dollars": ""})
                if dry:
                    continue
                placed = place_bracket(ib, contracts[sym], setup, target_r,
                                       equity=equity, size_factor=size_factor)
                if placed:
                    placed.update({"symbol": sym, "window": wname,
                                   "wclose": wclose, "fill_time": None,
                                   "max_hold": leg["max_hold"],
                                   "breakeven": leg["breakeven"],
                                   "be_armed": False})
                    open_mgmt.append(placed)

        # cloud mode: leave early once every window is closed and nothing is open
        if block and not open_mgmt:
            last_close = max(
                datetime(today.year, today.month, today.day, tzinfo=NY)
                + timedelta(minutes=l["wmin"] + 60) for l in legs)
            if now > last_close and not any(
                    p.position for p in ib.positions()
                    if p.contract.symbol in contracts):
                log(f"Block {block}: all windows closed, nothing open — done.")
                break

        ib.sleep(POLL_SECONDS)

    ib.disconnect()


if __name__ == "__main__":
    main()
