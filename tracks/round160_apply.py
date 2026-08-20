#!/usr/bin/env python3
"""Materialize exact direct blocked-cell bitsets for mobility search.

The mobility recursion currently scans up to three predicted cells per opponent
for every candidate node.  This keeps the original tiny cell arrays as the
outside-grid fallback, but adds one collision-free bitset per ply for ordinary
in-grid queries.  Reusable outer/nested workspaces avoid rebuilding the storage
on every AI turn; only words touched by the previous projection are cleared.

The bitset stores exactly the same 64-bit cells as the linear list.  It changes
lookup cost only, never membership or policy.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceAi.java")
source = race.read_text()

old_fields = """\tprivate final int[] mobilityMove = new int[4];
\tprivate final long[] rolloutFieldCost = new long[1];
"""
new_fields = """\tprivate final int[] mobilityMove = new int[4];
\tprivate MobilitySearch outerMobilityWorkspace;
\tprivate MobilitySearch nestedMobilityWorkspace;
\tprivate final long[] rolloutFieldCost = new long[1];
"""
assert source.count(old_fields) == 1, source.count(old_fields)
source = source.replace(old_fields, new_fields, 1)

old_locals = """\t\tfinal long[] b = search.blocked[ply - 1];
\t\tfinal int bc = search.blockedCount[ply - 1];
"""
new_locals = """\t\tfinal long[] b = search.blocked[ply - 1];
\t\tfinal int bc = search.blockedCount[ply - 1];
\t\tfinal long[] direct = search.blockedBits[ply - 1];
"""
assert source.count(old_locals) == 1, source.count(old_locals)
source = source.replace(old_locals, new_locals, 1)

old_call = "blockedContains(b, bc, ((long) nx << 32) | (ny & 0xffffffffL))"
new_call = "blockedContains(b, bc, direct, search.gridW, search.gridH, nx, ny)"
assert source.count(old_call) == 2, source.count(old_call)
source = source.replace(old_call, new_call)

old_class = """\tprivate static final class MobilitySearch {
\t\tfinal int depth;
\t\tfinal long[][] blocked;
\t\tfinal int[] blockedCount;
\t\tfinal int epoch;

\t\tMobilitySearch(final int depth, final long[][] blocked, final int[] blockedCount,
\t\t\t\tfinal int epoch) {
\t\t\tthis.depth = depth;
\t\t\tthis.blocked = blocked;
\t\t\tthis.blockedCount = blockedCount;
\t\t\tthis.epoch = epoch;
\t\t}
\t}
"""
new_class = """\tprivate static final class MobilitySearch {
\t\tint depth;
\t\tfinal long[][] blocked;
\t\tfinal int[] blockedCount;
\t\tfinal long[][] blockedBits;
\t\tfinal int[][] touchedWords;
\t\tfinal int[] touchedCount;
\t\tfinal int gridW;
\t\tfinal int gridH;
\t\tint epoch;

\t\tMobilitySearch(final int depth, final int players, final int gridW,
\t\t\t\tfinal int gridH) {
\t\t\tthis.gridW = gridW;
\t\t\tthis.gridH = gridH;
\t\t\tblocked = new long[depth][3 * players];
\t\t\tblockedCount = new int[depth];
\t\t\tfinal int words = (gridW * gridH + Long.SIZE - 1) >>> 6;
\t\t\tblockedBits = new long[depth][words];
\t\t\ttouchedWords = new int[depth][3 * players];
\t\t\ttouchedCount = new int[depth];
\t\t}

\t\tvoid reset(final int newDepth, final int newEpoch) {
\t\t\tfor (int ply = 0; ply < blockedBits.length; ply++) {
\t\t\t\tfor (int i = 0; i < touchedCount[ply]; i++)
\t\t\t\t\tblockedBits[ply][touchedWords[ply][i]] = 0L;
\t\t\t\ttouchedCount[ply] = 0;
\t\t\t\tblockedCount[ply] = 0;
\t\t\t}
\t\t\tdepth = newDepth;
\t\t\tepoch = newEpoch;
\t\t}

\t\tvoid indexBlockedCells() {
\t\t\tfor (int ply = 0; ply < depth; ply++) {
\t\t\t\tfinal long[] bits = blockedBits[ply];
\t\t\t\tfor (int i = 0; i < blockedCount[ply]; i++) {
\t\t\t\t\tfinal long cell = blocked[ply][i];
\t\t\t\t\tfinal int x = (int) (cell >> 32), y = (int) cell;
\t\t\t\t\tif (x < 0 || y < 0 || x >= gridW || y >= gridH)
\t\t\t\t\t\tcontinue;
\t\t\t\t\tfinal int index = x * gridH + y;
\t\t\t\t\tfinal int word = index >>> 6;
\t\t\t\t\tif (bits[word] == 0L)
\t\t\t\t\t\ttouchedWords[ply][touchedCount[ply]++] = word;
\t\t\t\t\tbits[word] |= 1L << (index & 63);
\t\t\t\t}
\t\t\t}
\t\t}
\t}
"""
assert source.count(old_class) == 1, source.count(old_class)
source = source.replace(old_class, new_class, 1)

old_contains = """\tprivate static boolean blockedContains(final long[] cells, final int count, final long cell) {
\t\tfor (int i = 0; i < count; i++)
\t\t\tif (cells[i] == cell)
\t\t\t\treturn true;
\t\treturn false;
\t}
"""
new_contains = """\tstatic boolean blockedContains(final long[] cells, final int count,
\t\t\tfinal long[] direct, final int gridW, final int gridH,
\t\t\tfinal int x, final int y) {
\t\tif (x >= 0 && y >= 0 && x < gridW && y < gridH) {
\t\t\tfinal int index = x * gridH + y;
\t\t\treturn (direct[index >>> 6] & 1L << (index & 63)) != 0;
\t\t}
\t\tfinal long cell = ((long) x << 32) | (y & 0xffffffffL);
\t\tfor (int i = 0; i < count; i++)
\t\t\tif (cells[i] == cell)
\t\t\t\treturn true;
\t\treturn false;
\t}
"""
assert source.count(old_contains) == 1, source.count(old_contains)
source = source.replace(old_contains, new_contains, 1)

old_start = """\tprivate MobilitySearch mobilitySearch(final int subjectNum, final boolean avoidOcc, final int depth) {
\t\tfinal long[][] blocked = new long[depth][3 * game.players.length];
\t\tfinal int[] blockedCount = new int[depth];
\t\tfor (final Player opponent : game.players) {
"""
new_start = """\tprivate MobilitySearch mobilitySearch(final int subjectNum, final boolean avoidOcc, final int depth) {
\t\tfinal boolean nested = inScorerSim || trueConfirmDepth != 0 || simDepth != 0;
\t\tMobilitySearch search = nested ? nestedMobilityWorkspace : outerMobilityWorkspace;
\t\tfinal int gridW = game.gameCols + 1, gridH = game.gameRows + 1;
\t\tif (search == null || search.blocked.length != depth
\t\t\t\t|| search.blocked[0].length != 3 * game.players.length
\t\t\t\t|| search.gridW != gridW || search.gridH != gridH) {
\t\t\tsearch = new MobilitySearch(depth, game.players.length, gridW, gridH);
\t\t\tif (nested)
\t\t\t\tnestedMobilityWorkspace = search;
\t\t\telse
\t\t\t\touterMobilityWorkspace = search;
\t\t}
\t\tsearch.reset(depth, ++fmMemoEpoch);
\t\tfinal long[][] blocked = search.blocked;
\t\tfinal int[] blockedCount = search.blockedCount;
\t\tfor (final Player opponent : game.players) {
"""
assert source.count(old_start) == 1, source.count(old_start)
source = source.replace(old_start, new_start, 1)

old_return = """\t\t}
\t\treturn new MobilitySearch(depth, blocked, blockedCount, ++fmMemoEpoch);
\t}

\t/** N-ply escape headroom"""
new_return = """\t\t}
\t\tsearch.indexBlockedCells();
\t\treturn search;
\t}

\t/** N-ply escape headroom"""
assert source.count(old_return) == 1, source.count(old_return)
source = source.replace(old_return, new_return, 1)

assert source.count("blockedContains(b, bc, direct, search.gridW, search.gridH, nx, ny)") == 2
assert source.count("private MobilitySearch outerMobilityWorkspace;") == 1
race.write_text(source)

core = Path("tests/tr/logic/CoreTests.java")
tests = core.read_text()
assert "private static void testDirectBlockedLookup()" not in tests
old_call = """        testDistinctCoverMatching();
        testTrackDistanceOrdering();
"""
new_call = """        testDistinctCoverMatching();
        testDirectBlockedLookup();
        testTrackDistanceOrdering();
"""
assert tests.count(old_call) == 1, tests.count(old_call)
tests = tests.replace(old_call, new_call, 1)

anchor = """    private static void testTrackDistanceOrdering() {
"""
method = """    private static void testDirectBlockedLookup() {
        final int width = 4, height = 5;
        final long inside = ((long) 2 << 32) | 3L;
        final long outside = ((long) -1 << 32) | 7L;
        final long[] cells = new long[]{inside, outside};
        final long[] direct = new long[(width * height + 63) >>> 6];
        final int index = 2 * height + 3;
        direct[index >>> 6] |= 1L << (index & 63);
        check(RaceAi.blockedContains(cells, 2, direct, width, height, 2, 3),
                "direct blocked-cell lookup missed an in-grid member");
        check(!RaceAi.blockedContains(cells, 2, direct, width, height, 1, 3),
                "direct blocked-cell lookup produced an in-grid false hit");
        check(RaceAi.blockedContains(cells, 2, direct, width, height, -1, 7),
                "blocked-cell outside-grid fallback missed a member");
        check(!RaceAi.blockedContains(cells, 2, direct, width, height, -1, 8),
                "blocked-cell outside-grid fallback produced a false hit");
    }

    private static void testTrackDistanceOrdering() {
"""
assert tests.count(anchor) == 1, tests.count(anchor)
tests = tests.replace(anchor, method, 1)
core.write_text(tests)

print("materialized exact direct mobility blocked-cell bitsets")
