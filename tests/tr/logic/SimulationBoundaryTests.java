package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Rectangle2D;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Properties;
import java.util.Set;
import tr.gui.RaceUI;

/** Physical occupancy and terminal classification must agree with the referee. */
public final class SimulationBoundaryTests {
    private SimulationBoundaryTests() {}

    public static void main(final String[] args) throws Exception {
        if (args.length == 0 || args[0].equals("physical")) testPhysicalOccupancy();
        if (args.length == 0 || args[0].equals("progress")) testProgressOccupancy();
        if (args.length == 0 || args[0].equals("survivor")) testLastSurvivor();
        if (args.length == 0 || args[0].equals("candidate")) testTerminalCandidateAndSolo();
        System.out.println("SimulationBoundaryTests: physical velocities, progress, budgets, survivor costs and solo exception OK");
    }

    private static RaceGame straight() throws Exception {
        final RaceGame g = new RaceGame(new Properties());
        g.gameCols = 180; g.gameRows = 20;
        g.track = new Track();
        g.track.addLeft(0, 1); g.track.addLeft(173, 1);
        g.track.addRight(0, 19); g.track.addRight(173, 19);
        g.trackA = new Area(new Rectangle2D.Double(0, 1, 173, 18));
        g.startZoneA = new Area();
        g.finishLine = new Line2D.Double(172.5, 1, 172.5, 19);
        set(g, "finishFwdX", 1.0);
        set(g, "rui", new RaceUI(g.gameRows, g.gameCols));
        g.players = new Player[]{car(1, 10, 10, 11, 0), car(2, 20, 10, 12, 0), car(3, 16, 10, 12, 0)};
        g.reach.computeDistMap();
        g.reach.computeReachability();
        return g;
    }

    private static Player car(final int number, final int x, final int y, final int vx, final int vy) {
        final Player p = new Player("P" + number, number, Color.BLUE, Player.Kind.AI1);
        p.setPosition(new int[]{x, y}); p.setVelocity(new int[]{vx, vy});
        return p;
    }

    private static Object oracle(final RaceGame g, final int budget) throws Exception {
        final Object session = new RaceAiPrivateLane(g).begin(1, 5, budget);
        final Class<?> type = Class.forName("tr.logic.RaceAiPrivateLane$ExactRivalReach");
        final Constructor<?> constructor = type.getDeclaredConstructors()[0];
        constructor.setAccessible(true);
        return constructor.newInstance(g, g.reach, 1, get(session, "rectangles"), budget);
    }

    private static boolean may(final Object oracle, final int ply, final int x, final int y) throws Exception {
        final Method method = oracle.getClass().getDeclaredMethod("mayOccupy", int.class, int.class, int.class);
        method.setAccessible(true);
        return (boolean) method.invoke(oracle, ply, x, y);
    }

    private static void testPhysicalOccupancy() throws Exception {
        final RaceGame g = straight();
        check(g.evaluateMove(0, 0, 20, 10, 33, 10, false).legal(), "speed-13 fixture is illegal");
        check(may(oracle(g, 512), 1, 33, 10), "legal speed-13 rival reply excluded");
        final RaceAiPrivateLane.ProofSession session = new RaceAiPrivateLane(g).begin(1, 5, 512);
        final int turns = g.reach.turnsToFinish(21, 10, 11, 0);
        check(!session.certifiesApproximate(21, 10, 11, 0, turns, 3, 3), "outer rectangle unexpectedly certifies");
        check(!session.certifiesExact(21, 10, 11, 0, turns, 4, 3), "false three-private-exit certificate survives");
        // Starting speeds outside the map domain must not be packed into another cell.
        g.players = new Player[]{car(1, 10, 10, 0, 0), car(2, 80, 10, 22, 0)};
        check(may(oracle(g, 512), 1, 103, 10), "unrepresentable positive starting speed was aliased");
        g.players[1].setVelocity(new int[]{-22, 0});
        check(may(oracle(g, 512), 1, 57, 10), "unrepresentable negative starting speed was aliased");
        final Object emptyBudget = oracle(g, 0);
        check(may(emptyBudget, 1, 57, 10), "budget exhaustion must retain possible occupancy");
        check(!may(emptyBudget, 1, 120, 10), "budget exhaustion discarded the outer rectangle exclusion");
    }

    private static void gates(final RaceGame g) throws Exception {
        g.finishLine = new Line2D.Double(72.5, 1, 72.5, 19);
        g.lapGates = new Line2D[]{g.finishLine,
                new Line2D.Double(68, 1, 68, 19), new Line2D.Double(70, 1, 70, 19)};
        set(g, "lapCrossGate", g.finishLine); set(g, "lapFwdX", 1.0);
    }

    private static void testProgressOccupancy() throws Exception {
        final RaceGame g = straight();
        gates(g); g.totalLaps = 2;
        g.players = new Player[]{car(1, 10, 10, 0, 0), car(2, 71, 10, 1, 0)};
        final Player rival = g.players[1]; rival.setNextGate(0);
        final RaceGame.MoveResult crossing = g.evaluateMove(rival, rival.getPosition(), new int[]{73, 10});
        check(crossing.legal() && crossing.lapCross() && !crossing.finishes() && crossing.lapAfter() == 1,
                "non-final crossing fixture is not a continuing lap");
        check(may(oracle(g, 512), 1, 73, 10), "non-final lap crossing removed a rival");
        check(may(oracle(g, 512), 2, 76, 10), "rival cannot continue after its non-final crossing");
        rival.incrementLap();
        check(g.evaluateMove(rival, rival.getPosition(), new int[]{73, 10}).finishes(), "terminal fixture did not finish");
        check(!may(oracle(g, 512), 1, 73, 10), "genuine terminal crossing remained an occupant");
        rival.setNextGate(1);
        check(may(oracle(g, 512), 1, 73, 10), "owed checkpoints were ignored at a geometric crossing");
        rival.setPosition(new int[]{65, 10}); rival.setVelocity(new int[]{10, 0});
        final RaceGame.MoveResult combined = g.evaluateMove(rival, rival.getPosition(), new int[]{76, 10});
        check(combined.passCp1() && combined.passCp2() && combined.finishes(), "ordered triple event fixture failed");
        check(!may(oracle(g, 512), 1, 76, 10), "combined checkpoint/finish events were not terminal");
        // Same kinematics but different progress cannot collapse to the terminal state.
        final Player continuing = car(3, 65, 10, 10, 0); continuing.setNextGate(1);
        g.players = new Player[]{g.players[0], rival, continuing};
        check(may(oracle(g, 512), 1, 76, 10), "different progress ledgers were deduplicated");
        // Exhaustive detached Player transitions are independent of frontier encoding.
        final int[] before = continuing.lapState();
        for (int ply = 1; ply <= 3; ply++) {
            final Set<String> endpoints = new HashSet<>();
            enumerate(g, continuing, ply, endpoints);
            final Object exact = oracle(g, 100_000);
            for (final String endpoint : endpoints) {
                final String[] xy = endpoint.split(",");
                check(may(exact, ply, Integer.parseInt(xy[0]), Integer.parseInt(xy[1])),
                        "exact search omitted physical path " + endpoint + " at ply " + ply);
            }
        }
        check(Arrays.equals(before, continuing.lapState()), "occupancy search changed live progress");
    }

    private static void enumerate(final RaceGame g, final Player p, final int steps,
            final Set<String> endpoints) {
        for (final Direction d : Direction.values()) {
            final int[] x = p.getPosition(), v = p.getVelocity();
            final int[] nv = {v[0] + d.dx, v[1] + d.dy};
            final int[] nx = {x[0] + nv[0], x[1] + nv[1]};
            final RaceGame.MoveResult r = g.evaluateMove(p.getLap(), p.getNextGate(), x[0], x[1], nx[0], nx[1], false);
            if (!r.legal() || r.finishes()) continue;
            if (steps == 1) { endpoints.add(nx[0] + "," + nx[1]); continue; }
            final Player next = car(p.getNumber(), nx[0], nx[1], nv[0], nv[1]);
            for (int lap = 0; lap < r.lapAfter(); lap++) next.incrementLap();
            next.setNextGate(r.gateAfter());
            enumerate(g, next, steps - 1, endpoints);
        }
    }

    private static int simulate(final RaceGame g, final int mover, final int rounds, final boolean pending,
            final int[] landing, final int[] velocity, final int[] tier, final long[] field,
            final int[] threads, final long[] rival) throws Exception {
        final Method prepare = RaceAi.class.getDeclaredMethod("prepareDecisionFrame", int[].class, int[].class, int.class);
        prepare.setAccessible(true);
        final Player me = g.players[mover];
        prepare.invoke(g.ai, me.getPosition(), me.getVelocity(), me.getNumber());
        for (final Method method : RaceAi.class.getDeclaredMethods()) {
            if (!method.getName().equals("simulate")) continue;
            method.setAccessible(true);
            return (int) method.invoke(g.ai, landing[0], landing[1], velocity[0], velocity[1], me.getNumber(), rounds,
                    true, true, true, false, false, false, 0, tier, field, threads, false, rival, pending);
        }
        throw new AssertionError("missing simulation entry point");
    }

    private static long projectedClock(final RaceGame g) throws Exception {
        return ((Number) get(((Object[]) get(g.ai, "rolloutsByDepth"))[1], "turns")).longValue();
    }

    private static void testLastSurvivor() throws Exception {
        final RaceGame g = straight();
        for (int mover = 0; mover < 3; mover++) {
            for (int kind = 0; kind < 3; kind++) {
                g.players = new Player[]{car(1, 10, 2, 0, -4), car(2, 30, 2, 0, -4), car(3, 45, 2, 0, -4)};
                g.subgamestate = mover;
                g.lapGates = null; g.finishLine = new Line2D.Double(172.5, 1, 172.5, 19); g.setQueryTurnCounter(0);
                if (kind == 1) { // Finish one rival, crash the other; survivor gets second place.
                    final int finishing = (mover + 1) % 3;
                    g.players[finishing].setPosition(new int[]{172, 10});
                    g.players[finishing].setVelocity(new int[]{3, 0});
                } else if (kind == 2) { gates(g); g.setQueryTurnCounter(2251); }
                final int[] tier = {0}, threads = {0, 0};
                final long[] field = {-9}, rivals = {-9, -9, -9};
                final Player me = g.players[mover];
                final int value = simulate(g, mover, 3, false, me.getPosition(), me.getVelocity(), tier, field, threads, rivals);
                // Round 274, rank first: a survivor classified behind a finisher is one
                // place down, not a win -- the verdict carries the rival ahead.
                check(value == (kind == 1 ? RaceAi.VERDICT_PLACE_STRIDE : 0) && tier[0] == 3,
                        "survivor was required to move after terminal retirement: kind=" + kind + " value=" + value);
                check(threads[0] == 0 && threads[1] == 0, "a phantom survivor turn was audited");
                check(projectedClock(g) == g.turnCount() + 2L, "rollout continued beyond two retirements");
                check(field[0] == (kind == 1 ? 1_000_000 : 2_000_000), "retired rival costs were lost: mover=" + mover + " kind=" + kind + " field=" + field[0]);
                check(rivals[mover] == -1, "mover acquired a rival cost");
                check(!me.isFinished() && (int) get(g.ai, "simDepth") == 0, "projected result leaked into the live board");
            }
        }
        g.lapGates = null; g.setQueryTurnCounter(0); g.subgamestate = 0;
        g.players = new Player[]{car(1, 10, 2, 0, -4), car(2, 30, 2, 0, -4), car(3, 45, 2, 0, -4)};
        g.players[2].setFinishedPlace(3);
        check(simulate(g, 0, 1, false, g.players[0].getPosition(), g.players[0].getVelocity(),
                new int[1], null, null, null) == 0, "terminal event on last horizon ply was missed");
        check(projectedClock(g) == 1, "already classified rival moved again");
    }

    private static void testTerminalCandidateAndSolo() throws Exception {
        final RaceGame g = straight();
        g.players = new Player[]{car(1, 171, 10, 2, 0), car(2, 30, 2, 0, -4)};
        final long[] rivals = new long[2], field = new long[1];
        check(simulate(g, 0, 4, true, new int[]{174, 10}, new int[]{3, 0}, new int[1], field, null, rivals) == 0,
                "finishing candidate was lost");
        check(projectedClock(g) == 1 && rivals[1] == 0 && field[0] == 0,
                "last rival was charged a phantom failure after our finish");
        check(simulate(g, 0, 4, true, new int[]{174, 10}, new int[]{3, 0}, new int[1], null, null, rivals) == 0
                && rivals[1] == 0, "rival-only output was left incomplete");
        gates(g); g.setQueryTurnCounter(1501);
        check(simulate(g, 0, 4, true, new int[]{174, 10}, new int[]{3, 0}, null, null, null, null) == -1,
                "candidate finish overrode mover-first timeout");
        g.lapGates = null; g.setQueryTurnCounter(0);
        g.players = new Player[]{car(1, 10, 2, 0, -4)};
        check(simulate(g, 0, 2, false, g.players[0].getPosition(), g.players[0].getVelocity(),
                null, null, null, null) == -1, "solo time trial was automatically classified as a survivor");
    }

    private static Object get(final Object o, final String name) throws Exception {
        final Field f = o.getClass().getDeclaredField(name); f.setAccessible(true); return f.get(o);
    }
    private static void set(final Object o, final String name, final Object value) throws Exception {
        final Field f = o.getClass().getDeclaredField(name); f.setAccessible(true); f.set(o, value);
    }
    private static void check(final boolean condition, final String message) {
        if (!condition) throw new AssertionError(message);
    }
}
