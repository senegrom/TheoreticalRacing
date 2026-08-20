#!/usr/bin/env python3
"""Materialize a shared exact point-containment cache for sequential batches.

The residual geometry fallback repeatedly probes the same rational points on
every seed. Main.runBatch executes one RaceGame at a time and installs an end
hook before start, so those exact Area.contains verdicts can warm once per track
and be reused by later seeds. Interactive, query, dump and single-race modes
remain private.

The shared table keeps full raw IEEE-754 coordinate identities, exact equality,
and the existing open-addressing lookup. It is capped at four LRU track tables;
each table stops caching new misses at 2^20 slots rather than growing without a
batch bound. A skipped store only causes an exact recomputation.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()

old_field = """\tprivate byte[] subRaster;
\tprivate int subW;
\tprivate int subH;
\tprivate final PointContainmentCache pointContainmentCache = new PointContainmentCache(1 << 18);
"""
new_field = """\tprivate byte[] subRaster;
\tprivate int subW;
\tprivate int subH;
\tprivate PointContainmentCache pointContainmentCache = new PointContainmentCache(1 << 18);
\tprivate boolean pointContainmentCacheShared;
"""
assert source.count(old_field) == 1, source.count(old_field)
source = source.replace(old_field, new_field, 1)

old_build_start = """\tprivate void buildLegalRaster() {
\t\tpointContainmentCache.clear();
"""
new_build_start = """\tprivate void buildLegalRaster() {
\t\t// A geometry rebuild must never clear a table retained for another batch.
\t\tif (pointContainmentCacheShared) {
\t\t\tpointContainmentCache = new PointContainmentCache(1 << 18);
\t\t\tpointContainmentCacheShared = false;
\t\t}
\t\tpointContainmentCache.clear();
"""
assert source.count(old_build_start) == 1, source.count(old_build_start)
source = source.replace(old_build_start, new_build_start, 1)

old_geometry = """\t\tbuildLegalRaster();
\t\trui.finishTrack();
\t\treach.computeDistMap();
"""
new_geometry = """\t\tbuildLegalRaster();
\t\t// The non-null batch hook is Main.runBatch's sequential-lifecycle marker.
\t\t// Assign only after raster construction, whose first step clears the
\t\t// current game's private point cache.
\t\tif (autoRaceEndHook != null && denseKey != null) {
\t\t\tpointContainmentCache = PointContainmentCache.shared(
\t\t\t\t\tdenseKey, 1 << 18, 1 << 20, 4);
\t\t\tpointContainmentCacheShared = true;
\t\t}
\t\trui.finishTrack();
\t\treach.computeDistMap();
"""
assert source.count(old_geometry) == 1, source.count(old_geometry)
source = source.replace(old_geometry, new_geometry, 1)

old_class_fields = """\tstatic final class PointContainmentCache {
\t\tstatic final byte FALSE = 1;
\t\tstatic final byte TRUE = 2;

\t\tprivate long[] xKeys;
\t\tprivate long[] yKeys;
\t\tprivate int mask;
\t\tprivate int resizeAt;
\t\tprivate int size;
\t\tprivate byte[] states;

\t\tPointContainmentCache(final int initialCapacity) {
\t\t\tif (initialCapacity < 1 || initialCapacity > 1 << 30)
\t\t\t\tthrow new IllegalArgumentException("invalid cache capacity");
\t\t\tint capacity = 4;
\t\t\twhile (capacity < initialCapacity)
\t\t\t\tcapacity <<= 1;
\t\t\tallocate(capacity);
\t\t}
"""
new_class_fields = """\tstatic final class PointContainmentCache {
\t\tstatic final byte FALSE = 1;
\t\tstatic final byte TRUE = 2;
\t\tprivate static final java.util.LinkedHashMap<String, PointContainmentCache> SHARED =
\t\t\t\tnew java.util.LinkedHashMap<>(8, 0.75f, true);

\t\tprivate long[] xKeys;
\t\tprivate long[] yKeys;
\t\tprivate int mask;
\t\tprivate final int maxCapacity;
\t\tprivate int resizeAt;
\t\tprivate int size;
\t\tprivate byte[] states;

\t\tPointContainmentCache(final int initialCapacity) {
\t\t\tthis(initialCapacity, 1 << 30);
\t\t}

\t\tprivate PointContainmentCache(final int initialCapacity,
\t\t\t\tfinal int maximumCapacity) {
\t\t\tif (initialCapacity < 1 || maximumCapacity < initialCapacity
\t\t\t\t\t|| maximumCapacity > 1 << 30)
\t\t\t\tthrow new IllegalArgumentException("invalid cache capacity");
\t\t\tint capacity = 4;
\t\t\twhile (capacity < initialCapacity)
\t\t\t\tcapacity <<= 1;
\t\t\tint maximum = 4;
\t\t\twhile (maximum < maximumCapacity)
\t\t\t\tmaximum <<= 1;
\t\t\tif (capacity > maximum)
\t\t\t\tthrow new IllegalArgumentException("initial cache exceeds maximum");
\t\t\tmaxCapacity = maximum;
\t\t\tallocate(capacity);
\t\t}

\t\tstatic synchronized PointContainmentCache shared(final String key,
\t\t\t\tfinal int initialCapacity, final int maximumCapacity,
\t\t\t\tfinal int maxCaches) {
\t\t\tif (key == null || maxCaches < 1)
\t\t\t\treturn new PointContainmentCache(initialCapacity, maximumCapacity);
\t\t\tfinal PointContainmentCache existing = SHARED.get(key);
\t\t\tif (existing != null)
\t\t\t\treturn existing;
\t\t\twhile (SHARED.size() >= maxCaches) {
\t\t\t\tfinal java.util.Iterator<java.util.Map.Entry<String, PointContainmentCache>> it =
\t\t\t\t\t\tSHARED.entrySet().iterator();
\t\t\t\tit.next();
\t\t\t\tit.remove();
\t\t\t}
\t\t\tfinal PointContainmentCache created =
\t\t\t\t\tnew PointContainmentCache(initialCapacity, maximumCapacity);
\t\t\tSHARED.put(key, created);
\t\t\treturn created;
\t\t}

\t\tstatic synchronized void clearSharedForTests() {
\t\t\tSHARED.clear();
\t\t}

\t\tint capacityForTests() {
\t\t\treturn xKeys.length;
\t\t}
"""
assert source.count(old_class_fields) == 1, source.count(old_class_fields)
source = source.replace(old_class_fields, new_class_fields, 1)

old_put = """\t\tvoid put(final long xKey, final long yKey, final boolean value) {
\t\t\tif (size >= resizeAt)
\t\t\t\tgrow();
\t\t\tint slot = (int) pointHash(xKey, yKey) & mask;
"""
new_put = """\t\tvoid put(final long xKey, final long yKey, final boolean value) {
\t\t\tif (size >= resizeAt && !grow())
\t\t\t\treturn;
\t\t\tint slot = (int) pointHash(xKey, yKey) & mask;
"""
assert source.count(old_put) == 1, source.count(old_put)
source = source.replace(old_put, new_put, 1)

old_grow = """\t\tprivate void grow() {
\t\t\tif (xKeys.length == 1 << 30)
\t\t\t\tthrow new IllegalStateException("point cache is too large");
\t\t\tfinal long[] oldX = xKeys;
\t\t\tfinal long[] oldY = yKeys;
\t\t\tfinal byte[] oldStates = states;
\t\t\tallocate(xKeys.length << 1);
\t\t\tsize = 0;
\t\t\tfor (int i = 0; i < oldStates.length; i++) {
\t\t\t\tif (oldStates[i] == 0)
\t\t\t\t\tcontinue;
\t\t\t\tint slot = (int) pointHash(oldX[i], oldY[i]) & mask;
\t\t\t\twhile (states[slot] != 0)
\t\t\t\t\tslot = slot + 1 & mask;
\t\t\t\txKeys[slot] = oldX[i];
\t\t\t\tyKeys[slot] = oldY[i];
\t\t\t\tstates[slot] = oldStates[i];
\t\t\t\tsize++;
\t\t\t}
\t\t}
"""
new_grow = """\t\tprivate boolean grow() {
\t\t\tif (xKeys.length >= maxCapacity)
\t\t\t\treturn false;
\t\t\tfinal long[] oldX = xKeys;
\t\t\tfinal long[] oldY = yKeys;
\t\t\tfinal byte[] oldStates = states;
\t\t\tallocate(xKeys.length << 1);
\t\t\tsize = 0;
\t\t\tfor (int i = 0; i < oldStates.length; i++) {
\t\t\t\tif (oldStates[i] == 0)
\t\t\t\t\tcontinue;
\t\t\t\tint slot = (int) pointHash(oldX[i], oldY[i]) & mask;
\t\t\t\twhile (states[slot] != 0)
\t\t\t\t\tslot = slot + 1 & mask;
\t\t\t\txKeys[slot] = oldX[i];
\t\t\t\tyKeys[slot] = oldY[i];
\t\t\t\tstates[slot] = oldStates[i];
\t\t\t\tsize++;
\t\t\t}
\t\t\treturn true;
\t\t}
"""
assert source.count(old_grow) == 1, source.count(old_grow)
source = source.replace(old_grow, new_grow, 1)

assert source.count("PointContainmentCache.shared(") == 1
assert source.count("pointContainmentCacheShared") == 3
race.write_text(source)

core = Path("tests/tr/logic/CoreTests.java")
tests = core.read_text()
assert "private static void testSharedPointContainmentCache()" not in tests
old_call = """        testPointContainmentCache();
        testSharedDistanceMaps();
"""
new_call = """        testPointContainmentCache();
        testSharedPointContainmentCache();
        testSharedDistanceMaps();
"""
assert tests.count(old_call) == 1, tests.count(old_call)
tests = tests.replace(old_call, new_call, 1)

anchor = """    private static void testSharedDistanceMaps() {
"""
method = """    private static void testSharedPointContainmentCache() {
        RaceGame.PointContainmentCache.clearSharedForTests();
        final RaceGame.PointContainmentCache first =
                RaceGame.PointContainmentCache.shared("core-point-a", 4, 8, 2);
        final RaceGame.PointContainmentCache again =
                RaceGame.PointContainmentCache.shared("core-point-a", 4, 8, 2);
        check(first == again, "shared point-containment cache was not reused");
        first.put(1L, 2L, true);
        check(again.get(1L, 2L) == RaceGame.PointContainmentCache.TRUE,
                "shared point-containment verdict was lost");

        final RaceGame.PointContainmentCache second =
                RaceGame.PointContainmentCache.shared("core-point-b", 4, 8, 2);
        check(second != first, "distinct geometry keys shared one point cache");
        check(RaceGame.PointContainmentCache.shared("core-point-a", 4, 8, 2) == first,
                "point-cache access did not preserve the existing entry");
        final RaceGame.PointContainmentCache third =
                RaceGame.PointContainmentCache.shared("core-point-c", 4, 8, 2);
        check(third != first && third != second, "point-cache LRU did not create a new entry");
        check(RaceGame.PointContainmentCache.shared("core-point-b", 4, 8, 2) != second,
                "point-cache LRU did not evict the eldest entry");

        final RaceGame.PointContainmentCache bounded =
                RaceGame.PointContainmentCache.shared("core-point-bound", 4, 4, 4);
        for (int i = 0; i < 100; i++)
            bounded.put(i, Long.rotateLeft(i * 17L, 11), (i & 1) == 0);
        check(bounded.capacityForTests() == 4,
                "bounded shared point cache exceeded its capacity");
        RaceGame.PointContainmentCache.clearSharedForTests();
    }

    private static void testSharedDistanceMaps() {
"""
assert tests.count(anchor) == 1, tests.count(anchor)
tests = tests.replace(anchor, method, 1)
core.write_text(tests)

print("materialized shared exact point-containment cache")
