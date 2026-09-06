package tr.logic;

import java.awt.Color;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.BitSet;
import java.util.List;

/** Lightweight dependency-free regression tests for pure core helpers. */
public final class CoreTests {
    private CoreTests() {}

    public static void main(final String[] args) {
        ReviewRuleTests.run();
        FollowupRuleTests.run();
        RaceAiTacticsTests.run();
        StartPlacementTests.run();
        testDirections();
        testPlayerKinds();
        testDefaultProperties();
        testPointParsing();
        testAtomicWrites();
        testTrackNames();
        testTrackListing();
        testBorderValidation();
        testEdgeLegalCache();
        testDenseEdgeLegalCache();
        testSharedDenseEdgeLegalCache();
        testSharedRasterMaps();
        testPointContainmentCache();
        testGeometryCacheThreadIsolation();
        testSharedDistanceMaps();
        testEndgameMemoKey();
        testDistinctCoverMatching();
        testDirectBlockedLookup();
        testCellOccupancyReuse();
        testTrackDistanceOrdering();
        testRaceAiStateIsolation();
        testExactRidgePlateauHold();
        testExactAxialVmaxHold();
        testReachabilityFailurePropagation();
        testReachabilityVelocityBounds();
        testReachabilityCacheIO();
        testAutomaticStartPositionBounds();
        testEmptyTrackUndo();
        testAiTurnRejectsManualDirection();
        tr.gui.GameUITests.run();
        testSegmentIntersection();
        testStartZone();
        TrackDataTests.run();
        System.out.println("CoreTests: OK");
    }

    private static void testDirections() {
        final Direction[] values = Direction.values();
        check(values.length == 9, "expected nine acceleration choices");
        for (int i = 0; i < values.length; i++)
            check(Direction.fromIndex(i) == values[i], "direction index round-trip failed at " + i);
        check("-".equals(Direction.NONE.label()), "NONE label should be '-' ");
    }

    private static void testExactRidgePlateauHold() {
        check(!RaceAi.isExactRidgePlateauHold(11, 10, 10, 10),
                "braking 11->10 must not count as a speed-10 hold");
        check(RaceAi.isExactRidgePlateauHold(10, 10, 9, 10),
                "unchanged y=10 must count as a speed-10 hold");
        check(RaceAi.isExactRidgePlateauHold(-10, 0, -10, 1),
                "signed target ridge hold was rejected");
    }

    private static void testExactAxialVmaxHold() {
        check(RaceAi.isExactAxialVmaxHold(11, 0, 11, 0),
                "positive-x axial speed-11 hold was rejected");
        check(RaceAi.isExactAxialVmaxHold(-11, 1, -11, 0),
                "signed axial speed-11 landing was rejected");
        check(RaceAi.isExactAxialVmaxHold(0, -11, 0, -11),
                "negative-y axial speed-11 hold was rejected");
        check(!RaceAi.isExactAxialVmaxHold(10, 0, 11, 0),
                "acceleration into speed 11 must not count as a hold");
        check(!RaceAi.isExactAxialVmaxHold(11, 0, 11, 1),
                "non-axial speed-11 landing must not count");
        check(!RaceAi.isExactAxialVmaxHold(11, 0, 10, 0),
                "braking from speed 11 must not count as a hold");
        check(!RaceAi.isExactAxialVmaxHold(-11, 0, 11, 0),
                "signed component reversal must not count as a hold");
    }

    private static void testPlayerKinds() {
        check(Player.Kind.parse(null) == Player.Kind.HUMAN, "null kind should be HUMAN");
        check(Player.Kind.parse("AI2") == Player.Kind.AI2, "AI2 parsing failed");
        check(Player.Kind.parse("nonsense") == Player.Kind.HUMAN, "unknown kind should be HUMAN");

        final Player p = new Player("P", 1, Color.BLUE, Player.Kind.AI1);
        check(p.isAi(), "AI1 player should report AI");
        check("0 0".equals(p.statusLabel()), "fresh player velocity label changed");
        p.setFinishedPlace(2);
        check(p.isFinished() && "2.".equals(p.statusLabel()), "finish status label changed");
    }

    private static void testDefaultProperties() {
        final java.util.Properties props = new java.util.Properties();
        new RaceGame(props);
        check("9".equals(props.getProperty("maxPlayers")), "maxPlayers default missing");
        check("2".equals(props.getProperty("nPlayers")), "nPlayers default missing");
        check("1500".equals(props.getProperty("windowX")), "windowX default missing");
        check("800".equals(props.getProperty("windowY")), "windowY default missing");
        check("86".equals(props.getProperty("gameX")), "gameX default missing");
        check("48".equals(props.getProperty("gameY")), "gameY default missing");
        check("HUMAN".equals(props.getProperty("player1Kind")), "player kind default missing");
    }

    private static void testPointParsing() {
        final List<int[]> pts = TrackIO.parsePointList("1,2; 3,4; -7,8");
        check(pts.size() == 3, "valid point list rejected");
        checkPoint(pts.get(0), 1, 2);
        checkPoint(pts.get(1), 3, 4);
        checkPoint(pts.get(2), -7, 8);
        check("1,2;3,4;-7,8".equals(TrackIO.pointListToString(pts)), "point serialization changed");
        check(TrackIO.parsePointList("1,2;bad;3,4").isEmpty(), "malformed point list should be rejected atomically");
        check(TrackIO.parsePointList("1,2;").isEmpty(), "trailing empty point should be rejected");
    }

    private static void testAtomicWrites() {
        java.nio.file.Path directory = null;
        try {
            directory = java.nio.file.Files.createTempDirectory("theoretical-racing-atomic-");
            final java.nio.file.Path target = directory.resolve("nested").resolve("state.bin");
            final byte[] first = new byte[128 * 1024];
            final byte[] second = new byte[128 * 1024];
            java.util.Arrays.fill(first, (byte) 'A');
            java.util.Arrays.fill(second, (byte) 'B');
            byte[] actual = null;
            for (int round = 0; round < 8; round++) {
                final java.util.concurrent.CountDownLatch ready = new java.util.concurrent.CountDownLatch(2);
                final java.util.concurrent.CountDownLatch release = new java.util.concurrent.CountDownLatch(1);
                final java.util.concurrent.atomic.AtomicReference<Throwable> failure =
                        new java.util.concurrent.atomic.AtomicReference<>();
                final Thread one = atomicWriter(target, first, ready, release, failure);
                final Thread two = atomicWriter(target, second, ready, release, failure);
                one.start();
                two.start();
                final boolean overlapped = ready.await(5, java.util.concurrent.TimeUnit.SECONDS);
                release.countDown();
                check(overlapped, "concurrent atomic writers did not overlap");
                one.join(20_000);
                two.join(20_000);
                check(!one.isAlive() && !two.isAlive(), "concurrent atomic writer hung");
                check(failure.get() == null, "concurrent atomic write failed: " + failure.get());
                actual = java.nio.file.Files.readAllBytes(target);
                check(java.util.Arrays.equals(actual, first) || java.util.Arrays.equals(actual, second),
                        "concurrent write exposed a partial file");
            }

            final byte[] beforeFailure = actual.clone();
            try {
                TrackIO.writeAtomically(target, out -> {
                    out.write('X');
                    throw new java.io.IOException("expected test failure");
                });
                throw new AssertionError("failed atomic write unexpectedly succeeded");
            } catch (final java.io.IOException expected) {
                check("expected test failure".equals(expected.getMessage()),
                        "atomic writer changed the original failure");
            }
            check(java.util.Arrays.equals(java.nio.file.Files.readAllBytes(target), beforeFailure),
                    "failed atomic write replaced the previous complete file");
            try (java.util.stream.Stream<java.nio.file.Path> files =
                    java.nio.file.Files.list(target.getParent())) {
                check(files.noneMatch(file -> file.getFileName().toString().contains(".tmp.")),
                        "atomic writer left a temporary file behind");
            }
        } catch (final InterruptedException error) {
            Thread.currentThread().interrupt();
            throw new AssertionError("atomic write regression test was interrupted", error);
        } catch (final java.io.IOException error) {
            throw new AssertionError("atomic write regression test failed", error);
        } finally {
            if (directory != null)
                deleteTree(directory);
        }
    }

    private static Thread atomicWriter(final java.nio.file.Path target, final byte[] payload,
            final java.util.concurrent.CountDownLatch ready,
            final java.util.concurrent.CountDownLatch release,
            final java.util.concurrent.atomic.AtomicReference<Throwable> failure) {
        final Thread thread = new Thread(() -> {
            try {
                TrackIO.writeAtomically(target, out -> {
                    ready.countDown();
                    try {
                        if (!release.await(5, java.util.concurrent.TimeUnit.SECONDS))
                            throw new java.io.IOException("timed out waiting for concurrent writer");
                    } catch (final InterruptedException error) {
                        Thread.currentThread().interrupt();
                        throw new java.io.IOException("atomic writer interrupted", error);
                    }
                    out.write(payload);
                });
            } catch (final Throwable error) {
                failure.compareAndSet(null, error);
            }
        }, "atomic-writer-test");
        thread.setDaemon(true);
        return thread;
    }

    private static void deleteTree(final java.nio.file.Path root) {
        if (!java.nio.file.Files.exists(root))
            return;
        try (java.util.stream.Stream<java.nio.file.Path> paths = java.nio.file.Files.walk(root)) {
            for (final java.nio.file.Path path : paths.sorted(java.util.Comparator.reverseOrder()).toList())
                java.nio.file.Files.deleteIfExists(path);
        } catch (final java.io.IOException error) {
            throw new AssertionError("could not clean test directory", error);
        }
    }


    private static void testTrackNames() {
        check(TrackIO.validTrackName("sprint"), "simple track name rejected");
        check(TrackIO.validTrackName("ugly_bump"), "underscore track name rejected");
        check(!TrackIO.validTrackName("../sprint"), "parent traversal track name accepted");
        check(!TrackIO.validTrackName("..\\sprint"), "Windows traversal track name accepted");
        check(!TrackIO.validTrackName("C:sprint"), "drive-qualified track name accepted");
    }


    private static void testTrackListing() {
        final java.nio.file.Path directory = TrackIO.tracksDir();
        final boolean directoryExisted = java.nio.file.Files.exists(directory);
        final String suffix = Long.toUnsignedString(System.nanoTime());
        final String validName = "listing_test_" + suffix;
        final java.nio.file.Path valid = directory.resolve(validName + ".track");
        final java.nio.file.Path invalid = directory.resolve("bad name " + suffix + ".track");
        final java.nio.file.Path folder = directory.resolve("folder_" + suffix + ".track");
        try {
            java.nio.file.Files.createDirectories(directory);
            java.nio.file.Files.writeString(valid, "");
            java.nio.file.Files.writeString(invalid, "");
            java.nio.file.Files.createDirectory(folder);
            final java.util.List<String> tracks = TrackIO.listTracks();
            check(tracks.contains(validName), "regular valid track file was not listed");
            check(!tracks.contains("bad name " + suffix), "invalid track name was listed");
            check(!tracks.contains("folder_" + suffix), "track directory was listed as a file");
        } catch (final java.io.IOException error) {
            throw new AssertionError("could not arrange track listing test", error);
        } finally {
            try {
                java.nio.file.Files.deleteIfExists(valid);
                java.nio.file.Files.deleteIfExists(invalid);
                java.nio.file.Files.deleteIfExists(folder);
                if (!directoryExisted)
                    java.nio.file.Files.deleteIfExists(directory);
            } catch (final java.io.IOException error) {
                throw new AssertionError("could not clean track listing test", error);
            }
        }
    }

    private static void testBorderValidation() {
        final List<int[]> left = new ArrayList<>();
        final List<int[]> right = new ArrayList<>();
        left.add(p(0, 0));
        left.add(p(10, 0));
        right.add(p(0, 4));
        right.add(p(10, 4));
        check(TrackIO.validBorders(left, right), "valid border pair rejected");

        right.set(0, p(0, 0));
        check(!TrackIO.validBorders(left, right), "zero-width start line accepted");
        right.set(0, p(0, 4));
        left.add(p(10, 0));
        check(!TrackIO.validBorders(left, right), "consecutive duplicate border point accepted");
    }

    private static void testEndgameMemoKey() {
        final long highY = RaceAi.endgameMemoKey(0, 256, 0, 0, 10, 20, 1, -1, 7, false);
        final long nextX = RaceAi.endgameMemoKey(1, 0, 0, 0, 10, 20, 1, -1, 7, false);
        check(highY != nextX, "endgame memo key collides above coordinate 255");

        final long maxGrid = RaceAi.endgameMemoKey(500, 500, 12, -12, 499, 498, -12, 12, 20, true);
        final long adjacent = RaceAi.endgameMemoKey(500, 499, 12, -12, 499, 498, -12, 12, 20, true);
        check(maxGrid != adjacent, "endgame memo key loses supported 9-bit coordinates");
    }

    private static void testEdgeLegalCache() {
        final RaceGame.EdgeLegalCache cache = new RaceGame.EdgeLegalCache(1);
        check(cache.get(0L) == 0, "fresh edge cache should miss");
        cache.put(0L, false);
        cache.put(Long.MIN_VALUE, true);
        check(cache.get(0L) == RaceGame.EdgeLegalCache.FALSE, "zero-key false value was lost");
        check(cache.get(Long.MIN_VALUE) == RaceGame.EdgeLegalCache.TRUE, "high-bit true value was lost");

        for (int i = 1; i <= 10_000; i++) {
            final long key = i * 0x9e3779b97f4a7c15L;
            cache.put(key, (i & 1) == 0);
        }
        for (int i = 1; i <= 10_000; i++) {
            final long key = i * 0x9e3779b97f4a7c15L;
            final byte expected = (i & 1) == 0 ? RaceGame.EdgeLegalCache.TRUE : RaceGame.EdgeLegalCache.FALSE;
            check(cache.get(key) == expected, "edge cache resize lost key " + i);
        }
        cache.put(0L, true);
        check(cache.get(0L) == RaceGame.EdgeLegalCache.TRUE, "edge cache update failed");
        check(cache.get(123456789L) == 0, "edge cache false hit");
    }


    private static void testDenseEdgeLegalCache() {
        final RaceGame.DenseEdgeLegalCache cache = RaceGame.DenseEdgeLegalCache.create(3, 4, 10_000);
        check(cache != null, "small dense edge cache was rejected");
        final int zero = cache.index(0, 0, 0, 0);
        final int max = cache.index(2, 3, 14, -9);
        final int min = cache.index(2, 3, -10, 15);
        check(zero >= 0 && max >= 0 && min >= 0, "bounded dense edge was rejected");
        check(zero != max && max != min && zero != min, "dense edge indices collided");
        cache.put(zero, false);
        cache.put(max, true);
        check(cache.get(zero) == RaceGame.DenseEdgeLegalCache.ILLEGAL,
                "dense false verdict was lost");
        check(cache.get(max) == RaceGame.DenseEdgeLegalCache.LEGAL,
                "dense true verdict was lost");

        final RaceGame.DenseEdgeLegalCache packed =
                RaceGame.DenseEdgeLegalCache.create(1, 1, 10_000);
        for (int index = 0; index < 16; index++)
            packed.put(index, (index & 1) == 0);
        for (int index = 0; index < 16; index++) {
            final int expected = (index & 1) == 0
                    ? RaceGame.DenseEdgeLegalCache.LEGAL
                    : RaceGame.DenseEdgeLegalCache.ILLEGAL;
            check(packed.get(index) == expected,
                    "dense packed state failed at slot " + index);
        }

        final RaceGame.DenseEdgeLegalCache concurrent =
                RaceGame.DenseEdgeLegalCache.create(1, 1, 10_000);
        final int edgeA = concurrent.index(0, 0, 0, 0);
        final int edgeB = concurrent.index(0, 0, 0, 1);
        final int edgeC = concurrent.index(0, 0, 0, 2);
        final int word = edgeA >>> 4;
        check(word == edgeB >>> 4 && word == edgeC >>> 4,
                "dense concurrency test edges do not share one word");
        final int snapshotA = concurrent.states[word];
        final int snapshotB = concurrent.states[word];
        concurrent.states[word] = snapshotA
                | RaceGame.DenseEdgeLegalCache.LEGAL << ((edgeA & 15) << 1);
        concurrent.states[word] = snapshotB
                | RaceGame.DenseEdgeLegalCache.LEGAL << ((edgeB & 15) << 1);
        check(concurrent.get(edgeA) == RaceGame.DenseEdgeLegalCache.UNKNOWN,
                "stale dense write manufactured a false verdict");
        check(concurrent.get(edgeB) == RaceGame.DenseEdgeLegalCache.LEGAL,
                "stale dense write lost its own verdict");
        concurrent.put(edgeA, true);
        concurrent.put(edgeC, false);
        check(concurrent.get(edgeA) == RaceGame.DenseEdgeLegalCache.LEGAL
                && concurrent.get(edgeB) == RaceGame.DenseEdgeLegalCache.LEGAL,
                "dense retry did not preserve both legal verdicts");
        check(concurrent.get(edgeC) == RaceGame.DenseEdgeLegalCache.ILLEGAL,
                "dense illegal state encoding failed");
        check(cache.index(-1, 0, 0, 0) == -1, "negative origin entered dense cache");
        check(cache.index(3, 0, 3, 0) == -1, "wide origin entered dense cache");
        check(cache.index(0, 0, 13, 0) == -1, "overspeed delta entered dense cache");
        check(RaceGame.DenseEdgeLegalCache.create(500, 500, 1_000) == null,
                "dense cache ignored its memory cap");
    }

    private static void testSharedDenseEdgeLegalCache() {
        final RaceGame.DenseEdgeLegalCache first = RaceGame.DenseEdgeLegalCache.shared(
                "core-test-track", 3, 4, 10_000, 20_000);
        final RaceGame.DenseEdgeLegalCache second = RaceGame.DenseEdgeLegalCache.shared(
                "core-test-track", 3, 4, 10_000, 20_000);
        check(first != null && first == second, "shared dense edge cache was not reused");

        final int zero = first.index(0, 0, 0, 0);
        final int max = first.index(2, 3, 14, -9);
        first.put(zero, false);
        first.put(max, true);
        check(second.get(zero) == RaceGame.DenseEdgeLegalCache.ILLEGAL,
                "shared dense false verdict was lost");
        check(second.get(max) == RaceGame.DenseEdgeLegalCache.LEGAL,
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

    private static void testSharedRasterMaps() {
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

    @SuppressWarnings("unchecked")
    private static void testGeometryCacheThreadIsolation() {
        try {
            final RaceGame game = new RaceGame(new java.util.Properties());
            final java.lang.reflect.Field pointField =
                    RaceGame.class.getDeclaredField("pointContainmentCaches");
            pointField.setAccessible(true);
            final ThreadLocal<RaceGame.PointContainmentCache> caches =
                    (ThreadLocal<RaceGame.PointContainmentCache>) pointField.get(game);
            final RaceGame.PointContainmentCache mainCache = caches.get();
            mainCache.put(11L, 22L, true);

            final java.util.concurrent.atomic.AtomicReference<RaceGame.PointContainmentCache>
                    workerCache = new java.util.concurrent.atomic.AtomicReference<>();
            final java.util.concurrent.atomic.AtomicReference<Throwable> failure =
                    new java.util.concurrent.atomic.AtomicReference<>();
            final Thread worker = new Thread(() -> {
                try {
                    final RaceGame.PointContainmentCache cache = caches.get();
                    workerCache.set(cache);
                    cache.put(11L, 22L, false);
                    check(cache.get(11L, 22L) == RaceGame.PointContainmentCache.FALSE,
                            "worker point cache lost its private verdict");
                } catch (final Throwable t) {
                    failure.set(t);
                } finally {
                    game.clearPointContainmentCacheForCurrentThread();
                }
            }, "point-cache-isolation-test");
            worker.start();
            worker.join(10_000);
            check(!worker.isAlive(), "point-cache isolation worker hung");
            check(failure.get() == null, "point-cache isolation worker failed: " + failure.get());
            check(workerCache.get() != mainCache, "point cache was shared across threads");
            check(mainCache.get(11L, 22L) == RaceGame.PointContainmentCache.TRUE,
                    "worker write corrupted the main-thread point cache");

            game.clearPointContainmentCacheForCurrentThread();
            check(caches.get() != mainCache, "point-cache cleanup retained the old table");
            game.clearPointContainmentCacheForCurrentThread();

            final java.lang.reflect.Field edgeField =
                    RaceGame.class.getDeclaredField("edgeLegalCache");
            edgeField.setAccessible(true);
            check(edgeField.get(game) == null, "fallback edge cache should be lazy");
            final java.lang.reflect.Method fallback =
                    RaceGame.class.getDeclaredMethod("fallbackEdgeLegalCache");
            fallback.setAccessible(true);
            final Object first = fallback.invoke(game);
            check(first != null && first == fallback.invoke(game),
                    "fallback edge cache was not retained after lazy creation");
        } catch (final ReflectiveOperationException | InterruptedException e) {
            throw new AssertionError("geometry-cache isolation test failed", e);
        }
    }

    private static void testSharedDistanceMaps() {
        Reachability.clearDistanceMemoForTests();
        final int[][] distance = new int[][]{{0, 1}, {2, 3}};
        final int[] rings = new int[]{1, 2};
        final Reachability.DistanceMaps first = Reachability.publishDistanceMaps(
                "core-distance-a", distance, rings, 10);
        check(Reachability.findDistanceMaps("core-distance-a", 2, 2) == first,
                "shared distance map was not retained");
        check(first.distance == distance && first.ringWidth == rings,
                "shared distance map copied or replaced exact arrays");

        final Reachability.DistanceMaps duplicate = Reachability.publishDistanceMaps(
                "core-distance-a", new int[][]{{9, 9}, {9, 9}}, new int[]{9}, 10);
        check(duplicate == first, "same geometry replaced a compatible distance map");

        final Reachability.DistanceMaps second = Reachability.publishDistanceMaps(
                "core-distance-b", new int[][]{{4, 5}}, new int[]{2}, 8);
        check(second != null && Reachability.findDistanceMaps("core-distance-b", 1, 2) == second,
                "second distance map was not retained");
        check(Reachability.findDistanceMaps("core-distance-a", 2, 2) == null,
                "distance-map LRU cap did not evict the eldest entry");

        final Reachability.DistanceMaps replacement = Reachability.publishDistanceMaps(
                "core-distance-b", new int[][]{{1}, {2}, {3}}, new int[]{3}, 10);
        check(replacement != second
                        && Reachability.findDistanceMaps("core-distance-b", 3, 1) == replacement,
                "dimension change retained an incompatible distance map");

        final Reachability.DistanceMaps oversized = Reachability.publishDistanceMaps(
                "core-distance-private", new int[][]{{1, 2}, {3, 4}}, new int[]{1, 2}, 5);
        check(oversized != null, "oversized distance map lost its private fallback");
        check(Reachability.findDistanceMaps("core-distance-private", 2, 2) == null,
                "distance map larger than the cap was retained globally");
        Reachability.clearDistanceMemoForTests();
    }

    private static void testDistinctCoverMatching() {
        final int[] uniqueEight = new int[8];
        for (int i = 0; i < uniqueEight.length; i++)
            uniqueEight[i] = 1 << i;
        check(RaceAi.hasDistinctCover(uniqueEight, 8), "eight opponents should cover eight distinct escapes");
        check(!RaceAi.hasDistinctCover(uniqueEight, 7), "seven opponents cannot cover eight escapes");
        check(!RaceAi.hasDistinctCover(new int[]{1, 1}, 2), "one opponent cannot cover two escapes simultaneously");
        check(RaceAi.hasDistinctCover(new int[]{3, 1}, 2), "matching should reroute a flexible first assignment");
    }

    private static void testRaceAiStateIsolation() {
        checkAiStateIsolation(RaceAi.class);
        checkAiStateIsolation(RaceAiPrivateLane.class);
    }

    private static void checkAiStateIsolation(final Class<?> type) {
        for (final java.lang.reflect.Field field : type.getDeclaredFields()) {
            final int modifiers = field.getModifiers();
            check(!java.lang.reflect.Modifier.isStatic(modifiers)
                    || java.lang.reflect.Modifier.isFinal(modifiers),
                    type.getSimpleName() + " mutable state must be instance-scoped: " + field.getName());
        }
    }

    private static void testReachabilityVelocityBounds() {
        check(!RaceGame.aiVelocityOutOfRange(RaceGame.AI_MAX_SPEED, -RaceGame.AI_MAX_SPEED),
                "AI velocity boundary was rejected");
        check(RaceGame.aiVelocityOutOfRange(RaceGame.AI_MAX_SPEED + 1, 0),
                "AI velocity above the boundary was accepted");
        check(RaceGame.aiVelocityOutOfRange(Integer.MIN_VALUE, 0),
                "minimum integer velocity escaped the AI bound");
        check(RaceGame.aiVelocityOutOfRange(Integer.MAX_VALUE, 0),
                "maximum integer velocity escaped the AI bound");

        final Reachability reach = new Reachability(new RaceGame(new java.util.Properties()));
        reach.aliveW = 1;
        reach.aliveH = 1;
        reach.aliveVMAX = RaceGame.AI_MAX_SPEED;
        reach.aliveSpan = 2 * reach.aliveVMAX + 1;
        final int states = reach.aliveSpan * reach.aliveSpan;
        reach.aliveStates = new java.util.BitSet(states);
        reach.turnsArr = new int[states];
        reach.certSq = new byte[states];
        check(!reach.isAlive(0, 0, Integer.MIN_VALUE, 0),
                "minimum integer velocity escaped the reachability bound");
        check(reach.turnsToFinish(0, 0, Integer.MIN_VALUE, 0) == Integer.MAX_VALUE,
                "minimum integer velocity reached the turns array");
        check(reach.certBudget(0, 0, Integer.MIN_VALUE, 0) == 0,
                "minimum integer velocity reached the certified-speed array");
        check(!reach.isAlive(0, 0, Integer.MAX_VALUE, 0),
                "maximum integer velocity escaped the reachability bound");
    }

    private static void testReachabilityFailurePropagation() {
        final RaceGame game = new RaceGame(new java.util.Properties());
        final IllegalStateException expected = new IllegalStateException("expected reachability failure");
        try {
            final java.lang.reflect.Field ready = Reachability.class.getDeclaredField("reachabilityReady");
            final java.lang.reflect.Field failure = Reachability.class.getDeclaredField("reachabilityFailure");
            ready.setAccessible(true);
            failure.setAccessible(true);
            failure.set(game.reach, expected);
            ready.setBoolean(game.reach, true);
        } catch (final ReflectiveOperationException error) {
            throw new AssertionError("could not arrange reachability failure test", error);
        }
        try {
            game.reach.ensureReachabilityReady();
            throw new AssertionError("background reachability failure was swallowed");
        } catch (final IllegalStateException actual) {
            check(actual == expected, "reachability failure identity was not preserved");
        }
    }

    private static void testReachabilityCacheIO() {
        final int[] expectedInts = {1, Integer.MAX_VALUE, 0x01020304, -7};
        final ByteBuffer intBytes = ByteBuffer.allocate(expectedInts.length * Integer.BYTES)
                .order(ByteOrder.LITTLE_ENDIAN);
        for (final int value : expectedInts)
            intBytes.putInt(value);
        final int[] actualInts = new int[expectedInts.length];
        try {
            check(Reachability.readLittleEndian(new ByteArrayInputStream(intBytes.array()), actualInts, new byte[5]),
                    "chunked integer cache read failed");
            check(Arrays.equals(expectedInts, actualInts), "integer cache byte order changed");
            check(!Reachability.readLittleEndian(
                    new ByteArrayInputStream(Arrays.copyOf(intBytes.array(), intBytes.array().length - 1)),
                    new int[expectedInts.length], new byte[7]), "truncated integer cache was accepted");
        } catch (final IOException error) {
            throw new AssertionError("cache integer test failed", error);
        }

        final short[] expectedShorts = {0, 1, 0x101, 7};
        final ByteBuffer shortBytes = ByteBuffer.allocate(expectedShorts.length * Short.BYTES)
                .order(ByteOrder.LITTLE_ENDIAN);
        for (final short value : expectedShorts)
            shortBytes.putShort(value);
        final short[] actualShorts = new short[expectedShorts.length];
        try {
            check(Reachability.readLittleEndian(new ByteArrayInputStream(shortBytes.array()), actualShorts, new byte[3]),
                    "chunked short cache read failed");
            check(Arrays.equals(expectedShorts, actualShorts), "short cache byte order changed");
        } catch (final IOException error) {
            throw new AssertionError("cache short test failed", error);
        }

        final BitSet alive = new BitSet();
        check(Reachability.validateCacheArrays(
                new int[]{1, Integer.MAX_VALUE, 3}, new short[]{1, 0, 0x101}, alive),
                "valid cache arrays were rejected");
        check(alive.cardinality() == 2 && alive.get(0) && alive.get(2), "alive cache set was decoded incorrectly");
        check(!Reachability.validateCacheArrays(new int[]{0}, new short[]{0}, new BitSet()),
                "zero-turn cache state was accepted");
        check(!Reachability.validateCacheArrays(new int[]{Integer.MAX_VALUE}, new short[]{1}, new BitSet()),
                "unreachable cache state retained a successor mask");
        check(!Reachability.validateCacheArrays(new int[]{1}, new short[]{1 << 9}, new BitSet()),
                "cache mask accepted a non-direction bit");

        final int[] cacheTurns = {1, Integer.MAX_VALUE, 3};
        final short[] cacheMasks = {1, 0, 0x101};
        try {
            final ByteArrayOutputStream encoded = new ByteArrayOutputStream();
            Reachability.writeCacheData(encoded, 2, 3, RaceGame.AI_MAX_SPEED, cacheTurns, cacheMasks);
            final byte[] cache = encoded.toByteArray();
            final int[] decodedTurns = new int[cacheTurns.length];
            final short[] decodedMasks = new short[cacheMasks.length];
            check(Reachability.readCacheData(new ByteArrayInputStream(cache), 2, 3,
                    RaceGame.AI_MAX_SPEED, decodedTurns, decodedMasks), "checksummed cache round-trip failed");
            check(Arrays.equals(cacheTurns, decodedTurns) && Arrays.equals(cacheMasks, decodedMasks),
                    "checksummed cache round-trip changed data");

            final byte[] corrupted = cache.clone();
            corrupted[4 * Integer.BYTES] = 2; // turn 1 -> turn 2: structurally valid, checksum-invalid
            check(!Reachability.readCacheData(new ByteArrayInputStream(corrupted), 2, 3,
                    RaceGame.AI_MAX_SPEED, new int[cacheTurns.length], new short[cacheMasks.length]),
                    "same-size cache corruption was accepted");
            check(!Reachability.readCacheData(
                    new ByteArrayInputStream(Arrays.copyOf(cache, cache.length - 1)), 2, 3,
                    RaceGame.AI_MAX_SPEED, new int[cacheTurns.length], new short[cacheMasks.length]),
                    "truncated checksummed cache was accepted");
            final byte[] trailing = Arrays.copyOf(cache, cache.length + 1);
            check(!Reachability.readCacheData(new ByteArrayInputStream(trailing), 2, 3,
                    RaceGame.AI_MAX_SPEED, new int[cacheTurns.length], new short[cacheMasks.length]),
                    "checksummed cache accepted trailing data");
        } catch (final IOException error) {
            throw new AssertionError("cache checksum test failed", error);
        }
    }

    private static void testAutomaticStartPositionBounds() {
        final RaceGame game = new RaceGame(new java.util.Properties());
        game.gameCols = 2;
        game.gameRows = 2;
        game.players = new Player[]{new Player("AI", 1, Color.BLUE, Player.Kind.AI1) };
        game.startZoneA = new java.awt.geom.Area(new java.awt.geom.Rectangle2D.Double(-3, -3, 5, 5));
        try {
            final java.lang.reflect.Field zone = RaceGame.class.getDeclaredField("startZone");
            zone.setAccessible(true);
            zone.set(game, new float[][]{{-2, 1, 1, -2 }, {-2, -2, 1, 1 } });
            final java.lang.reflect.Method find = RaceGame.class.getDeclaredMethod("findStartPosition");
            find.setAccessible(true);
            final int[] position = (int[]) find.invoke(game);
            check(position != null, "clipped start zone lost every grid position");
            checkPoint(position, 0, 0);
        } catch (final ReflectiveOperationException error) {
            throw new AssertionError("could not arrange automatic start-position test", error);
        }
    }

    private static void testEmptyTrackUndo() {
        final RaceGame game = new RaceGame(new java.util.Properties());
        try {
            final java.lang.reflect.Field state = RaceGame.class.getDeclaredField("gamestate");
            state.setAccessible(true);
            state.set(game, GameState.DRAWTRACK);
        } catch (final ReflectiveOperationException error) {
            throw new AssertionError("could not arrange track undo test", error);
        }
        game.subgamestate = 0;
        game.clickedUndo();
        game.track = new Track();
        game.subgamestate = 1;
        game.clickedUndo();
        check(game.track.getLeft().isEmpty() && game.track.getRight().isEmpty(),
                "undo on an empty border changed track state");
    }

    private static void testDirectBlockedLookup() {
        final int width = 4, height = 5;
        final long inside = ((long) 2 << 32) | 3L;
        final long outside = ((long) -1 << 32) | 7L;
        final long[] cells = new long[]{inside, outside};
        final long[] direct = new long[(width * height + 63) >>> 6];
        final int index = 2 * height + 3;
        direct[index >>> 6] |= 1L << (index & 63);
        check(RaceAi.blockedContains(cells, 2, direct, width, height, 2, 3),
                "direct blocked-cell lookup missed an in-grid member");
        check(!RaceAi.blockedContains(cells, 2, direct, width, height, 1, 3),
                "direct blocked-cell lookup produced an in-grid false hit");
        check(RaceAi.blockedContains(cells, 2, direct, width, height, -1, 7),
                "blocked-cell outside-grid fallback missed a member");
        check(!RaceAi.blockedContains(cells, 2, direct, width, height, -1, 8),
                "blocked-cell outside-grid fallback produced a false hit");
    }

    private static void testCellOccupancyReuse() {
        final RaceAi.CellOccupancy occupancy = new RaceAi.CellOccupancy(3, 3);
        for (int x = 0; x < 3; x++)
            for (int y = 0; y < 3; y++)
                occupancy.add(x, y);
        occupancy.remove(0, 0);
        check(!occupancy.contains(0, 0), "removed projected cell stayed occupied");
        occupancy.add(0, 0);
        check(occupancy.contains(0, 0), "re-added projected cell disappeared");
        occupancy.clear();
        for (int x = 0; x < 3; x++)
            for (int y = 0; y < 3; y++)
                check(!occupancy.contains(x, y), "projected occupancy clear left stale state");

        occupancy.add(1, 1);
        occupancy.add(1, 1);
        occupancy.remove(1, 1);
        check(occupancy.contains(1, 1), "duplicate projected occupancy lost its count");
        occupancy.remove(1, 1);
        check(!occupancy.contains(1, 1), "projected occupancy count did not reach zero");
        occupancy.add(1, 1);
        occupancy.clear();
        check(!occupancy.contains(1, 1), "re-added projected cell survived the next clear");
    }

    private static void testTrackDistanceOrdering() {
        check(RaceAi.isStrictlyAheadByTrackDistance(20, 19),
                "a smaller finite track distance should be strictly ahead");
        check(!RaceAi.isStrictlyAheadByTrackDistance(20, 20),
                "equal track-distance rings must not count as ahead");
        check(!RaceAi.isStrictlyAheadByTrackDistance(20, 21),
                "a larger track distance must not count as ahead");
        check(!RaceAi.isStrictlyAheadByTrackDistance(Integer.MAX_VALUE, 19),
                "an unavailable mover distance must fail closed");
        check(!RaceAi.isStrictlyAheadByTrackDistance(20, Integer.MAX_VALUE),
                "an unavailable rival distance must fail closed");
        check(RaceAi.useTrackDistanceForStagedLaunch(0, 0, true),
                "a stationary start-zone car should use track-distance ordering");
        check(!RaceAi.useTrackDistanceForStagedLaunch(1, 0, true),
                "a moving start-zone car should retain velocity ordering");
        check(!RaceAi.useTrackDistanceForStagedLaunch(0, 0, false),
                "a stopped car outside the start zone should retain velocity ordering");
    }

    private static void testAiTurnRejectsManualDirection() {
        final RaceGame game = new RaceGame(new java.util.Properties());
        final Player ai = new Player("AI", 1, Color.BLUE, Player.Kind.AI1);
        ai.setPosition(p(5, 6));
        ai.setVelocity(p(1, 0));
        game.players = new Player[]{ai};
        game.subgamestate = 0;
        try {
            final java.lang.reflect.Field state = RaceGame.class.getDeclaredField("gamestate");
            state.setAccessible(true);
            state.set(game, GameState.PLAY);
        } catch (final ReflectiveOperationException error) {
            throw new AssertionError("could not arrange AI input-guard test", error);
        }
        game.clickedDirection(Direction.E);
        checkPoint(ai.getPosition(), 5, 6);
        checkPoint(ai.getVelocity(), 1, 0);
    }

    private static void testSegmentIntersection() {
        check(TrackGeometry.checkIntersect(p(0, 0), p(10, 10), p(0, 10), p(10, 0), (byte) 0),
                "crossing diagonals should intersect");
        check(!TrackGeometry.checkIntersect(p(0, 0), p(10, 0), p(0, 2), p(10, 2), (byte) 0),
                "parallel separated segments should not intersect");
        check(TrackGeometry.checkIntersect(p(0, 0), p(10, 0), p(5, 0), p(15, 0), (byte) 0),
                "collinear overlap should intersect");
        check(TrackGeometry.checkIntersect(p(0, 0), p(10, 0), p(5, 0), p(5, 5), (byte) 0),
                "endpoint-to-interior T junction should intersect");
        check(TrackGeometry.checkIntersect(p(5, 0), p(5, 5), p(0, 0), p(10, 0), (byte) 0),
                "T-junction detection should be orientation independent");
        check(!TrackGeometry.checkIntersect(p(0, 0), p(10, 0), p(10, 0), p(20, 0), (byte) 2),
                "allowed adjacent endpoint should not count as self-intersection");
    }

    private static void testStartZone() {
        final float[][] zone = TrackGeometry.makeStartZone(p(0, 0), p(0, 10));
        check(zone.length == 2 && zone[0].length == 4 && zone[1].length == 4, "start zone shape changed");
        for (final float[] axis : zone)
            for (final float v : axis)
                check(Float.isFinite(v), "start zone produced non-finite coordinate");
    }

    private static int[] p(final int x, final int y) {
        return new int[]{x, y};
    }

    private static void checkPoint(final int[] p, final int x, final int y) {
        check(p[0] == x && p[1] == y, "unexpected point " + p[0] + "," + p[1]);
    }

    private static void check(final boolean condition, final String message) {
        if (!condition)
            throw new AssertionError(message);
    }
}
