package tr.logic;

import java.awt.Color;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.BitSet;
import java.util.List;

/** Lightweight dependency-free regression tests for pure core helpers. */
public final class CoreTests {
    private CoreTests() {}

    public static void main(final String[] args) {
        testDirections();
        testPlayerKinds();
        testDefaultProperties();
        testPointParsing();
        testAtomicWrites();
        testTrackNames();
        testTrackListing();
        testBorderValidation();
        testEdgeLegalCache();
        testEndgameMemoKey();
        testDistinctCoverMatching();
        testRaceAiStateIsolation();
        testReachabilityFailurePropagation();
        testReachabilityVelocityBounds();
        testReachabilityCacheIO();
        testAtomicWrite();
        testEmptyTrackUndo();
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
            final java.util.concurrent.CountDownLatch ready = new java.util.concurrent.CountDownLatch(2);
            final java.util.concurrent.CountDownLatch release = new java.util.concurrent.CountDownLatch(1);
            final java.util.concurrent.atomic.AtomicReference<Throwable> failure =
                    new java.util.concurrent.atomic.AtomicReference<>();
            final byte[] first = new byte[128 * 1024];
            final byte[] second = new byte[128 * 1024];
            java.util.Arrays.fill(first, (byte) 'A');
            java.util.Arrays.fill(second, (byte) 'B');
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
            final byte[] actual = java.nio.file.Files.readAllBytes(target);
            check(java.util.Arrays.equals(actual, first) || java.util.Arrays.equals(actual, second),
                    "concurrent write exposed a partial file");

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
                check(files.noneMatch(file -> file.getFileName().toString().contains(".tmp-")),
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
        check(TrackIO.validTrackName("the_long_loop"), "underscore track name rejected");
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
        for (final java.lang.reflect.Field field : RaceAi.class.getDeclaredFields()) {
            final int modifiers = field.getModifiers();
            check(!java.lang.reflect.Modifier.isStatic(modifiers)
                    || java.lang.reflect.Modifier.isFinal(modifiers),
                    "RaceAi mutable state must be instance-scoped: " + field.getName());
        }
    }

    private static void testReachabilityVelocityBounds() {
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
    }

    private static void testAtomicWrite() {
        Path directory = null;
        try {
            directory = Files.createTempDirectory("theoretical-racing-atomic-");
            final Path target = directory.resolve("nested/state.txt");
            TrackIO.writeAtomically(target, out -> out.write("complete".getBytes(java.nio.charset.StandardCharsets.UTF_8)));
            check("complete".equals(Files.readString(target)), "atomic writer lost complete output");

            boolean failed = false;
            try {
                TrackIO.writeAtomically(target, out -> {
                    out.write("partial".getBytes(java.nio.charset.StandardCharsets.UTF_8));
                    throw new IOException("expected writer failure");
                });
            } catch (final IOException expected) {
                failed = true;
            }
            check(failed, "atomic writer swallowed a callback failure");
            check("complete".equals(Files.readString(target)), "failed atomic write replaced the target");
            try (java.util.stream.Stream<Path> files = Files.list(target.getParent())) {
                check(files.noneMatch(path -> path.getFileName().toString().contains(".tmp.")),
                        "failed atomic write leaked a temporary file");
            }
            Files.delete(target);
            Files.delete(target.getParent());
            Files.delete(directory);
            directory = null;
        } catch (final IOException error) {
            throw new AssertionError("atomic write test failed", error);
        } finally {
            if (directory != null) {
                try (java.util.stream.Stream<Path> paths = Files.walk(directory)) {
                    paths.sorted(java.util.Comparator.reverseOrder()).forEach(path -> {
                        try {
                            Files.deleteIfExists(path);
                        } catch (final IOException ignored) {
                        }
                    });
                } catch (final IOException ignored) {
                }
            }
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
