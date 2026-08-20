#!/usr/bin/env python3
"""Materialize an exact precomputed velocity-magnitude table.

AI velocity components are bounded to [-12,12].  The scorer, brake proofs and
traffic tests repeatedly call Math.hypot on those same 625 integer pairs.  This
candidate computes Math.hypot once for every pair at class initialization and
reuses the exact returned doubles.  Out-of-domain calls retain the original
Math.hypot fallback, so arithmetic and policy semantics are unchanged.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceAi.java")
source = race.read_text()
count = source.count("Math.hypot(")
assert count >= 4, count
source = source.replace("Math.hypot(", "speedMagnitude(")

anchor = """\tprivate static int speedSquared(final int vx, final int vy) {
"""
helper = """\tprivate static final int SPEED_MAG_SPAN = 2 * RaceGame.AI_MAX_SPEED + 1;
\tprivate static final double[] SPEED_MAGNITUDES = buildSpeedMagnitudes();

\tprivate static double[] buildSpeedMagnitudes() {
\t\tfinal double[] result = new double[SPEED_MAG_SPAN * SPEED_MAG_SPAN];
\t\tfor (int vx = -RaceGame.AI_MAX_SPEED; vx <= RaceGame.AI_MAX_SPEED; vx++)
\t\t\tfor (int vy = -RaceGame.AI_MAX_SPEED; vy <= RaceGame.AI_MAX_SPEED; vy++)
\t\t\t\tresult[(vx + RaceGame.AI_MAX_SPEED) * SPEED_MAG_SPAN
\t\t\t\t\t\t+ vy + RaceGame.AI_MAX_SPEED] = Math.hypot(vx, vy);
\t\treturn result;
\t}

\tprivate static double speedMagnitude(final int vx, final int vy) {
\t\tif (vx >= -RaceGame.AI_MAX_SPEED && vx <= RaceGame.AI_MAX_SPEED
\t\t\t\t&& vy >= -RaceGame.AI_MAX_SPEED && vy <= RaceGame.AI_MAX_SPEED)
\t\t\treturn SPEED_MAGNITUDES[(vx + RaceGame.AI_MAX_SPEED) * SPEED_MAG_SPAN
\t\t\t\t\t+ vy + RaceGame.AI_MAX_SPEED];
\t\treturn Math.hypot(vx, vy);
\t}

\tprivate static int speedSquared(final int vx, final int vy) {
"""
assert source.count(anchor) == 1, source.count(anchor)
source = source.replace(anchor, helper, 1)
# The table initializer and out-of-domain fallback are the only remaining calls.
assert source.count("Math.hypot(") == 2, source.count("Math.hypot(")
race.write_text(source)
print(f"materialized exact magnitude cache for {count} hot call sites")
