#!/usr/bin/env python3
"""Materialize an exact Bloom prefilter for mobility blocked-cell scans.

The filter can only reject impossible matches. A set Bloom bit still runs the
existing exact linear scan, so collisions affect runtime only and every move
selection remains byte-identical.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceAi.java")
source = race.read_text()

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

old = """\t\tfinal long[][] blocked;
\t\tfinal int[] blockedCount;
\t\tfinal int epoch;

\t\tMobilitySearch(final int depth, final long[][] blocked, final int[] blockedCount,
\t\t\t\tfinal int epoch) {
\t\t\tthis.depth = depth;
\t\t\tthis.blocked = blocked;
\t\t\tthis.blockedCount = blockedCount;
\t\t\tthis.epoch = epoch;
\t\t}
"""
new = """\t\tfinal long[][] blocked;
\t\tfinal int[] blockedCount;
\t\tfinal long[] blockedBloom;
\t\tfinal int epoch;

\t\tMobilitySearch(final int depth, final long[][] blocked, final int[] blockedCount,
\t\t\t\tfinal long[] blockedBloom, final int epoch) {
\t\t\tthis.depth = depth;
\t\t\tthis.blocked = blocked;
\t\t\tthis.blockedCount = blockedCount;
\t\t\tthis.blockedBloom = blockedBloom;
\t\t\tthis.epoch = epoch;
\t\t}
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

old = """\t\tfinal long[][] blocked = new long[depth][3 * game.players.length];
\t\tfinal int[] blockedCount = new int[depth];
"""
new = """\t\tfinal long[][] blocked = new long[depth][3 * game.players.length];
\t\tfinal int[] blockedCount = new int[depth];
\t\tfinal long[] blockedBloom = new long[depth];
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
\t\t\tblockedBloom[ply] = bloom;
\t\t}
\t\treturn new MobilitySearch(depth, blocked, blockedCount, blockedBloom, ++fmMemoEpoch);
\t}

\t/** N-ply escape headroom"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

race.write_text(source)
print("materialized exact mobility blocked-cell Bloom prefilter")
