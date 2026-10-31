# Silver Bullet Strategy — Accumulating NQ Backtest

Fully mechanical backtest of the ICT "Silver Bullet" setup on E-mini Nasdaq 100 (NQ) futures, 5-minute bars, updated automatically on a schedule (GitHub Actions pulling delayed Yahoo Finance data, plus optional IBKR pulls). Every run re-tests the entire accumulated history, so the trade sample below grows over time.

**Last updated:** 2026-10-31 05:27 UTC · **Rules:** v1.1 (2026-08-18) · **Data:** NQ202609: 3499 bars, 2026-07-29 → 2026-08-16; NQF-continuous: 28033 bars, 2026-06-08 → 2026-10-30; CL: 27840 bars, 2026-06-09 → 2026-10-30; ES: 27760 bars, 2026-06-09 → 2026-10-30

> ⚠️ **Small-sample warning:** results below are not statistically meaningful until the sample reaches well over 100 trades across different market regimes. Treat everything here as an ongoing experiment, not evidence of an edge. Not financial advice.

## Headline (1 contract, after $10/trade costs)

| Net P&L | Trades | Win rate | Profit factor | Max drawdown | Avg/trade |
|---|---|---|---|---|---|
| **−$6,635** | 40 (8T/28S/4X) | 27.5% | 0.57 | $7,575 | −$166 |

T = target hit, S = stopped, X = 2-hour time exit

## Equity curve

![Cumulative P&L](results/equity.svg)

## By window (New York time)

| Window | Trades | Win rate | Net $ | Profit factor |
|---|---|---|---|---|
| London 3-4am | 23 | 34.8% | −$1,670 | 0.81 |
| AM 10-11am | 7 | 0.0% | −$1,875 | 0.0 |
| PM 2-3pm | 10 | 30.0% | −$3,090 | 0.38 |

## Cross-market robustness

Same mechanical rules run on other markets (continuous front-month, Yahoo data). Scored in **R-multiples** — profit measured in units of initial risk — so different point values compare fairly. NQ row uses the NQ trades above.

| Market | Trades | Win % | Avg R | Total R | Profit factor (R) | Net $ (1 contract) |
|---|---|---|---|---|---|---|
| NQ | 40 | 27.5% | -0.27 | -10.91 | 0.62 | −$6,635 |
| CL | 9 | 33.3% | 0.0 | 0.0 | 1.0 | −$230 |
| ES | 53 | 32.1% | -0.13 | -6.93 | 0.8 | −$2,305 |

## Old vs New — the retro comparison

**The v2 lesson (read this first):** the Aug-18 'optimized' spec (ES · London+AM · breakeven) showed +0.49R/trade at selection — then lost **−5.4R over its next 7 live trades**. That is selection bias demonstrated with real forward data: the best-looking retro spec is mostly luck. **v3** (selected Sep 19 from the full-history grid: NQ midday·1R, ES NYMEX-open+pre-settle·1R and London·2R, CL not traded — no CL configuration is profitable) carries exactly the same risk. Its retro numbers below are overstated by construction; only its forward record from Sep 19 onward counts, and v2's fate is the base rate for what to expect.

| Spec | Trades | Win % | Avg R | Total R | PF | IS → OOS |
|---|---|---|---|---|---|---|
| OLD — base spec · all markets · all windows | 102 | 30.4% | -0.227 | -23.19 | 0.68 | -0.265 → -0.141 |
| NEW v3 (sel. Sep 19) — NQ midday·1R · ES open+pre-settle·1R & London·2R · CL not traded | 80 | 52.5% | 0.107 | 8.57 | 1.23 | 0.257 → -0.242 |

## System Lab — which variant is most profitable?

Every mechanical variant of the strategy, run on all markets, ranked by total cost-adjusted R (profit in units of risk, after $10/trade costs). **How to read this honestly:** with this many variants, the top row will always look good by luck alone. Trust a variant only if it has a ✅ robust flag — positive overall, positive **out-of-sample** (the last 30% of trades, which it was not selected on), and positive in at least two markets — and only if it KEEPS its flag as data accumulates over the coming months.

| Rank | Variant | Trades | Win % | Avg R | Total R | PF | NQ avg R | ES avg R | CL avg R | IS → OOS | Robust |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2R · breakeven stop after +1R | 102 | 26.5% | -0.125 | -12.73 | 0.79 | -0.234 (40) | -0.075 (53) | 0.069 (9) | -0.136 → -0.099 | — |
| 2 | 1R target · stop@sweep | 102 | 45.1% | -0.157 | -16.0 | 0.73 | -0.284 (40) | -0.08 (53) | -0.042 (9) | -0.174 → -0.117 | — |
| 3 | 2R target · stop@sweep (base) | 102 | 30.4% | -0.227 | -23.19 | 0.68 | -0.311 (40) | -0.177 (53) | -0.154 (9) | -0.222 → -0.24 | — |
| 4 | 3R target · stop@gap edge | 209 | 25.4% | -0.118 | -24.64 | 0.86 | -0.09 (78) | -0.192 (72) | -0.065 (59) | -0.166 → -0.01 | — |
| 5 | 2R · no time exit (hold 6.5h) | 102 | 25.5% | -0.281 | -28.64 | 0.64 | -0.363 (40) | -0.24 (53) | -0.154 (9) | -0.255 → -0.341 | — |
| 6 | 1.5R target · stop@sweep | 102 | 33.3% | -0.281 | -28.69 | 0.6 | -0.349 (40) | -0.224 (53) | -0.32 (9) | -0.321 → -0.191 | — |
| 7 | FADE the setup (take opposite side) | 102 | 27.5% | -0.363 | -36.99 | 0.52 | -0.257 (40) | -0.365 (53) | -0.82 (9) | -0.399 → -0.28 | — |
| 8 | 3R target · stop@sweep | 102 | 21.6% | -0.4 | -40.76 | 0.51 | -0.424 (40) | -0.253 (53) | -1.154 (9) | -0.257 → -0.726 | — |
| 9 | 1.5R target · stop@gap edge | 209 | 36.8% | -0.206 | -42.95 | 0.72 | -0.218 (78) | -0.321 (72) | -0.048 (59) | -0.209 → -0.197 | — |
| 10 | 2R target · stop@gap edge | 209 | 29.7% | -0.237 | -49.45 | 0.7 | -0.27 (78) | -0.286 (72) | -0.132 (59) | -0.275 → -0.15 | — |
| 11 | 1R target · stop@gap edge | 209 | 41.6% | -0.294 | -61.45 | 0.56 | -0.372 (78) | -0.286 (72) | -0.2 (59) | -0.323 → -0.228 | — |

## Oil Lab — a Silver Bullet restructured for CL

Crude oil's liquidity clock differs from equity indices, so the same sweep→FVG mechanics are scanned across oil-native windows: Brent/London flow, the NYMEX open, the 10:30 EIA report hour, midday, and pre-settlement. Same honesty rules as the System Lab — trust ✅ rows only, and only if they persist as data grows.

| Rank | CL window · target | Trades | Win % | Avg R | Total R | PF | IS → OOS | Robust |
|---|---|---|---|---|---|---|---|---|
| 1 | EIA 10:30-11:30a · 2R | 2 | 100.0% | 1.935 | 3.87 | ∞ | 1.933 → 1.938 | — |
| 2 | EIA 10:30-11:30a · 1R | 2 | 100.0% | 0.935 | 1.87 | ∞ | 0.933 → 0.938 | — |
| 3 | Pre-settle 1:30-2:30p · 1R | 4 | 50.0% | -0.103 | -0.41 | 0.81 | -0.127 → -0.08 | — |
| 4 | Midday 12-1p · 1R | 3 | 33.3% | -0.514 | -1.54 | 0.37 | -1.225 → 0.909 | — |
| 5 | Brent/London 3-4a · 1R | 3 | 33.3% | -0.54 | -1.62 | 0.37 | -0.281 → -1.059 | — |
| 6 | NYMEX open 9-10a · 1R | 2 | 0.0% | -1.083 | -2.17 | 0.0 | -1.083 → -1.083 | — |
| 7 | NYMEX open 9-10a · 2R | 2 | 0.0% | -1.083 | -2.17 | 0.0 | -1.083 → -1.083 | — |
| 8 | Midday 12-1p · 2R | 3 | 0.0% | -1.18 | -3.54 | 0.0 | -1.225 → -1.091 | — |
| 9 | Brent/London 3-4a · 2R | 3 | 0.0% | -1.207 | -3.62 | 0.0 | -1.281 → -1.059 | — |
| 10 | Pre-settle 1:30-2:30p · 2R | 4 | 0.0% | -1.103 | -4.41 | 0.0 | -1.127 → -1.08 | — |

## Walk-Forward Verdict — the honest number

Simulation of adaptive re-optimization with **zero hindsight**: every 14 days, the top specs (up to 4) are re-selected using only data available before that date, then traded blind for the next period. This is what 'keep tuning and trade the winner' — the v2/v3 approach — would actually have earned.

| Trades | Win % | Avg R | **Total R** | PF | At 2× costs | Specs churned |
|---|---|---|---|---|---|---|
| 35 | 48.6% | -0.02 | **-0.71** | 0.96 | -2.16 | 9 distinct specs |

**Reading:** negative or flat walk-forward means the re-optimization process itself has no demonstrated edge — each period's 'best' specs did not stay best. High spec churn reinforces it: a real edge picks the same specs repeatedly; noise picks new ones each time.

## Recent trades

| Date | Window | Dir | Entry | Risk (pts) | Exit | P&L |
|---|---|---|---|---|---|---|
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
| 2026-09-16 | London 3-4am | bear | 29376.75 | 19.0 | target | +$750 |
| 2026-09-14 | PM 2-3pm | bear | 29567.25 | 18.75 | target | +$740 |
| 2026-09-09 | London 3-4am | bull | 29589.75 | 28.75 | stop | −$585 |
| 2026-09-03 | AM 10-11am | bear | 29283.25 | 2.0 | stop | −$50 |

Full log: [trades.csv](trades.csv) · raw stats: [results.json](results.json) · interactive report: [report.html](report.html) (download to view)

## The mechanical rules

Windows 3–4 AM / 10–11 AM / 2–3 PM NY. Liquidity sweep = bar takes out the prior 2-hour extreme and closes back inside (scanned from 30 min before the window). First fair value gap (≥0.5 pt, displacement candle closing in bias direction) forming inside the window after the sweep. Limit entry at the near gap edge, must fill before window close. Stop 1 tick beyond the sweep extreme (skip if risk > 60 pts). Target 2R. 2-hour time exit. Same-bar stop+target counts as a loss. One trade per window. $10 round-trip costs, $20/point, 1 contract.

## Caveats

Data is IBKR's 10-minute-delayed consolidated feed (fine for end-of-day analysis). IBKR serves at most 3,500 bars (~13.5 trading days of 5-min) per pull, which is why this repo accumulates them twice weekly — a missed fortnight of runs would leave a permanent gap. Contract months are kept as separate price series to avoid roll artifacts; trades are deduplicated per (day, window) across contracts. Limit fills are assumed at the touched price with no queue — real fills would be somewhat worse.
