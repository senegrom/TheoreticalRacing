#!/usr/bin/env python3
"""Materialize an exact primitive blocked-cell set with reusable workspaces.

Each mobility ply contains at most three predicted cells per opponent.  The
current implementation scans that list for every candidate node.  This version
builds a 64-slot primitive open-addressed set per ply.  Full 64-bit equality is
required for a hit; collisions probe onward, so results are exact.  Outer and
nested workspaces own separate storage and are reset between projections.
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
new = """\t\tfinal long[] blockedHash = search.blockedHash[ply - 1];
\t\tfinal byte[] blockedUsed = search.blockedUsed[ply - 1];
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old_call = "blockedContains(b, bc, ((long) nx << 32) | (ny & 0xffffffffL))"
new_call = "blockedContains(blockedHash, blockedUsed, ((long) nx << 32) | (ny & 0xffffffffL))"
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
new = """\tprivate static final int BLOCKED_HASH_CAPACITY = 64;

\tprivate static final class MobilitySearch {
\t\tint depth;
\t\tfinal long[][] blocked;
\t\tfinal int[] blockedCount;
\t\tfinal long[][] blockedHash;
\t\tfinal byte[][] blockedUsed;
\t\tint epoch;

\t\tMobilitySearch(final int depth, final int players) {
\t\t\tblocked = new long[depth][3 * players];
\t\t\tblockedCount = new int[depth];
\t\t\tblockedHash = new long[depth][BLOCKED_HASH_CAPACITY];
\t\t\tblockedUsed = new byte[depth][BLOCKED_HASH_CAPACITY];
\t\t}

\t\tvoid reset(final int newDepth, final int newEpoch) {
\t\t\tdepth = newDepth;
\t\t\tepoch = newEpoch;
\t\t\tjava.util.Arrays.fill(blockedCount, 0, newDepth, 0);
\t\t\tfor (int ply = 0; ply < newDepth; ply++)
\t\t\t\tjava.util.Arrays.fill(blockedUsed[ply], (byte) 0);
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
new = """\tprivate static int blockedHashSlot(final long cell) {
\t\tlong z = cell ^ (cell >>> 32);
\t\tz *= 0x9E3779B97F4A7C15L;
\t\tz ^= z >>> 29;
\t\treturn (int) z & (BLOCKED_HASH_CAPACITY - 1);
\t}

\tprivate static void blockedHashPut(final long[] table, final byte[] used,
\t\t\tfinal long cell) {
\t\tint slot = blockedHashSlot(cell);
\t\twhile (used[slot] != 0) {
\t\t\tif (table[slot] == cell)
\t\t\t\treturn;
\t\t\tslot = slot + 1 & (BLOCKED_HASH_CAPACITY - 1);
\t\t}
\t\ttable[slot] = cell;
\t\tused[slot] = 1;
\t}

\tprivate static boolean blockedContains(final long[] table, final byte[] used,
\t\t\tfinal long cell) {
\t\tint slot = blockedHashSlot(cell);
\t\twhile (used[slot] != 0) {
\t\t\tif (table[slot] == cell)
\t\t\t\treturn true;
\t\t\tslot = slot + 1 & (BLOCKED_HASH_CAPACITY - 1);
\t\t}
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
\t\tfor (int ply = 0; ply < depth; ply++)
\t\t\tfor (int i = 0; i < blockedCount[ply]; i++)
\t\t\t\tblockedHashPut(search.blockedHash[ply], search.blockedUsed[ply],
\t\t\t\t\t\tblocked[ply][i]);
\t\treturn search;
\t}

\t/** N-ply escape headroom"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

race.write_text(source)
print("materialized reusable exact blocked-cell hash tables")
