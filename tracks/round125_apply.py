#!/usr/bin/env python3
"""Lower only AI1's moderate field-acceleration floor from 9 to 5.

This is an exploratory census. Every other Round-115/117 admission rule and
proof remains unchanged: TTF<=45 for moderate gains, incumbent below the
speed-seven danger threshold, non-coasting scorer choice, two-to-five rivals
ahead, zero trap and uncertainty, one map-turn gain, eight-round strict mover
and aggregate-field progress, non-sealability, funnel protection and all
downstream danger vetoes. The exact-six-ahead high-energy arm and AI2 remain
untouched.
"""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()
old = (
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_FRONTIER_MIN_SPEED2_GAIN"
    "\t= 9;\t// round 115 frontier: moderate acceleration floor for AI1 only\n"
)
new = (
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_FRONTIER_MIN_SPEED2_GAIN"
    "\t= 5;\t// round 125 census: next lower acceleration quantum\n"
)
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)
assert source.count("AI1_FIELD_ACCEL_FRONTIER_MIN_SPEED2_GAIN\t= 5") == 1
assert source.count("sixAheadFrontier") == 5
path.write_text(source)
print("materialized Round 125 speed-squared-gain-five census")
