#!/usr/bin/env python3
"""Scheduling gate for cloud runs.

Usage:
    block_gate.py auto                      (scheduled firings)
    block_gate.py <london|morning|afternoon>  (manual dispatch)

"auto" mode makes the schedule self-healing: GitHub's cron scheduler fires
late or not at all on some days, so the workflow now carries many redundant
crons and every firing simply asks "which block is running or starting within
the next 90 minutes?" — whatever time the firing actually lands. The concurrency
group serializes runs, so extra firings queue behind the one that claimed the
block and then SKIP in seconds once it is over.

Prints two lines:  block=<name|none>  and  SKIP or seconds-to-sleep.
Named mode keeps explicit block choice for manual runs, same 90-min horizon.

2026-11-06: a firing that lands while today's run of a block is already
recorded (data/bot_status.json says that block is "running" or finished
"success" today) no longer re-claims that block when the NEXT block starts
within the horizon - it claims the next block instead. Cause: the exact-time
pings are fixed UTC clock times; after the 11/1 DST change the "afternoon"
ping (14:45 UTC) landed at 09:45 ET, inside the morning block, so it queued
behind the morning run, re-ran "morning" for a minute at 10:00 and nothing
started the afternoon block until a backup firing hours later (11/3 12:46,
11/4 13:51, 11/6 12:27 ET - the Late-morning window was missed on all
three). A block whose last run failed is still re-claimed as before.
"""
import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BLOCKS = {"london": 145, "morning": 445, "afternoon": 656}
ENDS = {"london": 370, "morning": 655, "afternoon": 995}
HORIZON = timedelta(minutes=90)   # claim a block up to 90 min early; longer
                                  # would risk GitHub's 6h job limit killing a
                                  # run mid-trade (sleep + London block + setup)
MIN_LEFT = timedelta(minutes=10)  # don't claim a block with <10 min left: a
                                  # fresh run can't trade or manage anything in
                                  # that time, and it would overwrite the day's
                                  # real status with a no-op heartbeat
NY = ZoneInfo("America/New_York")

arg = sys.argv[1].strip().lower()
if arg != "auto" and arg not in BLOCKS:
    sys.exit(f"unknown block {arg!r}")

now = datetime.fromisoformat(os.environ["SB_FAKE_NOW"]) \
    if os.environ.get("SB_FAKE_NOW") else datetime.now(NY)
midnight = datetime(now.year, now.month, now.day, tzinfo=NY)


def window(block):
    return (midnight + timedelta(minutes=BLOCKS[block]),
            midnight + timedelta(minutes=ENDS[block]))


def emit(block, verdict):
    print(f"block={block}")
    print(verdict)
    sys.exit(0)


if now.weekday() >= 5:
    emit("none", "SKIP")

def covered_today():
    """Block already handled today per data/bot_status.json: its run is
    'running' (the concurrency group means it is live, we are queued behind
    it) or finished 'success'. 'failure' or missing -> not covered."""
    path = os.environ.get("SB_STATUS_FILE") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "bot_status.json")
    try:
        with open(path) as f:
            st = json.load(f)
        utc = datetime.fromisoformat(str(st.get("utc", "")).replace("Z", "+00:00"))
        if utc.astimezone(NY).date() != now.date():
            return None
        if st.get("outcome") in ("running", "success") and st.get("block") in BLOCKS:
            return st["block"]
    except Exception:
        pass
    return None


if arg == "auto":
    # earliest block that is still running or starts within the horizon
    order = sorted(BLOCKS, key=BLOCKS.get)
    done = covered_today()
    for i, block in enumerate(order):
        start, end = window(block)
        if now < end - MIN_LEFT and (start - now) <= HORIZON:
            if block == done and i + 1 < len(order):
                # this block is already being handled today; if the next one
                # starts within the horizon, claim that instead of re-running
                nstart, nend = window(order[i + 1])
                if now < nend - MIN_LEFT and (nstart - now) <= HORIZON:
                    emit(order[i + 1], str(max(0, int((nstart - now).total_seconds()))))
            emit(block, str(max(0, int((start - now).total_seconds()))))
    emit("none", "SKIP")
else:
    start, end = window(arg)
    if now >= end - MIN_LEFT or (start - now) > HORIZON:
        emit(arg, "SKIP")
    emit(arg, str(max(0, int((start - now).total_seconds()))))
