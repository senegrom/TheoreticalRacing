#!/usr/bin/env python3
"""Materialize a direct in-grid edge-legality cache.

Every AI/reachability edge is identified by an integer origin and a bounded
velocity delta in [-12,12]^2.  For ordinary track grids, that finite domain is
small enough for a byte table: one direct indexed read replaces mixing and an
open-addressing probe chain.  Queries outside the dense domain retain the
existing exact hash cache.  A 64 MiB cap prevents the optimisation from
materially changing memory requirements on unusually large user tracks.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()

old = """\t\tstartZoneA = TrackGeometry.getToleranceExpandedShape(p);
\t\ttrackA = TrackGeometry.getToleranceExpandedShape(TrackGeometry.newPrefilledPath(track.getLeft(), track.getRight()));
\t\tbuildLegalRaster();
"""
new = """\t\tstartZoneA = TrackGeometry.getToleranceExpandedShape(p);
\t\ttrackA = TrackGeometry.getToleranceExpandedShape(TrackGeometry.newPrefilledPath(track.getLeft(), track.getRight()));
\t\tdenseEdgeLegalCache = DenseEdgeLegalCache.create(gameCols + 1, gameRows + 1,
\t\t\t\t64L << 20);
\t\tbuildLegalRaster();
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\tprivate final EdgeLegalCache\tedgeLegalCache\t\t= new EdgeLegalCache(1 << 16);

\tboolean isMoveLegalGeometryCached(final int x1, final int y1, final int x2, final int y2) {
\t\tfinal long packed = ((long) x1 & 0xFFFF) << 48 | ((long) y1 & 0xFFFF) << 32
\t\t\t\t| ((long) x2 & 0xFFFF) << 16 | (long) y2 & 0xFFFF;
\t\tfinal long key = mixEdgeKey(packed);
\t\tfinal byte cached = edgeLegalCache.get(key);
\t\tif (cached != 0)
\t\t\treturn cached == EdgeLegalCache.TRUE;
\t\tfinal boolean legal = isMoveLegalGeometry(x1, y1, x2, y2);
\t\tedgeLegalCache.put(key, legal);
\t\treturn legal;
\t}
"""
new = """\tprivate DenseEdgeLegalCache denseEdgeLegalCache;
\tprivate final EdgeLegalCache\tedgeLegalCache\t\t= new EdgeLegalCache(1 << 16);

\tboolean isMoveLegalGeometryCached(final int x1, final int y1, final int x2, final int y2) {
\t\tfinal DenseEdgeLegalCache dense = denseEdgeLegalCache;
\t\tfinal int denseIndex = dense == null ? -1 : dense.index(x1, y1, x2, y2);
\t\tif (denseIndex >= 0) {
\t\t\tfinal byte cached = dense.states[denseIndex];
\t\t\tif (cached != 0)
\t\t\t\treturn cached == DenseEdgeLegalCache.TRUE;
\t\t\tfinal boolean legal = isMoveLegalGeometry(x1, y1, x2, y2);
\t\t\tdense.states[denseIndex] = legal ? DenseEdgeLegalCache.TRUE
\t\t\t\t\t: DenseEdgeLegalCache.FALSE;
\t\t\treturn legal;
\t\t}
\t\tfinal long packed = ((long) x1 & 0xFFFF) << 48 | ((long) y1 & 0xFFFF) << 32
\t\t\t\t| ((long) x2 & 0xFFFF) << 16 | (long) y2 & 0xFFFF;
\t\tfinal long key = mixEdgeKey(packed);
\t\tfinal byte cached = edgeLegalCache.get(key);
\t\tif (cached != 0)
\t\t\treturn cached == EdgeLegalCache.TRUE;
\t\tfinal boolean legal = isMoveLegalGeometry(x1, y1, x2, y2);
\t\tedgeLegalCache.put(key, legal);
\t\treturn legal;
\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

anchor = """\t/** Open-addressed long-to-boolean map. A separate state byte means every
"""
dense = """\t/** Direct byte cache for in-grid, bounded-delta edges. */
\tstatic final class DenseEdgeLegalCache {
\t\tstatic final byte FALSE = 1;
\t\tstatic final byte TRUE = 2;
\t\tprivate static final int DELTA_SPAN = 2 * AI_MAX_SPEED + 1;
\t\tprivate static final int DELTAS = DELTA_SPAN * DELTA_SPAN;

\t\tfinal int width;
\t\tfinal int height;
\t\tfinal byte[] states;

\t\tprivate DenseEdgeLegalCache(final int width, final int height,
\t\t\t\tfinal int entries) {
\t\t\tthis.width = width;
\t\t\tthis.height = height;
\t\t\tstates = new byte[entries];
\t\t}

\t\tstatic DenseEdgeLegalCache create(final int width, final int height,
\t\t\t\tfinal long maxEntries) {
\t\t\tfinal long entries = (long) width * height * DELTAS;
\t\t\tif (width <= 0 || height <= 0 || entries <= 0 || entries > maxEntries
\t\t\t\t\t|| entries > Integer.MAX_VALUE)
\t\t\t\treturn null;
\t\t\treturn new DenseEdgeLegalCache(width, height, (int) entries);
\t\t}

\t\tint index(final int x1, final int y1, final int x2, final int y2) {
\t\t\tfinal int dx = x2 - x1, dy = y2 - y1;
\t\t\tif (x1 < 0 || y1 < 0 || x1 >= width || y1 >= height
\t\t\t\t\t|| dx < -AI_MAX_SPEED || dx > AI_MAX_SPEED
\t\t\t\t\t|| dy < -AI_MAX_SPEED || dy > AI_MAX_SPEED)
\t\t\t\treturn -1;
\t\t\treturn ((x1 * height + y1) * DELTA_SPAN + dx + AI_MAX_SPEED)
\t\t\t\t\t* DELTA_SPAN + dy + AI_MAX_SPEED;
\t\t}
\t}

\t/** Open-addressed long-to-boolean map. A separate state byte means every
"""
assert source.count(anchor) == 1, source.count(anchor)
source = source.replace(anchor, dense, 1)
race.write_text(source)

core = Path("tests/tr/logic/CoreTests.java")
tests = core.read_text()
old = """        testEdgeLegalCache();
        testPointContainmentCache();
"""
new = """        testEdgeLegalCache();
        testDenseEdgeLegalCache();
        testPointContainmentCache();
"""
assert tests.count(old) == 1, tests.count(old)
tests = tests.replace(old, new, 1)

anchor = """    private static void testPointContainmentCache() {
"""
method = """    private static void testDenseEdgeLegalCache() {
        final RaceGame.DenseEdgeLegalCache cache = RaceGame.DenseEdgeLegalCache.create(3, 4, 10_000);
        check(cache != null, "small dense edge cache was rejected");
        final int zero = cache.index(0, 0, 0, 0);
        final int max = cache.index(2, 3, 14, -9);
        final int min = cache.index(2, 3, -10, 15);
        check(zero >= 0 && max >= 0 && min >= 0, "bounded dense edge was rejected");
        check(zero != max && max != min && zero != min, "dense edge indices collided");
        cache.states[zero] = RaceGame.DenseEdgeLegalCache.FALSE;
        cache.states[max] = RaceGame.DenseEdgeLegalCache.TRUE;
        check(cache.states[zero] == RaceGame.DenseEdgeLegalCache.FALSE,
                "dense false verdict was lost");
        check(cache.states[max] == RaceGame.DenseEdgeLegalCache.TRUE,
                "dense true verdict was lost");
        check(cache.index(-1, 0, 0, 0) == -1, "negative origin entered dense cache");
        check(cache.index(3, 0, 3, 0) == -1, "wide origin entered dense cache");
        check(cache.index(0, 0, 13, 0) == -1, "overspeed delta entered dense cache");
        check(RaceGame.DenseEdgeLegalCache.create(500, 500, 1_000) == null,
                "dense cache ignored its memory cap");
    }

    private static void testPointContainmentCache() {
"""
assert tests.count(anchor) == 1, tests.count(anchor)
tests = tests.replace(anchor, method, 1)
core.write_text(tests)
print("materialized exact dense edge cache and unit tests")
