#!/usr/bin/env python3
"""Materialize shared immutable legality rasters for same-track auto batches.

The unit and RES=4 legality rasters are exact, deterministic products of track
geometry and are never mutated after construction. Every seed currently rebuilds
both arrays. Consecutive auto RaceGames can therefore adopt one exact raster pair
from a bounded LRU pool; interactive games remain private.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()

old_fields = """\tprivate byte[] legalRaster;
\tprivate int rasterH;

\tprivate void buildLegalRaster() {
"""
new_fields = """\tprivate byte[] legalRaster;
\tprivate int rasterH;

\t/** Immutable exact raster pairs shared only by auto games carrying the same
\t * geometry key. One entry is one byte, so the access-ordered pool is capped
\t * at 64 MiB plus small object overhead. */
\tprivate static final long RASTER_MEMO_MAX_BYTES = 64L << 20;
\tprivate static final java.util.LinkedHashMap<String, RasterMaps> RASTER_MEMO =
\t\t\tnew java.util.LinkedHashMap<>(16, 0.75f, true);
\tprivate static long rasterMemoBytes;

\tstatic final class RasterMaps {
\t\tfinal byte[] unit;
\t\tfinal byte[] sub;
\t\tfinal int unitW;
\t\tfinal int unitH;
\t\tfinal int subW;
\t\tfinal int subH;
\t\tfinal long byteCount;

\t\tRasterMaps(final byte[] unit, final int unitW, final int unitH,
\t\t\t\tfinal byte[] sub, final int subW, final int subH) {
\t\t\tif (unit == null || sub == null || unitW <= 0 || unitH <= 0
\t\t\t\t\t|| subW != unitW * SUB_RES || subH != unitH * SUB_RES
\t\t\t\t\t|| (long) unitW * unitH != unit.length
\t\t\t\t\t|| (long) subW * subH != sub.length)
\t\t\t\tthrow new IllegalArgumentException("invalid legality rasters");
\t\t\tthis.unit = unit;
\t\t\tthis.sub = sub;
\t\t\tthis.unitW = unitW;
\t\t\tthis.unitH = unitH;
\t\t\tthis.subW = subW;
\t\t\tthis.subH = subH;
\t\t\tbyteCount = (long) unit.length + sub.length;
\t\t}
\t}

\tstatic synchronized RasterMaps findRasterMaps(final String key,
\t\t\tfinal int unitW, final int unitH) {
\t\tif (key == null)
\t\t\treturn null;
\t\tfinal RasterMaps maps = RASTER_MEMO.get(key);
\t\treturn maps != null && maps.unitW == unitW && maps.unitH == unitH
\t\t\t\t? maps : null;
\t}

\tstatic synchronized RasterMaps publishRasterMaps(final String key,
\t\t\tfinal byte[] unit, final int unitW, final int unitH,
\t\t\tfinal byte[] sub, final int subW, final int subH,
\t\t\tfinal long maxBytes) {
\t\tfinal RasterMaps created = new RasterMaps(unit, unitW, unitH,
\t\t\t\tsub, subW, subH);
\t\tif (key == null || maxBytes < 1 || created.byteCount > maxBytes)
\t\t\treturn created;
\t\tfinal RasterMaps existing = RASTER_MEMO.get(key);
\t\tif (existing != null && existing.unitW == unitW && existing.unitH == unitH)
\t\t\treturn existing;
\t\tif (existing != null) {
\t\t\tRASTER_MEMO.remove(key);
\t\t\trasterMemoBytes -= existing.byteCount;
\t\t}
\t\twhile (!RASTER_MEMO.isEmpty()
\t\t\t\t&& rasterMemoBytes + created.byteCount > maxBytes) {
\t\t\tfinal java.util.Iterator<java.util.Map.Entry<String, RasterMaps>> it =
\t\t\t\t\tRASTER_MEMO.entrySet().iterator();
\t\t\tfinal RasterMaps evicted = it.next().getValue();
\t\t\tit.remove();
\t\t\trasterMemoBytes -= evicted.byteCount;
\t\t}
\t\tRASTER_MEMO.put(key, created);
\t\trasterMemoBytes += created.byteCount;
\t\treturn created;
\t}

\tstatic synchronized void clearRasterMemoForTests() {
\t\tRASTER_MEMO.clear();
\t\trasterMemoBytes = 0;
\t}

\tprivate void buildLegalRaster() {
"""
assert source.count(old_fields) == 1, source.count(old_fields)
source = source.replace(old_fields, new_fields, 1)

old_start = """\tprivate void buildLegalRaster() {
\t\tpointContainmentCache.clear();
\t\tfinal int w = gameCols + 2;
\t\trasterH = gameRows + 2;
\t\tfinal byte[] r = new byte[w * rasterH];
"""
new_start = """\tprivate void buildLegalRaster() {
\t\tpointContainmentCache.clear();
\t\tfinal int w = gameCols + 2;
\t\tfinal int h = gameRows + 2;
\t\tfinal String memoKey = autoMode ? reach.geometryCacheKey() : null;
\t\tfinal RasterMaps cached = findRasterMaps(memoKey, w, h);
\t\tif (cached != null) {
\t\t\tlegalRaster = cached.unit;
\t\t\trasterH = cached.unitH;
\t\t\tsubRaster = cached.sub;
\t\t\tsubW = cached.subW;
\t\t\tsubH = cached.subH;
\t\t\treturn;
\t\t}
\t\trasterH = h;
\t\tfinal byte[] r = new byte[w * rasterH];
"""
assert source.count(old_start) == 1, source.count(old_start)
source = source.replace(old_start, new_start, 1)

old_end = """\t\tmarkPath(r, w, track.getRight());
\t\tlegalRaster = r;
\t\tbuildSubRaster(r, w);
\t}

\t/** Round 112:"""
new_end = """\t\tmarkPath(r, w, track.getRight());
\t\tlegalRaster = r;
\t\tbuildSubRaster(r, w);
\t\tif (memoKey != null) {
\t\t\tfinal RasterMaps shared = publishRasterMaps(memoKey, legalRaster,
\t\t\t\t\tw, rasterH, subRaster, subW, subH, RASTER_MEMO_MAX_BYTES);
\t\t\tlegalRaster = shared.unit;
\t\t\trasterH = shared.unitH;
\t\t\tsubRaster = shared.sub;
\t\t\tsubW = shared.subW;
\t\t\tsubH = shared.subH;
\t\t}
\t}

\t/** Round 112:"""
assert source.count(old_end) == 1, source.count(old_end)
source = source.replace(old_end, new_end, 1)
assert source.count("final RasterMaps cached = findRasterMaps") == 1
race.write_text(source)

core = Path("tests/tr/logic/CoreTests.java")
tests = core.read_text()
assert "private static void testSharedRasterMaps()" not in tests
old_call = """        testSharedDenseEdgeLegalCache();
        testPointContainmentCache();
"""
new_call = """        testSharedDenseEdgeLegalCache();
        testSharedRasterMaps();
        testPointContainmentCache();
"""
assert tests.count(old_call) == 1, tests.count(old_call)
tests = tests.replace(old_call, new_call, 1)

anchor = """    private static void testPointContainmentCache() {
"""
method = """    private static void testSharedRasterMaps() {
        RaceGame.clearRasterMemoForTests();
        final byte[] unitA = new byte[4];
        final byte[] subA = new byte[64];
        final RaceGame.RasterMaps first = RaceGame.publishRasterMaps(
                "core-raster-a", unitA, 2, 2, subA, 8, 8, 100);
        check(RaceGame.findRasterMaps("core-raster-a", 2, 2) == first,
                "shared legality rasters were not retained");
        check(first.unit == unitA && first.sub == subA,
                "shared legality rasters copied or replaced exact arrays");

        final RaceGame.RasterMaps duplicate = RaceGame.publishRasterMaps(
                "core-raster-a", new byte[4], 2, 2, new byte[64], 8, 8, 100);
        check(duplicate == first, "same geometry replaced compatible legality rasters");

        final RaceGame.RasterMaps second = RaceGame.publishRasterMaps(
                "core-raster-b", new byte[1], 1, 1, new byte[16], 4, 4, 80);
        check(second != null && RaceGame.findRasterMaps("core-raster-b", 1, 1) == second,
                "second legality raster pair was not retained");
        check(RaceGame.findRasterMaps("core-raster-a", 2, 2) == null,
                "legality-raster LRU cap did not evict the eldest entry");

        final RaceGame.RasterMaps replacement = RaceGame.publishRasterMaps(
                "core-raster-b", new byte[2], 2, 1, new byte[32], 8, 4, 100);
        check(replacement != second
                        && RaceGame.findRasterMaps("core-raster-b", 2, 1) == replacement,
                "dimension change retained incompatible legality rasters");

        final RaceGame.RasterMaps oversized = RaceGame.publishRasterMaps(
                "core-raster-private", new byte[1], 1, 1, new byte[16], 4, 4, 10);
        check(oversized != null, "oversized legality rasters lost their private fallback");
        check(RaceGame.findRasterMaps("core-raster-private", 1, 1) == null,
                "legality rasters larger than the cap were retained globally");
        RaceGame.clearRasterMemoForTests();
    }

    private static void testPointContainmentCache() {
"""
assert tests.count(anchor) == 1, tests.count(anchor)
tests = tests.replace(anchor, method, 1)
core.write_text(tests)

print("materialized shared immutable legality rasters")
