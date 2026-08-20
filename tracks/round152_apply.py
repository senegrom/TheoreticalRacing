#!/usr/bin/env python3
"""Materialize adaptive cold-build versus warm-race geometry caches.

Batch racing creates a fresh RaceGame for every seed but adopts immutable
reachability products after the first seed. The historical 2^18 point table and
2^16 edge table are therefore needed only when a real cold reverse BFS runs.
Warm memo/cache-hit races start with compact exact tables. Immediately before a
cold BFS, both still-empty tables reserve the historical capacities; no entry
migration or semantic change is involved.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()

old = "\tprivate final PointContainmentCache pointContainmentCache = new PointContainmentCache(1 << 18);\n"
new = "\tprivate final PointContainmentCache pointContainmentCache = new PointContainmentCache(1 << 11);\n"
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = "\tprivate final EdgeLegalCache\tedgeLegalCache\t\t= new EdgeLegalCache(1 << 16);\n"
new = "\tprivate final EdgeLegalCache\tedgeLegalCache\t\t= new EdgeLegalCache(1 << 11);\n"
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

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

\t\tbyte get(final long xKey, final long yKey) {
"""
assert source.count(point_anchor) == 1, source.count(point_anchor)
source = source.replace(point_anchor, point_new, 1)

anchor = """\tfinal Reachability reach = new Reachability(this);
"""
method = """\t/** Reserve the proven cold-build capacities only when the reverse BFS
\t * actually runs. Memo/cache-hit races retain compact warm tables. */
\tvoid prepareGeometryCachesForReachability() {
\t\tedgeLegalCache.reserveEmpty(1 << 16);
\t\tpointContainmentCache.reserveEmpty(1 << 18);
\t}

\tfinal Reachability reach = new Reachability(this);
"""
assert source.count(anchor) == 1, source.count(anchor)
source = source.replace(anchor, method, 1)
race.write_text(source)

reach = Path("src/tr/logic/Reachability.java")
text = reach.read_text()
old = """\t\t\t\tif (!adoptMemo(memoKey)) {
\t\t\t\t\tif (!tryLoadReachabilityCache())
\t\t\t\t\t\tcomputeReachability();
\t\t\t\t\tpublishMemo(memoKey);
\t\t\t\t}
"""
new = """\t\t\t\tif (!adoptMemo(memoKey)) {
\t\t\t\t\tif (!tryLoadReachabilityCache()) {
\t\t\t\t\t\tgame.prepareGeometryCachesForReachability();
\t\t\t\t\t\tcomputeReachability();
\t\t\t\t\t}
\t\t\t\t\tpublishMemo(memoKey);
\t\t\t\t}
"""
assert text.count(old) == 1, text.count(old)
reach.write_text(text.replace(old, new, 1))

core = Path("tests/tr/logic/CoreTests.java")
tests = core.read_text()
old = """        final RaceGame.EdgeLegalCache cache = new RaceGame.EdgeLegalCache(1);
        check(cache.get(0L) == 0, "fresh edge cache should miss");
"""
new = """        final RaceGame.EdgeLegalCache cache = new RaceGame.EdgeLegalCache(1);
        cache.reserveEmpty(1 << 10);
        check(cache.get(0L) == 0, "fresh edge cache should miss");
"""
assert tests.count(old) == 1, tests.count(old)
tests = tests.replace(old, new, 1)
old = """        final RaceGame.PointContainmentCache cache = new RaceGame.PointContainmentCache(1);
        check(cache.get(0L, 0L) == 0, "fresh point cache should miss");
"""
new = """        final RaceGame.PointContainmentCache cache = new RaceGame.PointContainmentCache(1);
        cache.reserveEmpty(1 << 10);
        check(cache.get(0L, 0L) == 0, "fresh point cache should miss");
"""
assert tests.count(old) == 1, tests.count(old)
tests = tests.replace(old, new, 1)
core.write_text(tests)
print("materialized adaptive cold/warm geometry caches")
