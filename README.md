# Silver Bullet Strategy — Accumulating NQ Backtest

Fully mechanical backtest of the ICT "Silver Bullet" setup on E-mini Nasdaq 100 (NQ) futures, 5-minute bars, updated automatically on a schedule (GitHub Actions pulling delayed Yahoo Finance data, plus optional IBKR pulls). Every run re-tests the entire accumulated history, so the trade sample below grows over time.

**Last updated:** 2026-09-24 23:24 UTC · **Rules:** v1.1 (2026-08-18) · **Data:** NQ202609: 3499 bars, 2026-07-29 → 2026-08-16; NQF-continuous: 20902 bars, 2026-06-08 → 2026-09-24; CL: 20688 bars, 2026-06-09 → 2026-09-24; ES: 20627 bars, 2026-06-09 → 2026-09-24

> ⚠️ **Small-sample warning:** results below are not statistically meaningful until the sample reaches well over 100 trades across different market regimes. Treat everything here as an ongoing experiment, not evidence of an edge. Not financial advice.

## Headline (1 contract, after $10/trade costs)

| Net P&L | Trades | Win rate | Profit factor | Max drawdown | Avg/trade |
|---|---|---|---|---|---|
| **−$3,895** | 30 (7T/20S/3X) | 33.3% | 0.68 | $6,835 | −$130 |

T = target hit, S = stopped, X = 2-hour time exit

## Equity curve

![Cumulative P&L](results/equity.svg)

## By window (New York time)

| Window | Trades | Win rate | Net $ | Profit factor |
|---|---|---|---|---|
| London 3-4am | 18 | 38.9% | −$605 | 0.91 |
| AM 10-11am | 3 | 0.0% | −$695 | 0.0 |
| PM 2-3pm | 9 | 33.3% | −$2,595 | 0.42 |

## Cross-market robustness

Same mechanical rules run on other markets (continuous front-month, Yahoo data). Scored in **R-multiples** — profit measured in units of initial risk — so different point values compare fairly. NQ row uses the NQ trades above.

| Market | Trades | Win % | Avg R | Total R | Profit factor (R) | Net $ (1 contract) |
|---|---|---|---|---|---|---|
| NQ | 30 | 33.3% | -0.15 | -4.53 | 0.77 | −$3,895 |
| CL | 8 | 25.0% | -0.25 | -2.0 | 0.67 | −$380 |
| ES | 39 | 30.8% | -0.13 | -5.13 | 0.8 | −$1,978 |

## Old vs New — the retro comparison

**The v2 lesson (read this first):** the Aug-18 'optimized' spec (ES · London+AM · breakeven) showed +0.49R/trade at selection — then lost **−5.4R over its next 7 live trades**. That is selection bias demonstrated with real forward data: the best-looking retro spec is mostly luck. **v3** (selected Sep 19 from the full-history grid: NQ midday·1R, ES NYMEX-open+pre-settle·1R and London·2R, CL not traded — no CL configuration is profitable) carries exactly the same risk. Its retro numbers below are overstated by construction; only its forward record from Sep 19 onward counts, and v2's fate is the base rate for what to expect.

| Spec | Trades | Win % | Avg R | Total R | PF | IS → OOS |
|---|---|---|---|---|---|---|
| OLD — base spec · all markets · all windows | 77 | 31.2% | -0.208 | -16.02 | 0.71 | -0.188 → -0.252 |
| NEW v3 (sel. Sep 19) — NQ midday·1R · ES open+pre-settle·1R & London·2R · CL not traded | 54 | 59.3% | 0.267 | 14.4 | 1.67 | 0.276 → 0.247 |

## System Lab — which variant is most profitable?

Every mechanical variant of the strategy, run on all markets, ranked by total cost-adjusted R (profit in units of risk, after $10/trade costs). **How to read this honestly:** with this many variants, the top row will always look good by luck alone. Trust a variant only if it has a ✅ robust flag — positive overall, positive **out-of-sample** (the last 30% of trades, which it was not selected on), and positive in at least two markets — and only if it KEEPS its flag as data accumulates over the coming months.

| Rank | Variant | Trades | Win % | Avg R | Total R | PF | NQ avg R | ES avg R | CL avg R | IS → OOS | Robust |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2R · breakeven stop after +1R | 77 | 27.3% | -0.116 | -8.93 | 0.8 | -0.119 (30) | -0.105 (39) | -0.157 (8) | -0.049 → -0.264 | — |
| 2 | 1R target · stop@sweep | 77 | 45.5% | -0.164 | -12.63 | 0.72 | -0.186 (30) | -0.149 (39) | -0.157 (8) | -0.1 → -0.305 | — |
| 3 | 2R target · stop@sweep (base) | 77 | 31.2% | -0.208 | -16.02 | 0.71 | -0.189 (30) | -0.182 (39) | -0.407 (8) | -0.185 → -0.26 | — |
| 4 | 3R target · stop@gap edge | 161 | 25.5% | -0.111 | -17.94 | 0.87 | -0.21 (58) | -0.18 (54) | 0.082 (49) | -0.201 → 0.087 | — |
| 5 | 2R · no time exit (hold 6.5h) | 77 | 27.3% | -0.238 | -18.35 | 0.69 | -0.238 (30) | -0.204 (39) | -0.407 (8) | -0.208 → -0.305 | — |
| 6 | 3R target · stop@sweep | 77 | 24.7% | -0.256 | -19.71 | 0.67 | -0.24 (30) | -0.083 (39) | -1.157 (8) | -0.217 → -0.341 | — |
| 7 | 1.5R target · stop@sweep | 77 | 32.5% | -0.312 | -24.02 | 0.56 | -0.306 (30) | -0.272 (39) | -0.532 (8) | -0.279 → -0.385 | — |
| 8 | FADE the setup (take opposite side) | 77 | 27.3% | -0.379 | -29.21 | 0.5 | -0.411 (30) | -0.273 (39) | -0.782 (8) | -0.449 → -0.226 | — |
| 9 | 1.5R target · stop@gap edge | 161 | 36.6% | -0.207 | -33.25 | 0.71 | -0.288 (58) | -0.334 (54) | 0.031 (49) | -0.226 → -0.163 | — |
| 10 | 2R target · stop@gap edge | 161 | 29.2% | -0.247 | -39.75 | 0.69 | -0.383 (58) | -0.288 (54) | -0.041 (49) | -0.316 → -0.093 | — |
| 11 | 1R target · stop@gap edge | 161 | 41.0% | -0.303 | -48.75 | 0.55 | -0.417 (58) | -0.343 (54) | -0.123 (49) | -0.37 → -0.153 | — |

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
| 16 | 56.2% | 0.18 | **2.87** | 1.43 | 2.0 | 8 distinct specs |

**Reading:** positive walk-forward is a meaningfully stronger signal than any retro number — but with this few periods it is still fragile. Watch whether it persists and whether the picked specs stabilize (low churn) as data accumulates.

## Recent trades

| Date | Window | Dir | Entry | Risk (pts) | Exit | P&L |
|---|---|---|---|---|---|---|
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
| 2026-08-18 | PM 2-3pm | bull | 29592.5 | 2.0 | stop | −$50 |
| 2026-08-18 | AM 10-11am | bull | 29637.0 | 6.0 | stop | −$130 |
| 2026-08-17 | London 3-4am | bear | 30313.0 | 14.25 | stop | −$295 |
| 2026-08-13 | London 3-4am | bull | 29866.0 | 8.0 | target | +$310 |
| 2026-08-11 | London 3-4am | bull | 29770.0 | 42.25 | stop | −$855 |

Full log: [trades.csv](trades.csv) · raw stats: [results.json](results.json) · interactive report: [report.html](report.html) (download to view)

## The mechanical rules

Windows 3–4 AM / 10–11 AM / 2–3 PM NY. Liquidity sweep = bar takes out the prior 2-hour extreme and closes back inside (scanned from 30 min before the window). First fair value gap (≥0.5 pt, displacement candle closing in bias direction) forming inside the window after the sweep. Limit entry at the near gap edge, must fill before window close. Stop 1 tick beyond the sweep extreme (skip if risk > 60 pts). Target 2R. 2-hour time exit. Same-bar stop+target counts as a loss. One trade per window. $10 round-trip costs, $20/point, 1 contract.

## Caveats

Data is IBKR's 10-minute-delayed consolidated feed (fine for end-of-day analysis). IBKR serves at most 3,500 bars (~13.5 trading days of 5-min) per pull, which is why this repo accumulates them twice weekly — a missed fortnight of runs would leave a permanent gap. Contract months are kept as separate price series to avoid roll artifacts; trades are deduplicated per (day, window) across contracts. Limit fills are assumed at the touched price with no queue — real fills would be somewhat worse.
