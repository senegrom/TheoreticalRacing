#!/usr/bin/env python3
"""Keep warm-race point caches compact; reserve cold-BFS capacity on demand."""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()

old = '''\tprivate final ThreadLocal<PointContainmentCache> pointContainmentCaches =
\t\t\tThreadLocal.withInitial(() -> new PointContainmentCache(1 << 18));

\tvoid clearPointContainmentCacheForCurrentThread() {
'''
new = '''\tprivate final ThreadLocal<PointContainmentCache> pointContainmentCaches =
\t\t\tThreadLocal.withInitial(() -> new PointContainmentCache(1 << 11));

\t/** Warm same-track races normally need only a small residual point table.
\t * A real cold reverse BFS reserves the historical capacity on its own
\t * worker thread immediately before the first exact geometry scan. */
\tvoid preparePointContainmentCacheForReachability() {
\t\tpointContainmentCaches.get().reserveEmpty(1 << 18);
\t}

\tvoid clearPointContainmentCacheForCurrentThread() {
'''
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = '''\t\tPointContainmentCache(final int initialCapacity) {
\t\t\tif (initialCapacity < 1 || initialCapacity > 1 << 30)
\t\t\t\tthrow new IllegalArgumentException("invalid cache capacity");
\t\t\tint capacity = 4;
\t\t\twhile (capacity < initialCapacity)
\t\t\t\tcapacity <<= 1;
\t\t\tallocate(capacity);
\t\t}

\t\tbyte get(final long xKey, final long yKey) {
'''
new = '''\t\tPointContainmentCache(final int initialCapacity) {
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
'''
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)
race.write_text(source)

reach = Path("src/tr/logic/Reachability.java")
source = reach.read_text()
old = '''\t\t\t\tif (!adoptMemo(memoKey)) {
\t\t\t\t\tif (!tryLoadReachabilityCache())
\t\t\t\t\t\tcomputeReachability();
\t\t\t\t\tpublishMemo(memoKey);
\t\t\t\t}
'''
new = '''\t\t\t\tif (!adoptMemo(memoKey)) {
\t\t\t\t\tif (!tryLoadReachabilityCache()) {
\t\t\t\t\t\tgame.preparePointContainmentCacheForReachability();
\t\t\t\t\t\tcomputeReachability();
\t\t\t\t\t}
\t\t\t\t\tpublishMemo(memoKey);
\t\t\t\t}
'''
assert source.count(old) == 1, source.count(old)
reach.write_text(source.replace(old, new, 1))
print("materialized adaptive warm/cold point containment caches")
