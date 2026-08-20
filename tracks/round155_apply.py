#!/usr/bin/env python3
"""Materialize a shared direct in-grid edge-legality cache.

The direct table is the exact Round-150 domain: integer origin plus bounded
velocity delta. In auto batches, consecutive RaceGame instances for the same
geometry now reuse one table from a 128 MiB LRU pool instead of allocating and
repopulating it per seed. The geometry key is the same SHA-256-derived path used
by the reachability cache. Interactive games retain private tables. All stored
verdicts still come from the unchanged exact geometry predicate.
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
\t\tfinal String denseKey = autoMode ? reach.geometryCacheKey() : null;
\t\tdenseEdgeLegalCache = denseKey == null
\t\t\t\t? DenseEdgeLegalCache.create(gameCols + 1, gameRows + 1, 64L << 20)
\t\t\t\t: DenseEdgeLegalCache.shared(denseKey, gameCols + 1, gameRows + 1,
\t\t\t\t\t\t64L << 20, 128L << 20);
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
dense = """\t/** Direct byte cache for in-grid, bounded-delta edges. Auto batches
\t * share exact tables by the reachability geometry key through a bounded LRU. */
\tstatic final class DenseEdgeLegalCache {
\t\tstatic final byte FALSE = 1;
\t\tstatic final byte TRUE = 2;
\t\tprivate static final int DELTA_SPAN = 2 * AI_MAX_SPEED + 1;
\t\tprivate static final int DELTAS = DELTA_SPAN * DELTA_SPAN;
\t\tprivate static final java.util.LinkedHashMap<String, DenseEdgeLegalCache> SHARED =
\t\t\t\tnew java.util.LinkedHashMap<>(16, 0.75f, true);
\t\tprivate static long sharedEntries;

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

\t\tstatic synchronized DenseEdgeLegalCache shared(final String key,
\t\t\t\tfinal int width, final int height, final long maxEntries,
\t\t\t\tfinal long maxPoolEntries) {
\t\t\tfinal DenseEdgeLegalCache existing = SHARED.get(key);
\t\t\tif (existing != null && existing.width == width && existing.height == height)
\t\t\t\treturn existing;
\t\t\tif (existing != null) {
\t\t\t\tSHARED.remove(key);
\t\t\t\tsharedEntries -= existing.states.length;
\t\t\t}
\t\t\tfinal DenseEdgeLegalCache created = create(width, height, maxEntries);
\t\t\tif (created == null)
\t\t\t\treturn null;
\t\t\twhile (!SHARED.isEmpty()
\t\t\t\t\t&& sharedEntries + created.states.length > maxPoolEntries) {
\t\t\t\tfinal java.util.Iterator<java.util.Map.Entry<String, DenseEdgeLegalCache>> it =
\t\t\t\t\t\tSHARED.entrySet().iterator();
\t\t\t\tfinal DenseEdgeLegalCache evicted = it.next().getValue();
\t\t\t\tit.remove();
\t\t\t\tsharedEntries -= evicted.states.length;
\t\t\t}
\t\t\tSHARED.put(key, created);
\t\t\tsharedEntries += created.states.length;
\t\t\treturn created;
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

reach = Path("src/tr/logic/Reachability.java")
text = reach.read_text()
anchor = """\t/** Load turns + legal-alive from the geometry-keyed cache and re-derive
"""
method = """\t/** Stable geometry identity shared with the disk/memo reachability cache. */
\tString geometryCacheKey() {
\t\tfinal Path path = reachCachePath();
\t\treturn path == null ? null : path.toString();
\t}

\t/** Load turns + legal-alive from the geometry-keyed cache and re-derive
"""
assert text.count(anchor) == 1, text.count(anchor)
reach.write_text(text.replace(anchor, method, 1))

core = Path("tests/tr/logic/CoreTests.java")
tests = core.read_text()
old = """        testEdgeLegalCache();
        testPointContainmentCache();
"""
new = """        testEdgeLegalCache();
        testSharedDenseEdgeLegalCache();
        testPointContainmentCache();
"""
assert tests.count(old) == 1, tests.count(old)
tests = tests.replace(old, new, 1)

anchor = """    private static void testPointContainmentCache() {
"""
method = """    private static void testSharedDenseEdgeLegalCache() {
        final RaceGame.DenseEdgeLegalCache first = RaceGame.DenseEdgeLegalCache.shared(
                "core-test-track", 3, 4, 10_000, 20_000);
        final RaceGame.DenseEdgeLegalCache second = RaceGame.DenseEdgeLegalCache.shared(
                "core-test-track", 3, 4, 10_000, 20_000);
        check(first != null && first == second, "shared dense edge cache was not reused");
        final int zero = first.index(0, 0, 0, 0);
        final int max = first.index(2, 3, 14, -9);
        final int min = first.index(2, 3, -10, 15);
        check(zero >= 0 && max >= 0 && min >= 0, "bounded dense edge was rejected");
        check(zero != max && max != min && zero != min, "dense edge indices collided");
        first.states[zero] = RaceGame.DenseEdgeLegalCache.FALSE;
        first.states[max] = RaceGame.DenseEdgeLegalCache.TRUE;
        check(second.states[zero] == RaceGame.DenseEdgeLegalCache.FALSE,
                "shared dense false verdict was lost");
        check(second.states[max] == RaceGame.DenseEdgeLegalCache.TRUE,
                "shared dense true verdict was lost");
        check(first.index(-1, 0, 0, 0) == -1, "negative origin entered dense cache");
        check(first.index(3, 0, 3, 0) == -1, "wide origin entered dense cache");
        check(first.index(0, 0, 13, 0) == -1, "overspeed delta entered dense cache");
        check(RaceGame.DenseEdgeLegalCache.create(500, 500, 1_000) == null,
                "dense cache ignored its per-track memory cap");
    }

    private static void testPointContainmentCache() {
"""
assert tests.count(anchor) == 1, tests.count(anchor)
tests = tests.replace(anchor, method, 1)
core.write_text(tests)
print("materialized shared exact dense edge cache and unit tests")
