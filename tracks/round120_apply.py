#!/usr/bin/env python3
"""Materialize a low-speed moderate-acceleration TTF extension.

Round 115 capped speed-squared gains 9..15 at TTF 45. Its recorded long-range
counterexamples were high-speed states, while the promoted frontier separately
requires the incumbent speed squared to stay below 49 and forbids scorer
coasts. This census extends only that already low-speed, non-coasting AI1 class
to TTF 60. The strict eight-round mover/aggregate-field proof, trap and
uncertainty zeroes, funnel check, seal veto and downstream danger machinery are
unchanged. AI2 remains frozen.
"""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()
old = (
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_FRONTIER_LOW_GAIN_MAX_TTF\t= 45;"
    "\t// round 115: short-range boundary for speed2 gains 9..15\n"
)
new = (
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_FRONTIER_LOW_GAIN_MAX_TTF\t= 60;"
    "\t// round 120 census: low-speed non-coast moderate gains through TTF 60\n"
)
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)
anchor = (
    "\t/** Round 106: recover a one-turn acceleration only in a bounded forward\n"
)
marker = (
    "\t// Round 120 census: extend only the low-speed, non-coasting AI1 moderate\n"
    "\t// acceleration certificate from TTF 45 through TTF 60.\n"
)
assert source.count(anchor) == 1
source = source.replace(anchor, marker + anchor, 1)
assert source.count("AI1_FIELD_ACCEL_FRONTIER_LOW_GAIN_MAX_TTF\t= 60") == 1
assert source.count("private Direction optimalMoveAI2") == 1
path.write_text(source)
print("materialized Round 120 low-speed TTF-60 acceleration census")
