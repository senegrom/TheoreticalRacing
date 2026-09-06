package tr.logic;

import java.awt.Color;
import java.awt.Shape;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Rectangle2D;
import java.lang.reflect.Field;
import java.util.ArrayDeque;
import java.util.HashSet;
import java.util.Properties;
import tr.gui.RaceUI;

/** Differential contracts for checkpoint events, exact solvers and rendering. */
final class FollowupRuleTests {
    private FollowupRuleTests() {}

    static void run() {
        testCombinedEvents();
        testTerminalGridExit();
        testRendererUsesRefereeGeometry();
        testAutomaticGateGeometry();
        testEndgameProgressGuard();
        testCandidateProgressAndRestoration();
        System.out.println("FollowupRuleTests: OK");
    }

    private static RaceGame corridor(final int width, final int finish, final int cp1, final int cp2) {
        final RaceGame g = new RaceGame(new Properties());
        g.gameCols = width;
        g.gameRows = 4;
        g.totalLaps = 1;
        g.track = new Track();
        g.track.addLeft(0, 0);
        g.track.addLeft(width, 0);
        g.track.addRight(0, 4);
        g.track.addRight(width, 4);
        g.trackA = TrackGeometry.getToleranceExpandedShape(new Rectangle2D.Double(0, 0, width, 4));
        g.startZoneA = new Area();
        g.finishLine = new Line2D.Double(finish, 0, finish, 4);
        g.lapGates = new Line2D[]{g.finishLine, new Line2D.Double(cp1, 0, cp1, 4),
                new Line2D.Double(cp2, 0, cp2, 4)};
        set(g, "lapCrossGate", new Line2D.Double(finish, .3, finish, 3.7));
        set(g, "lapFwdX", 1.0);
        set(g, "lapFwdY", 0.0);
        g.players = new Player[]{new Player("A", 1, Color.BLUE, Player.Kind.AI1)};
        return g;
    }

    private record State(int x, int y, int vx, int vy, int lap, int gate) {}
    private record Node(State state, int distance) {}

    /** Independent forward traversal of the public referee result, with no
     * gate-count encoding or optimal-solver event logic duplicated here. */
    private static int referenceBfs(final RaceGame game, final int startX, final int startY) {
        final ArrayDeque<Node> queue = new ArrayDeque<>();
        final HashSet<State> seen = new HashSet<>();
        final State start = new State(startX, startY, 0, 0, 0, 1);
        seen.add(start);
        queue.add(new Node(start, 0));
        while (!queue.isEmpty()) {
            final Node node = queue.remove();
            final State s = node.state();
            final Player p = game.players[0];
            p.restoreLapState(new int[]{s.lap(), s.gate(), 0, 0, 0, 0});
            for (final Direction d : Direction.values()) {
                final int vx = s.vx() + d.dx, vy = s.vy() + d.dy;
                final int nx = s.x() + vx, ny = s.y() + vy;
                if (RaceGame.aiVelocityOutOfRange(vx, vy))
                    continue;
                final RaceGame.MoveResult result = game.evaluateMove(p,
                        new int[]{s.x(), s.y()}, new int[]{nx, ny});
                if (result.finishes())
                    return node.distance() + 1;
                if (!result.legal() || nx < 0 || ny < 0 || nx > game.gameCols || ny > game.gameRows)
                    continue;
                final State next = new State(nx, ny, vx, vy, result.lapAfter(), result.gateAfter());
                if (seen.add(next))
                    queue.add(new Node(next, node.distance() + 1));
            }
        }
        return -1;
    }

    private static void testCombinedEvents() {
        final RaceGame g = corridor(8, 7, 5, 6);
        final OptimalPotential pot = OptimalPotential.build(g, 1, 16L << 20);
        check(pot != null, "small potential was skipped");
        check(OptimalPotential.build(g, 1, pot.retainedBytes() + 1024) == null,
                "potential ignored construction/frontier memory budget");
        for (final int gate : new int[]{1, 2, 0}) {
            final int remaining = OptimalPotential.remainingEvents(gate, 0, 1);
            final RaceGame.MoveResult r = g.evaluateMove(0, gate, 4, 2, 8, 2, false);
            check(r.finishes(), "fixture must finish after all remaining events");
            check(pot.movesToFinish(remaining, 4, 2, 4, 0) == 1,
                    "terminal predecessor missing for gate " + gate);
            final Direction d = pot.bestMove(g, 4, 2, 4, 0, remaining);
            check(d != null && g.evaluateMove(0, gate, 4, 2, 8 + d.dx, 2 + d.dy, false).finishes(),
                    "potential's descent must finish legally");
        }
        for (final int laps : new int[]{1, 2}) {
            g.totalLaps = laps;
            final OptimalPotential multi = OptimalPotential.build(g, laps, 16L << 20);
            check(multi != null, "small multi-lap potential was skipped");
            for (final int start : new int[]{3, 4, 5}) {
                final int expected = referenceBfs(g, start, 2);
                check(OptimalLap.solve(g, start, 2, laps) == expected, "forward solver disagrees with referee");
                final int got = multi.movesToFinish(3 * laps, start, 2, 0, 0);
                check(got == (expected < 0 ? Integer.MAX_VALUE : expected),
                        "reverse solver disagrees with referee");
            }
        }
    }

    private static void testTerminalGridExit() {
        final RaceGame g = corridor(10, 10, 3, 5);
        final OptimalPotential pot = OptimalPotential.build(g, 1, 16L << 20);
        check(pot != null, "small potential was skipped");
        check(g.evaluateMove(0, 0, 9, 2, 13, 2, false).finishes(), "post-line exit should finish");
        check(pot.movesToFinish(1, 9, 2, 4, 0) == 1, "out-of-grid terminal seed was dropped");
        final Direction d = pot.bestMove(g, 9, 2, 4, 0, 1);
        check(d != null && g.evaluateMove(0, 0, 9, 2, 13 + d.dx, 2 + d.dy, false).finishes(),
                "out-of-grid terminal descent missing");
        final int expected = referenceBfs(g, 2, 2);
        check(OptimalLap.solve(g, 2, 2, 1) == expected, "forward solver clips final landing");
        // A non-final crossing does NOT acquire the terminal landing exemption.
        g.totalLaps = 2;
        check(!g.evaluateMove(0, 0, 9, 2, 13, 2, false).legal(), "mid-race grid exit became legal");
    }

    private static void testRendererUsesRefereeGeometry() {
        final RaceUI ui = new RaceUI(20, 20);
        final Area annulus = new Area(new Rectangle2D.Double(1, 1, 18, 18));
        annulus.subtract(new Area(new Rectangle2D.Double(5, 5, 10, 10)));
        final Line2D gate = new Line2D.Double(3, 1.3, 3, 4.7);
        ui.finishTrack(annulus);
        ui.setFinishLine(gate);
        final Shape painted = (Shape) get(ui, "trackPol");
        final Line2D visible = (Line2D) get(ui, "finishLine");
        check(painted.contains(3 * RaceUI.GRID_DIST, 3 * RaceUI.GRID_DIST), "closure band lost");
        check(!painted.contains(10 * RaceUI.GRID_DIST, 10 * RaceUI.GRID_DIST), "lap hole filled");
        check(visible.getX1() == gate.getX1() * RaceUI.GRID_DIST
                && visible.getY1() == gate.getY1() * RaceUI.GRID_DIST
                && visible.getY2() == gate.getY2() * RaceUI.GRID_DIST, "finish rounded or misplaced");
        annulus.reset();
        gate.setLine(0, 0, 0, 0);
        check(painted.contains(3 * RaceUI.GRID_DIST, 3 * RaceUI.GRID_DIST), "renderer aliases source area");
        check(visible.getX1() == 3 * RaceUI.GRID_DIST, "renderer aliases source line");
    }

    private static void testAutomaticGateGeometry() {
        final RaceGame g = new RaceGame(new Properties());
        g.gameCols = 30;
        g.gameRows = 14;
        g.track = new Track();
        for (final int[] p : new int[][]{{20, 0}, {30, 0}, {30, 14}, {0, 14}, {0, 0}})
            g.track.addLeft(p[0], p[1]);
        for (int x = 5; x <= 19; x++)
            g.track.addLeft(x, 0);
        for (final int[] p : new int[][]{{20, 4}, {26, 4}, {26, 10}, {4, 10}, {4, 4}})
            g.track.addRight(p[0], p[1]);
        for (int x = 5; x <= 19; x++)
            g.track.addRight(x, 4);
        g.players = new Player[]{new Player("A", 1, Color.BLUE, Player.Kind.AI1)};
        final RaceUI ui = new RaceUI(14, 30);
        set(g, "rui", ui);
        try {
            final var valid = RaceGame.class.getDeclaredMethod("isTrackSelfIntersecting");
            valid.setAccessible(true);
            check(!(boolean) valid.invoke(g), "auto-gate fixture intersects itself");
            final var build = RaceGame.class.getDeclaredMethod("buildTrackGeometry");
            build.setAccessible(true);
            build.invoke(g);
            g.reach.ensureReachabilityReady();
        } catch (final ReflectiveOperationException error) {
            throw new AssertionError(error);
        }
        check(g.lapGates != null, "actual gate generator rejected fixture");
        final Line2D actual = (Line2D) get(g, "lapCrossGate");
        final Line2D painted = (Line2D) get(ui, "finishLine");
        check(painted.getX1() == actual.getX1() * RaceUI.GRID_DIST
                && painted.getY1() == actual.getY1() * RaceUI.GRID_DIST
                && painted.getX2() == actual.getX2() * RaceUI.GRID_DIST
                && painted.getY2() == actual.getY2() * RaceUI.GRID_DIST,
                "game sent legacy finish line to renderer");
        final Shape corridor = (Shape) get(ui, "trackPol");
        for (int x = 0; x <= g.gameCols; x++)
            for (int y = 0; y <= g.gameRows; y++)
                check(g.trackA.contains(x, y) == corridor.contains(x * RaceUI.GRID_DIST, y * RaceUI.GRID_DIST),
                        "painted corridor differs from referee at " + x + "," + y);
        final OptimalPotential pot = OptimalPotential.build(g, 1, 32L << 20);
        check(g.evaluateMove(0, 2, 12, 2, 21, 2, false).finishes(), "actual CP2/SF fixture does not finish");
        check(pot != null && pot.movesToFinish(2, 12, 2, 9, 0) == 1,
                "auto-generated CP2/SF crossing is not a one-move optimum");
    }

    private static void testEndgameProgressGuard() {
        final RaceGame g = corridor(10, 9, 3, 6);
        g.totalLaps = 99;
        g.players = new Player[]{new Player("A", 1, Color.BLUE, Player.Kind.AI1),
                new Player("B", 2, Color.RED, Player.Kind.AI2)};
        g.players[0].setPosition(new int[]{7, 2});
        g.players[1].setPosition(new int[]{8, 3});
        set(g.ai, "frameLapAware", new boolean[]{true, false});
        set(g.ai, "lapAware", true);
        check(invokeEndgame(g) == null, "non-final mover entered terminal-only minimax");
        set(g.ai, "frameLapAware", new boolean[]{false, true});
        set(g.ai, "lapAware", false);
        check(invokeEndgame(g) == null, "non-final rival entered terminal-only minimax");
    }

    private static void testCandidateProgressAndRestoration() {
        final RaceGame g = corridor(8, 7, 5, 6);
        g.totalLaps = 2;
        final Player p = g.players[0];
        p.setPosition(new int[]{4, 2});
        p.setVelocity(new int[]{1, 0});
        p.setNextGate(1);
        g.setQueryTurnCounter(10);
        try {
            final var prepare = RaceAi.class.getDeclaredMethod("prepareDecisionFrame", int[].class, int[].class, int.class);
            prepare.setAccessible(true);
            prepare.invoke(g.ai, p.getPosition(), p.getVelocity(), 1);
            final int[] outerGates = (int[]) get(g.ai, "frameGate");
            final int[] savedGates = outerGates.clone();
            final int[] savedLap = p.lapState();
            final var simulate = RaceAi.class.getDeclaredMethod("scorerFieldOutcome", int.class, int.class,
                    int.class, int.class, int.class, int.class, int.class, long[].class);
            simulate.setAccessible(true);
            // With one simulated round and no later player, only the candidate
            // executes. It collects CP1 and CP2; the next simulated frame must
            // already owe S/F, while the live player's ledger must not change.
            simulate.invoke(g.ai, 6, 2, 2, 0, 1, 1, 0, new long[1]);
            final Object[] workspaces = (Object[]) get(g.ai, "rolloutsByDepth");
            check(((int[]) get(workspaces[1], "gates"))[0] == 0, "initial candidate kept old checkpoint");
            check((int) get(workspaces[1], "turns") == 11, "initial candidate was not counted once");
            check(get(g.ai, "frameGate") == outerGates && java.util.Arrays.equals(savedGates, outerGates),
                    "rollout leaked its frame into outer decision");
            check(java.util.Arrays.equals(savedLap, p.lapState()) && p.getPosition()[0] == 4,
                    "rollout mutated live player progress or position");
            check(g.turnCount() == 10 && (int) get(g.ai, "simDepth") == 0, "rollout did not restore clock/depth");
        } catch (final ReflectiveOperationException error) {
            throw new AssertionError(error);
        }
    }

    private static Object invokeEndgame(final RaceGame g) {
        try {
            final var method = RaceAi.class.getDeclaredMethod("endgameSolve", int[].class, int[].class, int.class);
            method.setAccessible(true);
            return method.invoke(g.ai, g.players[0].getPosition(), new int[]{1, 0}, 1);
        } catch (final ReflectiveOperationException error) {
            throw new AssertionError(error);
        }
    }

    private static Object get(final Object target, final String name) {
        try {
            final Field field = target.getClass().getDeclaredField(name);
            field.setAccessible(true);
            return field.get(target);
        } catch (final ReflectiveOperationException error) {
            throw new AssertionError(error);
        }
    }

    private static void set(final Object target, final String name, final Object value) {
        try {
            final Field field = target.getClass().getDeclaredField(name);
            field.setAccessible(true);
            field.set(target, value);
        } catch (final ReflectiveOperationException error) {
            throw new AssertionError(error);
        }
    }

    private static void check(final boolean condition, final String message) {
        if (!condition)
            throw new AssertionError(message);
    }
}
