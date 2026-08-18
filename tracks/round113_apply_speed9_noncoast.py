#!/usr/bin/env python3
"""Lower the strict field-acceleration threshold without overriding coasts.

The Round-106 proof remains unchanged except that speed-squared gains of 9–15
may now qualify.  A scorer decision to coast (Direction.NONE) is never replaced:
Coil seed 106 demonstrated that this class can redistribute the surviving field
even when the short scorer rollout strictly improves aggregate cost.  The clean
Coil seed-1 and seed-38 gains both accelerate from directed moves.
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
    "\t\t// Round 113: keep deliberate scorer coasts out of the lower-energy\n"
    "\t\t// acceleration class. Coil s106 is the measured counterexample.\n"
    "\t\tif (chosen == Direction.NONE || chosenT == Integer.MAX_VALUE\n"
    "\t\t\t\t|| chosenT < AI1_FINISH_HOMOGENEOUS_TTF + 2\n"
)
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

anchor = "\t/** Round 106: recover a one-turn acceleration only in a bounded forward\n"
marker = "\t// Round 113: strict-field speed-nine acceleration excludes scorer coasts.\n"
assert source.count(anchor) == 1
source = source.replace(anchor, marker + anchor, 1)

assert re.search(r"AI1_FIELD_ACCEL_MIN_SPEED2_GAIN\s*=\s*9;", source)
assert source.count("chosen == Direction.NONE || chosenT == Integer.MAX_VALUE") == 1
path.write_text(source)
print("materialized Round 113 non-coasting speed-nine acceleration")
