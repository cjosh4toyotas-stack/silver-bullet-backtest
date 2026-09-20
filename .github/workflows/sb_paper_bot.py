#!/usr/bin/env python3
"""
Silver Bullet v3 — automated PAPER trading bot (SPY/QQQ proxies).

Trades the v3 spec selected 2026-09-19, using ETF proxies while futures
permissions are pending:

    SPY (proxy for ES):  NYMEX open 9-10a ET   .. 1R target
                         Pre-settle 1:30-2:30p .. 1R target
                         London 3-4a ET        .. 2R target   (pre-market)
    QQQ (proxy for NQ):  Midday 12-1p ET       .. 1R target
    CL: not traded (no profitable configuration in the data)

Detection logic is a line-for-line port of update.py rules v1.1
(sweep of prior 2h extreme -> FVG with displacement -> limit at gap edge,
stop beyond sweep, R-multiple target, 2h time exit, one trade per window).

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
MAX_POSITION_VALUE = 400_000.0    # sanity cap on notional per trade
POLL_SECONDS = 20
KILL_FILE = os.path.join(HERE, "STOP")
JOURNAL = os.path.join(HERE, "sb_bot_journal.csv")

# Strategy constants — must match update.py rules v1.1
LOOKBACK = 24            # bars (2h of 5-min) for the sweep reference extreme
MAX_HOLD = 24            # bars (2h) max hold after fill
TICK = 0.01              # ETF tick

def min_gap(p):  return max(0.01, p * 1.7e-5)    # relative thresholds, as ES/CL
def max_stop(p): return p * 0.002

# (symbol, window name, window start in minutes after NY midnight, target R)
LEGS = [
    ("SPY", "London 3-4a",          180, 2.0),
    ("SPY", "NYMEX open 9-10a",     540, 1.0),
    ("QQQ", "Midday 12-1p",         720, 1.0),
    ("SPY", "Pre-settle 1:30-2:30p", 810, 1.0),
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
                 tick=TICK, min_gap_fn=min_gap, max_stop_fn=max_stop):
    """Given completed 5-min bars (dicts with ny/o/h/l/c), return the v3 setup
    for `day`'s window starting at `wmin` minutes after NY midnight, or None.
    Identical decision path to update.py run_backtest up to order placement."""
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


def place_bracket(ib, contract, setup, target_r):
    risk = setup["risk"]
    qty = int(RISK_DOLLARS / risk)
    if qty < 1:
        log("qty < 1 — risk too wide for RISK_DOLLARS, skipping")
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
            "tp_id": tp.orderId, "sl_id": sl.orderId}


def main():
    dry = "--dry-run" in sys.argv
    block = os.environ.get("SB_BLOCK", "").strip().lower() or None
    legs = LEGS
    block_end = None
    if block:
        if block not in BLOCKS:
            sys.exit(f"Unknown SB_BLOCK {block!r}; use one of {sorted(BLOCKS)}")
        b0, b1, wnames = BLOCKS[block]
        legs = [l for l in LEGS if l[1] in wnames]
        now = datetime.now(NY)
        block_end = (datetime(now.year, now.month, now.day, tzinfo=NY)
                     + timedelta(minutes=b1))
        if now >= block_end:
            log(f"Block {block} already over — nothing to do.")
            return
    ib = IB()
    for port in PAPER_PORTS:
        try:
            ib.connect("127.0.0.1", port, clientId=CLIENT_ID, timeout=8)
            break
        except Exception:
            continue
    if not ib.isConnected():
        sys.exit("Could not connect. Is IB Gateway (paper) or TWS (paper) "
                 "running with API enabled on port 4002/7497?")

    accounts = ib.managedAccounts()
    if not accounts or not all(a.startswith("DU") for a in accounts):
        ib.disconnect()
        sys.exit(f"SAFETY STOP: non-paper account detected ({accounts}). "
                 "This bot only ever runs against DU* paper accounts.")
    log(f"Connected. Paper account(s): {accounts}. "
        f"Mode: {'DRY RUN — no orders' if dry else 'LIVE PAPER'}"
        + (f". Block: {block} (ends {block_end:%H:%M} ET)" if block else ""))
    ib.reqMarketDataType(1)

    contracts = {}
    for sym in {l[0] for l in legs}:
        c = Stock(sym, "SMART", "USD", primaryExchange="ARCA")
        ib.qualifyContracts(c)
        contracts[sym] = c

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

        # daily loss cutoff
        if not dry and halted_day != today:
            pnl = realized_pnl_today([f for f in ib.fills()
                                      if f.time.astimezone(NY).date() == today])
            if pnl <= -MAX_DAILY_LOSS:
                log(f"DAILY LOSS CUTOFF hit ({pnl:.0f}) — flattening, done for today.")
                flatten_all(ib)
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
            if m.get("fill_time") and now >= m["fill_time"] + timedelta(minutes=5 * MAX_HOLD):
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
                    ib.placeOrder(c, o)
                    log(f"TIME EXIT {m['symbol']} {m['window']} after 2h")
                open_mgmt.remove(m)

        # scan active windows
        if halted_day != today:
            for sym, wname, wmin, target_r in legs:
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
                setup = detect_setup(bars, today, wmin, target_r)
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
                placed = place_bracket(ib, contracts[sym], setup, target_r)
                if placed:
                    placed.update({"symbol": sym, "window": wname,
                                   "wclose": wclose, "fill_time": None})
                    open_mgmt.append(placed)

        # cloud mode: leave early once every window is closed and nothing is open
        if block and not open_mgmt:
            last_close = max(
                datetime(today.year, today.month, today.day, tzinfo=NY)
                + timedelta(minutes=wmin + 60) for _, _, wmin, _ in legs)
            if now > last_close and not any(
                    p.position for p in ib.positions()
                    if p.contract.symbol in contracts):
                log(f"Block {block}: all windows closed, nothing open — done.")
                break

        ib.sleep(POLL_SECONDS)

    ib.disconnect()


if __name__ == "__main__":
    main()
