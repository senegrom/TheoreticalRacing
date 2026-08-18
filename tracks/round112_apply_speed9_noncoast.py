#!/usr/bin/env python3
"""Materialize the Round 112 non-coasting speed-nine acceleration candidate.

The Round-106 strict scorer-field certificate is otherwise unchanged.  The
minimum speed-squared gain is reduced from 16 to 9, but the arm may not override
a scorer decision to coast.  Coil seed 106 showed why: accelerating from NONE
can replace a back marker and redistribute the field despite a short-horizon
strict aggregate gain.  The clean Coil seed-1 and seed-38 gains both accelerate
from an already directed move and remain eligible.
"""
from __future__ import annotations

import re
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()

pattern = re.compile(
    r"^(\s*private final static int\s+AI1_FIELD_ACCEL_MIN_SPEED2_GAIN\s*=\s*)16(;.*)$",
    re.MULTILINE,
)
source, count = pattern.subn(r"\g<1>9\2", source, count=1)
assert count == 1, count

old = (
    "\t\tfinal int chosenT = turnsByDir[chosen.ordinal()];\n"
    "\t\tif (chosenT == Integer.MAX_VALUE || chosenT < AI1_FINISH_HOMOGENEOUS_TTF + 2\n"
)
new = (
    "\t\tfinal int chosenT = turnsByDir[chosen.ordinal()];\n"
    "\t\t// Round 112: do not turn a scorer coast into a pack acceleration.\n"
    "\t\t// Coil s106 proved that this class can replace the surviving back\n"
    "\t\t// marker even when the eight-round aggregate field cost improves.\n"
    "\t\tif (chosen == Direction.NONE || chosenT == Integer.MAX_VALUE\n"
    "\t\t\t\t|| chosenT < AI1_FINISH_HOMOGENEOUS_TTF + 2\n"
)
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

marker = (
    "\t// Round 112: speed-nine strict-field acceleration excludes scorer coasts.\n"
)
anchor = "\t/** Round 106: recover a one-turn acceleration only in a bounded forward\n"
assert source.count(anchor) == 1
source = source.replace(anchor, marker + anchor, 1)

assert re.search(r"AI1_FIELD_ACCEL_MIN_SPEED2_GAIN\s*=\s*9;", source)
assert source.count("chosen == Direction.NONE || chosenT == Integer.MAX_VALUE") == 1
path.write_text(source)
print("materialized Round 112 non-coasting speed-nine acceleration")
