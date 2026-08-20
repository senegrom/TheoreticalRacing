#!/usr/bin/env python3
"""Materialize a direct live-cell map for mobility projections.

mobilitySearch repeatedly asks whether a successor cell is occupied by a live
player other than the projected source cell. The live board is fixed for the
lifetime of one mobility projection, including nested scorer projections, so
refresh one touched-cell byte raster at mobilitySearch entry and replace every
per-successor player scan with a direct lookup.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceAi.java")
source = race.read_text()

old = """\tprivate final int[] mobilityMove = new int[4];
\tprivate MobilitySearch outerMobilityWorkspace;
\tprivate MobilitySearch nestedMobilityWorkspace;
\tprivate final long[] rolloutFieldCost = new long[1];
"""
new = """\tprivate final int[] mobilityMove = new int[4];
\tprivate MobilitySearch outerMobilityWorkspace;
\tprivate MobilitySearch nestedMobilityWorkspace;
\tprivate byte[] liveOccupancy;
\tprivate int[] liveOccupancyTouched;
\tprivate int liveOccupancyTouchedCount;
\tprivate final long[] rolloutFieldCost = new long[1];
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\tprivate MobilitySearch mobilitySearch(final int subjectNum, final boolean avoidOcc, final int depth) {
\t\tfinal boolean nested = inScorerSim || trueConfirmDepth != 0 || simDepth != 0;
"""
new = """\tprivate MobilitySearch mobilitySearch(final int subjectNum, final boolean avoidOcc, final int depth) {
\t\trefreshLiveOccupancy();
\t\tfinal boolean nested = inScorerSim || trueConfirmDepth != 0 || simDepth != 0;
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t/** True iff a live player other than the one at (sx,sy) occupies (nx,ny). */
\tprivate boolean cellOccupiedByLive(final int nx, final int ny, final int sx, final int sy) {
\t\tfor (final Player p : game.players) {
\t\t\tif (p.isFinished())
\t\t\t\tcontinue;
\t\t\tfinal int[] pp = p.getPosition();
\t\t\tif (pp[0] == nx && pp[1] == ny && !(pp[0] == sx && pp[1] == sy))
\t\t\t\treturn true;
\t\t}
\t\treturn false;
\t}
"""
new = """\t/** Rebuild the exact live-cell set once per mobility projection. Only cells
\t * touched by the preceding projection are cleared. */
\tprivate void refreshLiveOccupancy() {
\t\tfinal int cells = (game.gameCols + 1) * (game.gameRows + 1);
\t\tif (liveOccupancy == null || liveOccupancy.length != cells) {
\t\t\tliveOccupancy = new byte[cells];
\t\t\tliveOccupancyTouched = new int[game.players.length];
\t\t\tliveOccupancyTouchedCount = 0;
\t\t} else {
\t\t\tfor (int i = 0; i < liveOccupancyTouchedCount; i++)
\t\t\t\tliveOccupancy[liveOccupancyTouched[i]] = 0;
\t\t\tliveOccupancyTouchedCount = 0;
\t\t}
\t\tfinal int h = game.gameRows + 1;
\t\tfor (final Player p : game.players) {
\t\t\tif (p.isFinished())
\t\t\t\tcontinue;
\t\t\tfinal int[] pp = p.getPosition();
\t\t\tif (pp[0] < 0 || pp[1] < 0 || pp[0] > game.gameCols
\t\t\t\t\t|| pp[1] > game.gameRows)
\t\t\t\tcontinue;
\t\t\tfinal int index = pp[0] * h + pp[1];
\t\t\tif (liveOccupancy[index] != 0)
\t\t\t\tcontinue;
\t\t\tliveOccupancy[index] = 1;
\t\t\tliveOccupancyTouched[liveOccupancyTouchedCount++] = index;
\t\t}
\t}

\t/** True iff a live player other than the one at (sx,sy) occupies (nx,ny). */
\tprivate boolean cellOccupiedByLive(final int nx, final int ny, final int sx, final int sy) {
\t\tif (nx == sx && ny == sy)
\t\t\treturn false;
\t\tif (nx < 0 || ny < 0 || nx > game.gameCols || ny > game.gameRows)
\t\t\treturn false;
\t\treturn liveOccupancy[nx * (game.gameRows + 1) + ny] != 0;
\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)
assert source.count("refreshLiveOccupancy();") == 1
assert source.count("liveOccupancy[nx * (game.gameRows + 1) + ny]") == 1
race.write_text(source)
print("materialized direct live-cell mobility occupancy map")
