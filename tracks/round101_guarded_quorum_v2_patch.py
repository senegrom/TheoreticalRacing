#!/usr/bin/env python3
"""Apply the refined Round 101 guarded-quorum candidate.

The base candidate recovers scorer-certified one-turn accelerations. This
refinement requires real geometric separation when a partial forward quorum is
more than sixty empty-map turns from the line, blocking the Spa seed-79
counterexample without narrowing the proven short-tail and full-quorum gains.
"""
from pathlib import Path
import runpy

runpy.run_path("tracks/round101_guarded_quorum_patch.py", run_name="__main__")

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()

anchor = (
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_LONG_TURNS\t= 100;"
    "\t// a fixed eight-round proof is only a small slice of a three-digit tail\n"
)
replacement = anchor + (
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_MID_TURNS\t= 60;"
    "\t// partial quorums need geometric separation beyond the fixed rollout\n"
)
assert source.count(anchor) == 1
source = source.replace(anchor, replacement, 1)

old = """\t\tif (liveRivals < AI1_PRIVATE_FIELD_MIN_RIVALS
\t\t\t\t|| rivalsAhead < AI1_FIELD_ACCEL_MIN_AHEAD
\t\t\t\t|| rivalsAhead > AI1_FIELD_ACCEL_MAX_AHEAD || aheadProgress <= 0L
\t\t\t\t|| chosenT >= AI1_FIELD_ACCEL_LONG_TURNS
\t\t\t\t\t\t&& rivalsAhead < AI1_FIELD_ACCEL_LONG_MIN_AHEAD)
"""
new = """\t\tif (liveRivals < AI1_PRIVATE_FIELD_MIN_RIVALS
\t\t\t\t|| rivalsAhead < AI1_FIELD_ACCEL_MIN_AHEAD
\t\t\t\t|| rivalsAhead > AI1_FIELD_ACCEL_MAX_AHEAD || aheadProgress <= 0L
\t\t\t\t|| chosenT >= AI1_FIELD_ACCEL_MID_TURNS
\t\t\t\t\t\t&& rivalsAhead < AI1_FIELD_ACCEL_LONG_MIN_AHEAD
\t\t\t\t\t\t&& aheadProgress * 2L < chosenT
\t\t\t\t|| chosenT >= AI1_FIELD_ACCEL_LONG_TURNS
\t\t\t\t\t\t&& rivalsAhead < AI1_FIELD_ACCEL_LONG_MIN_AHEAD)
"""
assert source.count(old) == 1
path.write_text(source.replace(old, new, 1))
