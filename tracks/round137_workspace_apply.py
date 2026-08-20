#!/usr/bin/env python3
"""Materialize reusable, recursion-separated mobility projection storage.

The projection is consumed only during the candidate-enumeration phase that
built it. Scorer/true-rival recursion starts afterwards, but receives a second
workspace anyway, preserving the repository's state-isolation discipline.
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
\t\tint epoch;

\t\tMobilitySearch(final int depth, final int players) {
\t\t\tblocked = new long[depth][3 * players];
\t\t\tblockedCount = new int[depth];
\t\t}

\t\tvoid reset(final int newDepth, final int newEpoch) {
\t\t\tdepth = newDepth;
\t\t\tepoch = newEpoch;
\t\t\tjava.util.Arrays.fill(blockedCount, 0, newDepth, 0);
\t\t}
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
\t\t// Full scorer recursion begins after the caller's candidate enumeration;
\t\t// nevertheless keep a separate nested store so future call-order changes
\t\t// cannot make one simulated scorer overwrite a real-turn projection.
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
\t\treturn search;
\t}

\t/** N-ply escape headroom"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

race.write_text(source)
print("materialized reusable mobility projection workspaces")
