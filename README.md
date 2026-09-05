# Silver Bullet Strategy — Accumulating NQ Backtest

Fully mechanical backtest of the ICT "Silver Bullet" setup on E-mini Nasdaq 100 (NQ) futures, 5-minute bars, updated automatically on a schedule (GitHub Actions pulling delayed Yahoo Finance data, plus optional IBKR pulls). Every run re-tests the entire accumulated history, so the trade sample below grows over time.

**Last updated:** 2026-09-05 13:50 UTC · **Rules:** v1.1 (2026-08-18) · **Data:** NQ202609: 3499 bars, 2026-07-29 → 2026-08-16; NQF-continuous: 17384 bars, 2026-06-08 → 2026-09-04; CL: 17161 bars, 2026-06-09 → 2026-09-04; ES: 17109 bars, 2026-06-09 → 2026-09-04

> ⚠️ **Small-sample warning:** results below are not statistically meaningful until the sample reaches well over 100 trades across different market regimes. Treat everything here as an ongoing experiment, not evidence of an edge. Not financial advice.

## Headline (1 contract, after $10/trade costs)

| Net P&L | Trades | Win rate | Profit factor | Max drawdown | Avg/trade |
|---|---|---|---|---|---|
| **−$5,310** | 26 (4T/19S/3X) | 26.9% | 0.54 | $6,755 | −$204 |

T = target hit, S = stopped, X = 2-hour time exit

## Equity curve

![Cumulative P&L](results/equity.svg)

## By window (New York time)

| Window | Trades | Win rate | Net $ | Profit factor |
|---|---|---|---|---|
| London 3-4am | 15 | 33.3% | −$1,280 | 0.8 |
| AM 10-11am | 3 | 0.0% | −$695 | 0.0 |
| PM 2-3pm | 8 | 25.0% | −$3,335 | 0.25 |

## Cross-market robustness

Same mechanical rules run on other markets (continuous front-month, Yahoo data). Scored in **R-multiples** — profit measured in units of initial risk — so different point values compare fairly. NQ row uses the NQ trades above.

| Market | Trades | Win % | Avg R | Total R | Profit factor (R) | Net $ (1 contract) |
|---|---|---|---|---|---|---|
| NQ | 26 | 26.9% | -0.37 | -9.53 | 0.5 | −$5,310 |
| CL | 7 | 28.6% | -0.14 | -1.0 | 0.8 | −$200 |
| ES | 33 | 33.3% | -0.06 | -2.13 | 0.9 | −$380 |

## Old vs New — the retro comparison

The parameter analysis (Aug 2026) found the base spec's consistent failures — the PM window, gap-edge stops, and NQ itself — and produced a fixed spec: **v2 = ES only · London+AM windows · 2R target · breakeven stop after +1R**. Both are re-run over all accumulated history on every update. v2 was *selected* on this same history (selection bias), so its edge is overstated here — the growing out-of-sample record is the real verdict.

| Spec | Trades | Win % | Avg R | Total R | PF | IS → OOS |
|---|---|---|---|---|---|---|
| OLD — base spec · all markets · all windows | 66 | 30.3% | -0.252 | -16.66 | 0.65 | -0.074 → -0.663 |
| NEW v2 — ES only · London+AM · 2R · breakeven after +1R | 24 | 37.5% | 0.162 | 3.9 | 1.34 | 0.284 → -0.08 |

## System Lab — which variant is most profitable?

Every mechanical variant of the strategy, run on all markets, ranked by total cost-adjusted R (profit in units of risk, after $10/trade costs). **How to read this honestly:** with this many variants, the top row will always look good by luck alone. Trust a variant only if it has a ✅ robust flag — positive overall, positive **out-of-sample** (the last 30% of trades, which it was not selected on), and positive in at least two markets — and only if it KEEPS its flag as data accumulates over the coming months.

| Rank | Variant | Trades | Win % | Avg R | Total R | PF | NQ avg R | ES avg R | CL avg R | IS → OOS | Robust |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2R · breakeven stop after +1R | 66 | 27.3% | -0.115 | -7.57 | 0.8 | -0.326 (26) | 0.033 (33) | -0.028 (7) | 0.027 → -0.418 | — |
| 2 | 1R target · stop@sweep | 66 | 47.0% | -0.14 | -9.27 | 0.75 | -0.287 (26) | -0.048 (33) | -0.028 (7) | -0.033 → -0.37 | — |
| 3 | 2R target · stop@sweep (base) | 66 | 30.3% | -0.252 | -16.66 | 0.65 | -0.406 (26) | -0.118 (33) | -0.314 (7) | -0.111 → -0.556 | — |
| 4 | 2R · no time exit (hold 6.5h) | 66 | 25.8% | -0.288 | -18.99 | 0.63 | -0.463 (26) | -0.144 (33) | -0.314 (7) | -0.112 → -0.664 | — |
| 5 | 3R target · stop@sweep | 66 | 24.2% | -0.309 | -20.38 | 0.61 | -0.457 (26) | -0.009 (33) | -1.171 (7) | -0.082 → -0.794 | — |
| 6 | 3R target · stop@gap edge | 138 | 24.6% | -0.149 | -20.6 | 0.82 | -0.3 (49) | -0.194 (46) | 0.07 (43) | -0.094 → -0.275 | — |
| 7 | 1.5R target · stop@sweep | 66 | 31.8% | -0.343 | -22.66 | 0.53 | -0.483 (26) | -0.209 (33) | -0.457 (7) | -0.211 → -0.627 | — |
| 8 | 1.5R target · stop@gap edge | 138 | 37.7% | -0.184 | -25.41 | 0.74 | -0.3 (49) | -0.309 (46) | 0.081 (43) | -0.16 → -0.239 | — |
| 9 | FADE the setup (take opposite side) | 66 | 25.8% | -0.433 | -28.58 | 0.44 | -0.407 (26) | -0.388 (33) | -0.743 (7) | -0.548 → -0.187 | — |
| 10 | 2R target · stop@gap edge | 138 | 29.0% | -0.257 | -35.41 | 0.68 | -0.443 (49) | -0.276 (46) | -0.023 (43) | -0.217 → -0.346 | — |
| 11 | 1R target · stop@gap edge | 138 | 40.6% | -0.315 | -43.41 | 0.54 | -0.463 (49) | -0.342 (46) | -0.116 (43) | -0.311 → -0.322 | — |

## Oil Lab — a Silver Bullet restructured for CL

Crude oil's liquidity clock differs from equity indices, so the same sweep→FVG mechanics are scanned across oil-native windows: Brent/London flow, the NYMEX open, the 10:30 EIA report hour, midday, and pre-settlement. Same honesty rules as the System Lab — trust ✅ rows only, and only if they persist as data grows.

| Rank | CL window · target | Trades | Win % | Avg R | Total R | PF | IS → OOS | Robust |
|---|---|---|---|---|---|---|---|---|
| 1 | EIA 10:30-11:30a · 2R | 1 | 100.0% | 1.933 | 1.93 | ∞ | None → 1.933 | — |
| 2 | EIA 10:30-11:30a · 1R | 1 | 100.0% | 0.933 | 0.93 | ∞ | None → 0.933 | — |
| 3 | Brent/London 3-4a · 1R | 2 | 50.0% | -0.281 | -0.56 | 0.63 | -1.5 → 0.938 | — |
| 4 | NYMEX open 9-10a · 1R | 1 | 0.0% | -1.083 | -1.08 | 0.0 | None → -1.083 | — |
| 5 | NYMEX open 9-10a · 2R | 1 | 0.0% | -1.083 | -1.08 | 0.0 | None → -1.083 | — |
| 6 | Pre-settle 1:30-2:30p · 1R | 3 | 33.3% | -0.444 | -1.33 | 0.4 | -0.127 → -1.077 | — |
| 7 | Midday 12-1p · 1R | 3 | 33.3% | -0.514 | -1.54 | 0.37 | -1.225 → 0.909 | — |
| 8 | Brent/London 3-4a · 2R | 2 | 0.0% | -1.281 | -2.56 | 0.0 | -1.5 → -1.062 | — |
| 9 | Pre-settle 1:30-2:30p · 2R | 3 | 0.0% | -1.11 | -3.33 | 0.0 | -1.127 → -1.077 | — |
| 10 | Midday 12-1p · 2R | 3 | 0.0% | -1.18 | -3.54 | 0.0 | -1.225 → -1.091 | — |

## Recent trades

| Date | Window | Dir | Entry | Risk (pts) | Exit | P&L |
|---|---|---|---|---|---|---|
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
| 2026-08-06 | PM 2-3pm | bear | 29524.5 | 51.25 | time | +$560 |
| 2026-08-04 | London 3-4am | bear | 29093.0 | 7.5 | stop | −$160 |
| 2026-07-31 | London 3-4am | bull | 28509.75 | 60.0 | target | +$2,390 |
| 2026-07-22 | London 3-4am | bull | 29090.75 | 40.0 | stop | −$810 |

Full log: [trades.csv](trades.csv) · raw stats: [results.json](results.json) · interactive report: [report.html](report.html) (download to view)

## The mechanical rules

Windows 3–4 AM / 10–11 AM / 2–3 PM NY. Liquidity sweep = bar takes out the prior 2-hour extreme and closes back inside (scanned from 30 min before the window). First fair value gap (≥0.5 pt, displacement candle closing in bias direction) forming inside the window after the sweep. Limit entry at the near gap edge, must fill before window close. Stop 1 tick beyond the sweep extreme (skip if risk > 60 pts). Target 2R. 2-hour time exit. Same-bar stop+target counts as a loss. One trade per window. $10 round-trip costs, $20/point, 1 contract.

## Caveats

Data is IBKR's 10-minute-delayed consolidated feed (fine for end-of-day analysis). IBKR serves at most 3,500 bars (~13.5 trading days of 5-min) per pull, which is why this repo accumulates them twice weekly — a missed fortnight of runs would leave a permanent gap. Contract months are kept as separate price series to avoid roll artifacts; trades are deduplicated per (day, window) across contracts. Limit fills are assumed at the touched price with no queue — real fills would be somewhat worse.
