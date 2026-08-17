# Getting this repo onto GitHub

The repository `cjosh4toyotas-stack/silver-bullet-backtest` already exists
(private, empty). Pick ONE of the two options below.

## Option A — Terminal (if you have git installed)

Unzip this folder, open Terminal, and run:

    cd path/to/silver-bullet-backtest
    git init -b main
    git add -A
    git commit -m "Initial: Silver Bullet accumulating backtest"
    git remote add origin https://github.com/cjosh4toyotas-stack/silver-bullet-backtest.git
    git push -u origin main

When git asks for a password, paste your fine-grained access token
(the one starting with `github_pat_`), not your GitHub password.

## Option B — GitHub website (no terminal needed)

1. Open https://github.com/cjosh4toyotas-stack/silver-bullet-backtest
2. Click the "uploading an existing file" link on the empty-repo page
3. Drag the CONTENTS of the unzipped folder (all files AND the `data` and
   `results` folders) into the upload area — drag the items inside the
   folder, not the folder itself, so paths are preserved
4. Commit message: "Initial: Silver Bullet accumulating backtest"
5. Click "Commit changes"

## What you should see afterwards

The repo front page will render README.md with the current stats, the
equity-curve chart, and the trade log. `report.html` can be downloaded and
opened in a browser for the interactive version.

## Files in this bundle

- `update.py` — the whole pipeline: merges new price data, re-runs the
  mechanical Silver Bullet rules over all accumulated history, regenerates
  README.md, results.json, trades.csv, results/equity.svg and report.html
- `data/NQ202609.csv` — accumulated 5-min NQ bars (Sep-2026 contract)
- `results/`, `results.json`, `trades.csv`, `report.html`, `README.md` —
  current outputs (regenerated on every run)
- `RUNBOOK.md` — the steps the automated update follows

Never commit an access token to this repo.
