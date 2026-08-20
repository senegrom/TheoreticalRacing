#!/usr/bin/env python3
"""Materialize shared immutable progress maps for same-track auto batches.

Every RaceGame currently rebuilds the 8-connected distance-to-finish BFS and
its derived corridor-width vector before racing. Those arrays depend only on
the geometry cache key and are never mutated after construction. Consecutive
auto races can therefore adopt one exact immutable pair from a bounded LRU
pool. Interactive games remain private.
"""
from pathlib import Path

reach = Path("src/tr/logic/Reachability.java")
source = reach.read_text()

old_fields = """\tprivate Thread reachabilityThread;
\tint[][] distToFinish;

\tBitSet\taliveStates;
"""
new_fields = """\tprivate Thread reachabilityThread;
\tint[][] distToFinish;

\t/** Exact immutable progress-map pairs shared only by auto games carrying
\t * the same geometry cache key. The cap counts int entries (4 bytes each),
\t * so the 8M-entry pool retains at most roughly 32 MiB plus row overhead. */
\tprivate static final long DISTANCE_MEMO_MAX_INTS = 8L << 20;
\tprivate static final java.util.LinkedHashMap<String, DistanceMaps> DISTANCE_MEMO =
\t\t\tnew java.util.LinkedHashMap<>(16, 0.75f, true);
\tprivate static long distanceMemoInts;

\tstatic final class DistanceMaps {
\t\tfinal int[][] distance;
\t\tfinal int[] ringWidth;
\t\tfinal int width;
\t\tfinal int height;
\t\tfinal long intCount;

\t\tDistanceMaps(final int[][] distance, final int[] ringWidth) {
\t\t\tif (distance == null || distance.length == 0 || distance[0] == null
\t\t\t\t\t|| ringWidth == null)
\t\t\t\tthrow new IllegalArgumentException("invalid distance maps");
\t\t\twidth = distance.length;
\t\t\theight = distance[0].length;
\t\t\tif (height == 0)
\t\t\t\tthrow new IllegalArgumentException("empty distance-map row");
\t\t\tfor (final int[] column : distance)
\t\t\t\tif (column == null || column.length != height)
\t\t\t\t\tthrow new IllegalArgumentException("ragged distance map");
\t\t\tthis.distance = distance;
\t\t\tthis.ringWidth = ringWidth;
\t\t\tintCount = (long) width * height + ringWidth.length;
\t\t}
\t}

\tstatic synchronized DistanceMaps findDistanceMaps(final String key,
\t\t\tfinal int width, final int height) {
\t\tif (key == null)
\t\t\treturn null;
\t\tfinal DistanceMaps maps = DISTANCE_MEMO.get(key);
\t\treturn maps != null && maps.width == width && maps.height == height
\t\t\t\t? maps : null;
\t}

\tstatic synchronized DistanceMaps publishDistanceMaps(final String key,
\t\t\tfinal int[][] distance, final int[] ringWidth, final long maxInts) {
\t\tfinal DistanceMaps created = new DistanceMaps(distance, ringWidth);
\t\tif (key == null || maxInts < 1 || created.intCount > maxInts)
\t\t\treturn created;
\t\tfinal DistanceMaps existing = DISTANCE_MEMO.get(key);
\t\tif (existing != null && existing.width == created.width
\t\t\t\t&& existing.height == created.height)
\t\t\treturn existing;
\t\tif (existing != null) {
\t\t\tDISTANCE_MEMO.remove(key);
\t\t\tdistanceMemoInts -= existing.intCount;
\t\t}
\t\twhile (!DISTANCE_MEMO.isEmpty()
\t\t\t\t&& distanceMemoInts + created.intCount > maxInts) {
\t\t\tfinal java.util.Iterator<java.util.Map.Entry<String, DistanceMaps>> it =
\t\t\t\t\tDISTANCE_MEMO.entrySet().iterator();
\t\t\tfinal DistanceMaps evicted = it.next().getValue();
\t\t\tit.remove();
\t\t\tdistanceMemoInts -= evicted.intCount;
\t\t}
\t\tDISTANCE_MEMO.put(key, created);
\t\tdistanceMemoInts += created.intCount;
\t\treturn created;
\t}

\tstatic synchronized void clearDistanceMemoForTests() {
\t\tDISTANCE_MEMO.clear();
\t\tdistanceMemoInts = 0;
\t}

\tBitSet\taliveStates;
"""
assert source.count(old_fields) == 1, source.count(old_fields)
source = source.replace(old_fields, new_fields, 1)

old_start = """\tvoid computeDistMap() {
\t\tfinal int w = game.gameCols + 1;
\t\tfinal int h = game.gameRows + 1;
\t\tdistToFinish = new int[w][h];
"""
new_start = """\tvoid computeDistMap() {
\t\tfinal int w = game.gameCols + 1;
\t\tfinal int h = game.gameRows + 1;
\t\tfinal String memoKey = game.autoMode ? geometryCacheKey() : null;
\t\tfinal DistanceMaps cached = findDistanceMaps(memoKey, w, h);
\t\tif (cached != null) {
\t\t\tdistToFinish = cached.distance;
\t\t\tringWidth = cached.ringWidth;
\t\t\treturn;
\t\t}
\t\tdistToFinish = new int[w][h];
"""
assert source.count(old_start) == 1, source.count(old_start)
source = source.replace(old_start, new_start, 1)

old_end = """\t\t}
\t\tbuildRingWidths(w, h);
\t}

\t/** Round 83: per-progress-ring corridor widths."""
new_end = """\t\t}
\t\tbuildRingWidths(w, h);
\t\tif (memoKey != null) {
\t\t\tfinal DistanceMaps shared = publishDistanceMaps(memoKey, distToFinish,
\t\t\t\t\tringWidth, DISTANCE_MEMO_MAX_INTS);
\t\t\tdistToFinish = shared.distance;
\t\t\tringWidth = shared.ringWidth;
\t\t}
\t}

\t/** Round 83: per-progress-ring corridor widths."""
assert source.count(old_end) == 1, source.count(old_end)
source = source.replace(old_end, new_end, 1)
assert source.count("final DistanceMaps cached = findDistanceMaps") == 1
reach.write_text(source)

core = Path("tests/tr/logic/CoreTests.java")
tests = core.read_text()
assert "private static void testSharedDistanceMaps()" not in tests
old_call = """        testPointContainmentCache();
        testEndgameMemoKey();
"""
new_call = """        testPointContainmentCache();
        testSharedDistanceMaps();
        testEndgameMemoKey();
"""
assert tests.count(old_call) == 1, tests.count(old_call)
tests = tests.replace(old_call, new_call, 1)

anchor = """    private static void testDistinctCoverMatching() {
"""
method = """    private static void testSharedDistanceMaps() {
        Reachability.clearDistanceMemoForTests();
        final int[][] distance = new int[][]{{0, 1}, {2, 3}};
        final int[] rings = new int[]{1, 2};
        final Reachability.DistanceMaps first = Reachability.publishDistanceMaps(
                "core-distance-a", distance, rings, 10);
        check(Reachability.findDistanceMaps("core-distance-a", 2, 2) == first,
                "shared distance map was not retained");
        check(first.distance == distance && first.ringWidth == rings,
                "shared distance map copied or replaced exact arrays");

        final Reachability.DistanceMaps duplicate = Reachability.publishDistanceMaps(
                "core-distance-a", new int[][]{{9, 9}, {9, 9}}, new int[]{9}, 10);
        check(duplicate == first, "same geometry replaced a compatible distance map");

        final Reachability.DistanceMaps second = Reachability.publishDistanceMaps(
                "core-distance-b", new int[][]{{4, 5}}, new int[]{2}, 10);
        check(second != null && Reachability.findDistanceMaps("core-distance-b", 1, 2) == second,
                "second distance map was not retained");
        check(Reachability.findDistanceMaps("core-distance-a", 2, 2) == null,
                "distance-map LRU cap did not evict the eldest entry");

        final Reachability.DistanceMaps replacement = Reachability.publishDistanceMaps(
                "core-distance-b", new int[][]{{1}, {2}, {3}}, new int[]{3}, 10);
        check(replacement != second
                        && Reachability.findDistanceMaps("core-distance-b", 3, 1) == replacement,
                "dimension change retained an incompatible distance map");

        final Reachability.DistanceMaps oversized = Reachability.publishDistanceMaps(
                "core-distance-private", new int[][]{{1, 2}, {3, 4}}, new int[]{1, 2}, 5);
        check(oversized != null, "oversized distance map lost its private fallback");
        check(Reachability.findDistanceMaps("core-distance-private", 2, 2) == null,
                "distance map larger than the cap was retained globally");
        Reachability.clearDistanceMemoForTests();
    }

    private static void testDistinctCoverMatching() {
"""
assert tests.count(anchor) == 1, tests.count(anchor)
tests = tests.replace(anchor, method, 1)
core.write_text(tests)

print("materialized shared immutable distance and corridor maps")
