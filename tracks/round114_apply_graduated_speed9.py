#!/usr/bin/env python3
"""Materialize the graduated Round 114 field-acceleration rule.

The promoted Round-106 certificate remains the authority. High-energy
accelerations (speed-squared gain >=16) retain their established TTF-90 range.
Moderate gains (9..15) are admitted only through TTF 45, where the eight-round
proof covers a materially larger fraction of the remaining race. A deliberate
scorer coast is never replaced. These two boundaries retain the clean Coil
seed-1/38 gains while excluding Coil seed 106 and the Spa seed 12/31/40/47
counterexamples, without using track, seed, player, or coordinate identity.
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

constant_anchor = (
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_MAX_TTF\t= 90;"
    "\t// keep the 8-round proof in the medium-range race phase\n"
)
assert source.count(constant_anchor) == 1
source = source.replace(
    constant_anchor,
    constant_anchor
    + "\tprivate final static int\t\tAI1_FIELD_ACCEL_LONG_RANGE_MIN_SPEED2_GAIN\t= 16;"
      "\t// round 114: retain the promoted long-range energy floor\n"
    + "\tprivate final static int\t\tAI1_FIELD_ACCEL_LOW_GAIN_MAX_TTF\t= 45;"
      "\t// round 114: moderate 9..15 gains need the nearer proof window\n",
    1,
)

old_entry = (
    "\t\tfinal int chosenT = turnsByDir[chosen.ordinal()];\n"
    "\t\tif (chosenT == Integer.MAX_VALUE || chosenT < AI1_FINISH_HOMOGENEOUS_TTF + 2\n"
)
new_entry = (
    "\t\tfinal int chosenT = turnsByDir[chosen.ordinal()];\n"
    "\t\t// Round 114: never replace a deliberate scorer coast. Coil s106\n"
    "\t\t// proves that this can redistribute the surviving back marker even\n"
    "\t\t// when the short aggregate field projection improves.\n"
    "\t\tif (chosen == Direction.NONE || chosenT == Integer.MAX_VALUE\n"
    "\t\t\t\t|| chosenT < AI1_FINISH_HOMOGENEOUS_TTF + 2\n"
)
assert source.count(old_entry) == 1, source.count(old_entry)
source = source.replace(old_entry, new_entry, 1)

old_speed = (
    "\t\t\tfinal int speed2 = speedSquared(nvx, nvy);\n"
    "\t\t\tif (speed2 - chosenSpeed2 < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN)\n"
    "\t\t\t\tcontinue;\n"
)
new_speed = (
    "\t\t\tfinal int speed2 = speedSquared(nvx, nvy);\n"
    "\t\t\tfinal int speed2Gain = speed2 - chosenSpeed2;\n"
    "\t\t\tif (speed2Gain < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN\n"
    "\t\t\t\t\t|| speed2Gain < AI1_FIELD_ACCEL_LONG_RANGE_MIN_SPEED2_GAIN\n"
    "\t\t\t\t\t\t\t&& chosenT > AI1_FIELD_ACCEL_LOW_GAIN_MAX_TTF)\n"
    "\t\t\t\tcontinue;\n"
)
assert source.count(old_speed) == 1, source.count(old_speed)
source = source.replace(old_speed, new_speed, 1)

marker = (
    "\t// Round 114: graduated strict-field acceleration; speed2 gain 9..15\n"
    "\t// is limited to TTF 45 and scorer coasts remain authoritative.\n"
)
anchor = "\t/** Round 106: recover a one-turn acceleration only in a bounded forward\n"
assert source.count(anchor) == 1
source = source.replace(anchor, marker + anchor, 1)

assert re.search(r"AI1_FIELD_ACCEL_MIN_SPEED2_GAIN\s*=\s*9;", source)
assert source.count("AI1_FIELD_ACCEL_LOW_GAIN_MAX_TTF") == 2
assert source.count("chosen == Direction.NONE || chosenT == Integer.MAX_VALUE") == 1
assert source.count("final int speed2Gain = speed2 - chosenSpeed2;") == 1
path.write_text(source)
print("materialized Round 114 graduated speed-nine acceleration")
