package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Rectangle2D;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Properties;
import java.util.Random;
import java.util.Set;
import tr.gui.RaceUI;

/** Physical occupancy and terminal lifecycle regressions from the 745798f review. */
public final class ReviewBoundaryTests {
    private ReviewBoundaryTests() { }

    public static void main(final String[] args) throws Exception {
        if (args.length == 0 || args[0].equals("physical")) testPhysicalOccupancy();
        if (args.length == 0 || args[0].equals("laps")) testLapOccupancy();
        if (args.length == 0 || args[0].equals("rollout")) testLastSurvivor();
        System.out.println("ReviewBoundaryTests: physical/lap occupancy, fail-closed budgets, survivor classification and clocks OK");
    }

    private static Player car(final int n, final int x, final int y, final int vx, final int vy) {
        return car(n, x, y, vx, vy, Player.Kind.AI1);
    }

    private static Player car(final int n, final int x, final int y, final int vx, final int vy,
            final Player.Kind kind) {
        final Player p = new Player("P" + n, n, Color.BLUE, kind);
        p.setPosition(new int[]{x, y}); p.setVelocity(new int[]{vx, vy});
        return p;
    }

    private static RaceGame straight() throws Exception {
        final RaceGame g = new RaceGame(new Properties());
        g.gameCols = 180; g.gameRows = 20; g.track = new Track();
        g.track.addLeft(0, 1); g.track.addLeft(173, 1);
        g.track.addRight(0, 19); g.track.addRight(173, 19);
        g.trackA = new Area(new Rectangle2D.Double(0, 1, 173, 18));
        g.startZoneA = new Area();
        g.finishLine = new Line2D.Double(172.5, 1, 172.5, 19);
        set(g, "finishFwdX", 1.0); set(g, "rui", new RaceUI(20, 180));
        set(g, "gamestate", GameState.PLAY);
        return g;
    }

    private static Object occupancy(final RaceGame g, final int me, final int budget) throws Exception {
        final RaceAiPrivateLane.ProofSession proof = new RaceAiPrivateLane(g).begin(me, 5, budget);
        final Object rectangles = get(proof, "rectangles");
        final Class<?> exact = Class.forName("tr.logic.RaceAiPrivateLane$ExactRivalReach");
        final Constructor<?> constructor = exact.getDeclaredConstructors()[0];
        constructor.setAccessible(true);
        return constructor.newInstance(g, g.reach, me, rectangles, budget);
    }

    private static boolean may(final Object reach, final int ply, final int x, final int y) throws Exception {
        final Method method = reach.getClass().getDeclaredMethod("mayOccupy", int.class, int.class, int.class);
        method.setAccessible(true);
        return (boolean) method.invoke(reach, ply, x, y);
    }

    private static void testPhysicalOccupancy() throws Exception {
        final RaceGame g = straight();
        g.players = new Player[]{car(1, 10, 10, 11, 0), car(2, 20, 10, 12, 0, Player.Kind.HUMAN), car(3, 16, 10, 12, 0, Player.Kind.HUMAN)};
        g.reach.computeDistMap(); g.reach.computeReachability();
        check(g.evaluateMove(0, 0, 20, 10, 33, 10, false).legal(), "speed-13 fixture must be legal");
        check(may(occupancy(g, 1, 512), 1, 33, 10), "physical speed-13 reply was excluded");
        final RaceAiPrivateLane.ProofSession proof = new RaceAiPrivateLane(g).begin(1, 5, 512);
        final int turns = g.reach.turnsToFinish(21, 10, 11, 0);
        check(!proof.certifiesApproximate(21, 10, 11, 0, turns, 3, 3), "rectangle unexpectedly certifies fixture");
        check(!proof.certifiesExact(21, 10, 11, 0, turns, 4, 3), "false three-private-exit certificate survived");
        g.players = new Player[]{g.players[0], car(2, 100, 10, -12, 0)};
        check(may(occupancy(g, 1, 512), 1, 87, 10), "negative speed-13 reply was excluded");
        g.players[1] = car(2, 80, 10, 22, 0);
        check(may(occupancy(g, 1, 512), 1, 102, 10), "out-of-map initial velocity was misencoded");
        check(!may(occupancy(g, 1, 512), 1, 70, 10), "physical state aliased a reverse velocity");
        g.players[1] = car(2, 30, 2, 0, -3);
        check(may(occupancy(g, 1, 0), 1, 30, 0), "zero budget must keep rectangle uncertainty");
        check(!may(occupancy(g, 1, 0), 1, 80, 10), "budget failure expanded beyond rectangle");

        // Independently expand detached Players via the referee overload. The
        // bounded production oracle may overapproximate, but must never miss a
        // physically reachable nonterminal cell, including initial speeds >12.
        final Random random = new Random(745798);
        int checked = 0;
        for (int sample = 0; sample < 60; sample++) {
            g.players[1] = car(2, 30 + random.nextInt(110), 3 + random.nextInt(14),
                    random.nextInt(33) - 16, random.nextInt(7) - 3);
            final Object exact = occupancy(g, 1, 512);
            Set<State> frontier = Set.of(State.of(g.players[1]));
            for (int ply = 1; ply <= 3; ply++) {
                frontier = physicalStep(g, frontier);
                for (final State state : frontier) {
                    check(may(exact, ply, state.x, state.y), "physical oracle missed sample " + sample + "/" + ply);
                    checked++;
                }
            }
        }
        System.out.println("Private-lane physical oracle: " + checked + " nonterminal states covered");
    }

    private record State(int x, int y, int vx, int vy, int lap, int gate) {
        static State of(final Player p) {
            return new State(p.getPosition()[0], p.getPosition()[1], p.getVelocity()[0],
                    p.getVelocity()[1], p.getLap(), p.getNextGate());
        }
    }

    private static Set<State> physicalStep(final RaceGame game, final Set<State> source) {
        final Set<State> next = new HashSet<>();
        for (final State s : source) {
            final Player p = car(2, s.x, s.y, s.vx, s.vy);
            for (int i = 0; i < s.lap; i++) p.incrementLap();
            p.setNextGate(s.gate);
            for (final Direction d : Direction.values()) {
                final int vx = s.vx + d.dx, vy = s.vy + d.dy;
                final int x = s.x + vx, y = s.y + vy;
                final RaceGame.MoveResult move = game.evaluateMove(p, new int[]{s.x, s.y}, new int[]{x, y});
                if (move.legal() && !move.finishes())
                    next.add(new State(x, y, vx, vy, move.lapAfter(), move.gateAfter()));
            }
        }
        return next;
    }

    private static void testLapOccupancy() throws Exception {
        final Properties properties = new Properties();
        try (java.io.InputStream in = Files.newInputStream(Path.of("tracks", "circle.track"))) {
            properties.load(in);
        }
        properties.setProperty("laps", "2");
        properties.setProperty("lastTrackLeft", properties.getProperty("trackLeft"));
        properties.setProperty("lastTrackRight", properties.getProperty("trackRight"));
        final RaceGame g = new RaceGame(properties);
        final TrackIO.TrackData data = TrackIO.loadLastTrackData(properties);
        g.gameCols = data.gameX(); g.gameRows = data.gameY(); g.track = new Track();
        for (final int[] p : data.left()) g.track.addLeft(p[0], p[1]);
        for (final int[] p : data.right()) g.track.addRight(p[0], p[1]);
        set(g, "rui", new RaceUI(g.gameRows, g.gameCols));
        g.players = new Player[]{car(1, 80, 50, 0, 0), car(2, 50, 8, 1, 0)};
        g.players[1].setNextGate(0);
        final Method build = RaceGame.class.getDeclaredMethod("buildTrackGeometry");
        build.setAccessible(true); build.invoke(g);
        g.reach.ensureReachabilityReady();
        final RaceGame.MoveResult cross = g.evaluateMove(g.players[1], new int[]{50, 8}, new int[]{52, 8});
        check(cross.legal() && cross.lapCross() && !cross.finishes() && cross.lapAfter() == 1,
                "non-final crossing fixture changed");
        check(may(occupancy(g, 1, 512), 1, 52, 8), "first lap made a live rival disappear");
        check(may(occupancy(g, 1, 512), 2, 55, 8), "lap progress was lost in a subsequent ply");
        g.players[1].incrementLap();
        check(g.evaluateMove(g.players[1], new int[]{50, 8}, new int[]{52, 8}).finishes(), "final-lap fixture changed");
        check(!may(occupancy(g, 1, 512), 1, 52, 8), "terminal finish kept a body on the board");
        for (final int gate : new int[]{0, 1, 2}) {
            g.players[1] = car(2, 50, 8, 1, 0); g.players[1].setNextGate(gate);
            final Object exact = occupancy(g, 1, 512);
            Set<State> frontier = Set.of(State.of(g.players[1]));
            for (int ply = 1; ply <= 3; ply++) {
                frontier = physicalStep(g, frontier);
                for (final State s : frontier)
                    check(may(exact, ply, s.x, s.y), "checkpoint-aware physical continuation disappeared");
            }
        }
        // Identical kinematics but different progress must not be merged.
        g.players = new Player[]{g.players[0], car(2, 50, 8, 1, 0), car(3, 50, 8, 1, 0)};
        g.players[1].incrementLap(); g.players[1].setNextGate(0); g.players[2].setNextGate(0);
        check(may(occupancy(g, 1, 512), 2, 55, 8), "different lap states were merged");
    }

    private static void testLastSurvivor() throws Exception {
        for (int mover = 0; mover < 3; mover++) {
            final RaceGame g = straight();
            g.players = new Player[]{car(1, 10, 2, 0, -4), car(2, 30, 2, 0, -4), car(3, 45, 2, 0, -4)};
            g.subgamestate = mover;
            g.reach.computeDistMap(); g.reach.computeReachability();
            final int[] audit = new int[3];
            check(g.ai.querySimOutcome(mover, 3, false, false, false, 0, audit) == 0,
                    "survivor was scheduled again after both rivals crashed, slot " + mover);
            check(audit[0] == 3 && audit[1] == 0 && audit[2] == 0, "survivor audit is not terminal");
            final int[] tier = {-99}, threads = {0, 0};
            final long[] field = {-99}, rivals = new long[3];
            check(simulate(g, mover, false, 3, tier, field, threads, rivals) == 0, "optional outputs changed terminal verdict");
            final long failure = ((Number) get(g.ai, "ROLLOUT_FAILURE_COST")).longValue();
            check(field[0] == 2 * failure, "failed rivals' field diagnostics were lost");
            for (int i = 0; i < 3; i++) if (i != mover) check(rivals[i] == failure, "failed rival cost lost");
            check(tier[0] == 3 && threads[0] == 0, "extra self ply contaminated outputs");
            // Actual referee classifies after exactly the two remaining moves.
            g.setAutoMode(true); g.setAutoRaceEndHook(() -> { });
            final Path log = Files.createTempFile("survivor-referee-", ".log");
            try {
                g.setGameLogPath(log.toString());
                for (int n = 1; n < 3; n++) {
                    final int i = (mover + n) % 3; final Player p = g.players[i];
                    for (final Direction d : Direction.values())
                        check(!g.evaluateMove(p, p.getPosition(), new int[]{p.getPosition()[0] + d.dx,
                                p.getPosition()[1] - 4 + d.dy}).legal(), "rival is not physically doomed");
                    g.subgamestate = i;
                    commit(g, new int[]{0, -4}, new int[]{p.getPosition()[0], p.getPosition()[1] - 4});
                }
                check(g.players[mover].getFinishedPlace() == 1 && g.turnCount() == 2, "referee survivor mismatch");
            } finally { Files.deleteIfExists(log); }
        }
        final RaceGame solo = straight(); solo.players = new Player[]{car(1, 10, 2, 0, -4)};
        solo.reach.computeDistMap(); solo.reach.computeReachability();
        check(solo.ai.querySimOutcome(0, 3, false, false, false, 0, null) == -1, "one-car exception was lost");
        final RaceGame g = straight();
        g.players = new Player[]{car(1, 10, 10, 0, 0), car(2, 30, 10, 0, 0), car(3, 45, 10, 0, 0)};
        g.lapGates = new Line2D[]{g.finishLine, new Line2D.Double(60, 1, 60, 19), new Line2D.Double(100, 1, 100, 19)};
        set(g, "lapCrossGate", g.finishLine); set(g, "lapFwdX", 1.0);
        g.reach.computeDistMap(); g.reach.computeReachability();
        g.setQueryTurnCounter(2251);
        check(g.ai.querySimOutcome(0, 3, false, false, false, 0, null) == 0, "rival timeouts failed to terminate rollout");
        check(simulate(g, 0, true, 0, new int[1], new long[1], new int[2], new long[3]) == -1,
                "pending own timeout became a survivor win");
        // Our candidate finishes; the rival's unreachable remaining distance must
        // not become a failure charge when it is automatically classified second.
        g.lapGates = null; g.setQueryTurnCounter(0);
        g.players = new Player[]{car(1, 171, 10, 1, 0), car(2, 30, 2, 0, -4)};
        g.subgamestate = 0;
        g.ai.querySimOutcome(0, 0, false, false, false, 0, null);
        final long[] field = {-99}, rivals = new long[2];
        check(invokeSimulate(g, 0, 173, 10, 2, 0, true, 3, new int[1], field, new int[2], rivals) == 0,
                "candidate finish was lost");
        check(field[0] == 0 && rivals[1] == 0, "classified rival was charged for a nonexistent future");
        // A rival can finish first; our last-survivor result is still terminal,
        // not a prediction that we must survive another move.
        g.players = new Player[]{car(1, 10, 2, 0, -4), car(2, 171, 10, 1, 0)};
        check(g.ai.querySimOutcome(0, 3, false, false, false, 0, null) == 0, "rival finish failed to classify survivor");
    }

    private static int simulate(final RaceGame g, final int mover, final boolean pending, final int rounds,
            final int[] tier, final long[] field, final int[] threads, final long[] rivals) throws Exception {
        final Player p = g.players[mover];
        return invokeSimulate(g, mover, p.getPosition()[0], p.getPosition()[1], p.getVelocity()[0],
                p.getVelocity()[1], pending, rounds, tier, field, threads, rivals);
    }

    private static int invokeSimulate(final RaceGame g, final int mover, final int x, final int y, final int vx,
            final int vy, final boolean pending, final int rounds, final int[] tier, final long[] field,
            final int[] threads, final long[] rivals) throws Exception {
        for (final Method m : RaceAi.class.getDeclaredMethods()) if (m.getName().equals("simulate")) {
            m.setAccessible(true);
            return (int) m.invoke(g.ai, x, y, vx, vy, g.players[mover].getNumber(), rounds, true, true,
                    true, false, false, false, 0, tier, field, threads, false, rivals, pending);
        }
        throw new AssertionError("simulate missing");
    }

    private static void commit(final RaceGame game, final int[] velocity, final int[] destination) throws Exception {
        final Method m = RaceGame.class.getDeclaredMethod("commitMove", int[].class, int[].class, int[].class);
        m.setAccessible(true); m.invoke(game, game.players[game.subgamestate].getPosition(), velocity, destination);
    }

    private static Object get(final Object object, final String name) throws Exception {
        final Field field = object.getClass().getDeclaredField(name); field.setAccessible(true); return field.get(object);
    }
    private static void set(final Object object, final String name, final Object value) throws Exception {
        final Field field = object.getClass().getDeclaredField(name); field.setAccessible(true); field.set(object, value);
    }
    private static void check(final boolean condition, final String message) {
        if (!condition) throw new AssertionError(message);
    }
}
