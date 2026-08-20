#!/usr/bin/env python3
"""Materialize a bounded exact cache for finish-line edge intersections.

The same simulated edge is tested for a finish many times.  A direct-mapped
primitive cache stores the exact Line2D verdict.  Full mixed-key equality is
required for a hit; collisions overwrite and merely force recomputation, so
capacity cannot affect behaviour.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()

old = """\tprivate void buildLegalRaster() {
\t\tpointContainmentCache.clear();
"""
new = """\tprivate void buildLegalRaster() {
\t\tpointContainmentCache.clear();
\t\tfinishCrossCache.clear();
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

anchor = """\t/** Primitive exact-double-pair to boolean cache for the residual legality
"""
cache = """\t/** Bounded direct-mapped cache for exact finish-line intersections.
\t *  A replacement loses only a cached result; key equality is required for
\t *  every hit, so collisions can never change a verdict. */
\tstatic final class FinishCrossCache {
\t\tstatic final byte FALSE = 1;
\t\tstatic final byte TRUE = 2;
\t\tprivate final long[] keys;
\t\tprivate final byte[] states;
\t\tprivate final int mask;

\t\tFinishCrossCache(final int capacity) {
\t\t\tif (capacity < 1 || Integer.bitCount(capacity) != 1)
\t\t\t\tthrow new IllegalArgumentException("finish cache capacity must be a power of two");
\t\t\tkeys = new long[capacity];
\t\t\tstates = new byte[capacity];
\t\t\tmask = capacity - 1;
\t\t}

\t\tbyte get(final long key) {
\t\t\tfinal int slot = (int) key & mask;
\t\t\treturn states[slot] != 0 && keys[slot] == key ? states[slot] : 0;
\t\t}

\t\tvoid put(final long key, final boolean value) {
\t\t\tfinal int slot = (int) key & mask;
\t\t\tkeys[slot] = key;
\t\t\tstates[slot] = value ? TRUE : FALSE;
\t\t}

\t\tvoid clear() {
\t\t\tjava.util.Arrays.fill(states, (byte) 0);
\t\t}
\t}

\tprivate final FinishCrossCache finishCrossCache = new FinishCrossCache(1 << 16);

\t/** Primitive exact-double-pair to boolean cache for the residual legality
"""
assert source.count(anchor) == 1, source.count(anchor)
source = source.replace(anchor, cache, 1)

old = """\tboolean crossesFinish(final double x1, final double y1, final double x2, final double y2) {
\t\tif (!Line2D.linesIntersect(finishLine.getX1(), finishLine.getY1(), finishLine.getX2(), finishLine.getY2(), x1, y1, x2, y2))
\t\t\treturn false;
\t\t// Only a forward crossing counts (move heads in the racing direction).
\t\t// A zero-length or backward move across the line is not a finish.
\t\treturn (x2 - x1) * finishFwdX + (y2 - y1) * finishFwdY > 0;
\t}
"""
new = """\tboolean crossesFinish(final int x1, final int y1, final int x2, final int y2) {
\t\tfinal long packed = ((long) x1 & 0xFFFF) << 48 | ((long) y1 & 0xFFFF) << 32
\t\t\t\t| ((long) x2 & 0xFFFF) << 16 | (long) y2 & 0xFFFF;
\t\tfinal long key = mixEdgeKey(packed);
\t\tbyte cached = finishCrossCache.get(key);
\t\tif (cached == 0) {
\t\t\tfinal boolean intersects = Line2D.linesIntersect(finishLine.getX1(), finishLine.getY1(),
\t\t\t\t\tfinishLine.getX2(), finishLine.getY2(), x1, y1, x2, y2);
\t\t\tfinishCrossCache.put(key, intersects);
\t\t\tcached = intersects ? FinishCrossCache.TRUE : FinishCrossCache.FALSE;
\t\t}
\t\tif (cached == FinishCrossCache.FALSE)
\t\t\treturn false;
\t\t// Preserve the existing forward-only finish rule exactly.
\t\treturn (x2 - x1) * finishFwdX + (y2 - y1) * finishFwdY > 0;
\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)
race.write_text(source)
print("materialized bounded exact finish-edge cache")
