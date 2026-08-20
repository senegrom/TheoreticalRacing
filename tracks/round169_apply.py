#!/usr/bin/env python3
"""Eliminate the per-root two-double result allocation.

searchMinTurnsCountedSoft3 is non-recursive; only its plain-cost helper recurses.
Each AI candidate nevertheless allocated a fresh double[2] to return best cost
and plateau width. The already recursion-safe outer/nested CandidateWorkspace
pair can own one exact result buffer each.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceAi.java")
source = race.read_text()

old = """\t\tfinal double[] uncertaintyByDirection = new double[DIRECTIONS.length];

\t\tvoid reset() {
"""
new = """\t\tfinal double[] uncertaintyByDirection = new double[DIRECTIONS.length];
\t\tfinal double[] countedResult = new double[2];

\t\tvoid reset() {
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\t\tfinal double[] deepCounted = searchMinTurnsCountedSoft3(newX, newY, newVx, newVy, AI1_DEEP_LOOKAHEAD, 0,
\t\t\t\t\tpredictedSteps, playerNum, worlds.world1, worlds.current, reach.distAt(pos[0], pos[1]));
\t\t\tfinal double deep = deepCounted[0];
"""
new = """\t\t\tfinal double[] deepCounted = candidateWorkspace.countedResult;
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
\t\t\tfinal int[][] occupancy2, final int myDist, final double[] result) {
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\treturn new double[]{best, countAtMin };
\t}
"""
new = """\t\tresult[0] = best;
\t\tresult[1] = countAtMin;
\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)
assert source.count("candidateWorkspace.countedResult") == 1
assert "return new double[]{best, countAtMin" not in source
race.write_text(source)
print("materialized workspace-owned counted search result")
