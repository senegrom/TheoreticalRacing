#!/usr/bin/env python3
"""Materialize the combined behavior-exact mobility runtime batch.

1. Reuse allocation-heavy projection storage in outer/nested workspaces.
2. Use a no-false-negative 64-bit Bloom prefilter before exact blocked scans.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceAi.java")
source = race.read_text()

old = """\tprivate final int[] mobilityMove = new int[4];
\tprivate final long[] rolloutFieldCost = new long[1];
"""
new = """\tprivate final int[] mobilityMove = new int[4];
\tprivate MobilitySearch outerMobilityWorkspace;
\tprivate MobilitySearch nestedMobilityWorkspace;
\tprivate final long[] rolloutFieldCost = new long[1];
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\tfinal long[] b = search.blocked[ply - 1];
\t\tfinal int bc = search.blockedCount[ply - 1];
"""
new = """\t\tfinal long[] b = search.blocked[ply - 1];
\t\tfinal int bc = search.blockedCount[ply - 1];
\t\tfinal long bb = search.blockedBloom[ply - 1];
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old_call = "blockedContains(b, bc, ((long) nx << 32) | (ny & 0xffffffffL))"
new_call = "blockedContains(b, bc, bb, ((long) nx << 32) | (ny & 0xffffffffL))"
assert source.count(old_call) == 2, source.count(old_call)
source = source.replace(old_call, new_call)

old = """\tprivate static final class MobilitySearch {
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
new = """\tprivate static final class MobilitySearch {
\t\tint depth;
\t\tfinal long[][] blocked;
\t\tfinal int[] blockedCount;
\t\tfinal long[] blockedBloom;
\t\tint epoch;

\t\tMobilitySearch(final int depth, final int players) {
\t\t\tblocked = new long[depth][3 * players];
\t\t\tblockedCount = new int[depth];
\t\t\tblockedBloom = new long[depth];
\t\t}

\t\tvoid reset(final int newDepth, final int newEpoch) {
\t\t\tdepth = newDepth;
\t\t\tepoch = newEpoch;
\t\t\tjava.util.Arrays.fill(blockedCount, 0, newDepth, 0);
\t\t\tjava.util.Arrays.fill(blockedBloom, 0, newDepth, 0L);
\t\t}
\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\tprivate static boolean blockedContains(final long[] cells, final int count, final long cell) {
\t\tfor (int i = 0; i < count; i++)
\t\t\tif (cells[i] == cell)
\t\t\t\treturn true;
\t\treturn false;
\t}
"""
new = """\tprivate static long blockedBloomBit(final long cell) {
\t\treturn 1L << (cell * 0x9E3779B97F4A7C15L >>> 58);
\t}

\tprivate static boolean blockedContains(final long[] cells, final int count,
\t\t\tfinal long bloom, final long cell) {
\t\tif ((bloom & blockedBloomBit(cell)) == 0)
\t\t\treturn false;
\t\tfor (int i = 0; i < count; i++)
\t\t\tif (cells[i] == cell)
\t\t\t\treturn true;
\t\treturn false;
\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\tprivate MobilitySearch mobilitySearch(final int subjectNum, final boolean avoidOcc, final int depth) {
\t\tfinal long[][] blocked = new long[depth][3 * game.players.length];
\t\tfinal int[] blockedCount = new int[depth];
\t\tfor (final Player opponent : game.players) {
"""
new = """\tprivate MobilitySearch mobilitySearch(final int subjectNum, final boolean avoidOcc, final int depth) {
\t\tfinal boolean nested = inScorerSim || trueConfirmDepth != 0 || simDepth != 0;
\t\tMobilitySearch search = nested ? nestedMobilityWorkspace : outerMobilityWorkspace;
\t\tif (search == null || search.blocked.length != depth
\t\t\t\t|| search.blocked[0].length != 3 * game.players.length) {
\t\t\tsearch = new MobilitySearch(depth, game.players.length);
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
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\t}
\t\treturn new MobilitySearch(depth, blocked, blockedCount, ++fmMemoEpoch);
\t}

\t/** N-ply escape headroom"""
new = """\t\t}
\t\tfor (int ply = 0; ply < depth; ply++) {
\t\t\tlong bloom = 0;
\t\t\tfor (int i = 0; i < blockedCount[ply]; i++)
\t\t\t\tbloom |= blockedBloomBit(blocked[ply][i]);
\t\t\tsearch.blockedBloom[ply] = bloom;
\t\t}
\t\treturn search;
\t}

\t/** N-ply escape headroom"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

race.write_text(source)
print("materialized combined mobility runtime batch")
