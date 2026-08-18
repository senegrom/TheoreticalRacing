#!/usr/bin/env python3
"""Lower only Round 115's AI1 moderate field-acceleration floor, 9 -> 7.

Every other admission rule and proof remains unchanged: TTF <=45, incumbent
speed-squared below 49, non-coasting scorer choice, two-to-five rivals ahead,
zero trap and uncertainty, one map-turn gain, eight-round strict mover and
aggregate-field progress, non-sealability, funnel protection and downstream
danger vetoes. Round 117's six-ahead high-energy formation is untouched and AI2
remains frozen.
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
    "\t= 7;\t// round 119 census: one lower odd-square acceleration quantum\n"
)
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)
assert source.count("AI1_FIELD_ACCEL_FRONTIER_MIN_SPEED2_GAIN\t= 7") == 1
assert source.count("sevenAheadFrontier") == 0
assert source.count("sixAheadFrontier") == 5
path.write_text(source)
print("materialized Round 119 speed-squared-gain-seven census")
