# Silver Bullet Strategy — Accumulating NQ Backtest

Fully mechanical backtest of the ICT "Silver Bullet" setup on E-mini Nasdaq 100 (NQ) futures, 5-minute bars, updated automatically on a schedule (GitHub Actions pulling delayed Yahoo Finance data, plus optional IBKR pulls). Every run re-tests the entire accumulated history, so the trade sample below grows over time.

**Last updated:** 2026-10-08 06:36 UTC · **Rules:** v1.1 (2026-08-18) · **Data:** NQ202609: 3499 bars, 2026-07-29 → 2026-08-16; NQF-continuous: 23463 bars, 2026-06-08 → 2026-10-08; CL: 23256 bars, 2026-06-09 → 2026-10-08; ES: 23188 bars, 2026-06-09 → 2026-10-08

> ⚠️ **Small-sample warning:** results below are not statistically meaningful until the sample reaches well over 100 trades across different market regimes. Treat everything here as an ongoing experiment, not evidence of an edge. Not financial advice.

## Headline (1 contract, after $10/trade costs)

| Net P&L | Trades | Win rate | Profit factor | Max drawdown | Avg/trade |
|---|---|---|---|---|---|
| **−$4,530** | 35 (8T/24S/3X) | 31.4% | 0.66 | $6,835 | −$129 |

T = target hit, S = stopped, X = 2-hour time exit

## Equity curve

![Cumulative P&L](results/equity.svg)

## By window (New York time)

| Window | Trades | Win rate | Net $ | Profit factor |
|---|---|---|---|---|
| London 3-4am | 20 | 40.0% | −$430 | 0.94 |
| AM 10-11am | 6 | 0.0% | −$1,505 | 0.0 |
| PM 2-3pm | 9 | 33.3% | −$2,595 | 0.42 |

## Cross-market robustness

Same mechanical rules run on other markets (continuous front-month, Yahoo data). Scored in **R-multiples** — profit measured in units of initial risk — so different point values compare fairly. NQ row uses the NQ trades above.

| Market | Trades | Win % | Avg R | Total R | Profit factor (R) | Net $ (1 contract) |
|---|---|---|---|---|---|---|
| NQ | 35 | 31.4% | -0.19 | -6.53 | 0.73 | −$4,530 |
| CL | 9 | 33.3% | 0.0 | 0.0 | 1.0 | −$230 |
| ES | 40 | 30.0% | -0.15 | -6.13 | 0.77 | −$2,638 |

## Old vs New — the retro comparison

**The v2 lesson (read this first):** the Aug-18 'optimized' spec (ES · London+AM · breakeven) showed +0.49R/trade at selection — then lost **−5.4R over its next 7 live trades**. That is selection bias demonstrated with real forward data: the best-looking retro spec is mostly luck. **v3** (selected Sep 19 from the full-history grid: NQ midday·1R, ES NYMEX-open+pre-settle·1R and London·2R, CL not traded — no CL configuration is profitable) carries exactly the same risk. Its retro numbers below are overstated by construction; only its forward record from Sep 19 onward counts, and v2's fate is the base rate for what to expect.

| Spec | Trades | Win % | Avg R | Total R | PF | IS → OOS |
|---|---|---|---|---|---|---|
| OLD — base spec · all markets · all windows | 84 | 31.0% | -0.206 | -17.34 | 0.71 | -0.158 → -0.313 |
| NEW v3 (sel. Sep 19) — NQ midday·1R · ES open+pre-settle·1R & London·2R · CL not traded | 61 | 60.7% | 0.283 | 17.24 | 1.73 | 0.258 → 0.337 |

## System Lab — which variant is most profitable?

Every mechanical variant of the strategy, run on all markets, ranked by total cost-adjusted R (profit in units of risk, after $10/trade costs). **How to read this honestly:** with this many variants, the top row will always look good by luck alone. Trust a variant only if it has a ✅ robust flag — positive overall, positive **out-of-sample** (the last 30% of trades, which it was not selected on), and positive in at least two markets — and only if it KEEPS its flag as data accumulates over the coming months.

| Rank | Variant | Trades | Win % | Avg R | Total R | PF | NQ avg R | ES avg R | CL avg R | IS → OOS | Robust |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2R · breakeven stop after +1R | 84 | 27.4% | -0.098 | -8.25 | 0.83 | -0.138 (35) | -0.101 (40) | 0.069 (9) | -0.016 → -0.281 | — |
| 2 | 1R target · stop@sweep | 84 | 46.4% | -0.142 | -11.94 | 0.75 | -0.196 (35) | -0.118 (40) | -0.042 (9) | -0.08 → -0.281 | — |
| 3 | 2R target · stop@sweep (base) | 84 | 31.0% | -0.206 | -17.34 | 0.71 | -0.227 (35) | -0.201 (40) | -0.154 (9) | -0.138 → -0.358 | — |
| 4 | 2R · no time exit (hold 6.5h) | 84 | 27.4% | -0.234 | -19.67 | 0.69 | -0.269 (35) | -0.222 (40) | -0.154 (9) | -0.179 → -0.358 | — |
| 5 | 1.5R target · stop@sweep | 84 | 33.3% | -0.284 | -23.84 | 0.6 | -0.269 (35) | -0.288 (40) | -0.32 (9) | -0.242 → -0.377 | — |
| 6 | 3R target · stop@gap edge | 180 | 25.0% | -0.133 | -23.86 | 0.84 | -0.097 (67) | -0.263 (59) | -0.035 (54) | -0.171 → -0.048 | — |
| 7 | 3R target · stop@sweep | 84 | 22.6% | -0.322 | -27.02 | 0.6 | -0.356 (35) | -0.105 (40) | -1.154 (9) | -0.203 → -0.587 | — |
| 8 | FADE the setup (take opposite side) | 84 | 28.6% | -0.339 | -28.48 | 0.55 | -0.331 (35) | -0.238 (40) | -0.82 (9) | -0.45 → -0.091 | — |
| 9 | 1.5R target · stop@gap edge | 180 | 35.0% | -0.251 | -45.17 | 0.66 | -0.253 (67) | -0.404 (59) | -0.081 (54) | -0.222 → -0.316 | — |
| 10 | 2R target · stop@gap edge | 180 | 28.3% | -0.276 | -49.67 | 0.66 | -0.305 (67) | -0.361 (59) | -0.146 (54) | -0.282 → -0.263 | — |
| 11 | 1R target · stop@gap edge | 180 | 38.9% | -0.348 | -62.67 | 0.5 | -0.395 (67) | -0.412 (59) | -0.22 (54) | -0.355 → -0.334 | — |

## Oil Lab — a Silver Bullet restructured for CL

Crude oil's liquidity clock differs from equity indices, so the same sweep→FVG mechanics are scanned across oil-native windows: Brent/London flow, the NYMEX open, the 10:30 EIA report hour, midday, and pre-settlement. Same honesty rules as the System Lab — trust ✅ rows only, and only if they persist as data grows.

| Rank | CL window · target | Trades | Win % | Avg R | Total R | PF | IS → OOS | Robust |
|---|---|---|---|---|---|---|---|---|
| 1 | EIA 10:30-11:30a · 2R | 1 | 100.0% | 1.933 | 1.93 | ∞ | None → 1.933 | — |
| 2 | EIA 10:30-11:30a · 1R | 1 | 100.0% | 0.933 | 0.93 | ∞ | None → 0.933 | — |
| 3 | Pre-settle 1:30-2:30p · 1R | 4 | 50.0% | -0.103 | -0.41 | 0.81 | -0.127 → -0.08 | — |
| 4 | NYMEX open 9-10a · 1R | 1 | 0.0% | -1.083 | -1.08 | 0.0 | None → -1.083 | — |
| 5 | NYMEX open 9-10a · 2R | 1 | 0.0% | -1.083 | -1.08 | 0.0 | None → -1.083 | — |
| 6 | Midday 12-1p · 1R | 3 | 33.3% | -0.514 | -1.54 | 0.37 | -1.225 → 0.909 | — |
| 7 | Brent/London 3-4a · 1R | 3 | 33.3% | -0.54 | -1.62 | 0.37 | -0.281 → -1.059 | — |
| 8 | Midday 12-1p · 2R | 3 | 0.0% | -1.18 | -3.54 | 0.0 | -1.225 → -1.091 | — |
| 9 | Brent/London 3-4a · 2R | 3 | 0.0% | -1.207 | -3.62 | 0.0 | -1.281 → -1.059 | — |
| 10 | Pre-settle 1:30-2:30p · 2R | 4 | 0.0% | -1.103 | -4.41 | 0.0 | -1.127 → -1.08 | — |

## Walk-Forward Verdict — the honest number

Simulation of adaptive re-optimization with **zero hindsight**: every 14 days, the top specs (up to 4) are re-selected using only data available before that date, then traded blind for the next period. This is what 'keep tuning and trade the winner' — the v2/v3 approach — would actually have earned.

| Trades | Win % | Avg R | **Total R** | PF | At 2× costs | Specs churned |
|---|---|---|---|---|---|---|
| 22 | 63.6% | 0.307 | **6.75** | 1.88 | 5.74 | 8 distinct specs |

**Reading:** positive walk-forward is a meaningfully stronger signal than any retro number — but with this few periods it is still fragile. Watch whether it persists and whether the picked specs stabilize (low churn) as data accumulates.

## Recent trades

| Date | Window | Dir | Entry | Risk (pts) | Exit | P&L |
|---|---|---|---|---|---|---|
| 2026-10-07 | London 3-4am | bull | 31470.0 | 20.25 | stop | −$415 |
| 2026-10-06 | AM 10-11am | bear | 31541.75 | 25.5 | stop | −$520 |
| 2026-10-06 | London 3-4am | bear | 31384.25 | 15.0 | target | +$590 |
| 2026-10-05 | AM 10-11am | bear | 31220.0 | 9.75 | stop | −$205 |
| 2026-10-02 | AM 10-11am | bear | 31256.0 | 3.75 | stop | −$85 |
| 2026-09-24 | London 3-4am | bull | 30575.25 | 13.0 | target | +$510 |
| 2026-09-16 | London 3-4am | bear | 29376.75 | 19.0 | target | +$750 |
| 2026-09-14 | PM 2-3pm | bear | 29567.25 | 18.75 | target | +$740 |
| 2026-09-09 | London 3-4am | bull | 29589.75 | 28.75 | stop | −$585 |
| 2026-09-03 | AM 10-11am | bear | 29283.25 | 2.0 | stop | −$50 |
| 2026-09-02 | PM 2-3pm | bear | 29143.5 | 56.5 | stop | −$1,140 |
| 2026-08-28 | London 3-4am | bear | 29619.0 | 34.75 | time | +$55 |
| 2026-08-27 | London 3-4am | bear | 29515.0 | 27.5 | stop | −$560 |
| 2026-08-20 | London 3-4am | bear | 29643.25 | 34.25 | target | +$1,360 |
| 2026-08-19 | PM 2-3pm | bull | 29537.75 | 46.0 | stop | −$930 |

Full log: [trades.csv](trades.csv) · raw stats: [results.json](results.json) · interactive report: [report.html](report.html) (download to view)

## The mechanical rules

Windows 3–4 AM / 10–11 AM / 2–3 PM NY. Liquidity sweep = bar takes out the prior 2-hour extreme and closes back inside (scanned from 30 min before the window). First fair value gap (≥0.5 pt, displacement candle closing in bias direction) forming inside the window after the sweep. Limit entry at the near gap edge, must fill before window close. Stop 1 tick beyond the sweep extreme (skip if risk > 60 pts). Target 2R. 2-hour time exit. Same-bar stop+target counts as a loss. One trade per window. $10 round-trip costs, $20/point, 1 contract.

## Caveats

Data is IBKR's 10-minute-delayed consolidated feed (fine for end-of-day analysis). IBKR serves at most 3,500 bars (~13.5 trading days of 5-min) per pull, which is why this repo accumulates them twice weekly — a missed fortnight of runs would leave a permanent gap. Contract months are kept as separate price series to avoid roll artifacts; trades are deduplicated per (day, window) across contracts. Limit fills are assumed at the touched price with no queue — real fills would be somewhat worse.
