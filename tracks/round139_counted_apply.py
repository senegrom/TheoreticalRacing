#!/usr/bin/env python3
"""Materialize allocation-free depth-two counted-search results.

Each scorer candidate currently allocates a fresh double[2] containing the
minimum continuation cost and plateau width. CandidateWorkspace is already
outer/nested instance-owned scratch, so storing the two outputs there removes
that allocation without changing arithmetic, traversal order or policy.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceAi.java")
source = race.read_text()

old = """\t\tfinal double[] uncertaintyByDirection = new double[DIRECTIONS.length];

\t\tvoid reset() {
"""
new = """\t\tfinal double[] uncertaintyByDirection = new double[DIRECTIONS.length];
\t\tfinal double[] deepCounted = new double[2];

\t\tvoid reset() {
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t		final double[] deepCounted = searchMinTurnsCountedSoft3(newX, newY, newVx, newVy, AI1_DEEP_LOOKAHEAD, 0,
\t\t\t\t\tpredictedSteps, playerNum, worlds.world1, worlds.current, reach.distAt(pos[0], pos[1]));
\t\t\tfinal double deep = deepCounted[0];
"""
new = """\t\t\tfinal double[] deepCounted = candidateWorkspace.deepCounted;
\t\t\tsearchMinTurnsCountedSoft3(newX, newY, newVx, newVy, AI1_DEEP_LOOKAHEAD, 0,
\t\t\t\t\tpredictedSteps, playerNum, worlds.world1, worlds.current,
\t\t\t\t\treach.distAt(pos[0], pos[1]), deepCounted);
\t\t\tfinal double deep = deepCounted[0];
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\tprivate double[] searchMinTurnsCountedSoft3(final int x, final int y, final int vx, final int vy, final int levels,
\t\t\tfinal int stepIdx, final int[][][] predictedSteps, final int playerNum, final int[][] occupancy,
\t\t\tfinal int[][] occupancy2, final int myDist) {
"""
new = """\tprivate void searchMinTurnsCountedSoft3(final int x, final int y, final int vx, final int vy, final int levels,
\t\t\tfinal int stepIdx, final int[][][] predictedSteps, final int playerNum, final int[][] occupancy,
\t\t\tfinal int[][] occupancy2, final int myDist, final double[] out) {
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\t\tif (game.crossesFinish(x, y, nx, ny))
\t\t\t\treturn new double[]{1, 9 };
"""
new = """\t\t\tif (game.crossesFinish(x, y, nx, ny)) {
\t\t\t\tout[0] = 1;
\t\t\t\tout[1] = 9;
\t\t\t\treturn;
\t\t\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\treturn new double[]{best, countAtMin };
\t}
"""
new = """\t\tout[0] = best;
\t\tout[1] = countAtMin;
\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

race.write_text(source)
print("materialized allocation-free counted-search scratch")
