package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Rectangle2D;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.Properties;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import tr.gui.GameUI;
import tr.gui.RaceUI;

/** Regression contracts for fallback cache publication, resize and failed AI startup. */
public final class PreparationSafetyTests {
    private PreparationSafetyTests() {}

    public static void main(final String[] args) {
        testConcurrentResize();
        testConcurrentGeometry();
        testParallelMaps();
        testPreparationFailures();
        testCheckpointMetadata();
        testCacheGeneration();
        System.out.println("PreparationSafetyTests: concurrent fallback, serial/parallel maps, failure recovery and checkpoint metadata OK");
    }

    private static void check(final boolean condition, final String message) {
        if (!condition) throw new AssertionError(message);
    }
    private static Field field(final Object object, final String name) {
        try {
            final Field f = object.getClass().getDeclaredField(name);
            f.setAccessible(true);
            return f;
        } catch (final ReflectiveOperationException e) { throw new AssertionError(e); }
    }
    private static void set(final Object object, final String name, final Object value) {
        try { field(object, name).set(object, value); }
        catch (final IllegalAccessException e) { throw new AssertionError(e); }
    }
    private static Object get(final Object object, final String name) {
        try { return field(object, name).get(object); }
        catch (final IllegalAccessException e) { throw new AssertionError(e); }
    }
    private static void invoke(final Object object, final String name) {
        try {
            final Method method = object.getClass().getDeclaredMethod(name);
            method.setAccessible(true);
            method.invoke(object);
        } catch (final ReflectiveOperationException e) { throw new AssertionError(e); }
    }

    /** Bounded daemon workers make a broken probe loop fail instead of hanging CI. */
    private static void together(final Runnable... tasks) {
        final CountDownLatch ready = new CountDownLatch(tasks.length);
        final CountDownLatch start = new CountDownLatch(1);
        final AtomicReference<Throwable> failure = new AtomicReference<>();
        final Thread[] threads = new Thread[tasks.length];
        for (int i = 0; i < tasks.length; i++) {
            final Runnable task = tasks[i];
            threads[i] = new Thread(() -> {
                ready.countDown();
                try {
                    if (!start.await(10, TimeUnit.SECONDS)) throw new AssertionError("start barrier timed out");
                    task.run();
                } catch (final Throwable error) { failure.compareAndSet(null, error); }
            }, "preparation-regression-" + i);
            threads[i].setDaemon(true);
            threads[i].start();
        }
        try {
            check(ready.await(10, TimeUnit.SECONDS), "workers did not reach start barrier");
            start.countDown();
            for (final Thread thread : threads) {
                thread.join(30_000);
                check(!thread.isAlive(), "concurrent cache/map worker hung");
            }
        } catch (final InterruptedException error) {
            Thread.currentThread().interrupt();
            throw new AssertionError(error);
        } finally { start.countDown(); }
        if (failure.get() != null) throw new AssertionError("concurrent cache/map failure", failure.get());
    }

    private static long key(final int i) {
        long value = i * 0x9e3779b97f4a7c15L;
        value = (value ^ (value >>> 30)) * 0xbf58476d1ce4e5b9L;
        value = (value ^ (value >>> 27)) * 0x94d049bb133111ebL;
        return value ^ (value >>> 31);
    }
    private static void testConcurrentResize() {
        for (final int initialCapacity : new int[]{4, 1 << 16}) {
            final RaceGame.EdgeLegalCache cache = new RaceGame.EdgeLegalCache(initialCapacity);
            final int count = 120_000;
            final Runnable[] tasks = new Runnable[4];
            for (int worker = 0; worker < tasks.length; worker++) {
                final int offset = worker;
                tasks[worker] = () -> {
                    for (int i = offset; i < count; i += tasks.length) {
                        final long k = key(i);
                        final boolean value = (i & 1) == 0;
                        cache.put(k, value);
                        check(cache.get(k) == (value ? RaceGame.EdgeLegalCache.TRUE : RaceGame.EdgeLegalCache.FALSE),
                                "concurrent table lookup changed verdict");
                    }
                };
            }
            together(tasks);
            for (int i = 0; i < count; i++)
                check(cache.get(key(i)) == ((i & 1) == 0 ? RaceGame.EdgeLegalCache.TRUE : RaceGame.EdgeLegalCache.FALSE),
                        "resizing lost a key or changed its verdict: " + i);
        }
    }

    private static RaceGame corridor() {
        final Properties props = new Properties();
        props.setProperty("aiStartPlacement", "informed");
        final RaceGame game = new RaceGame(props);
        game.gameCols = 12;
        game.gameRows = 4;
        game.totalLaps = 1;
        game.track = new Track();
        game.track.addLeft(0, 0); game.track.addLeft(12, 0);
        game.track.addRight(0, 4); game.track.addRight(12, 4);
        game.trackA = TrackGeometry.getToleranceExpandedShape(new Rectangle2D.Double(0, 0, 12, 4));
        game.startZoneA = new Area();
        game.finishLine = new Line2D.Double(11, 0, 11, 4);
        game.lapGates = new Line2D[]{game.finishLine, new Line2D.Double(4, 0, 4, 4), new Line2D.Double(8, 0, 8, 4)};
        set(game, "lapCrossGate", new Line2D.Double(11, .3, 11, 3.7));
        set(game, "lapFwdX", 1.0); set(game, "lapFwdY", 0.0);
        set(game, "finishFwdX", 1.0); set(game, "finishFwdY", 0.0);
        game.players = new Player[]{new Player("A", 1, Color.BLUE, Player.Kind.AI2),
                new Player("B", 2, Color.RED, Player.Kind.AI2)};
        game.players[0].setPosition(new int[]{1, 1});
        game.players[1].setPosition(new int[]{2, 2});
        // No dense cache: force the production fallback without large map allocations.
        check(get(game, "denseEdgeLegalCache") == null, "fixture did not force fallback");
        return game;
    }

    private static void testConcurrentGeometry() {
        final RaceGame game = corridor();
        final Runnable query = () -> {
            try {
                for (int x = 0; x <= game.gameCols; x++) for (int y = 0; y <= game.gameRows; y++)
                    for (int dx = -4; dx <= 4; dx++) for (int dy = -4; dy <= 4; dy++)
                        check(game.isMoveLegalGeometry(x, y, x + dx, y + dy)
                                        == game.isMoveLegalGeometryCached(x, y, x + dx, y + dy),
                                "cached geometry disagrees with the referee");
            } finally { game.clearPointContainmentCacheForCurrentThread(); }
        };
        together(query, query, query, query);
        check(get(game, "edgeLegalCache") != null, "fallback publication was not exercised");
    }

    private static void prepareReach(final RaceGame game) {
        try {
            game.reach.computeReachability();
            game.reach.computeGateMaps(game.lapGates);
        } finally { game.clearPointContainmentCacheForCurrentThread(); }
    }
    private static void testParallelMaps() {
        final RaceGame serial = corridor();
        serial.reach.computeDistMap();
        prepareReach(serial);
        final OptimalPotential expected = OptimalPotential.build(serial, 1, 16L << 20);
        check(expected != null, "small exact map missing");
        for (int iteration = 0; iteration < 3; iteration++) {
            final RaceGame parallel = corridor();
            parallel.reach.computeDistMap();
            final AtomicReference<OptimalPotential> actual = new AtomicReference<>();
            together(() -> prepareReach(parallel), () -> {
                try { actual.set(OptimalPotential.build(parallel, 1, 16L << 20)); }
                finally { parallel.clearPointContainmentCacheForCurrentThread(); }
            });
            check(actual.get() != null, "parallel exact map missing");
            check(Arrays.equals((short[]) get(expected, "dist"), (short[]) get(actual.get(), "dist")),
                    "parallel exact distances changed");
            for (final Field f : Reachability.class.getDeclaredFields()) {
                if (java.lang.reflect.Modifier.isStatic(f.getModifiers())) continue;
                final Class<?> type = f.getType();
                if (type.isArray() || type == java.util.BitSet.class) {
                    check(java.util.Objects.deepEquals(get(serial.reach, f.getName()), get(parallel.reach, f.getName())),
                            "parallel reachability data changed: " + f.getName());
                }
            }
        }
    }

    private static void testPreparationFailures() {
        for (final Throwable failure : new Throwable[]{new OutOfMemoryError("injected preparation failure"),
                new IllegalStateException("injected preparation failure"), new LinkageError("injected preparation failure")}) {
            final RaceGame game = corridor();
            set(game, "gamestate", GameState.PLAY);
            set(game, "rui", new RaceUI(game.gameRows, game.gameCols));
            set(game, "isShowingPrePath", 5);
            final GameUI ui = (GameUI) get(game, "gameFrame");
            ui.setStatus("Computing track reachability...");
            ui.setUndoEnabled(true); ui.setOkEnabled(true);
            set(game.reach, "reachabilityFailure", failure);
            set(game.reach, "reachabilityReady", true);
            invoke(game, "doAiTurn");
            check(get(game, "gamestate") == GameState.FINISHED, "preparation failure left the race playing");
            check(get(ui, "status").toString().contains(failure.toString()), "failure not shown in persistent status");
            check(Boolean.FALSE.equals(get(ui, "undoEnabled")) && Boolean.FALSE.equals(get(ui, "okEnabled")),
                    "failed-race controls left enabled");
            check(Integer.valueOf(-1).equals(get(game, "isShowingPrePath")), "stale move preview retained");
            check(game.turnCount() == 0 && get(game, "gameLog").toString().isEmpty(), "failed preparation committed a move/result");
            invoke(game, "doAiTurn"); // already queued callbacks are harmless
            check(game.turnCount() == 0, "queued AI callback resumed a failed race");
        }
    }

    private static void testCacheGeneration() {
        final RaceGame game = corridor();
        final java.nio.file.Path directory = TrackIO.reachCacheDir();
        check(directory.getFileName().toString().equals("maps-v2"), "unsafe map generation was not retired");
        check(java.nio.file.Path.of(game.reach.geometryCacheKey()).getParent().equals(directory),
                "reachability/derived/edge cache identity bypasses the new generation");
        final String override = System.getenv("RACING_REACH_CACHE");
        if (override != null && !override.isBlank())
            check(directory.equals(java.nio.file.Path.of(override).resolve("maps-v2")), "cache root override lost");
    }

    private static void testCheckpointMetadata() {
        final RaceGame game = corridor();
        invoke(game, "initGameLog");
        check(get(game, "gameLog").toString().contains("# checkpoints enabled\n"), "one-lap checkpoint metadata missing");
        game.lapGates = null;
        invoke(game, "initGameLog");
        check(get(game, "gameLog").toString().contains("# checkpoints disabled\n"), "ungated metadata missing");
    }
}
