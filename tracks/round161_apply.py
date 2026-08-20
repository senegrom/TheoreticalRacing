#!/usr/bin/env python3
"""Materialize compact warm-race geometry fallback caches.

Round 156/158 share the dominant same-track geometry products, but every new
RaceGame still allocates the historical 2^18 point-containment table and 2^16
edge fallback table before it knows whether a cold reverse BFS is needed. Warm
memo/cache-hit races now start with compact exact tables. Immediately before an
actual cold BFS, both still-empty tables reserve their historical capacities.

No cache key, verdict, probing rule or AI policy changes.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()

old_point = "\tprivate final PointContainmentCache pointContainmentCache = new PointContainmentCache(1 << 18);\n"
new_point = "\tprivate final PointContainmentCache pointContainmentCache = new PointContainmentCache(1 << 11);\n"
assert source.count(old_point) == 1, source.count(old_point)
source = source.replace(old_point, new_point, 1)

old_edge = "\tprivate final EdgeLegalCache\tedgeLegalCache\t\t= new EdgeLegalCache(1 << 16);\n"
new_edge = "\tprivate final EdgeLegalCache\tedgeLegalCache\t\t= new EdgeLegalCache(1 << 11);\n"
assert source.count(old_edge) == 1, source.count(old_edge)
source = source.replace(old_edge, new_edge, 1)

edge_anchor = """\t\tEdgeLegalCache(final int initialCapacity) {
\t\t\tif (initialCapacity < 1 || initialCapacity > 1 << 30)
\t\t\t\tthrow new IllegalArgumentException("invalid cache capacity");
\t\t\tint capacity = 4;
\t\t\twhile (capacity < initialCapacity)
\t\t\t\tcapacity <<= 1;
\t\t\tallocate(capacity);
\t\t}

\t\tbyte get(final long key) {
"""
edge_new = """\t\tEdgeLegalCache(final int initialCapacity) {
\t\t\tif (initialCapacity < 1 || initialCapacity > 1 << 30)
\t\t\t\tthrow new IllegalArgumentException("invalid cache capacity");
\t\t\tint capacity = 4;
\t\t\twhile (capacity < initialCapacity)
\t\t\t\tcapacity <<= 1;
\t\t\tallocate(capacity);
\t\t}

\t\tvoid reserveEmpty(final int minimumCapacity) {
\t\t\tif (size != 0)
\t\t\t\tthrow new IllegalStateException("edge cache reserve after use");
\t\t\tif (minimumCapacity < 1 || minimumCapacity > 1 << 30)
\t\t\t\tthrow new IllegalArgumentException("invalid cache capacity");
\t\t\tint capacity = 4;
\t\t\twhile (capacity < minimumCapacity)
\t\t\t\tcapacity <<= 1;
\t\t\tif (capacity > keys.length)
\t\t\t\tallocate(capacity);
\t\t}

\t\tint capacityForTests() {
\t\t\treturn keys.length;
\t\t}

\t\tbyte get(final long key) {
"""
assert source.count(edge_anchor) == 1, source.count(edge_anchor)
source = source.replace(edge_anchor, edge_new, 1)

point_anchor = """\t\tPointContainmentCache(final int initialCapacity) {
\t\t\tif (initialCapacity < 1 || initialCapacity > 1 << 30)
\t\t\t\tthrow new IllegalArgumentException("invalid cache capacity");
\t\t\tint capacity = 4;
\t\t\twhile (capacity < initialCapacity)
\t\t\t\tcapacity <<= 1;
\t\t\tallocate(capacity);
\t\t}

\t\tbyte get(final long xKey, final long yKey) {
"""
point_new = """\t\tPointContainmentCache(final int initialCapacity) {
\t\t\tif (initialCapacity < 1 || initialCapacity > 1 << 30)
\t\t\t\tthrow new IllegalArgumentException("invalid cache capacity");
\t\t\tint capacity = 4;
\t\t\twhile (capacity < initialCapacity)
\t\t\t\tcapacity <<= 1;
\t\t\tallocate(capacity);
\t\t}

\t\tvoid reserveEmpty(final int minimumCapacity) {
\t\t\tif (size != 0)
\t\t\t\tthrow new IllegalStateException("point cache reserve after use");
\t\t\tif (minimumCapacity < 1 || minimumCapacity > 1 << 30)
\t\t\t\tthrow new IllegalArgumentException("invalid cache capacity");
\t\t\tint capacity = 4;
\t\t\twhile (capacity < minimumCapacity)
\t\t\t\tcapacity <<= 1;
\t\t\tif (capacity > xKeys.length)
\t\t\t\tallocate(capacity);
\t\t}

\t\tint capacityForTests() {
\t\t\treturn xKeys.length;
\t\t}

\t\tbyte get(final long xKey, final long yKey) {
"""
assert source.count(point_anchor) == 1, source.count(point_anchor)
source = source.replace(point_anchor, point_new, 1)

reach_anchor = """\tfinal Reachability reach = new Reachability(this);
"""
reach_method = """\t/** Reserve the proven cold-build fallback capacities only when the
\t * reverse BFS really runs. Warm memo/cache-hit races keep compact tables. */
\tvoid prepareGeometryFallbackCachesForReachability() {
\t\tedgeLegalCache.reserveEmpty(1 << 16);
\t\tpointContainmentCache.reserveEmpty(1 << 18);
\t}

\tfinal Reachability reach = new Reachability(this);
"""
assert source.count(reach_anchor) == 1, source.count(reach_anchor)
assert "prepareGeometryFallbackCachesForReachability" not in source
source = source.replace(reach_anchor, reach_method, 1)
race.write_text(source)

reach = Path("src/tr/logic/Reachability.java")
text = reach.read_text()
old_compute = """\t\t\t\tif (!adoptMemo(memoKey)) {
\t\t\t\t\tif (!tryLoadReachabilityCache())
\t\t\t\t\t\tcomputeReachability();
\t\t\t\t\tpublishMemo(memoKey);
\t\t\t\t}
"""
new_compute = """\t\t\t\tif (!adoptMemo(memoKey)) {
\t\t\t\t\tif (!tryLoadReachabilityCache()) {
\t\t\t\t\t\tgame.prepareGeometryFallbackCachesForReachability();
\t\t\t\t\t\tcomputeReachability();
\t\t\t\t\t}
\t\t\t\t\tpublishMemo(memoKey);
\t\t\t\t}
"""
assert text.count(old_compute) == 1, text.count(old_compute)
reach.write_text(text.replace(old_compute, new_compute, 1))

core = Path("tests/tr/logic/CoreTests.java")
tests = core.read_text()
old_edge_test = """        final RaceGame.EdgeLegalCache cache = new RaceGame.EdgeLegalCache(1);
        check(cache.get(0L) == 0, "fresh edge cache should miss");
"""
new_edge_test = """        final RaceGame.EdgeLegalCache cache = new RaceGame.EdgeLegalCache(1);
        final int edgeInitial = cache.capacityForTests();
        cache.reserveEmpty(1 << 10);
        check(edgeInitial < cache.capacityForTests()
                        && cache.capacityForTests() >= 1 << 10,
                "edge cache reserve did not grow an empty table");
        check(cache.get(0L) == 0, "fresh edge cache should miss");
"""
assert tests.count(old_edge_test) == 1, tests.count(old_edge_test)
tests = tests.replace(old_edge_test, new_edge_test, 1)

old_point_test = """        final RaceGame.PointContainmentCache cache = new RaceGame.PointContainmentCache(1);
        check(cache.get(0L, 0L) == 0, "fresh point cache should miss");
"""
new_point_test = """        final RaceGame.PointContainmentCache cache = new RaceGame.PointContainmentCache(1);
        final int pointInitial = cache.capacityForTests();
        cache.reserveEmpty(1 << 10);
        check(pointInitial < cache.capacityForTests()
                        && cache.capacityForTests() >= 1 << 10,
                "point cache reserve did not grow an empty table");
        check(cache.get(0L, 0L) == 0, "fresh point cache should miss");
"""
assert tests.count(old_point_test) == 1, tests.count(old_point_test)
tests = tests.replace(old_point_test, new_point_test, 1)
core.write_text(tests)

print("materialized compact warm geometry fallback caches")
