#!/usr/bin/env python3
"""
Fetch recent NQ futures 5-minute bars from Yahoo Finance (NQ=F, continuous
front month, delayed public feed) and write them as
/tmp/yahoo_bars.csv with columns: timestamp_utc,open,high,low,close,volume

Runs inside GitHub Actions. Exits non-zero with a clear message on failure so
the workflow shows red instead of silently committing nothing.
"""
import sys
import pandas as pd
import yfinance as yf

OUT = "/tmp/yahoo_bars.csv"


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


def main():
    last_err = None
    for period in ("59d", "30d", "7d"):   # fall back if Yahoo rejects long span
        try:
            df = yf.download("NQ=F", interval="5m", period=period,
                             progress=False, auto_adjust=False, threads=False)
            if df is not None and len(df) > 50:
                rows = frame_to_rows(df)
                if len(rows) > 50:
                    with open(OUT, "w") as f:
                        f.write("timestamp_utc,open,high,low,close,volume\n")
                        for r in rows:
                            f.write(",".join(map(str, r)) + "\n")
                    print(f"[fetch] {len(rows)} bars ({period}) "
                          f"{rows[0][0]} -> {rows[-1][0]}")
                    return
        except SystemExit:
            raise
        except Exception as e:      # noqa: BLE001 - report and try shorter span
            last_err = e
    raise SystemExit(f"Yahoo fetch failed for all periods: {last_err}")


if __name__ == "__main__":
    main()
