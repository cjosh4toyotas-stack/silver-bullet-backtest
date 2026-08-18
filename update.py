#!/usr/bin/env python3
"""
Silver Bullet accumulating backtest pipeline.

Usage:
    python3 update.py --new NEW_BARS.csv --contract NQ202609
    python3 update.py            (re-run backtest on existing data only)

--new      CSV of fresh 5-min bars (columns: timestamp_utc,open,high,low,close,volume)
--contract label of the futures contract the new bars belong to (e.g. NQ202609).
           Data is stored per contract under data/<label>.csv so different
           contract months are never stitched into one price series (avoids
           artificial roll gaps).

Each run: merge new bars (dedupe by timestamp) -> run the mechanical Silver
Bullet rules over the FULL accumulated history of every contract -> dedupe
trades by (day, window) across contracts (prefer the contract with higher
volume that day) -> regenerate results.json, trades.csv, results/equity.svg,
README.md and report.html.

Mechanical rules (fixed since 2026-08-17, do not change without noting it):
windows 3-4AM / 10-11AM / 2-3PM NY; sweep = bar takes out prior 2h extreme and
closes back inside, scanned from 30min before window; first FVG (>=0.5pt,
displacement candle closes in bias direction) with 3rd candle in window after
sweep; limit entry at near gap edge, must fill before window close; stop 1
tick beyond sweep extreme (skip if risk>60pt or stop on wrong side of entry);
target 2R; 2h time exit; same-bar stop+target counts as loss; one trade per
window; $10 round-trip costs; $20/point.
"""
import argparse, csv, json, os, glob
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
TICK = 0.25
POINT_VALUE = 20.0
COST_RT_DOLLARS = 10.0
WINDOWS = [("London 3-4am", 3), ("AM 10-11am", 10), ("PM 2-3pm", 14)]
LOOKBACK = 24
PRE_WINDOW_BARS = 6
MAX_HOLD = 24
MAX_STOP_PTS = 60.0
MIN_GAP_PTS = 0.5
RULES_VERSION = "1.0 (2026-08-17)"

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
RESULTS_DIR = os.path.join(ROOT, "results")


# ---------- data handling ----------

def read_bars_csv(path):
    bars = []
    with open(path) as f:
        for row in csv.DictReader(f):
            ts = row["timestamp_utc"].strip().replace("Z", "+00:00")
            t = datetime.fromisoformat(ts)
            bars.append({
                "utc": t, "ny": t.astimezone(NY),
                "o": float(row["open"]), "h": float(row["high"]),
                "l": float(row["low"]), "c": float(row["close"]),
                "v": int(float(row.get("volume") or 0)),
            })
    return bars


def write_bars_csv(path, bars):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp_utc", "open", "high", "low", "close", "volume"])
        for b in bars:
            w.writerow([b["utc"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                        b["o"], b["h"], b["l"], b["c"], b["v"]])


def merge_bars(existing, new):
    by_ts = {b["utc"]: b for b in existing}
    added = 0
    for b in new:
        if b["utc"] not in by_ts:
            added += 1
        by_ts[b["utc"]] = b  # newer pull wins (finalizes in-progress bars)
    merged = sorted(by_ts.values(), key=lambda b: b["utc"])
    return merged, added


# ---------- strategy ----------

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


def find_fvg(bars, start, end, bias):
    for k in range(max(start, 2), end):
        c1, c2, c3 = bars[k - 2], bars[k - 1], bars[k]
        if bias == "bull" and c3["l"] - c1["h"] >= MIN_GAP_PTS and c2["c"] > c2["o"]:
            return k, c1["h"], c3["l"]
        if bias == "bear" and c1["l"] - c3["h"] >= MIN_GAP_PTS and c2["c"] < c2["o"]:
            return k, c1["l"], c3["h"]
    return None


def run_backtest(bars, contract):
    trades = []
    n = len(bars)
    days = sorted({b["ny"].date() for b in bars})
    for day in days:
        for wname, whour in WINDOWS:
            wopen = datetime(day.year, day.month, day.day, whour, 0, tzinfo=NY)
            wclose = wopen + timedelta(hours=1)
            scan_start = wopen - timedelta(minutes=30)
            idx = [i for i, b in enumerate(bars) if scan_start <= b["ny"] < wclose]
            if not idx:
                continue
            i0, i1 = idx[0], idx[-1] + 1
            win_idx = [i for i in idx if bars[i]["ny"] >= wopen]
            if len(win_idx) < 4:
                continue
            sw = find_sweep(bars, i0, i1)
            if not sw:
                continue
            si, bias, sweep_ext = sw
            fvg = find_fvg(bars, max(si + 1, win_idx[0]), i1, bias)
            if not fvg:
                continue
            fi, gfar, gnear = fvg
            entry = gnear
            stop = sweep_ext - TICK if bias == "bull" else sweep_ext + TICK
            if bias == "bull" and stop >= entry:
                continue
            if bias == "bear" and stop <= entry:
                continue
            risk = abs(entry - stop)
            if risk <= 0 or risk > MAX_STOP_PTS:
                continue
            tgt = entry + 2 * risk if bias == "bull" else entry - 2 * risk
            fill_i = None
            for j in range(fi + 1, i1):
                b = bars[j]
                if (b["l"] <= entry) if bias == "bull" else (b["h"] >= entry):
                    fill_i = j
                    break
            if fill_i is None:
                continue
            outcome, exit_px, exit_i = None, None, None
            for j in range(fill_i, min(fill_i + MAX_HOLD + 1, n)):
                b = bars[j]
                if bias == "bull":
                    hit_stop, hit_tgt = b["l"] <= stop, b["h"] >= tgt
                else:
                    hit_stop, hit_tgt = b["h"] >= stop, b["l"] <= tgt
                if hit_stop:
                    outcome, exit_px, exit_i = "stop", stop, j
                    break
                if hit_tgt:
                    outcome, exit_px, exit_i = "target", tgt, j
                    break
            if outcome is None:
                exit_i = min(fill_i + MAX_HOLD, n - 1)
                outcome, exit_px = "time", bars[exit_i]["c"]
            pts = (exit_px - entry) if bias == "bull" else (entry - exit_px)
            trades.append({
                "contract": contract,
                "day": str(day), "window": wname, "bias": bias,
                "sweep_time": bars[si]["ny"].strftime("%Y-%m-%d %H:%M"),
                "entry_time": bars[fill_i]["ny"].strftime("%Y-%m-%d %H:%M"),
                "exit_time": bars[exit_i]["ny"].strftime("%Y-%m-%d %H:%M"),
                "entry": entry, "stop": stop, "target": round(tgt, 2),
                "risk_pts": round(risk, 2), "outcome": outcome,
                "exit": round(exit_px, 2), "pts": round(pts, 2),
                "dollars": round(pts * POINT_VALUE - COST_RT_DOLLARS, 2),
            })
    return trades


def summarize(trades, label):
    if not trades:
        return {"label": label, "n": 0}
    wins = [t for t in trades if t["pts"] > 0]
    gross_w = sum(t["dollars"] for t in trades if t["dollars"] > 0)
    gross_l = -sum(t["dollars"] for t in trades if t["dollars"] < 0)
    eq, peak, mdd = 0.0, 0.0, 0.0
    for t in trades:
        eq += t["dollars"]
        peak = max(peak, eq)
        mdd = max(mdd, peak - eq)
    return {
        "label": label, "n": len(trades), "wins": len(wins),
        "win_rate": round(100 * len(wins) / len(trades), 1),
        "total_pts": round(sum(t["pts"] for t in trades), 2),
        "total_dollars": round(sum(t["dollars"] for t in trades), 2),
        "avg_dollars": round(sum(t["dollars"] for t in trades) / len(trades), 2),
        "profit_factor": (round(gross_w / gross_l, 2) if gross_l > 0 else None),
        "max_drawdown_dollars": round(mdd, 2),
        "stops": sum(1 for t in trades if t["outcome"] == "stop"),
        "targets": sum(1 for t in trades if t["outcome"] == "target"),
        "time_exits": sum(1 for t in trades if t["outcome"] == "time"),
    }


# ---------- outputs ----------

def equity_svg(trades, path):
    vals = [0.0]
    for t in trades:
        vals.append(vals[-1] + t["dollars"])
    W, H, ml, mr, mt, mb = 800, 260, 60, 20, 16, 28
    iw, ih = W - ml - mr, H - mt - mb
    lo, hi = min(vals), max(vals)
    span = max(hi - lo, 1.0)
    lo -= span * 0.08
    hi += span * 0.08
    def x(i):
        return ml + iw * (i / max(len(vals) - 1, 1))
    def y(v):
        return mt + ih * (1 - (v - lo) / (hi - lo))
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))
    grid = ""
    for gv in (0, lo + span * 0.5, hi - span * 0.16):
        pass
    lines = []
    step = max(round(span / 4 / 500) * 500, 500)
    g = (int(lo // step)) * step
    while g <= hi:
        if lo <= g <= hi:
            lines.append(
                f'<line x1="{ml}" x2="{W-mr}" y1="{y(g):.1f}" y2="{y(g):.1f}" '
                f'stroke="#898781" stroke-opacity="0.25" stroke-width="1"/>'
                f'<text x="{ml-8}" y="{y(g)+4:.1f}" text-anchor="end" '
                f'font-size="11" fill="#898781">${g:,.0f}</text>')
        g += step
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="system-ui,sans-serif">'
        + "".join(lines)
        + f'<polyline points="{pts}" fill="none" stroke="#2a78d6" '
          f'stroke-width="2" stroke-linejoin="round"/>'
        + (f'<circle cx="{x(len(vals)-1):.1f}" cy="{y(vals[-1]):.1f}" r="4" '
           f'fill="#2a78d6"/>'
           f'<text x="{x(len(vals)-1)-8:.1f}" y="{y(vals[-1])-10:.1f}" '
           f'text-anchor="end" font-size="12" font-weight="600" fill="#898781">'
           f'${vals[-1]:,.0f}</text>')
        + f'<text x="{ml}" y="{H-6}" font-size="11" fill="#898781">'
          f'trade 0 → {len(trades)}</text></svg>')
    with open(path, "w") as f:
        f.write(svg)


def fmt_money(d):
    return ("+$" if d >= 0 else "−$") + f"{abs(d):,.0f}"


def make_readme(res, coverage, path):
    o = res["overall"]
    lines = []
    a = lines.append
    a("# Silver Bullet Strategy — Accumulating NQ Backtest")
    a("")
    a("Fully mechanical backtest of the ICT \"Silver Bullet\" setup on E-mini "
      "Nasdaq 100 (NQ) futures, 5-minute bars, updated automatically on a "
      "schedule (GitHub Actions pulling delayed Yahoo Finance data, plus "
      "optional IBKR pulls). Every run re-tests the entire accumulated "
      "history, so the trade sample below grows over time.")
    a("")
    a(f"**Last updated:** {res['generated_utc']} UTC · "
      f"**Rules:** v{RULES_VERSION} · **Data:** "
      + "; ".join(f"{c['contract']}: {c['bars']} bars, {c['first_ny'][:10]} → {c['last_ny'][:10]}"
                  for c in coverage))
    a("")
    a("> ⚠️ **Small-sample warning:** results below are not "
      "statistically meaningful until the sample reaches well over 100 trades "
      "across different market regimes. Treat everything here as an ongoing "
      "experiment, not evidence of an edge. Not financial advice.")
    a("")
    a("## Headline (1 contract, after $10/trade costs)")
    a("")
    a("| Net P&L | Trades | Win rate | Profit factor | Max drawdown | Avg/trade |")
    a("|---|---|---|---|---|---|")
    if o["n"]:
        pf = o["profit_factor"] if o["profit_factor"] is not None else "∞"
        a(f"| **{fmt_money(o['total_dollars'])}** | {o['n']} "
          f"({o['targets']}T/{o['stops']}S/{o['time_exits']}X) | {o['win_rate']}% "
          f"| {pf} | ${o['max_drawdown_dollars']:,.0f} | {fmt_money(o['avg_dollars'])} |")
    else:
        a("| — | 0 | — | — | — | — |")
    a("")
    a("T = target hit, S = stopped, X = 2-hour time exit")
    a("")
    a("## Equity curve")
    a("")
    a("![Cumulative P&L](results/equity.svg)")
    a("")
    a("## By window (New York time)")
    a("")
    a("| Window | Trades | Win rate | Net $ | Profit factor |")
    a("|---|---|---|---|---|")
    for w in res["by_window"]:
        if w["n"]:
            pf = w["profit_factor"] if w["profit_factor"] is not None else "∞"
            a(f"| {w['label']} | {w['n']} | {w['win_rate']}% | "
              f"{fmt_money(w['total_dollars'])} | {pf} |")
        else:
            a(f"| {w['label']} | 0 | — | — | — |")
    a("")
    a("## Recent trades")
    a("")
    a("| Date | Window | Dir | Entry | Risk (pts) | Exit | P&L |")
    a("|---|---|---|---|---|---|---|")
    for t in res["trades"][-15:][::-1]:
        a(f"| {t['day']} | {t['window']} | {t['bias']} | {t['entry']} | "
          f"{t['risk_pts']} | {t['outcome']} | {fmt_money(t['dollars'])} |")
    a("")
    a("Full log: [trades.csv](trades.csv) · raw stats: "
      "[results.json](results.json) · interactive report: "
      "[report.html](report.html) (download to view)")
    a("")
    a("## The mechanical rules")
    a("")
    a("Windows 3–4 AM / 10–11 AM / 2–3 PM NY. Liquidity sweep = "
      "bar takes out the prior 2-hour extreme and closes back inside (scanned "
      "from 30 min before the window). First fair value gap (≥0.5 pt, "
      "displacement candle closing in bias direction) forming inside the "
      "window after the sweep. Limit entry at the near gap edge, must fill "
      "before window close. Stop 1 tick beyond the sweep extreme (skip if "
      "risk > 60 pts). Target 2R. 2-hour time exit. Same-bar stop+target "
      "counts as a loss. One trade per window. $10 round-trip costs, "
      "$20/point, 1 contract.")
    a("")
    a("## Caveats")
    a("")
    a("Data is IBKR's 10-minute-delayed consolidated feed (fine for "
      "end-of-day analysis). IBKR serves at most 3,500 bars (~13.5 trading "
      "days of 5-min) per pull, which is why this repo accumulates them "
      "twice weekly — a missed fortnight of runs would leave a permanent "
      "gap. Contract months are kept as separate price series to avoid roll "
      "artifacts; trades are deduplicated per (day, window) across contracts. "
      "Limit fills are assumed at the touched price with no queue — real "
      "fills would be somewhat worse.")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Silver Bullet Backtest — NQ</title>
<style>
.viz-root{color-scheme:light;--surface-1:#fcfcfb;--page:#f9f9f7;--ink-1:#0b0b0b;
--ink-2:#52514e;--ink-muted:#898781;--grid:#e1e0d9;--baseline:#c3c2b7;
--border:rgba(11,11,11,.10);--pos:#2a78d6;--neg:#e34948}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme=light])) .viz-root{
color-scheme:dark;--surface-1:#1a1a19;--page:#0d0d0d;--ink-1:#fff;--ink-2:#c3c2b7;
--grid:#2c2c2a;--baseline:#383835;--border:rgba(255,255,255,.10);--pos:#3987e5;--neg:#e66767}}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif}
.viz-root{background:var(--page);color:var(--ink-1);min-height:100vh;padding:32px 16px}
.wrap{max-width:880px;margin:0 auto;display:flex;flex-direction:column;gap:20px}
.card{background:var(--surface-1);border:1px solid var(--border);border-radius:10px;padding:20px 24px}
h1{font-size:22px;font-weight:650}h2{font-size:15px;font-weight:650;margin-bottom:12px}
.sub{color:var(--ink-2);font-size:13px;margin-top:6px;line-height:1.5}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.tile{background:var(--surface-1);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.tile .k{font-size:12px;color:var(--ink-muted);margin-bottom:6px}
.tile .v{font-size:26px;font-weight:650}.tile .d{font-size:12px;color:var(--ink-2);margin-top:4px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:var(--ink-muted);font-weight:550;padding:6px 8px;border-bottom:1px solid var(--baseline)}
td{padding:7px 8px;border-bottom:1px solid var(--grid);font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:none}.r{text-align:right}th.r{text-align:right}
footer{font-size:12px;color:var(--ink-muted);line-height:1.6}
svg text{font-family:system-ui,sans-serif}
</style></head><body class="viz-root"><div class="wrap">
<div><h1>Silver Bullet — accumulating mechanical backtest on NQ</h1>
<div class="sub" id="meta"></div></div>
<div class="tiles" id="tiles"></div>
<div class="card"><h2>Cumulative P&amp;L</h2><svg id="eq" viewBox="0 0 800 260" width="100%"></svg></div>
<div class="card"><h2>By window</h2><table id="wtable"></table></div>
<div class="card"><h2>Trade log</h2><table id="ttable"></table></div>
<footer>Mechanical rules v__RULES__. IBKR 10-min-delayed data, 5-min bars, $20/pt,
$10 round-trip costs, 1 contract. Small samples are not evidence of an edge.
Educational only — not financial advice.</footer>
</div>
<script>
const R = __DATA__;
const fm = d => (d>=0?"+$":"−$")+Math.abs(Math.round(d)).toLocaleString();
const o = R.overall;
document.getElementById("meta").textContent =
  `Updated ${R.generated_utc} UTC · ${R.coverage.map(c=>`${c.contract}: ${c.first_ny.slice(0,10)} → ${c.last_ny.slice(0,10)}`).join(" · ")}`;
const tiles=[["Net P&L",fm(o.total_dollars||0),`${o.total_pts||0} pts after costs`],
["Trades",o.n||0,`${o.wins||0} wins`],["Win rate",(o.win_rate||0)+"%",`${o.targets||0} tgt · ${o.stops||0} stop · ${o.time_exits||0} time`],
["Profit factor",o.profit_factor==null?"∞":o.profit_factor,`max DD $${(o.max_drawdown_dollars||0).toLocaleString()}`]];
document.getElementById("tiles").innerHTML=tiles.map(t=>`<div class="tile"><div class="k">${t[0]}</div><div class="v">${t[1]}</div><div class="d">${t[2]}</div></div>`).join("");
document.getElementById("wtable").innerHTML=`<thead><tr><th>Window (NY)</th><th class="r">Trades</th><th class="r">Win rate</th><th class="r">Net $</th><th class="r">PF</th></tr></thead><tbody>`+
R.by_window.map(w=>w.n?`<tr><td>${w.label}</td><td class="r">${w.n}</td><td class="r">${w.win_rate}%</td><td class="r">${fm(w.total_dollars)}</td><td class="r">${w.profit_factor==null?"∞":w.profit_factor}</td></tr>`:`<tr><td>${w.label}</td><td class="r">0</td><td class="r">—</td><td class="r">—</td><td class="r">—</td></tr>`).join("")+"</tbody>";
document.getElementById("ttable").innerHTML=`<thead><tr><th>Date</th><th>Window</th><th>Dir</th><th class="r">Entry</th><th class="r">Risk</th><th>Exit</th><th class="r">P&L</th></tr></thead><tbody>`+
R.trades.slice().reverse().map(t=>`<tr><td>${t.day}</td><td>${t.window}</td><td>${t.bias}</td><td class="r">${t.entry.toLocaleString()}</td><td class="r">${t.risk_pts}</td><td>${t.outcome}</td><td class="r">${fm(t.dollars)}</td></tr>`).join("")+"</tbody>";
(function(){
const css=n=>getComputedStyle(document.body).getPropertyValue(n).trim();
function draw(){
const svg=document.getElementById("eq");svg.innerHTML="";
const W=800,H=260,m={t:16,r:44,b:28,l:60},iw=W-m.l-m.r,ih=H-m.t-m.b;
let cum=0;const pts=[0].concat(R.trades.map(t=>cum+=t.dollars));
let lo=Math.min(...pts),hi=Math.max(...pts);const span=Math.max(hi-lo,1);lo-=span*.08;hi+=span*.08;
const x=i=>m.l+iw*(i/Math.max(pts.length-1,1)),y=v=>m.t+ih*(1-(v-lo)/(hi-lo));
const ns="http://www.w3.org/2000/svg",el=(t,a)=>{const n=document.createElementNS(ns,t);for(const k in a)n.setAttribute(k,a[k]);return n};
const step=Math.max(Math.round(span/4/500)*500,500);
for(let g=Math.floor(lo/step)*step;g<=hi;g+=step){if(g<lo)continue;
svg.appendChild(el("line",{x1:m.l,x2:W-m.r,y1:y(g),y2:y(g),stroke:g===0?css("--baseline"):css("--grid"),"stroke-width":1}));
const t=el("text",{x:m.l-8,y:y(g)+4,"text-anchor":"end","font-size":11,fill:css("--ink-muted")});t.textContent="$"+g.toLocaleString();svg.appendChild(t);}
svg.appendChild(el("polyline",{points:pts.map((v,i)=>`${x(i)},${y(v)}`).join(" "),fill:"none",stroke:css("--pos"),"stroke-width":2,"stroke-linejoin":"round"}));
svg.appendChild(el("circle",{cx:x(pts.length-1),cy:y(pts[pts.length-1]),r:4,fill:css("--pos")}));
const f=el("text",{x:x(pts.length-1)-8,y:y(pts[pts.length-1])-10,"text-anchor":"end","font-size":12,"font-weight":650,fill:css("--ink-1")});
f.textContent=fm(pts[pts.length-1]);svg.appendChild(f);}
draw();
if(window.matchMedia)window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change",draw);
})();
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", help="CSV of new bars to merge")
    ap.add_argument("--contract", help="contract label, e.g. NQ202609")
    args = ap.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    added = 0
    if args.new:
        if not args.contract:
            raise SystemExit("--contract is required with --new")
        target = os.path.join(DATA_DIR, args.contract + ".csv")
        existing = read_bars_csv(target) if os.path.exists(target) else []
        merged, added = merge_bars(existing, read_bars_csv(args.new))
        write_bars_csv(target, merged)
        print(f"[update] {args.contract}: +{added} new bars "
              f"({len(existing)} -> {len(merged)})")

    # backtest every contract series
    all_trades, coverage, daily_vol = [], [], {}
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.csv"))):
        contract = os.path.splitext(os.path.basename(path))[0]
        bars = read_bars_csv(path)
        if not bars:
            continue
        coverage.append({
            "contract": contract, "bars": len(bars),
            "first_ny": bars[0]["ny"].strftime("%Y-%m-%d %H:%M"),
            "last_ny": bars[-1]["ny"].strftime("%Y-%m-%d %H:%M"),
        })
        for b in bars:
            k = (contract, str(b["ny"].date()))
            daily_vol[k] = daily_vol.get(k, 0) + b["v"]
        all_trades.extend(run_backtest(bars, contract))

    # dedupe trades across contracts by (day, window): keep higher-volume contract
    best = {}
    for t in all_trades:
        key = (t["day"], t["window"])
        vol = daily_vol.get((t["contract"], t["day"]), 0)
        if key not in best or vol > best[key][0]:
            best[key] = (vol, t)
    trades = sorted((v[1] for v in best.values()),
                    key=lambda t: (t["day"], t["entry_time"]))

    now_utc = datetime.now(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M")
    res = {
        "generated_utc": now_utc,
        "rules_version": RULES_VERSION,
        "coverage": coverage,
        "overall": summarize(trades, "ALL"),
        "by_window": [summarize([t for t in trades if t["window"] == w], w)
                      for w, _ in WINDOWS],
        "trades": trades,
    }

    with open(os.path.join(ROOT, "results.json"), "w") as f:
        json.dump(res, f, indent=1)
    with open(os.path.join(ROOT, "trades.csv"), "w", newline="") as f:
        if trades:
            w = csv.DictWriter(f, fieldnames=list(trades[0].keys()))
            w.writeheader()
            w.writerows(trades)
        else:
            f.write("no trades yet\n")
    equity_svg(trades, os.path.join(RESULTS_DIR, "equity.svg"))
    make_readme(res, coverage, os.path.join(ROOT, "README.md"))
    html = REPORT_TEMPLATE.replace("__DATA__", json.dumps(res)) \
                          .replace("__RULES__", RULES_VERSION)
    with open(os.path.join(ROOT, "report.html"), "w") as f:
        f.write(html)
    o = res["overall"]
    print(f"[update] {o.get('n', 0)} trades, net "
          f"${o.get('total_dollars', 0):,} | +{added} bars this run")


if __name__ == "__main__":
    main()
