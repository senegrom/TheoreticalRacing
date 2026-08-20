#!/usr/bin/env python3
"""Materialize Round 156's shared exact dense edge cache.

Round 150 introduced a collision-free direct byte table for in-grid geometry
edges, but every RaceGame in an auto batch still allocated and repopulated that
same table. Consecutive races of the same geometry now reuse one exact table
from a bounded LRU pool. Interactive games remain private.

All table entries are still produced by the unchanged exact geometry predicate.
Concurrent duplicate writes are idempotent byte writes of the same verdict; a
stale zero can only cause an exact recomputation.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()

old_build = """\t\tstartZoneA = TrackGeometry.getToleranceExpandedShape(p);
\t\ttrackA = TrackGeometry.getToleranceExpandedShape(TrackGeometry.newPrefilledPath(track.getLeft(), track.getRight()));
\t\tdenseEdgeLegalCache = DenseEdgeLegalCache.create(gameCols + 1, gameRows + 1,
\t\t\t\t64L << 20);
\t\tbuildLegalRaster();
"""
new_build = """\t\tstartZoneA = TrackGeometry.getToleranceExpandedShape(p);
\t\ttrackA = TrackGeometry.getToleranceExpandedShape(TrackGeometry.newPrefilledPath(track.getLeft(), track.getRight()));
\t\tfinal String denseKey = autoMode ? reach.geometryCacheKey() : null;
\t\tdenseEdgeLegalCache = denseKey == null
\t\t\t\t? DenseEdgeLegalCache.create(gameCols + 1, gameRows + 1, 64L << 20)
\t\t\t\t: DenseEdgeLegalCache.shared(denseKey, gameCols + 1, gameRows + 1,
\t\t\t\t\t\t64L << 20, 128L << 20);
\t\tbuildLegalRaster();
"""
assert source.count(old_build) == 1, source.count(old_build)
source = source.replace(old_build, new_build, 1)

old_fields = """\t\tprivate static final int DELTA_SPAN = 2 * AI_MAX_SPEED + 1;
\t\tprivate static final int DELTAS = DELTA_SPAN * DELTA_SPAN;

\t\tfinal int width;
"""
new_fields = """\t\tprivate static final int DELTA_SPAN = 2 * AI_MAX_SPEED + 1;
\t\tprivate static final int DELTAS = DELTA_SPAN * DELTA_SPAN;
\t\tprivate static final java.util.LinkedHashMap<String, DenseEdgeLegalCache> SHARED =
\t\t\t\tnew java.util.LinkedHashMap<>(16, 0.75f, true);
\t\tprivate static long sharedEntries;

\t\tfinal int width;
"""
assert source.count(old_fields) == 1, source.count(old_fields)
source = source.replace(old_fields, new_fields, 1)

old_create = """\t\tstatic DenseEdgeLegalCache create(final int width, final int height,
\t\t\t\tfinal long maxEntries) {
\t\t\tfinal long entries = (long) width * height * DELTAS;
\t\t\tif (width <= 0 || height <= 0 || entries <= 0 || entries > maxEntries
\t\t\t\t\t|| entries > Integer.MAX_VALUE)
\t\t\t\treturn null;
\t\t\treturn new DenseEdgeLegalCache(width, height, (int) entries);
\t\t}

\t\tint index(final int x1, final int y1, final int x2, final int y2) {
"""
new_create = """\t\tstatic DenseEdgeLegalCache create(final int width, final int height,
\t\t\t\tfinal long maxEntries) {
\t\t\tfinal long entries = (long) width * height * DELTAS;
\t\t\tif (width <= 0 || height <= 0 || entries <= 0 || entries > maxEntries
\t\t\t\t\t|| entries > Integer.MAX_VALUE)
\t\t\t\treturn null;
\t\t\treturn new DenseEdgeLegalCache(width, height, (int) entries);
\t\t}

\t\t/** Reuse an exact table for the same immutable track geometry. The pool
\t\t * is access-ordered and measured in byte-table entries (one byte each).
\t\t * A table larger than the pool cap remains a private exact table. */
\t\tstatic synchronized DenseEdgeLegalCache shared(final String key,
\t\t\t\tfinal int width, final int height, final long maxEntries,
\t\t\t\tfinal long maxPoolEntries) {
\t\t\tif (key == null)
\t\t\t\treturn create(width, height, maxEntries);
\t\t\tfinal DenseEdgeLegalCache existing = SHARED.get(key);
\t\t\tif (existing != null && existing.width == width && existing.height == height)
\t\t\t\treturn existing;
\t\t\tif (existing != null) {
\t\t\t\tSHARED.remove(key);
\t\t\t\tsharedEntries -= existing.states.length;
\t\t\t}
\t\t\tfinal DenseEdgeLegalCache created = create(width, height, maxEntries);
\t\t\tif (created == null || created.states.length > maxPoolEntries)
\t\t\t\treturn created;
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
"""
assert source.count(old_create) == 1, source.count(old_create)
source = source.replace(old_create, new_create, 1)
assert source.count("DenseEdgeLegalCache shared(final String key") == 1
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
assert "String geometryCacheKey()" not in text
reach.write_text(text.replace(anchor, method, 1))

core = Path("tests/tr/logic/CoreTests.java")
tests = core.read_text()
old_call = """        testEdgeLegalCache();
        testDenseEdgeLegalCache();
        testPointContainmentCache();
"""
new_call = """        testEdgeLegalCache();
        testDenseEdgeLegalCache();
        testSharedDenseEdgeLegalCache();
        testPointContainmentCache();
"""
assert tests.count(old_call) == 1, tests.count(old_call)
tests = tests.replace(old_call, new_call, 1)

test_anchor = """    private static void testPointContainmentCache() {
"""
test_method = """    private static void testSharedDenseEdgeLegalCache() {
        final RaceGame.DenseEdgeLegalCache first = RaceGame.DenseEdgeLegalCache.shared(
                "core-test-track", 3, 4, 10_000, 20_000);
        final RaceGame.DenseEdgeLegalCache second = RaceGame.DenseEdgeLegalCache.shared(
                "core-test-track", 3, 4, 10_000, 20_000);
        check(first != null && first == second, "shared dense edge cache was not reused");

        final int zero = first.index(0, 0, 0, 0);
        final int max = first.index(2, 3, 14, -9);
        first.states[zero] = RaceGame.DenseEdgeLegalCache.FALSE;
        first.states[max] = RaceGame.DenseEdgeLegalCache.TRUE;
        check(second.states[zero] == RaceGame.DenseEdgeLegalCache.FALSE,
                "shared dense false verdict was lost");
        check(second.states[max] == RaceGame.DenseEdgeLegalCache.TRUE,
                "shared dense true verdict was lost");

        final RaceGame.DenseEdgeLegalCache replacement = RaceGame.DenseEdgeLegalCache.shared(
                "core-test-track", 4, 4, 10_000, 20_000);
        check(replacement != null && replacement != first,
                "dimension change retained an incompatible shared table");
        check(RaceGame.DenseEdgeLegalCache.shared(
                "core-test-track", 4, 4, 10_000, 20_000) == replacement,
                "replacement shared table was not reused");

        final RaceGame.DenseEdgeLegalCache oversized = RaceGame.DenseEdgeLegalCache.shared(
                "core-test-private", 3, 4, 10_000, 1_000);
        check(oversized != null, "oversized shared request lost its private fallback");
        check(RaceGame.DenseEdgeLegalCache.shared(
                "core-test-private", 3, 4, 10_000, 1_000) != oversized,
                "table larger than the pool cap was retained globally");
    }

    private static void testPointContainmentCache() {
"""
assert tests.count(test_anchor) == 1, tests.count(test_anchor)
assert "testSharedDenseEdgeLegalCache" not in tests
tests = tests.replace(test_anchor, test_method, 1)
core.write_text(tests)

print("materialized shared exact dense edge cache")
