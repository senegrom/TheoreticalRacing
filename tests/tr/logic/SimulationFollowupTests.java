package tr.logic;

import java.awt.Color;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Properties;
import java.util.Set;
import tr.gui.RaceUI;

/** Referee transitions, not map heuristics or geometric crossings, end a race. */
public final class SimulationFollowupTests {
    private SimulationFollowupTests() {}

    public static void main(final String[] args) throws Exception {
        if (args.length == 0 || args[0].equals("blockade")) testLegalBlockade();
        if (args.length == 0 || args[0].equals("proxy")) testProxyAbstention();
        if (args.length == 0 || args[0].equals("progress")) testMoverProgress();
        System.out.println("SimulationFollowupTests: legal blockades, proxy continuations and mover progress OK");
    }

    private static void testLegalBlockade() throws Exception {
        for (int my = 0; my < 2; my++) {
            final RaceGame g = fixture(RaceAiTacticsTests.class, "hairpin");
            set(g, "rui", new RaceUI(g.gameRows, g.gameCols));
            g.players = new Player[2];
            g.players[my] = car(my + 1, 17, 25, 1, -2);
            g.players[1 - my] = car(2 - my, 15, 22, 2, 2);
            g.reach.computeDistMap(); g.reach.computeReachability();
            g.subgamestate = 1 - my;
            final Direction chosen = g.ai.computeAiMove();
            check(chosen == Direction.NONE, "fixture no longer selects the winning blockade");
            final Player rival = g.players[1 - my];
            final int[] position = rival.getPosition(), velocity = rival.getVelocity();
            final int[] landing = {17, 24};
            final RaceGame.MoveResult transition = g.evaluateMove(rival, position, landing);
            check(transition.legal() && !transition.finishes()
                    && !g.reach.isAlive(17, 24, 2, 2), "blockade must be legal but map-dead");
            g.subgamestate = my;
            final String before = state(g);
            for (final boolean full : new boolean[]{false, true}) {
                for (final boolean self : new boolean[]{false, true}) {
                    final int[] audit = new int[3];
                    check(g.ai.querySimOutcome(my, 3, true, full, self, 1, audit) == -1,
                            "legal rival blockade was converted to a retirement");
                    check(state(g).equals(before), "rollout changed the live board or clock");
                }
            }
            // Execute the real two-action referee sequence, not a duplicate classifier.
            set(g, "gamestate", GameState.PLAY);
            g.setAutoMode(true); g.setAutoRaceEndHook(() -> {});
            final Path log = Files.createTempFile("blockade-followup-", ".log");
            try {
                g.setGameLogPath(log.toString());
                g.subgamestate = 1 - my;
                commit(g, position, velocity, landing);
                final Player me = g.players[my];
                for (final Direction d : Direction.values()) {
                    final int[] p = me.getPosition(), v = me.getVelocity();
                    check(!g.evaluateMove(me, p, new int[]{p[0] + v[0] + d.dx, p[1] + v[1] + d.dy}).legal(),
                            "fixture leaves a physical escape");
                }
                final int[] p = me.getPosition(), v = me.getVelocity();
                commit(g, p, v, new int[]{p[0] + v[0], p[1] + v[1]});
                check(me.getFinishedPlace() == 2 && rival.getFinishedPlace() == 1 && g.turnCount() == 2,
                        "live referee disagrees with the corrected rollout");
            } finally { Files.deleteIfExists(log); }
        }
    }

    private static void testProxyAbstention() throws Exception {
        final RaceGame g = fixture(RaceAiTacticsTests.class, "hairpin");
        g.players = new Player[]{car(1, 30, 8, 0, 0), car(2, 15, 22, 2, 2),
                car(3, 16, 23, 0, 0), car(4, 16, 24, 0, 0)};
        g.reach.computeDistMap(); g.reach.computeReachability();
        int legal = 0, alive = 0;
        for (final Direction d : Direction.values()) {
            final int x = 17 + d.dx, y = 24 + d.dy;
            if (!g.evaluateMove(g.players[1], new int[]{15, 22}, new int[]{x, y}).legal()) continue;
            legal++;
            if (g.reach.isAlive(x, y, 2 + d.dx, 2 + d.dy)) alive++;
        }
        check(legal > 0 && alive == 0, "proxy fixture needs legal but no map-alive actions");
        g.subgamestate = 0;
        final String before = state(g);
        g.ai.querySimOutcome(0, 1, false, false, false, 0, null);
        Object workspace = ((Object[]) get(g.ai, "rolloutsByDepth"))[1];
        check(((boolean[]) get(workspace, "alive"))[1], "proxy abstention retired a legal car");
        check(state(g).equals(before), "physical fallback changed the live players");

        // The fallback is a physical model, not another AI-capped map lookup.
        final RaceGame straight = fixture(SimulationBoundaryTests.class, "straight");
        straight.players = new Player[]{car(1, 10, 10, 0, 0), car(2, 80, 10, 22, 0)};
        straight.subgamestate = 0;
        straight.ai.querySimOutcome(0, 1, false, false, false, 0, null);
        workspace = ((Object[]) get(straight.ai, "rolloutsByDepth"))[1];
        check(((boolean[]) get(workspace, "alive"))[1], "high-speed legal continuation retired");
        check(((int[]) get(workspace, "px"))[1] >= 101, "fallback failed to advance the physical car");
        // Genuine crashes still retire immediately, including real-scorer actions.
        straight.players[1] = car(2, 30, 2, 0, -4);
        check(straight.ai.querySimOutcome(0, 1, true, true, false, 1, null) == 0,
                "genuine retirement did not classify the survivor");
    }

    private static RaceGame circle() throws Exception {
        // Read the unchanged fixture from the checkout; no installation or saved-settings writes.
        final Properties p = new Properties();
        try (InputStream in = Files.newInputStream(Path.of("tracks/circle.track"))) { p.load(in); }
        p.setProperty("laps", "2");
        p.setProperty("lastTrackLeft", p.getProperty("trackLeft"));
        p.setProperty("lastTrackRight", p.getProperty("trackRight"));
        final TrackIO.TrackData data = TrackIO.loadLastTrackData(p);
        check(data != null, "invalid Circle fixture");
        final RaceGame g = new RaceGame(p);
        g.totalLaps = 2; g.gameCols = data.gameX(); g.gameRows = data.gameY();
        g.track = new Track();
        for (final int[] xy : data.left()) g.track.addLeft(xy[0], xy[1]);
        for (final int[] xy : data.right()) g.track.addRight(xy[0], xy[1]);
        set(g, "rui", new RaceUI(g.gameRows, g.gameCols));
        g.players = new Player[]{car(1, 48, 8, 1, 0), car(2, 52, 8, 0, 0)};
        final Method build = RaceGame.class.getDeclaredMethod("buildTrackGeometry");
        build.setAccessible(true); build.invoke(g);
        g.reach.ensureReachabilityReady();
        return g;
    }

    private static void testMoverProgress() throws Exception {
        final RaceGame g = circle();
        final Player me = g.players[0];
        final String before = state(g);
        for (final Direction d : Direction.values()) {
            final int x = 52 + d.dx, y = 8 + d.dy;
            final RaceGame.MoveResult move = g.evaluateMove(0, 0, 50, 8, x, y, false);
            check(g.crossesFinishLegally(50, 8, x, y) && move.legal() && !move.finishes(),
                    "first-lap exits must cross without finishing");
            check(g.evaluateMove(0, 0, 52, 8, x, y, false).legal(), "rival cannot cover an exit");
        }
        check(!certificate(g, false, 50, 8, 2, 0) && !certificate(g, true, 50, 8, 2, 0),
                "non-final self crossing bypassed rival occupancy");
        check(state(g).equals(before), "private proof changed live progress");
        me.incrementLap();
        check(certificate(g, false, 50, 8, 2, 0) && certificate(g, true, 50, 8, 2, 0),
                "actual final finish lost the referee's terminal landing exemption");
        me.setNextGate(1);
        check(!certificate(g, false, 50, 8, 2, 0) && !certificate(g, true, 50, 8, 2, 0),
                "owed checkpoints were erased at the mover's crossing");

        // The candidate itself, not just its descendants, must apply gate credit.
        final RaceGame s = fixture(SimulationBoundaryTests.class, "straight");
        final Method gates = SimulationBoundaryTests.class.getDeclaredMethod("gates", RaceGame.class);
        gates.setAccessible(true); gates.invoke(null, s); s.totalLaps = 2;
        s.players = new Player[]{car(1, 65, 10, 10, 0), car(2, 120, 10, 0, 0)};
        s.players[0].setNextGate(1);
        final RaceGame.MoveResult candidate = s.evaluateMove(0, 1, 65, 10, 76, 10, false);
        check(candidate.passCp1() && candidate.passCp2() && candidate.lapAfter() == 1,
                "candidate must score ordered gates and a non-final lap");
        final RaceAiPrivateLane.ProofSession session = new RaceAiPrivateLane(s).begin(1, 5, 512);
        final Method start = session.getClass().getDeclaredMethod("candidateState", int.class, int.class, int.class, int.class);
        start.setAccessible(true);
        final Object projected = start.invoke(session, 76, 10, 11, 0);
        check(intAccessor(projected, "lap") == candidate.lapAfter()
                && intAccessor(projected, "gate") == candidate.gateAfter(), "candidate progress was not propagated");
        final Object other = start.invoke(session, 75, 10, 10, 0);
        check(intAccessor(other, "lap") == 1 && s.players[0].getLap() == 0,
                "candidate loop accumulated progress into the next candidate");
        s.players[1].setPosition(new int[]{76, 10});
        check(!certificate(s, true, 76, 10, 11, 0), "occupied nonterminal candidate accepted");
        s.players[0].incrementLap();
        check(certificate(s, true, 76, 10, 11, 0), "terminal candidate incorrectly blocked");

        // With ten required exits, counting nine moves cannot certify a leaf.
        // Success must propagate checkpoint progress through recursive continuations.
        s.players = new Player[]{car(1, 65, 10, 1, 0), car(2, 120, 10, 0, 0)};
        s.totalLaps = 1; s.players[0].setNextGate(1);
        final int recursiveTurns = s.reach.turnsToFinish(67, 10, 2, 0);
        check(new RaceAiPrivateLane(s).begin(1, 5, 512)
                .certifiesExact(67, 10, 2, 0, recursiveTurns, 4, 10),
                "recursive continuation failed to credit ordered checkpoints before finishing");
        s.lapGates[1] = new java.awt.geom.Line2D.Double(90, 1, 90, 19);
        s.lapGates[2] = new java.awt.geom.Line2D.Double(100, 1, 100, 19);
        check(!new RaceAiPrivateLane(s).begin(1, 5, 512)
                .certifiesExact(67, 10, 2, 0, recursiveTurns, 4, 10),
                "recursive geometric crossing ignored checkpoints still owed");

        // Independent exhaustive, short-horizon rival endpoints and own paths.
        int checked = 0, accepted = 0;
        for (int lap = 0; lap < 2; lap++) for (int gate = 0; gate < 3; gate++)
            for (int x = 44; x <= 52; x += 2) for (int vx = 0; vx <= 3; vx++) {
                g.players = new Player[]{car(1, x, 8, vx, 0), car(2, 52, 8, 0, 0)};
                g.players[0].restoreLapState(new int[]{lap, gate, 0, 0, 0, 0});
                final int nx = x + vx + 1, nvx = vx + 1;
                final RaceGame.MoveResult first = g.evaluateMove(g.players[0], new int[]{x, 8}, new int[]{nx, 8});
                if (!first.legal()) continue;
                final RaceAiPrivateLane.ProofSession proof = new RaceAiPrivateLane(g).begin(1, 3, 4096);
                final int turns = g.reach.turnsToFinish(nx, 8, nvx, 0);
                final boolean got = proof.certifiesExact(nx, 8, nvx, 0, turns, 1, 3);
                checked++;
                if (!got) continue;
                accepted++;
                final Set<String> one = new HashSet<>(), two = new HashSet<>();
                endpoints(g, g.players[1], 1, one); endpoints(g, g.players[1], 2, two);
                final Player next = after(g.players[0], first, nx, 8, nvx, 0);
                check(first.finishes() || verifyOwn(g, next, turns, 0, one, two),
                        "certificate disagrees with exhaustive detached continuations");
            }
        check(checked >= 80 && accepted > 0, "insufficient exhaustive progress coverage");
        System.out.println("Mover progress: " + checked + " candidates, " + accepted + " verified certificates");
    }

    private static boolean verifyOwn(final RaceGame g, final Player p, final int turns, final int depth,
            final Set<String> one, final Set<String> two) {
        int privateExits = 0;
        final Set<String> blocked = depth == 0 ? one : two;
        for (final Direction d : Direction.values()) {
            final int[] x = p.getPosition(), v = p.getVelocity();
            final int vx = v[0] + d.dx, vy = v[1] + d.dy, nx = x[0] + vx, ny = x[1] + vy;
            if (RaceGame.aiVelocityOutOfRange(vx, vy)) continue;
            final RaceGame.MoveResult result = g.evaluateMove(p.getLap(), p.getNextGate(), x[0], x[1], nx, ny,
                    blocked.contains(nx + "," + ny));
            if (result.finishes()) return true;
            if (!result.legal() || !g.reach.isAlive(nx, ny, vx, vy)) continue;
            if (++privateExits >= 3) return true;
            final int remaining = g.reach.turnsToFinish(nx, ny, vx, vy);
            if (depth == 0 && remaining < turns
                    && verifyOwn(g, after(p, result, nx, ny, vx, vy), remaining, 1, one, two)) return true;
        }
        return false;
    }

    private static void endpoints(final RaceGame g, final Player p, final int steps, final Set<String> result) {
        for (final Direction d : Direction.values()) {
            final int[] x = p.getPosition(), v = p.getVelocity();
            final int vx = v[0] + d.dx, vy = v[1] + d.dy, nx = x[0] + vx, ny = x[1] + vy;
            final RaceGame.MoveResult move = g.evaluateMove(p.getLap(), p.getNextGate(), x[0], x[1], nx, ny, false);
            if (!move.legal() || move.finishes()) continue;
            if (steps == 1) result.add(nx + "," + ny);
            else endpoints(g, after(p, move, nx, ny, vx, vy), steps - 1, result);
        }
    }

    private static Player after(final Player original, final RaceGame.MoveResult move,
            final int x, final int y, final int vx, final int vy) {
        final Player p = car(original.getNumber(), x, y, vx, vy);
        p.restoreLapState(new int[]{move.lapAfter(), move.gateAfter(), 0, 0, 0, 0});
        return p;
    }
    private static boolean certificate(final RaceGame g, final boolean exact,
            final int x, final int y, final int vx, final int vy) {
        final RaceAiPrivateLane.ProofSession p = new RaceAiPrivateLane(g).begin(1, 5, 512);
        final int turns = g.reach.turnsToFinish(x, y, vx, vy);
        return exact ? p.certifiesExact(x, y, vx, vy, turns, 4, 3)
                : p.certifiesApproximate(x, y, vx, vy, turns, 3, 3);
    }
    private static int intAccessor(final Object o, final String name) throws Exception {
        final Method m = o.getClass().getDeclaredMethod(name); m.setAccessible(true); return (int) m.invoke(o);
    }
    private static RaceGame fixture(final Class<?> type, final String name) throws Exception {
        final Method m = type.getDeclaredMethod(name); m.setAccessible(true); return (RaceGame) m.invoke(null);
    }
    private static void commit(final RaceGame g, final int[] p, final int[] v, final int[] n) throws Exception {
        final Method m = RaceGame.class.getDeclaredMethod("commitMove", int[].class, int[].class, int[].class);
        m.setAccessible(true); m.invoke(g, p, v, n);
    }
    private static Player car(final int number, final int x, final int y, final int vx, final int vy) {
        final Player p = new Player("P" + number, number, Color.BLUE, Player.Kind.AI1);
        p.setPosition(new int[]{x, y}); p.setVelocity(new int[]{vx, vy}); p.setNextGate(0); return p;
    }
    private static Object get(final Object o, final String name) throws Exception {
        final Field f = o.getClass().getDeclaredField(name); f.setAccessible(true); return f.get(o);
    }
    private static void set(final Object o, final String name, final Object value) throws Exception {
        final Field f = o.getClass().getDeclaredField(name); f.setAccessible(true); f.set(o, value);
    }
    private static String state(final RaceGame g) {
        final StringBuilder b = new StringBuilder().append(g.subgamestate).append('/').append(g.turnCount());
        for (final Player p : g.players) b.append(Arrays.toString(p.getPosition())).append(Arrays.toString(p.getVelocity()))
                .append(Arrays.toString(p.lapState())).append(p.getFinishedPlace());
        return b.toString();
    }
    private static void check(final boolean condition, final String message) {
        if (!condition) throw new AssertionError(message);
    }
}
