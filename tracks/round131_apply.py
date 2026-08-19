#!/usr/bin/env python3
"""Materialize Round 131's exact point-containment cache."""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()

old = """\tprivate void buildLegalRaster() {
\t\tfinal int w = gameCols + 2;
"""
new = """\tprivate void buildLegalRaster() {
\t\tpointContainmentCache.clear();
\t\tfinal int w = gameCols + 2;
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\tprivate static final int SUB_RES = 4;
\tprivate byte[] subRaster;
\tprivate int subH;

\tprivate void buildSubRaster(final byte[] unit, final int unitW) {
\t\tfinal int w = unitW * SUB_RES;
\t\tsubH = rasterH * SUB_RES;
"""
new = """\tprivate static final int SUB_RES = 4;
\tprivate byte[] subRaster;
\tprivate int subW;
\tprivate int subH;
\tprivate final PointContainmentCache pointContainmentCache = new PointContainmentCache(1 << 18);

\tprivate void buildSubRaster(final byte[] unit, final int unitW) {
\t\tfinal int w = unitW * SUB_RES;
\t\tsubW = w;
\t\tsubH = rasterH * SUB_RES;
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

anchor = """\t\tsubRaster = r;
\t}

\tprivate void markSubPath"""
helper = """\t\tsubRaster = r;
\t}

\t/**
\t * Reuse the conservative sub-raster for the exact legality scan's point
\t * probes. A subcell whose interior bit is set was built from an
\t * Area.contains(rect) proof (with a boundary-covering margin), so every
\t * point in it is inside the track or start zone. Unproven cells retain the
\t * exact Area.contains fallback; this helper can therefore only skip work,
\t * never change a geometry verdict.
\t */
\tprivate boolean containsTrackOrStart(final double x, final double y) {
\t\tfinal byte[] r = subRaster;
\t\tif (r != null) {
\t\t\tfinal int sx = (int) Math.floor(x * SUB_RES);
\t\t\tfinal int sy = (int) Math.floor(y * SUB_RES);
\t\t\tif (sx >= 0 && sy >= 0 && sx < subW && sy < subH
\t\t\t\t\t&& (r[sx * subH + sy] & 1) != 0)
\t\t\t\treturn true;
\t\t}
\t\tfinal long xBits = Double.doubleToRawLongBits(x);
\t\tfinal long yBits = Double.doubleToRawLongBits(y);
\t\tfinal byte cached = pointContainmentCache.get(xBits, yBits);
\t\tif (cached != 0)
\t\t\treturn cached == PointContainmentCache.TRUE;
\t\tfinal boolean inside = trackA.contains(x, y) || startZoneA.contains(x, y);
\t\tpointContainmentCache.put(xBits, yBits, inside);
\t\treturn inside;
\t}

\tprivate void markSubPath"""
assert source.count(anchor) == 1, source.count(anchor)
source = source.replace(anchor, helper, 1)

old = "\t\tif (!trackA.contains(x2, y2) && !startZoneA.contains(x2, y2))\n"
new = "\t\tif (!containsTrackOrStart(x2, y2))\n"
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)
old = "\t\t\tif (!trackA.contains(cx, cy) && !startZoneA.contains(cx, cy))\n"
new = "\t\t\tif (!containsTrackOrStart(cx, cy))\n"
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

anchor = """\t/** Bijective SplitMix64 finalizer. Packed nearby endpoints have strongly
"""
cache = """\t/** Primitive exact-double-pair to boolean cache for the residual legality
\t *  scan. Different edges repeatedly probe the same rational points; keeping
\t *  both coordinate bit patterns avoids the collision risk of compressing a
\t *  128-bit identity into one key while retaining allocation-free lookup. */
\tstatic final class PointContainmentCache {
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

\t\tbyte get(final long xKey, final long yKey) {
\t\t\tint slot = (int) pointHash(xKey, yKey) & mask;
\t\t\twhile (states[slot] != 0) {
\t\t\t\tif (xKeys[slot] == xKey && yKeys[slot] == yKey)
\t\t\t\t\treturn states[slot];
\t\t\t\tslot = slot + 1 & mask;
\t\t\t}
\t\t\treturn 0;
\t\t}

\t\tvoid clear() {
\t\t\tjava.util.Arrays.fill(states, (byte) 0);
\t\t\tsize = 0;
\t\t}

\t\tvoid put(final long xKey, final long yKey, final boolean value) {
\t\t\tif (size >= resizeAt)
\t\t\t\tgrow();
\t\t\tint slot = (int) pointHash(xKey, yKey) & mask;
\t\t\twhile (states[slot] != 0) {
\t\t\t\tif (xKeys[slot] == xKey && yKeys[slot] == yKey) {
\t\t\t\t\tstates[slot] = value ? TRUE : FALSE;
\t\t\t\t\treturn;
\t\t\t\t}
\t\t\t\tslot = slot + 1 & mask;
\t\t\t}
\t\t\txKeys[slot] = xKey;
\t\t\tyKeys[slot] = yKey;
\t\t\tstates[slot] = value ? TRUE : FALSE;
\t\t\tsize++;
\t\t}

\t\tprivate void allocate(final int capacity) {
\t\t\txKeys = new long[capacity];
\t\t\tyKeys = new long[capacity];
\t\t\tstates = new byte[capacity];
\t\t\tmask = capacity - 1;
\t\t\tresizeAt = capacity - capacity / 3;
\t\t}

\t\tprivate void grow() {
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
\t}

\tprivate static long pointHash(final long xKey, final long yKey) {
\t\treturn mixEdgeKey(xKey ^ Long.rotateLeft(yKey, 29));
\t}

\t/** Bijective SplitMix64 finalizer. Packed nearby endpoints have strongly
"""
assert source.count(anchor) == 1, source.count(anchor)
source = source.replace(anchor, cache, 1)
race.write_text(source)

core = Path("tests/tr/logic/CoreTests.java")
tests = core.read_text()
old = "        testEdgeLegalCache();\n        testEndgameMemoKey();\n"
new = "        testEdgeLegalCache();\n        testPointContainmentCache();\n        testEndgameMemoKey();\n"
assert tests.count(old) == 1, tests.count(old)
tests = tests.replace(old, new, 1)

anchor = """    private static void testDistinctCoverMatching() {
"""
method = """
    private static void testPointContainmentCache() {
        final RaceGame.PointContainmentCache cache = new RaceGame.PointContainmentCache(1);
        check(cache.get(0L, 0L) == 0, "fresh point cache should miss");
        cache.put(0L, 0L, false);
        cache.put(0L, Long.MIN_VALUE, true);
        cache.put(Long.MIN_VALUE, 0L, true);
        check(cache.get(0L, 0L) == RaceGame.PointContainmentCache.FALSE,
                "zero-pair false value was lost");
        check(cache.get(0L, Long.MIN_VALUE) == RaceGame.PointContainmentCache.TRUE,
                "point cache lost the y coordinate");
        check(cache.get(Long.MIN_VALUE, 0L) == RaceGame.PointContainmentCache.TRUE,
                "point cache lost the x coordinate");

        for (int i = 1; i <= 10_000; i++) {
            final long x = i * 0x9e3779b97f4a7c15L;
            final long y = Long.rotateLeft(x ^ 0xd1b54a32d192ed03L, i & 63);
            cache.put(x, y, (i & 1) == 0);
        }
        for (int i = 1; i <= 10_000; i++) {
            final long x = i * 0x9e3779b97f4a7c15L;
            final long y = Long.rotateLeft(x ^ 0xd1b54a32d192ed03L, i & 63);
            final byte expected = (i & 1) == 0
                    ? RaceGame.PointContainmentCache.TRUE : RaceGame.PointContainmentCache.FALSE;
            check(cache.get(x, y) == expected, "point cache resize lost key pair " + i);
        }
        cache.put(0L, 0L, true);
        check(cache.get(0L, 0L) == RaceGame.PointContainmentCache.TRUE,
                "point cache update failed");
        cache.clear();
        check(cache.get(0L, 0L) == 0, "point cache clear retained a stale geometry verdict");
        check(cache.get(Double.doubleToRawLongBits(-0.0), Double.doubleToRawLongBits(-0.0)) == 0,
                "point cache merged distinct double bit patterns");
    }

    private static void testDistinctCoverMatching() {
"""
assert tests.count(anchor) == 1, tests.count(anchor)
tests = tests.replace(anchor, method, 1)
core.write_text(tests)

print("materialized Round 131 point-containment cache")
