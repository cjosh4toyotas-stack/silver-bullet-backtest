# Update runbook (for the automated twice-weekly run)

This repo is updated by a scheduled Claude session. Steps each run:

1. Resolve the active NQ front-month contract via the IBKR connector:
   - `search_futures` with `underlying_contract_id=11004958` (E-mini NASDAQ 100, CME)
   - Sort by `contract_month` ascending; pick the earliest non-expired contract
     whose `last_trading_date` is more than 2 calendar days away; otherwise the
     next expiry. Label = `NQ` + `contract_month` (e.g. `NQ202609`).
2. Pull bars: `get_price_history` with that contract's numeric `contract_id`,
   `exchange="CME"`, `security_type="FUT"`, `step="FIVE_MINS"`,
   `step_count=3500`, `outside_rth=true`.
3. Convert the response to CSV with columns
   `timestamp_utc,open,high,low,close,volume` (ISO-8601 UTC timestamps).
4. `python3 update.py --new <that csv> --contract <label>`
5. Commit everything and push to `main` with message
   `Auto-update <UTC date>: +<new bars> bars, <total> trades total`.
6. Around a contract roll, if the previous front month still has >2 days of
   unfetched history, pull it too and run update.py once per contract.

If the IBKR connector is unavailable, or the push fails, say so clearly in the
run's final message instead of failing silently.

Never commit credentials to this repo. The push token lives only in the
scheduled task configuration.
