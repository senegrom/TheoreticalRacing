#!/usr/bin/env python3
"""Materialize a direct per-candidate map for round-two ahead occupancy.

The depth-two soft search asks the same question at many nodes: whether a
round-two simulated cell is occupied by the first player at that cell and that
player is currently strictly ahead.  Build that exact first-match verdict once
per root candidate in a byte raster and clear only touched cells before reuse.
The recursive search then performs one bounds check and byte load instead of
rescanning every simulated player and recomputing distAt each time.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceAi.java")
source = race.read_text()

old = """\t\tfinal int[] candidatePosition = new int[2];

\t\tTwoRoundWorkspace(final int players) {
"""
new = """\t\tfinal int[] candidatePosition = new int[2];
\t\tfinal byte[] aheadOccupancy;
\t\tfinal int[] aheadTouched;
\t\tint aheadTouchedCount;

\t\tTwoRoundWorkspace(final int players, final int cells) {
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\t\tround2Velocity = new int[players][2];
\t\t}
\t}
"""
new = """\t\t\tround2Velocity = new int[players][2];
\t\t\taheadOccupancy = new byte[cells];
\t\t\taheadTouched = new int[players];
\t\t}
\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\tprivate TwoRoundWorkspace twoRoundWorkspace() {
\t\tfinal int players = game.players.length;
\t\tif (twoRoundWorkspace == null || twoRoundWorkspace.current.length != players)
\t\t\ttwoRoundWorkspace = new TwoRoundWorkspace(players);
\t\treturn twoRoundWorkspace;
\t}
"""
new = """\tprivate TwoRoundWorkspace twoRoundWorkspace() {
\t\tfinal int players = game.players.length;
\t\tif (twoRoundWorkspace == null || twoRoundWorkspace.current.length != players)
\t\t\ttwoRoundWorkspace = new TwoRoundWorkspace(players,
\t\t\t\t\t(game.gameCols + 1) * (game.gameRows + 1));
\t\treturn twoRoundWorkspace;
\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t/** Is cell (x,y) occupied in the simulated occupancy by a rival currently
\t *  strictly AHEAD of me on track ({@code myDist} from {@link #distAt})?
\t *  Chaser bodies are deliberately not priced: a detour ceded two rounds out
\t *  to a car behind me surrenders race position for nothing. */
\tprivate boolean occupiedByAheadRival(final int x, final int y, final int[][] occupancy, final int myDist) {
\t\tfor (int i = 0; i < occupancy.length; i++) {
\t\t\tfinal int[] cell = occupancy[i];
\t\t\tif (cell != null && cell[0] == x && cell[1] == y) {
\t\t\t\tfinal int[] rivalPos = game.players[i].getPosition();
\t\t\t\treturn reach.distAt(rivalPos[0], rivalPos[1]) < myDist;
\t\t\t}
\t\t}
\t\treturn false;
\t}
"""
new = """\t/** Build the exact first-occupant ahead verdict once for this candidate.
\t * Byte 1 means the first simulated occupant is not ahead; byte 2 means it
\t * is ahead. Duplicate simulated cells therefore retain the original loop's
\t * first-match semantics. */
\tprivate byte[] buildAheadOccupancy(final int[][] occupancy, final int myDist) {
\t\tfinal TwoRoundWorkspace workspace = twoRoundWorkspace();
\t\tfinal byte[] direct = workspace.aheadOccupancy;
\t\tfor (int i = 0; i < workspace.aheadTouchedCount; i++)
\t\t\tdirect[workspace.aheadTouched[i]] = 0;
\t\tworkspace.aheadTouchedCount = 0;
\t\tfinal int h = game.gameRows + 1;
\t\tfor (int i = 0; i < occupancy.length; i++) {
\t\t\tfinal int[] cell = occupancy[i];
\t\t\tif (cell == null || cell[0] < 0 || cell[1] < 0
\t\t\t\t\t|| cell[0] > game.gameCols || cell[1] > game.gameRows)
\t\t\t\tcontinue;
\t\t\tfinal int index = cell[0] * h + cell[1];
\t\t\tif (direct[index] != 0)
\t\t\t\tcontinue;
\t\t\tfinal int[] rivalPos = game.players[i].getPosition();
\t\t\tdirect[index] = reach.distAt(rivalPos[0], rivalPos[1]) < myDist
\t\t\t\t\t? (byte) 2 : (byte) 1;
\t\t\tworkspace.aheadTouched[workspace.aheadTouchedCount++] = index;
\t\t}
\t\treturn direct;
\t}

\tprivate boolean occupiedByAheadRival(final int x, final int y,
\t\t\tfinal byte[] occupancy) {
\t\tif (x < 0 || y < 0 || x > game.gameCols || y > game.gameRows)
\t\t\treturn false;
\t\treturn occupancy[x * (game.gameRows + 1) + y] == 2;
\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\t\tfinal TwoRoundWorkspace worlds = simulateTwoRounds(playerNum, newX, newY);
\t\t\tfinal int[][] world = worlds.world1;
\t\t\tfinal double[] deepCounted = searchMinTurnsCountedSoft3(newX, newY, newVx, newVy, AI1_DEEP_LOOKAHEAD, 0,
\t\t\t\t\tpredictedSteps, playerNum, worlds.world1, worlds.current, reach.distAt(pos[0], pos[1]));
"""
new = """\t\t\tfinal TwoRoundWorkspace worlds = simulateTwoRounds(playerNum, newX, newY);
\t\t\tfinal int[][] world = worlds.world1;
\t\t\tfinal byte[] aheadOccupancy = buildAheadOccupancy(worlds.current,
\t\t\t\t\treach.distAt(pos[0], pos[1]));
\t\t\tfinal double[] deepCounted = searchMinTurnsCountedSoft3(newX, newY, newVx, newVy, AI1_DEEP_LOOKAHEAD, 0,
\t\t\t\t\tpredictedSteps, playerNum, worlds.world1, aheadOccupancy);
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old_sig = "final int[][] occupancy2, final int myDist)"
new_sig = "final byte[] aheadOccupancy)"
assert source.count(old_sig) == 2, source.count(old_sig)
source = source.replace(old_sig, new_sig)

old_check = "stepIdx == 1 && occupancy2 != null && occupiedByAheadRival(nx, ny, occupancy2, myDist)"
new_check = "stepIdx == 1 && aheadOccupancy != null && occupiedByAheadRival(nx, ny, aheadOccupancy)"
assert source.count(old_check) == 2, source.count(old_check)
source = source.replace(old_check, new_check)

old_recurse = "occupancy, occupancy2, myDist)"
new_recurse = "occupancy, aheadOccupancy)"
assert source.count(old_recurse) == 2, source.count(old_recurse)
source = source.replace(old_recurse, new_recurse)

source = source.replace("{@code occupancy2}", "the round-two occupancy map")
source = source.replace("{@code myDist} = distAt of my CURRENT cell), via", "the mover's current progress), via")
source = source.replace("{@code myDist} threads unchanged through\n\t *  the recursion.", "the precomputed verdict map threads unchanged through\n\t *  the recursion.")
source = source.replace("{@code myDist} is threaded from the caller (distAt of my\n\t *  CURRENT cell).", "The ahead-occupancy verdict map is built once by the caller.")

assert source.count("buildAheadOccupancy(") == 2
assert source.count("occupiedByAheadRival(nx, ny, aheadOccupancy)") == 2
assert "occupancy2, myDist" not in source
race.write_text(source)
print("materialized direct round-two ahead-occupancy map")
