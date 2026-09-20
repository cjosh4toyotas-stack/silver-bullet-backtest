#!/usr/bin/env python3
"""Scheduling gate for cloud runs. Usage: block_gate.py <london|morning|afternoon>

Prints SKIP if this firing should not run (block already over, or this is the
wrong-DST cron twin and the start is more than 75 minutes away), otherwise the
number of seconds to sleep before the block starts (0 if already inside it).
Each block has two UTC crons so the schedule survives DST in both directions;
the 75-minute rule lets exactly one of the twins claim each day.
"""
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BLOCKS = {"london": 145, "morning": 505, "afternoon": 689}
ENDS = {"london": 370, "morning": 688, "afternoon": 995}
NY = ZoneInfo("America/New_York")

block = sys.argv[1].strip().lower()
if block not in BLOCKS:
    sys.exit(f"unknown block {block!r}")

now = datetime.fromisoformat(os.environ["SB_FAKE_NOW"]) \
    if os.environ.get("SB_FAKE_NOW") else datetime.now(NY)
midnight = datetime(now.year, now.month, now.day, tzinfo=NY)
start = midnight + timedelta(minutes=BLOCKS[block])
end = midnight + timedelta(minutes=ENDS[block])

if now.weekday() >= 5 or now >= end:
    print("SKIP")
elif (start - now) > timedelta(minutes=75):
    print("SKIP")
else:
    print(max(0, int((start - now).total_seconds())))
