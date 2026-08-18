# Silver Bullet Strategy — Accumulating NQ Backtest

Fully mechanical backtest of the ICT "Silver Bullet" setup on E-mini Nasdaq 100 (NQ) futures, 5-minute bars, updated automatically on a schedule (GitHub Actions pulling delayed Yahoo Finance data, plus optional IBKR pulls). Every run re-tests the entire accumulated history, so the trade sample below grows over time.

**Last updated:** 2026-08-18 13:14 UTC · **Rules:** v1.1 (2026-08-18) · **Data:** NQ202609: 3499 bars, 2026-07-29 → 2026-08-16; NQF-continuous: 13717 bars, 2026-06-08 → 2026-08-18; CL: 13484 bars, 2026-06-09 → 2026-08-18; ES: 13442 bars, 2026-06-09 → 2026-08-18

> ⚠️ **Small-sample warning:** results below are not statistically meaningful until the sample reaches well over 100 trades across different market regimes. Treat everything here as an ongoing experiment, not evidence of an edge. Not financial advice.

## Headline (1 contract, after $10/trade costs)

| Net P&L | Trades | Win rate | Profit factor | Max drawdown | Avg/trade |
|---|---|---|---|---|---|
| **−$3,865** | 18 (3T/13S/2X) | 27.8% | 0.55 | $6,755 | −$215 |

T = target hit, S = stopped, X = 2-hour time exit

## Equity curve

![Cumulative P&L](results/equity.svg)

## By window (New York time)

| Window | Trades | Win rate | Net $ | Profit factor |
|---|---|---|---|---|
| London 3-4am | 12 | 25.0% | −$2,135 | 0.63 |
| AM 10-11am | 1 | 0.0% | −$515 | 0.0 |
| PM 2-3pm | 5 | 40.0% | −$1,215 | 0.48 |

## Cross-market robustness

Same mechanical rules run on other markets (continuous front-month, Yahoo data). Scored in **R-multiples** — profit measured in units of initial risk — so different point values compare fairly. NQ row uses the NQ trades above.

| Market | Trades | Win % | Avg R | Total R | Profit factor (R) | Net $ (1 contract) |
|---|---|---|---|---|---|---|
| NQ | 18 | 27.8% | -0.31 | -5.62 | 0.57 | −$3,865 |
| CL | 5 | 20.0% | -0.4 | -2.0 | 0.5 | −$240 |
| ES | 27 | 40.7% | 0.14 | 3.87 | 1.26 | +$930 |

## System Lab — which variant is most profitable?

Every mechanical variant of the strategy, run on all markets, ranked by total cost-adjusted R (profit in units of risk, after $10/trade costs). **How to read this honestly:** with this many variants, the top row will always look good by luck alone. Trust a variant only if it has a ✅ robust flag — positive overall, positive **out-of-sample** (the last 30% of trades, which it was not selected on), and positive in at least two markets — and only if it KEEPS its flag as data accumulates over the coming months.

| Rank | Variant | Trades | Win % | Avg R | Total R | PF | NQ avg R | ES avg R | CL avg R | IS → OOS | Robust |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2R · breakeven stop after +1R | 50 | 32.0% | -0.005 | -0.26 | 0.99 | -0.268 (18) | 0.245 (27) | -0.409 (5) | -0.045 → 0.073 | — |
| 2 | 1R target · stop@sweep | 50 | 50.0% | -0.079 | -3.96 | 0.85 | -0.268 (18) | 0.108 (27) | -0.409 (5) | -0.067 → -0.104 | — |
| 3 | 2R target · stop@sweep (base) | 50 | 34.0% | -0.129 | -6.44 | 0.81 | -0.334 (18) | 0.097 (27) | -0.609 (5) | -0.172 → -0.045 | — |
| 4 | 2R · no time exit (hold 6.5h) | 50 | 30.0% | -0.154 | -7.68 | 0.79 | -0.354 (18) | 0.065 (27) | -0.609 (5) | -0.127 → -0.205 | — |
| 5 | 3R target · stop@sweep | 50 | 28.0% | -0.163 | -8.16 | 0.78 | -0.463 (18) | 0.23 (27) | -1.209 (5) | -0.051 → -0.381 | — |
| 6 | 1.5R target · stop@sweep | 50 | 36.0% | -0.229 | -11.44 | 0.66 | -0.417 (18) | -0.015 (27) | -0.709 (5) | -0.248 → -0.192 | — |
| 7 | 3R target · stop@gap edge | 107 | 24.3% | -0.166 | -17.71 | 0.81 | -0.35 (37) | -0.076 (37) | -0.059 (33) | -0.162 → -0.174 | — |
| 8 | FADE the setup (take opposite side) | 50 | 26.0% | -0.409 | -20.43 | 0.46 | -0.347 (18) | -0.413 (27) | -0.609 (5) | -0.494 → -0.244 | — |
| 9 | 1.5R target · stop@gap edge | 107 | 36.4% | -0.215 | -23.03 | 0.7 | -0.296 (37) | -0.247 (37) | -0.09 (33) | -0.276 → -0.086 | — |
| 10 | 2R target · stop@gap edge | 107 | 28.0% | -0.285 | -30.53 | 0.65 | -0.458 (37) | -0.152 (37) | -0.241 (33) | -0.269 → -0.321 | — |
| 11 | 1R target · stop@gap edge | 107 | 38.3% | -0.36 | -38.53 | 0.49 | -0.458 (37) | -0.368 (37) | -0.241 (33) | -0.392 → -0.292 | — |

## Oil Lab — a Silver Bullet restructured for CL

Crude oil's liquidity clock differs from equity indices, so the same sweep→FVG mechanics are scanned across oil-native windows: Brent/London flow, the NYMEX open, the 10:30 EIA report hour, midday, and pre-settlement. Same honesty rules as the System Lab — trust ✅ rows only, and only if they persist as data grows.

| Rank | CL window · target | Trades | Win % | Avg R | Total R | PF | IS → OOS | Robust |
|---|---|---|---|---|---|---|---|---|
| 1 | Pre-settle 1:30-2:30p · 1R | 2 | 50.0% | -0.127 | -0.25 | 0.78 | 0.889 → -1.143 | — |
| 2 | Brent/London 3-4a · 1R | 1 | 0.0% | -1.5 | -1.5 | 0.0 | None → -1.5 | — |
| 3 | Brent/London 3-4a · 2R | 1 | 0.0% | -1.5 | -1.5 | 0.0 | None → -1.5 | — |
| 4 | Midday 12-1p · 1R | 3 | 33.3% | -0.514 | -1.54 | 0.37 | -1.225 → 0.909 | — |
| 5 | Pre-settle 1:30-2:30p · 2R | 2 | 0.0% | -1.127 | -2.25 | 0.0 | -1.111 → -1.143 | — |
| 6 | Midday 12-1p · 2R | 3 | 0.0% | -1.18 | -3.54 | 0.0 | -1.225 → -1.091 | — |
| 7 | NYMEX open 9-10a · 1R | 0 | — | — | — | — | — | — |
| 8 | NYMEX open 9-10a · 2R | 0 | — | — | — | — | — | — |
| 9 | EIA 10:30-11:30a · 1R | 0 | — | — | — | — | — | — |
| 10 | EIA 10:30-11:30a · 2R | 0 | — | — | — | — | — | — |

## Recent trades

| Date | Window | Dir | Entry | Risk (pts) | Exit | P&L |
|---|---|---|---|---|---|---|
| 2026-08-17 | London 3-4am | bear | 30313.0 | 14.25 | stop | −$295 |
| 2026-08-13 | London 3-4am | bull | 29866.0 | 8.0 | target | +$310 |
| 2026-08-11 | London 3-4am | bull | 29770.0 | 42.25 | stop | −$855 |
| 2026-08-06 | PM 2-3pm | bear | 29524.5 | 51.25 | time | +$560 |
| 2026-08-04 | London 3-4am | bear | 29093.0 | 7.5 | stop | −$160 |
| 2026-07-31 | London 3-4am | bull | 28509.75 | 60.0 | target | +$2,390 |
| 2026-07-22 | London 3-4am | bull | 29090.75 | 40.0 | stop | −$810 |
| 2026-07-21 | PM 2-3pm | bear | 29329.25 | 35.75 | time | +$575 |
| 2026-07-10 | AM 10-11am | bear | 29911.75 | 25.25 | stop | −$515 |
| 2026-07-06 | London 3-4am | bear | 29839.75 | 21.75 | stop | −$445 |
| 2026-06-29 | PM 2-3pm | bear | 30004.5 | 34.0 | stop | −$690 |
| 2026-06-29 | London 3-4am | bear | 29633.75 | 51.25 | stop | −$1,035 |
| 2026-06-24 | London 3-4am | bull | 29812.0 | 46.75 | stop | −$945 |
| 2026-06-18 | PM 2-3pm | bear | 30684.25 | 52.75 | stop | −$1,065 |
| 2026-06-18 | London 3-4am | bear | 30406.25 | 32.5 | stop | −$660 |

Full log: [trades.csv](trades.csv) · raw stats: [results.json](results.json) · interactive report: [report.html](report.html) (download to view)

## The mechanical rules

Windows 3–4 AM / 10–11 AM / 2–3 PM NY. Liquidity sweep = bar takes out the prior 2-hour extreme and closes back inside (scanned from 30 min before the window). First fair value gap (≥0.5 pt, displacement candle closing in bias direction) forming inside the window after the sweep. Limit entry at the near gap edge, must fill before window close. Stop 1 tick beyond the sweep extreme (skip if risk > 60 pts). Target 2R. 2-hour time exit. Same-bar stop+target counts as a loss. One trade per window. $10 round-trip costs, $20/point, 1 contract.

## Caveats

Data is IBKR's 10-minute-delayed consolidated feed (fine for end-of-day analysis). IBKR serves at most 3,500 bars (~13.5 trading days of 5-min) per pull, which is why this repo accumulates them twice weekly — a missed fortnight of runs would leave a permanent gap. Contract months are kept as separate price series to avoid roll artifacts; trades are deduplicated per (day, window) across contracts. Limit fills are assumed at the touched price with no queue — real fills would be somewhat worse.
