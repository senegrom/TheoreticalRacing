#!/usr/bin/env python3
"""Materialize adaptive geometry-cache sizing.

Batch races create a fresh RaceGame per seed but adopt the immutable reachability
memo after the first seed. Eagerly allocating the cold-build 2^18 point table
and 2^16 edge table on every warm race wastes roughly five MiB per seed. Start
both exact caches small, then reserve the historical capacities only on the
actual cold reverse-BFS path. Growth and reserve rehash with full key equality,
so behavior is unchanged.
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

old = """\t\tprivate void grow() {
\t\t\tif (keys.length == 1 << 30)
\t\t\t\tthrow new IllegalStateException("geometry cache is too large");
\t\t\tfinal long[] oldKeys = keys;
\t\t\tfinal byte[] oldStates = states;
\t\t\tallocate(keys.length << 1);
\t\t\tsize = 0;
\t\t\tfor (int i = 0; i < oldStates.length; i++) {
\t\t\t\tif (oldStates[i] == 0)
\t\t\t\t\tcontinue;
\t\t\t\tint slot = (int) oldKeys[i] & mask;
\t\t\t\twhile (states[slot] != 0)
\t\t\t\t\tslot = slot + 1 & mask;
\t\t\t\tkeys[slot] = oldKeys[i];
\t\t\t\tstates[slot] = oldStates[i];
\t\t\t\tsize++;
\t\t\t}
\t\t}
"""
new = """\t\tvoid ensureCapacity(final int minimumCapacity) {
\t\t\tif (minimumCapacity < 1 || minimumCapacity > 1 << 30)
\t\t\t\tthrow new IllegalArgumentException("invalid cache capacity");
\t\t\tint capacity = 4;
\t\t\twhile (capacity < minimumCapacity)
\t\t\t\tcapacity <<= 1;
\t\t\tif (capacity > keys.length)
\t\t\t\trehash(capacity);
\t\t}

\t\tprivate void grow() {
\t\t\tif (keys.length == 1 << 30)
\t\t\t\tthrow new IllegalStateException("geometry cache is too large");
\t\t\trehash(keys.length << 1);
\t\t}

\t\tprivate void rehash(final int capacity) {
\t\t\tfinal long[] oldKeys = keys;
\t\t\tfinal byte[] oldStates = states;
\t\t\tallocate(capacity);
\t\t\tsize = 0;
\t\t\tfor (int i = 0; i < oldStates.length; i++) {
\t\t\t\tif (oldStates[i] == 0)
\t\t\t\t\tcontinue;
\t\t\t\tint slot = (int) oldKeys[i] & mask;
\t\t\t\twhile (states[slot] != 0)
\t\t\t\t\tslot = slot + 1 & mask;
\t\t\t\tkeys[slot] = oldKeys[i];
\t\t\t\tstates[slot] = oldStates[i];
\t\t\t\tsize++;
\t\t\t}
\t\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\tprivate void grow() {
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
new = """\t\tvoid ensureCapacity(final int minimumCapacity) {
\t\t\tif (minimumCapacity < 1 || minimumCapacity > 1 << 30)
\t\t\t\tthrow new IllegalArgumentException("invalid cache capacity");
\t\t\tint capacity = 4;
\t\t\twhile (capacity < minimumCapacity)
\t\t\t\tcapacity <<= 1;
\t\t\tif (capacity > xKeys.length)
\t\t\t\trehash(capacity);
\t\t}

\t\tprivate void grow() {
\t\t\tif (xKeys.length == 1 << 30)
\t\t\t\tthrow new IllegalStateException("point cache is too large");
\t\t\trehash(xKeys.length << 1);
\t\t}

\t\tprivate void rehash(final int capacity) {
\t\t\tfinal long[] oldX = xKeys;
\t\t\tfinal long[] oldY = yKeys;
\t\t\tfinal byte[] oldStates = states;
\t\t\tallocate(capacity);
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
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

anchor = """\tfinal Reachability reach = new Reachability(this);
"""
method = """\t/** Reserve the proven cold-build capacities only when the reverse BFS
\t * actually runs. Memo/cache-hit races retain compact warm tables. */
\tvoid prepareGeometryCachesForReachability() {
\t\tedgeLegalCache.ensureCapacity(1 << 16);
\t\tpointContainmentCache.ensureCapacity(1 << 18);
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
old = """        cache.put(0L, true);
        check(cache.get(0L) == RaceGame.EdgeLegalCache.TRUE, "edge cache update failed");
        check(cache.get(123456789L) == 0, "edge cache false hit");
"""
new = """        cache.put(0L, true);
        check(cache.get(0L) == RaceGame.EdgeLegalCache.TRUE, "edge cache update failed");
        cache.ensureCapacity(1 << 16);
        check(cache.get(0L) == RaceGame.EdgeLegalCache.TRUE,
                "edge cache reserve lost an existing verdict");
        check(cache.get(123456789L) == 0, "edge cache false hit");
"""
assert tests.count(old) == 1, tests.count(old)
tests = tests.replace(old, new, 1)
old = """        cache.put(0L, 0L, true);
        check(cache.get(0L, 0L) == RaceGame.PointContainmentCache.TRUE,
                "point cache update failed");
        cache.clear();
"""
new = """        cache.put(0L, 0L, true);
        check(cache.get(0L, 0L) == RaceGame.PointContainmentCache.TRUE,
                "point cache update failed");
        cache.ensureCapacity(1 << 16);
        check(cache.get(0L, 0L) == RaceGame.PointContainmentCache.TRUE,
                "point cache reserve lost an existing verdict");
        cache.clear();
"""
assert tests.count(old) == 1, tests.count(old)
tests = tests.replace(old, new, 1)
core.write_text(tests)
print("materialized adaptive cold/warm geometry caches")
