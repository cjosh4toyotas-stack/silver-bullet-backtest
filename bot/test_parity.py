#!/usr/bin/env python3
"""Parity check: the bot's detect_setup must reproduce every v3 trade the
backtest engine (update.py) finds on the same historical bars.

Run from the repo root:  python3 bot/test_parity.py
(needs update.py in the repo root and data/ populated)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import update as U                      # backtest engine
import sb_paper_bot as B                # live bot

V3 = {
    "NQ": [(("Midday 12-1p", 720), 1.0)],
    "ES": [(("NYMEX open 9-10a", 540), 1.0),
           (("Pre-settle 1:30-2:30p", 810), 1.0),
           (("London 3-4am", 180), 2.0)],
}
DATA = {"NQ": os.path.join(ROOT, "data", "NQF-continuous.csv"),
        "ES": os.path.join(ROOT, "data", "markets", "ES.csv")}

fails = checked = 0
for mkt, legs in V3.items():
    bars = U.read_bars_csv(DATA[mkt])
    cfg = U.MARKETS[mkt]
    for (wname, wmin), tgt in legs:
        trades = U.run_backtest(bars, mkt, market=mkt,
                                variant={"target_r": tgt, "stop_mode": "sweep"},
                                windows=[(wname, wmin)])
        for t in trades:
            day = U.datetime.strptime(t["day"], "%Y-%m-%d").date()
            s = B.detect_setup(bars, day, wmin, tgt, tick=cfg["tick"],
                               min_gap_fn=cfg["min_gap"],
                               max_stop_fn=cfg["max_stop"])
            checked += 1
            ok = (s is not None
                  and s["bias"] == t["bias"]
                  and abs(s["entry"] - t["entry"]) < 1e-6
                  and abs(s["stop"] - t["stop"]) < 1e-6
                  and abs(s["target"] - t["target"]) < 0.011)
            if not ok:
                fails += 1
                print(f"MISMATCH {mkt} {t['day']} {wname}: backtest={t['bias']} "
                      f"e{t['entry']} s{t['stop']} t{t['target']} bot={s}")

print(f"\n{checked} backtest trades checked against bot detector, "
      f"{fails} mismatches")
sys.exit(1 if fails else 0)
