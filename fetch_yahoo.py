#!/usr/bin/env python3
"""
Fetch recent NQ futures 5-minute bars from Yahoo Finance (NQ=F, continuous
front month, delayed public feed) and write them as
/tmp/yahoo_bars.csv with columns: timestamp_utc,open,high,low,close,volume

Runs inside GitHub Actions. Exits non-zero with a clear message on failure so
the workflow shows red instead of silently committing nothing.
"""
import os
import sys
import pandas as pd
import yfinance as yf

OUT = "/tmp/yahoo_bars.csv"

# Additional markets for the cross-market robustness comparison.
# Written to /tmp/sb_markets/<MARKET>.csv; update.py auto-ingests that folder.
EXTRA_MARKETS = {"ES": "ES=F", "CL": "CL=F"}
MARKETS_DIR = "/tmp/sb_markets"


def frame_to_rows(df):
    """Normalize a yfinance download frame to our CSV rows."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns=str.lower)
    need = ["open", "high", "low", "close", "volume"]
    for col in need:
        if col not in df.columns:
            raise SystemExit(f"missing column {col!r} in Yahoo response")
    df = df[need].dropna(subset=["open", "high", "low", "close"])
    df = df[(df["high"] >= df["low"]) & (df["low"] > 0)]
    rows = []
    for ts, r in df.iterrows():
        ts = pd.Timestamp(ts)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        ts = ts.tz_convert("UTC")
        rows.append((
            ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            round(float(r["open"]), 2), round(float(r["high"]), 2),
            round(float(r["low"]), 2), round(float(r["close"]), 2),
            int(r["volume"]) if pd.notna(r["volume"]) else 0,
        ))
    return rows


def fetch_symbol(ticker):
    last_err = None
    for period in ("59d", "30d", "7d"):   # fall back if Yahoo rejects long span
        try:
            df = yf.download(ticker, interval="5m", period=period,
                             progress=False, auto_adjust=False, threads=False)
            if df is not None and len(df) > 50:
                rows = frame_to_rows(df)
                if len(rows) > 50:
                    return rows, period
        except SystemExit:
            raise
        except Exception as e:      # noqa: BLE001 - report and try shorter span
            last_err = e
    raise RuntimeError(f"Yahoo fetch failed for {ticker}: {last_err}")


def write_rows(path, rows):
    with open(path, "w") as f:
        f.write("timestamp_utc,open,high,low,close,volume\n")
        for r in rows:
            f.write(",".join(map(str, r)) + "\n")


def main():
    # primary market (NQ) — a failure here fails the whole run
    try:
        rows, period = fetch_symbol("NQ=F")
    except RuntimeError as e:
        raise SystemExit(str(e))
    write_rows(OUT, rows)
    print(f"[fetch] NQ: {len(rows)} bars ({period}) {rows[0][0]} -> {rows[-1][0]}")

    # comparison markets — failures are reported but never kill the run
    os.makedirs(MARKETS_DIR, exist_ok=True)
    for market, ticker in EXTRA_MARKETS.items():
        try:
            rows, period = fetch_symbol(ticker)
            write_rows(os.path.join(MARKETS_DIR, market + ".csv"), rows)
            print(f"[fetch] {market}: {len(rows)} bars ({period}) "
                  f"{rows[0][0]} -> {rows[-1][0]}")
        except Exception as e:      # noqa: BLE001
            print(f"[fetch] WARNING: {market} skipped this run: {e}",
                  file=sys.stderr)


if __name__ == "__main__":
    main()
