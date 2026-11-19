# Silver Bullet Strategy — Accumulating NQ Backtest

Fully mechanical backtest of the ICT "Silver Bullet" setup on E-mini Nasdaq 100 (NQ) futures, 5-minute bars, updated automatically on a schedule (GitHub Actions pulling delayed Yahoo Finance data, plus optional IBKR pulls). Every run re-tests the entire accumulated history, so the trade sample below grows over time.

**Last updated:** 2026-11-19 23:46 UTC · **Rules:** v1.1 (2026-08-18) · **Data:** NQ202609: 3499 bars, 2026-07-29 → 2026-08-16; NQF-continuous: 31889 bars, 2026-06-08 → 2026-11-19; CL: 31708 bars, 2026-06-09 → 2026-11-19; ES: 31616 bars, 2026-06-09 → 2026-11-19

> ⚠️ **Small-sample warning:** results below are not statistically meaningful until the sample reaches well over 100 trades across different market regimes. Treat everything here as an ongoing experiment, not evidence of an edge. Not financial advice.

## Headline (1 contract, after $10/trade costs)

| Net P&L | Trades | Win rate | Profit factor | Max drawdown | Avg/trade |
|---|---|---|---|---|---|
| **−$5,985** | 44 (9T/31S/4X) | 27.3% | 0.64 | $8,595 | −$136 |

T = target hit, S = stopped, X = 2-hour time exit

## Equity curve

![Cumulative P&L](results/equity.svg)

## By window (New York time)

| Window | Trades | Win rate | Net $ | Profit factor |
|---|---|---|---|---|
| London 3-4am | 25 | 36.0% | +$40 | 1.0 |
| AM 10-11am | 7 | 0.0% | −$1,875 | 0.0 |
| PM 2-3pm | 12 | 25.0% | −$4,150 | 0.31 |

## Cross-market robustness

Same mechanical rules run on other markets (continuous front-month, Yahoo data). Scored in **R-multiples** — profit measured in units of initial risk — so different point values compare fairly. NQ row uses the NQ trades above.

| Market | Trades | Win % | Avg R | Total R | Profit factor (R) | Net $ (1 contract) |
|---|---|---|---|---|---|---|
| NQ | 44 | 27.3% | -0.27 | -11.91 | 0.62 | −$5,985 |
| CL | 10 | 40.0% | 0.2 | 2.0 | 1.33 | +$20 |
| ES | 56 | 32.1% | -0.12 | -6.93 | 0.81 | −$2,198 |

## Old vs New — the retro comparison

**The v2 lesson (read this first):** the Aug-18 'optimized' spec (ES · London+AM · breakeven) showed +0.49R/trade at selection — then lost **−5.4R over its next 7 live trades**. That is selection bias demonstrated with real forward data: the best-looking retro spec is mostly luck. **v3** (selected Sep 19 from the full-history grid: NQ midday·1R, ES NYMEX-open+pre-settle·1R and London·2R, CL not traded — no CL configuration is profitable) carries exactly the same risk. Its retro numbers below are overstated by construction; only its forward record from Sep 19 onward counts, and v2's fate is the base rate for what to expect.

| Spec | Trades | Win % | Avg R | Total R | PF | IS → OOS |
|---|---|---|---|---|---|---|
| OLD — base spec · all markets · all windows | 110 | 30.9% | -0.207 | -22.8 | 0.71 | -0.208 → -0.207 |
| NEW v3 (sel. Sep 19) — NQ midday·1R · ES open+pre-settle·1R & London·2R · CL not traded | 86 | 52.3% | 0.109 | 9.37 | 1.23 | 0.271 → -0.265 |

## System Lab — which variant is most profitable?

Every mechanical variant of the strategy, run on all markets, ranked by total cost-adjusted R (profit in units of risk, after $10/trade costs). **How to read this honestly:** with this many variants, the top row will always look good by luck alone. Trust a variant only if it has a ✅ robust flag — positive overall, positive **out-of-sample** (the last 30% of trades, which it was not selected on), and positive in at least two markets — and only if it KEEPS its flag as data accumulates over the coming months.

| Rank | Variant | Trades | Win % | Avg R | Total R | PF | NQ avg R | ES avg R | CL avg R | IS → OOS | Robust |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2R · breakeven stop after +1R | 110 | 27.3% | -0.112 | -12.34 | 0.81 | -0.245 (44) | -0.074 (56) | 0.254 (10) | -0.09 → -0.162 | — |
| 2 | 1R target · stop@sweep | 110 | 44.5% | -0.169 | -18.61 | 0.71 | -0.313 (44) | -0.096 (56) | 0.054 (10) | -0.125 → -0.267 | — |
| 3 | 2R target · stop@sweep (base) | 110 | 30.9% | -0.207 | -22.8 | 0.71 | -0.315 (44) | -0.169 (56) | 0.054 (10) | -0.196 → -0.232 | — |
| 4 | 2R · no time exit (hold 6.5h) | 110 | 26.4% | -0.257 | -28.25 | 0.67 | -0.362 (44) | -0.23 (56) | 0.054 (10) | -0.227 → -0.324 | — |
| 5 | 1.5R target · stop@sweep | 110 | 33.6% | -0.271 | -29.8 | 0.61 | -0.36 (44) | -0.223 (56) | -0.146 (10) | -0.302 → -0.202 | — |
| 6 | FADE the setup (take opposite side) | 110 | 27.3% | -0.36 | -39.6 | 0.52 | -0.265 (44) | -0.347 (56) | -0.846 (10) | -0.409 → -0.25 | — |
| 7 | 3R target · stop@gap edge | 234 | 23.9% | -0.172 | -40.14 | 0.8 | -0.179 (86) | -0.202 (82) | -0.124 (66) | -0.098 → -0.341 | — |
| 8 | 3R target · stop@sweep | 110 | 21.8% | -0.393 | -43.25 | 0.51 | -0.438 (44) | -0.295 (56) | -0.746 (10) | -0.245 → -0.725 | — |
| 9 | 1.5R target · stop@gap edge | 234 | 35.9% | -0.226 | -52.96 | 0.69 | -0.237 (86) | -0.291 (82) | -0.132 (66) | -0.201 → -0.285 | — |
| 10 | 2R target · stop@gap edge | 234 | 28.2% | -0.278 | -64.96 | 0.66 | -0.342 (86) | -0.272 (82) | -0.2 (66) | -0.238 → -0.369 | — |
| 11 | 1R target · stop@gap edge | 234 | 40.2% | -0.32 | -74.96 | 0.53 | -0.388 (86) | -0.285 (82) | -0.276 (66) | -0.311 → -0.341 | — |

## Oil Lab — a Silver Bullet restructured for CL

Crude oil's liquidity clock differs from equity indices, so the same sweep→FVG mechanics are scanned across oil-native windows: Brent/London flow, the NYMEX open, the 10:30 EIA report hour, midday, and pre-settlement. Same honesty rules as the System Lab — trust ✅ rows only, and only if they persist as data grows.

| Rank | CL window · target | Trades | Win % | Avg R | Total R | PF | IS → OOS | Robust |
|---|---|---|---|---|---|---|---|---|
| 1 | EIA 10:30-11:30a · 1R | 3 | 100.0% | 0.927 | 2.78 | ∞ | 0.935 → 0.909 | — |
| 2 | EIA 10:30-11:30a · 2R | 3 | 66.7% | 0.927 | 2.78 | 3.55 | 1.935 → -1.091 | — |
| 3 | Pre-settle 1:30-2:30p · 1R | 5 | 60.0% | 0.099 | 0.5 | 1.22 | -0.444 → 0.913 | — |
| 4 | Midday 12-1p · 1R | 3 | 33.3% | -0.514 | -1.54 | 0.37 | -1.225 → 0.909 | — |
| 5 | Brent/London 3-4a · 1R | 3 | 33.3% | -0.54 | -1.62 | 0.37 | -0.281 → -1.059 | — |
| 6 | NYMEX open 9-10a · 1R | 2 | 0.0% | -1.083 | -2.17 | 0.0 | -1.083 → -1.083 | — |
| 7 | NYMEX open 9-10a · 2R | 2 | 0.0% | -1.083 | -2.17 | 0.0 | -1.083 → -1.083 | — |
| 8 | Pre-settle 1:30-2:30p · 2R | 5 | 20.0% | -0.501 | -2.5 | 0.43 | -1.11 → 0.413 | — |
| 9 | Midday 12-1p · 2R | 3 | 0.0% | -1.18 | -3.54 | 0.0 | -1.225 → -1.091 | — |
| 10 | Brent/London 3-4a · 2R | 3 | 0.0% | -1.207 | -3.62 | 0.0 | -1.281 → -1.059 | — |

## Walk-Forward Verdict — the honest number

Simulation of adaptive re-optimization with **zero hindsight**: every 14 days, the top specs (up to 4) are re-selected using only data available before that date, then traded blind for the next period. This is what 'keep tuning and trade the winner' — the v2/v3 approach — would actually have earned.

| Trades | Win % | Avg R | **Total R** | PF | At 2× costs | Specs churned |
|---|---|---|---|---|---|---|
| 38 | 50.0% | 0.006 | **0.23** | 1.01 | -1.29 | 9 distinct specs |

**Reading:** positive walk-forward is a meaningfully stronger signal than any retro number — but with this few periods it is still fragile. Watch whether it persists and whether the picked specs stabilize (low churn) as data accumulates.

## Recent trades

| Date | Window | Dir | Entry | Risk (pts) | Exit | P&L |
|---|---|---|---|---|---|---|
| 2026-11-13 | PM 2-3pm | bear | 27980.5 | 1.5 | stop | −$40 |
| 2026-11-11 | London 3-4am | bear | 28271.75 | 11.0 | stop | −$230 |
| 2026-11-10 | London 3-4am | bear | 27995.75 | 48.75 | target | +$1,940 |
| 2026-11-09 | PM 2-3pm | bear | 27950.0 | 50.5 | stop | −$1,020 |
| 2026-10-28 | London 3-4am | bear | 29953.25 | 8.0 | stop | −$170 |
| 2026-10-16 | AM 10-11am | bull | 29871.5 | 18.0 | stop | −$370 |
| 2026-10-16 | London 3-4am | bull | 30184.0 | 57.25 | time | −$450 |
| 2026-10-12 | London 3-4am | bull | 31186.25 | 30.5 | stop | −$620 |
| 2026-10-09 | PM 2-3pm | bear | 31108.25 | 24.25 | stop | −$495 |
| 2026-10-07 | London 3-4am | bull | 31470.0 | 20.25 | stop | −$415 |
| 2026-10-06 | AM 10-11am | bear | 31541.75 | 25.5 | stop | −$520 |
| 2026-10-06 | London 3-4am | bear | 31384.25 | 15.0 | target | +$590 |
| 2026-10-05 | AM 10-11am | bear | 31220.0 | 9.75 | stop | −$205 |
| 2026-10-02 | AM 10-11am | bear | 31256.0 | 3.75 | stop | −$85 |
| 2026-09-24 | London 3-4am | bull | 30575.25 | 13.0 | target | +$510 |

Full log: [trades.csv](trades.csv) · raw stats: [results.json](results.json) · interactive report: [report.html](report.html) (download to view)

## The mechanical rules

Windows 3–4 AM / 10–11 AM / 2–3 PM NY. Liquidity sweep = bar takes out the prior 2-hour extreme and closes back inside (scanned from 30 min before the window). First fair value gap (≥0.5 pt, displacement candle closing in bias direction) forming inside the window after the sweep. Limit entry at the near gap edge, must fill before window close. Stop 1 tick beyond the sweep extreme (skip if risk > 60 pts). Target 2R. 2-hour time exit. Same-bar stop+target counts as a loss. One trade per window. $10 round-trip costs, $20/point, 1 contract.

## Caveats

Data is IBKR's 10-minute-delayed consolidated feed (fine for end-of-day analysis). IBKR serves at most 3,500 bars (~13.5 trading days of 5-min) per pull, which is why this repo accumulates them twice weekly — a missed fortnight of runs would leave a permanent gap. Contract months are kept as separate price series to avoid roll artifacts; trades are deduplicated per (day, window) across contracts. Limit fills are assumed at the touched price with no queue — real fills would be somewhat worse.
