# Silver Bullet Strategy — Accumulating NQ Backtest

Fully mechanical backtest of the ICT "Silver Bullet" setup on E-mini Nasdaq 100 (NQ) futures, 5-minute bars, updated automatically on a schedule (GitHub Actions pulling delayed Yahoo Finance data, plus optional IBKR pulls). Every run re-tests the entire accumulated history, so the trade sample below grows over time.

**Last updated:** 2026-09-15 17:45 UTC · **Rules:** v1.1 (2026-08-18) · **Data:** NQ202609: 3499 bars, 2026-07-29 → 2026-08-16; NQF-continuous: 18923 bars, 2026-06-08 → 2026-09-15; CL: 18704 bars, 2026-06-09 → 2026-09-15; ES: 18648 bars, 2026-06-09 → 2026-09-15

> ⚠️ **Small-sample warning:** results below are not statistically meaningful until the sample reaches well over 100 trades across different market regimes. Treat everything here as an ongoing experiment, not evidence of an edge. Not financial advice.

## Headline (1 contract, after $10/trade costs)

| Net P&L | Trades | Win rate | Profit factor | Max drawdown | Avg/trade |
|---|---|---|---|---|---|
| **−$5,155** | 28 (5T/20S/3X) | 28.6% | 0.57 | $6,835 | −$184 |

T = target hit, S = stopped, X = 2-hour time exit

## Equity curve

![Cumulative P&L](results/equity.svg)

## By window (New York time)

| Window | Trades | Win rate | Net $ | Profit factor |
|---|---|---|---|---|
| London 3-4am | 16 | 31.2% | −$1,865 | 0.73 |
| AM 10-11am | 3 | 0.0% | −$695 | 0.0 |
| PM 2-3pm | 9 | 33.3% | −$2,595 | 0.42 |

## Cross-market robustness

Same mechanical rules run on other markets (continuous front-month, Yahoo data). Scored in **R-multiples** — profit measured in units of initial risk — so different point values compare fairly. NQ row uses the NQ trades above.

| Market | Trades | Win % | Avg R | Total R | Profit factor (R) | Net $ (1 contract) |
|---|---|---|---|---|---|---|
| NQ | 28 | 28.6% | -0.3 | -8.53 | 0.57 | −$5,155 |
| CL | 8 | 25.0% | -0.25 | -2.0 | 0.67 | −$380 |
| ES | 37 | 32.4% | -0.08 | -3.13 | 0.87 | −$1,158 |

## Old vs New — the retro comparison

The parameter analysis (Aug 2026) found the base spec's consistent failures — the PM window, gap-edge stops, and NQ itself — and produced a fixed spec: **v2 = ES only · London+AM windows · 2R target · breakeven stop after +1R**. Both are re-run over all accumulated history on every update. v2 was *selected* on this same history (selection bias), so its edge is overstated here — the growing out-of-sample record is the real verdict.

| Spec | Trades | Win % | Avg R | Total R | PF | IS → OOS |
|---|---|---|---|---|---|---|
| OLD — base spec · all markets · all windows | 73 | 30.1% | -0.245 | -17.9 | 0.66 | -0.148 → -0.471 |
| NEW v2 — ES only · London+AM · 2R · breakeven after +1R | 27 | 33.3% | 0.066 | 1.79 | 1.13 | 0.303 → -0.407 |

## System Lab — which variant is most profitable?

Every mechanical variant of the strategy, run on all markets, ranked by total cost-adjusted R (profit in units of risk, after $10/trade costs). **How to read this honestly:** with this many variants, the top row will always look good by luck alone. Trust a variant only if it has a ✅ robust flag — positive overall, positive **out-of-sample** (the last 30% of trades, which it was not selected on), and positive in at least two markets — and only if it KEEPS its flag as data accumulates over the coming months.

| Rank | Variant | Trades | Win % | Avg R | Total R | PF | NQ avg R | ES avg R | CL avg R | IS → OOS | Robust |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2R · breakeven stop after +1R | 73 | 26.0% | -0.148 | -10.81 | 0.75 | -0.268 (28) | -0.055 (37) | -0.157 (8) | -0.009 → -0.433 | — |
| 2 | 1R target · stop@sweep | 73 | 45.2% | -0.171 | -12.51 | 0.71 | -0.268 (28) | -0.101 (37) | -0.157 (8) | -0.084 → -0.349 | — |
| 3 | 2R target · stop@sweep (base) | 73 | 30.1% | -0.245 | -17.9 | 0.66 | -0.343 (28) | -0.136 (37) | -0.407 (8) | -0.135 → -0.471 | — |
| 4 | 2R · no time exit (hold 6.5h) | 73 | 26.0% | -0.277 | -20.23 | 0.65 | -0.395 (28) | -0.159 (37) | -0.407 (8) | -0.136 → -0.565 | — |
| 5 | 3R target · stop@sweep | 73 | 24.7% | -0.279 | -20.39 | 0.65 | -0.355 (28) | -0.032 (37) | -1.157 (8) | -0.17 → -0.502 | — |
| 6 | 1.5R target · stop@sweep | 73 | 31.5% | -0.341 | -24.9 | 0.53 | -0.432 (28) | -0.231 (37) | -0.532 (8) | -0.237 → -0.554 | — |
| 7 | 3R target · stop@gap edge | 150 | 24.0% | -0.172 | -25.81 | 0.8 | -0.358 (53) | -0.205 (51) | 0.078 (46) | -0.174 → -0.168 | — |
| 8 | FADE the setup (take opposite side) | 73 | 26.0% | -0.417 | -30.45 | 0.46 | -0.366 (28) | -0.377 (37) | -0.782 (8) | -0.475 → -0.299 | — |
| 9 | 1.5R target · stop@gap edge | 150 | 36.0% | -0.224 | -33.62 | 0.69 | -0.358 (53) | -0.338 (51) | 0.057 (46) | -0.211 → -0.255 | — |
| 10 | 2R target · stop@gap edge | 150 | 28.0% | -0.284 | -42.62 | 0.65 | -0.49 (53) | -0.299 (51) | -0.03 (46) | -0.288 → -0.276 | — |
| 11 | 1R target · stop@gap edge | 150 | 39.3% | -0.337 | -50.62 | 0.51 | -0.471 (53) | -0.377 (51) | -0.139 (46) | -0.355 → -0.298 | — |

## Oil Lab — a Silver Bullet restructured for CL

Crude oil's liquidity clock differs from equity indices, so the same sweep→FVG mechanics are scanned across oil-native windows: Brent/London flow, the NYMEX open, the 10:30 EIA report hour, midday, and pre-settlement. Same honesty rules as the System Lab — trust ✅ rows only, and only if they persist as data grows.

| Rank | CL window · target | Trades | Win % | Avg R | Total R | PF | IS → OOS | Robust |
|---|---|---|---|---|---|---|---|---|
| 1 | EIA 10:30-11:30a · 2R | 1 | 100.0% | 1.933 | 1.93 | ∞ | None → 1.933 | — |
| 2 | EIA 10:30-11:30a · 1R | 1 | 100.0% | 0.933 | 0.93 | ∞ | None → 0.933 | — |
| 3 | NYMEX open 9-10a · 1R | 1 | 0.0% | -1.083 | -1.08 | 0.0 | None → -1.083 | — |
| 4 | NYMEX open 9-10a · 2R | 1 | 0.0% | -1.083 | -1.08 | 0.0 | None → -1.083 | — |
| 5 | Pre-settle 1:30-2:30p · 1R | 3 | 33.3% | -0.444 | -1.33 | 0.4 | -0.127 → -1.077 | — |
| 6 | Midday 12-1p · 1R | 3 | 33.3% | -0.514 | -1.54 | 0.37 | -1.225 → 0.909 | — |
| 7 | Brent/London 3-4a · 1R | 3 | 33.3% | -0.54 | -1.62 | 0.37 | -0.281 → -1.059 | — |
| 8 | Pre-settle 1:30-2:30p · 2R | 3 | 0.0% | -1.11 | -3.33 | 0.0 | -1.127 → -1.077 | — |
| 9 | Midday 12-1p · 2R | 3 | 0.0% | -1.18 | -3.54 | 0.0 | -1.225 → -1.091 | — |
| 10 | Brent/London 3-4a · 2R | 3 | 0.0% | -1.207 | -3.62 | 0.0 | -1.281 → -1.059 | — |

## Recent trades

| Date | Window | Dir | Entry | Risk (pts) | Exit | P&L |
|---|---|---|---|---|---|---|
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
| 2026-08-06 | PM 2-3pm | bear | 29524.5 | 51.25 | time | +$560 |
| 2026-08-04 | London 3-4am | bear | 29093.0 | 7.5 | stop | −$160 |

Full log: [trades.csv](trades.csv) · raw stats: [results.json](results.json) · interactive report: [report.html](report.html) (download to view)

## The mechanical rules

Windows 3–4 AM / 10–11 AM / 2–3 PM NY. Liquidity sweep = bar takes out the prior 2-hour extreme and closes back inside (scanned from 30 min before the window). First fair value gap (≥0.5 pt, displacement candle closing in bias direction) forming inside the window after the sweep. Limit entry at the near gap edge, must fill before window close. Stop 1 tick beyond the sweep extreme (skip if risk > 60 pts). Target 2R. 2-hour time exit. Same-bar stop+target counts as a loss. One trade per window. $10 round-trip costs, $20/point, 1 contract.

## Caveats

Data is IBKR's 10-minute-delayed consolidated feed (fine for end-of-day analysis). IBKR serves at most 3,500 bars (~13.5 trading days of 5-min) per pull, which is why this repo accumulates them twice weekly — a missed fortnight of runs would leave a permanent gap. Contract months are kept as separate price series to avoid roll artifacts; trades are deduplicated per (day, window) across contracts. Limit fills are assumed at the touched price with no queue — real fills would be somewhat worse.
