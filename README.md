# Silver Bullet Strategy — Accumulating NQ Backtest

Fully mechanical backtest of the ICT "Silver Bullet" setup on E-mini Nasdaq 100 (NQ) futures, 5-minute bars, updated automatically on a schedule (GitHub Actions pulling delayed Yahoo Finance data, plus optional IBKR pulls). Every run re-tests the entire accumulated history, so the trade sample below grows over time.

**Last updated:** 2026-09-10 01:25 UTC · **Rules:** v1.1 (2026-08-18) · **Data:** NQ202609: 3499 bars, 2026-07-29 → 2026-08-16; NQF-continuous: 17903 bars, 2026-06-08 → 2026-09-09; CL: 17682 bars, 2026-06-09 → 2026-09-09; ES: 17628 bars, 2026-06-09 → 2026-09-09

> ⚠️ **Small-sample warning:** results below are not statistically meaningful until the sample reaches well over 100 trades across different market regimes. Treat everything here as an ongoing experiment, not evidence of an edge. Not financial advice.

## Headline (1 contract, after $10/trade costs)

| Net P&L | Trades | Win rate | Profit factor | Max drawdown | Avg/trade |
|---|---|---|---|---|---|
| **−$5,895** | 27 (4T/20S/3X) | 25.9% | 0.51 | $6,835 | −$218 |

T = target hit, S = stopped, X = 2-hour time exit

## Equity curve

![Cumulative P&L](results/equity.svg)

## By window (New York time)

| Window | Trades | Win rate | Net $ | Profit factor |
|---|---|---|---|---|
| London 3-4am | 16 | 31.2% | −$1,865 | 0.73 |
| AM 10-11am | 3 | 0.0% | −$695 | 0.0 |
| PM 2-3pm | 8 | 25.0% | −$3,335 | 0.25 |

## Cross-market robustness

Same mechanical rules run on other markets (continuous front-month, Yahoo data). Scored in **R-multiples** — profit measured in units of initial risk — so different point values compare fairly. NQ row uses the NQ trades above.

| Market | Trades | Win % | Avg R | Total R | Profit factor (R) | Net $ (1 contract) |
|---|---|---|---|---|---|---|
| NQ | 27 | 25.9% | -0.39 | -10.53 | 0.47 | −$5,895 |
| CL | 8 | 25.0% | -0.25 | -2.0 | 0.67 | −$380 |
| ES | 36 | 30.6% | -0.14 | -5.13 | 0.79 | −$1,572 |

## Old vs New — the retro comparison

The parameter analysis (Aug 2026) found the base spec's consistent failures — the PM window, gap-edge stops, and NQ itself — and produced a fixed spec: **v2 = ES only · London+AM windows · 2R target · breakeven stop after +1R**. Both are re-run over all accumulated history on every update. v2 was *selected* on this same history (selection bias), so its edge is overstated here — the growing out-of-sample record is the real verdict.

| Spec | Trades | Win % | Avg R | Total R | PF | IS → OOS |
|---|---|---|---|---|---|---|
| OLD — base spec · all markets · all windows | 71 | 28.2% | -0.307 | -21.83 | 0.59 | -0.11 → -0.747 |
| NEW v2 — ES only · London+AM · 2R · breakeven after +1R | 26 | 34.6% | 0.071 | 1.84 | 1.13 | 0.303 → -0.452 |

## System Lab — which variant is most profitable?

Every mechanical variant of the strategy, run on all markets, ranked by total cost-adjusted R (profit in units of risk, after $10/trade costs). **How to read this honestly:** with this many variants, the top row will always look good by luck alone. Trust a variant only if it has a ✅ robust flag — positive overall, positive **out-of-sample** (the last 30% of trades, which it was not selected on), and positive in at least two markets — and only if it KEEPS its flag as data accumulates over the coming months.

| Rank | Variant | Trades | Win % | Avg R | Total R | PF | NQ avg R | ES avg R | CL avg R | IS → OOS | Robust |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2R · breakeven stop after +1R | 71 | 25.4% | -0.179 | -12.74 | 0.7 | -0.351 (27) | -0.055 (36) | -0.157 (8) | 0.014 → -0.582 | — |
| 2 | 1R target · stop@sweep | 71 | 43.7% | -0.203 | -14.43 | 0.66 | -0.314 (27) | -0.13 (36) | -0.157 (8) | -0.063 → -0.495 | — |
| 3 | 2R target · stop@sweep (base) | 71 | 28.2% | -0.307 | -21.83 | 0.59 | -0.429 (27) | -0.194 (36) | -0.407 (8) | -0.115 → -0.709 | — |
| 4 | 3R target · stop@gap edge | 145 | 24.1% | -0.166 | -24.12 | 0.81 | -0.344 (52) | -0.185 (50) | 0.07 (43) | -0.145 → -0.216 | — |
| 5 | 2R · no time exit (hold 6.5h) | 71 | 23.9% | -0.34 | -24.16 | 0.58 | -0.483 (27) | -0.218 (36) | -0.407 (8) | -0.117 → -0.807 | — |
| 6 | 3R target · stop@sweep | 71 | 22.5% | -0.36 | -25.55 | 0.56 | -0.478 (27) | -0.094 (36) | -1.157 (8) | -0.151 → -0.796 | — |
| 7 | 1.5R target · stop@sweep | 71 | 29.6% | -0.392 | -27.83 | 0.47 | -0.503 (27) | -0.278 (36) | -0.532 (8) | -0.219 → -0.752 | — |
| 8 | FADE the setup (take opposite side) | 71 | 26.8% | -0.4 | -28.38 | 0.48 | -0.342 (27) | -0.358 (36) | -0.782 (8) | -0.462 → -0.269 | — |
| 9 | 1.5R target · stop@gap edge | 145 | 36.6% | -0.21 | -30.44 | 0.71 | -0.344 (52) | -0.321 (50) | 0.081 (43) | -0.207 → -0.216 | — |
| 10 | 2R target · stop@gap edge | 145 | 28.3% | -0.275 | -39.94 | 0.66 | -0.479 (52) | -0.281 (50) | -0.023 (43) | -0.262 → -0.307 | — |
| 11 | 1R target · stop@gap edge | 145 | 40.0% | -0.324 | -46.94 | 0.53 | -0.459 (52) | -0.361 (50) | -0.116 (43) | -0.351 → -0.261 | — |

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
| 2026-07-31 | London 3-4am | bull | 28509.75 | 60.0 | target | +$2,390 |

Full log: [trades.csv](trades.csv) · raw stats: [results.json](results.json) · interactive report: [report.html](report.html) (download to view)

## The mechanical rules

Windows 3–4 AM / 10–11 AM / 2–3 PM NY. Liquidity sweep = bar takes out the prior 2-hour extreme and closes back inside (scanned from 30 min before the window). First fair value gap (≥0.5 pt, displacement candle closing in bias direction) forming inside the window after the sweep. Limit entry at the near gap edge, must fill before window close. Stop 1 tick beyond the sweep extreme (skip if risk > 60 pts). Target 2R. 2-hour time exit. Same-bar stop+target counts as a loss. One trade per window. $10 round-trip costs, $20/point, 1 contract.

## Caveats

Data is IBKR's 10-minute-delayed consolidated feed (fine for end-of-day analysis). IBKR serves at most 3,500 bars (~13.5 trading days of 5-min) per pull, which is why this repo accumulates them twice weekly — a missed fortnight of runs would leave a permanent gap. Contract months are kept as separate price series to avoid roll artifacts; trades are deduplicated per (day, window) across contracts. Limit fills are assumed at the touched price with no queue — real fills would be somewhat worse.
