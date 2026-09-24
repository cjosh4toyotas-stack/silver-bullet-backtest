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
"""
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BLOCKS = {"london": 145, "morning": 445, "afternoon": 656}
ENDS = {"london": 370, "morning": 655, "afternoon": 995}
HORIZON = timedelta(minutes=90)   # claim a block up to 90 min early; longer
                                  # would risk GitHub's 6h job limit killing a
                                  # run mid-trade (sleep + London block + setup)
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

if arg == "auto":
    # earliest block that is still running or starts within the horizon
    for block in sorted(BLOCKS, key=BLOCKS.get):
        start, end = window(block)
        if now < end and (start - now) <= HORIZON:
            emit(block, str(max(0, int((start - now).total_seconds()))))
    emit("none", "SKIP")
else:
    start, end = window(arg)
    if now >= end or (start - now) > HORIZON:
        emit(arg, "SKIP")
    emit(arg, str(max(0, int((start - now).total_seconds()))))
