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
        if (args.length == 0 || args[0].equals("human")) testHumanAboveCap();
        if (args.length == 0 || args[0].equals("twingates")) testTwinGates();
        if (args.length == 0 || args[0].equals("twinfinish")) testTwinFinishLeaves();
        System.out.println("SimulationFollowupTests: legal blockades, proxy continuations, mover progress,"
                + " human rivals above the AI cap, the rival twin's gate rules and its finishes OK");
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

    /** Round 340: only an AI move is capped, so a human may arrive at v=(14,0), where no map holds a state
     *  and the AI's policy, which takes only moves that land within the cap, finds none. Its forecast
     *  sheds the excess speed and projects its arrival from the moves that takes, so it is neither
     *  retired by a coast into the first wall nor counted behind. An AI car above the cap, only ever a
     *  forecast's model, keeps its model: the gate is the car's kind. */
    private static void testHumanAboveCap() throws Exception {
        for (final Player.Kind kind : new Player.Kind[]{Player.Kind.HUMAN, Player.Kind.AI1}) {
            final boolean human = kind == Player.Kind.HUMAN;
            final RaceGame g = capCorridor(kind, false);
            check(g.evaluateMove(0, 0, 129, 10, 143, 10, false).legal()
                    && !g.evaluateMove(0, 0, 143, 10, 157, 10, false).legal(),
                    "a coast at 14 from x = 101 must meet the step on its fourth move");
            // Five rounds: the human sheds its excess speed, then races by its scorer.
            final Forecast five = forecast(g, 0, 1, 5);
            check(five.verdict() >= 0, "the mover did not survive the forecast: " + five);
            if (human) {
                check(five.alive(), "a human above the AI cap was retired by a phantom crash: " + five);
                check(five.arrival() != Integer.MAX_VALUE && five.arrival() != Integer.MIN_VALUE && five.ahead() == 1,
                        "a human above the AI cap was not projected ahead of the mover: " + five);
                // Two braking moves bring it into the cap at x = 126; the exact distance runs from there.
                int expected = Integer.MAX_VALUE;
                for (int a1 = -1; a1 <= 1; a1++)
                    for (int a2 = -1; a2 <= 1; a2++)
                        if (g.evaluateMove(0, 0, 101, 10, 114, 10 + a1, false).legal()
                                && g.evaluateMove(0, 0, 114, 10 + a1, 126, 10 + 2 * a1 + a2, false).legal()) {
                            final int t = g.reach.turnsToFinish(126, 10 + 2 * a1 + a2, 12, a1 + a2);
                            if (t != Integer.MAX_VALUE) expected = Math.min(expected, 2 + t);
                        }
                check(expected != Integer.MAX_VALUE && shedTurns(g, 101, 10, 14, 0) == expected,
                        "a human above the AI cap was not projected by its braking moves and the exact distance");
            } else
                check(!five.alive() && five.arrival() == Integer.MAX_VALUE && five.ahead() == 0,
                        "an AI car above the cap left its model: the gate is the car's kind, not its speed: " + five);
            // One round, which its projection alone decides: the human ends it above the cap. Moving after
            // the mover, it sheds one unit and is projected after that move; first in the move order, it
            // does not move before the mover's next slot and is projected at the forecast's start.
            final Forecast after = forecast(g, 0, 1, 1);
            final RaceGame first = capCorridor(kind, true);
            final Forecast start = forecast(first, 1, 0, 1);
            if (human) {
                check(after.x() == 114 && after.vx() == 13 && after.ahead() == 1
                        && after.arrival() == shedTurns(g, after.x(), after.y(), after.vx(), after.vy()),
                        "a human above the AI cap was not projected by shedTurns after its move: " + after);
                check(start.x() == 101 && start.vx() == 14 && start.ahead() == 1
                        && start.arrival() == shedTurns(first, 101, 10, 14, 0),
                        "a human above the AI cap was not projected by shedTurns at the forecast's start: " + start);
            } else
                check(after.x() == 115 && after.vx() == 14 && after.arrival() == Integer.MAX_VALUE
                        && after.ahead() == 0 && start.arrival() == Integer.MAX_VALUE && start.ahead() == 0,
                        "an AI car above the cap was projected or left its model's coast: " + after + ", " + start);
            // The score's simulated round: the human brakes onto x = 114; the AI car finds no move
            // there and keeps its cell.
            final Method frame = RaceAi.class.getDeclaredMethod("prepareDecisionFrame", int[].class, int[].class,
                    int.class);
            frame.setAccessible(true);
            frame.invoke(g.ai, g.players[0].getPosition(), g.players[0].getVelocity(), 1);
            final Method round = RaceAi.class.getDeclaredMethod("simulateTwoRounds",
                    int.class, int.class, int.class, int.class, int.class);
            round.setAccessible(true);
            final RaceAi.CellOccupancy cells = (RaceAi.CellOccupancy) get(round.invoke(g.ai, 1, 102, 12, 12, -2),
                    "world1Occupancy");
            final boolean braked = cells.contains(114, 9) || cells.contains(114, 10) || cells.contains(114, 11);
            check(braked == human, human ? "a human above the cap did not shed speed in the simulated round"
                    : "an AI car above the cap left its model in the simulated round");
        }
    }

    /** Round 340: the step corridor with an AI1 mover at rest on (100, 10) and, one cell ahead at v=(14,0), a
     *  rival of {@code kind}, after the mover in the move order or, {@code rivalFirst}, before it. The
     *  mover's slot is to move. */
    private static RaceGame capCorridor(final Player.Kind kind, final boolean rivalFirst) throws Exception {
        final RaceGame g = stepCorridor();
        final Player rival = new Player("P" + (rivalFirst ? 1 : 2), rivalFirst ? 1 : 2, Color.RED, kind);
        rival.setPosition(new int[]{101, 10}); rival.setVelocity(new int[]{14, 0}); rival.setNextGate(0);
        final Player mover = car(rivalFirst ? 2 : 1, 100, 10, 0, 0);
        g.players = rivalFirst ? new Player[]{rival, mover} : new Player[]{mover, rival};
        g.reach.computeDistMap(); g.reach.computeReachability();
        g.subgamestate = rivalFirst ? 1 : 0;
        return g;
    }

    /** Round 340: what a projected-place forecast leaves of one car -- its cell, velocity, life and projected
     *  arrival -- with the rivals its key counts ahead of the mover, and its verdict. */
    private record Forecast(int x, int y, int vx, int vy, boolean alive, int arrival, long ahead, int verdict) {}

    /** Round 340: a projected-place forecast of {@code rounds} for the car in slot {@code mover}, every rival
     *  by its scorer as in a chooser's, read at the car in slot {@code car}. */
    private static Forecast forecast(final RaceGame g, final int mover, final int car, final int rounds)
            throws Exception {
        set(g.ai, "ppDepth", 1); set(g.ai, "placeKeyDepth", 1);
        final int verdict = g.ai.querySimOutcome(mover, rounds, true, false, true, 1, null);
        set(g.ai, "ppDepth", -1); set(g.ai, "placeKeyDepth", -1);
        final Object w = ((Object[]) get(g.ai, "rolloutsByDepth"))[1];
        return new Forecast(((int[]) get(w, "px"))[car], ((int[]) get(w, "py"))[car], ((int[]) get(w, "vx"))[car],
                ((int[]) get(w, "vy"))[car], ((boolean[]) get(w, "alive"))[car], ((int[]) get(w, "ppArrival"))[car],
                (long) get(g.ai, "placeKey") / RaceAi.VERDICT_PLACE_STRIDE, verdict);
    }

    /** Round 340: RaceAi.shedTurns in the step corridor's one frame (no lap done, no gates). */
    private static int shedTurns(final RaceGame g, final int x, final int y, final int vx, final int vy)
            throws Exception {
        final Method m = RaceAi.class.getDeclaredMethod("shedTurns", int.class, int.class, int.class, int.class,
                int.class, int.class);
        m.setAccessible(true);
        return (int) m.invoke(g.ai, 0, 0, x, y, vx, vy);
    }

    /** SimulationBoundaryTests' straight with a step: from x = 150 only its lower half, y 11 to 19, is
     *  track, and the line crosses that half. A car on y = 10 has to leave its row before the step. */
    private static RaceGame stepCorridor() throws Exception {
        final RaceGame g = new RaceGame(new Properties());
        g.gameCols = 180; g.gameRows = 20;
        g.track = new Track();
        g.track.addLeft(0, 1); g.track.addLeft(150, 1); g.track.addLeft(150, 11); g.track.addLeft(173, 11);
        g.track.addRight(0, 19); g.track.addRight(173, 19);
        final java.awt.geom.Area track = new java.awt.geom.Area(new java.awt.geom.Rectangle2D.Double(0, 1, 150, 18));
        track.add(new java.awt.geom.Area(new java.awt.geom.Rectangle2D.Double(150, 11, 23, 8)));
        g.trackA = track;
        g.startZoneA = new java.awt.geom.Area();
        g.finishLine = new java.awt.geom.Line2D.Double(172.5, 11, 172.5, 19);
        set(g, "finishFwdX", 1.0);
        set(g, "rui", new RaceUI(g.gameRows, g.gameCols));
        return g;
    }

    /** Round 341: the score's rival twin -- RaceAi.pureMinTurnsMoveSim, the move the score's simulated round
     *  gives every rival but a human above the AI speed cap (round 340) -- plays the rival's own gate rules.
     *  Where the exact potential prices the gates, a lap-scoring S/F crossing and a checkpoint touch are
     *  ordinary landings, ranked by the exact distance with the move's gate events paid (ttfForAfter), as
     *  round 336 made them in the car's own decision; a finish keeps its precedence; where no potential prices
     *  the gates the old precedences still decide. On the two-lap Circle, player 1 deciding and player 2 the
     *  rival: (a) owing the line on its first lap, (b) owing CP1, (c) both with the exact map capped, (d) on
     *  its final lap with a body on its first finishing landing. (a) and (b) accept any of the fastest
     *  landings, so the twin's tie-break is not pinned; (c) and (d) guard what round 341 must not change and
     *  pass on round 340 too. Each part runs on its own and the failures are reported together. */
    private static void testTwinGates() throws Exception {
        final java.util.List<String> failures = new java.util.ArrayList<>();
        final RaceGame priced = circle();
        twinPart(failures, "(a) a lap-scoring S/F crossing is an ordinary landing", () -> twinCrossing(priced));
        twinPart(failures, "(b) a checkpoint touch is an ordinary landing", () -> twinTouch(priced));
        twinPart(failures, "(c) with no exact potential the old precedences decide", () -> twinUnpriced());
        twinPart(failures, "(d) a finish keeps its precedence", () -> twinFinish(priced));
        check(failures.isEmpty(),
                "the score's rival twin broke the rival's gate rules: " + String.join("; ", failures));
    }

    /** Round 341: one part of testTwinGates. */
    private interface TwinPart {
        String run() throws Exception;
    }

    private static void twinPart(final java.util.List<String> failures, final String name, final TwinPart part)
            throws Exception {
        try {
            System.out.println("Twin gates " + name + ": ok, " + part.run());
        } catch (final AssertionError | java.lang.reflect.InvocationTargetException e) {
            final String why = e instanceof AssertionError ? e.getMessage() : "the code under test threw " + e.getCause();
            System.out.println("Twin gates " + name + ": FAILED: " + why);
            failures.add(name + ": " + why);
        }
    }

    /** (a) The rival on its first lap, past both checkpoints, at (47, 10) doing 5 right and 2 up: all nine
     *  landings cross the line, and the first permitted lap-scoring crossing is slower than the fastest. */
    private static String twinCrossing(final RaceGame g) throws Exception {
        final Player rival = twinField(g, 47, 10, 5, -2, 0, 0);
        final RaceAi.CellOccupancy free = cells(g);
        check(g.optimalPotential() != null, "fixture: the Circle's exact potential was not built");
        for (final Direction d : Direction.values()) {
            final int[] p = rival.getPosition(), n = landing(rival, d);
            check(g.crossesFinishLegally(p[0], p[1], n[0], n[1]), "fixture: " + d + " does not cross the line");
        }
        final Direction first = firstPermittedCrossing(g, rival, free), fastest = fastestLanding(g, rival, free);
        check(first != null && referee(g, rival, first).lapCross() && !referee(g, rival, first).finishes(),
                "fixture: no permitted lap-scoring crossing");
        check(fastest != null && fastest != first && turnsAfter(g, rival, fastest) < turnsAfter(g, rival, first),
                "fixture: the first permitted crossing " + first + " is the fastest landing");
        final Direction twin = twin(g, rival, free);
        final int best = turnsAfter(g, rival, fastest);
        final String fastestSet = fastestLandings(g, rival, free);
        check(twin != null && freeLegal(g, rival, twin, free) && turnsAfter(g, rival, twin) == best,
                "the twin took " + twin + (twin == first ? ", the first permitted crossing" : "")
                + ", not one of the fastest landings (" + fastestSet + " at " + best + " moves; the first permitted"
                + " crossing " + first + " at " + turnsAfter(g, rival, first) + ")");
        final int[] landed = roundLanding(g, rival);
        check(Arrays.equals(landed, landing(rival, twin)), "the score's simulated round put the rival on "
                + Arrays.toString(landed) + ", not on the twin's landing " + Arrays.toString(landing(rival, twin)));
        return "the twin takes " + twin + ", one of the fastest (" + fastestSet + " at " + best
                + " moves), not the first permitted crossing " + first + " (" + turnsAfter(g, rival, first) + ")";
    }

    /** (b) The rival on its first lap owing CP1, at (80, 65) doing 2 left and 4 down: all nine landings touch
     *  CP1, and the first permitted touch is slower than the fastest. */
    private static String twinTouch(final RaceGame g) throws Exception {
        final Player rival = twinField(g, 80, 65, -2, 4, 0, 1);
        final RaceAi.CellOccupancy free = cells(g);
        check(g.optimalPotential() != null, "fixture: the Circle's exact potential was not built");
        for (final Direction d : Direction.values()) {
            final int[] p = rival.getPosition(), n = landing(rival, d);
            check(g.touchesGate(1, p[0], p[1], n[0], n[1]), "fixture: " + d + " does not touch CP1");
        }
        final Direction first = firstPermittedTouch(g, rival, free), fastest = fastestLanding(g, rival, free);
        check(first != null && referee(g, rival, first).passCp1(), "fixture: no permitted checkpoint touch");
        check(fastest != null && fastest != first && turnsAfter(g, rival, fastest) < turnsAfter(g, rival, first),
                "fixture: the first permitted touch " + first + " is the fastest landing");
        final Direction twin = twin(g, rival, free);
        final int best = turnsAfter(g, rival, fastest);
        final String fastestSet = fastestLandings(g, rival, free);
        check(twin != null && freeLegal(g, rival, twin, free) && turnsAfter(g, rival, twin) == best,
                "the twin took " + twin + (twin == first ? ", the first permitted touch" : "")
                + ", not one of the fastest landings (" + fastestSet + " at " + best + " moves; the first permitted"
                + " touch " + first + " at " + turnsAfter(g, rival, first) + ")");
        final int[] landed = roundLanding(g, rival);
        check(Arrays.equals(landed, landing(rival, twin)), "the score's simulated round put the rival on "
                + Arrays.toString(landed) + ", not on the twin's landing " + Arrays.toString(landing(rival, twin)));
        return "the twin takes " + twin + ", one of the fastest (" + fastestSet + " at " + best
                + " moves), not the first permitted touch " + first + " (" + turnsAfter(g, rival, first) + ")";
    }

    /** (c) The rivals of (a) and (b) on the Circle with the exact map capped, as over budget (the
     *  Nordschleife): the lap gates stay, and the gate maps, which cannot price a crossing or a touch, would
     *  rank another landing first. The twin keeps round 224's precedences. */
    private static String twinUnpriced() throws Exception {
        final String cap = System.getProperty("tr.optimalBuildBytes");
        RaceGame.clearOptimalMemoForTests();
        System.setProperty("tr.optimalBuildBytes", "0");
        try {
            final RaceGame g = circle();
            check(g.optimalPotential() == null && g.lapGates != null,
                    "fixture: the capped Circle has an exact potential");
            final Player crossing = twinField(g, 47, 10, 5, -2, 0, 0);
            final RaceAi.CellOccupancy free = cells(g);
            final Direction line = firstPermittedCrossing(g, crossing, free);
            final Direction lineByMap = gateMapFastest(g, crossing, free);
            check(line != null && lineByMap != null && lineByMap != line,
                    "fixture: the gate map ranks the first permitted crossing first");
            final Direction lineTwin = twin(g, crossing, free);
            final Player touching = twinField(g, 80, 65, -2, 4, 0, 1);
            final Direction touch = firstPermittedTouch(g, touching, free);
            final Direction touchByMap = gateMapFastest(g, touching, free);
            check(touch != null && touchByMap != null && touchByMap != touch,
                    "fixture: the gate map ranks the first permitted touch first");
            final Direction touchTwin = twin(g, touching, free);
            String broken = "";
            if (lineTwin != line)
                broken = lineTwin + ", not " + line + ", the first permitted crossing"
                        + (lineTwin == lineByMap ? " (the gate map's pick)" : "");
            if (touchTwin != touch)
                broken += (broken.isEmpty() ? "" : ", and ") + touchTwin + ", not " + touch
                        + ", the first permitted touch" + (touchTwin == touchByMap ? " (the gate map's pick)" : "");
            check(broken.isEmpty(), "with no exact potential the twin took " + broken);
            return "the twin takes the first permitted crossing " + lineTwin + " (the gate map: " + lineByMap
                    + ") and the first permitted touch " + touchTwin + " (the gate map: " + touchByMap + ")";
        } finally {
            if (cap == null) System.clearProperty("tr.optimalBuildBytes");
            else System.setProperty("tr.optimalBuildBytes", cap);
            RaceGame.clearOptimalMemoForTests();
        }
    }

    /** (d) The rival of (a) on its final lap: all nine landings finish. A third car stands on the first
     *  finishing landing, which the referee lets a finish land on, so ranking the landings would take another. */
    private static String twinFinish(final RaceGame g) throws Exception {
        final Player body = car(3, 51, 7, 0, 0);
        final Player rival = twinField(g, 47, 10, 5, -2, 1, 0, body);
        final RaceAi.CellOccupancy held = cells(g);
        held.add(body.getPosition()[0], body.getPosition()[1]);
        check(g.optimalPotential() != null, "fixture: the Circle's exact potential was not built");
        Direction first = null;
        int finishing = 0;
        for (final Direction d : Direction.values()) {
            final int[] p = rival.getPosition(), v = rival.getVelocity(), n = landing(rival, d);
            if (!RaceGame.aiVelocityOutOfRange(v[0] + d.dx, v[1] + d.dy) && g.evaluateMove(rival.getLap(),
                    rival.getNextGate(), p[0], p[1], n[0], n[1], held.contains(n[0], n[1])).finishes()) {
                finishing++;
                if (first == null)
                    first = d;
            }
        }
        check(finishing == 9 && held.contains(landing(rival, first)[0], landing(rival, first)[1]),
                "fixture: not every landing finishes, or no body on the first finishing landing");
        final Direction fastest = fastestLanding(g, rival, held);
        check(fastest != null && fastest != first, "fixture: ranking the landings takes the first finishing one");
        final Direction twin = twin(g, rival, held);
        check(twin == first, "the twin took " + twin + ", not " + first + ", the first finishing landing"
                + (twin == fastest ? " (ranked as an ordinary landing)" : ""));
        return "the twin takes the first finishing landing " + twin + ", on a body, where ranking takes " + fastest;
    }

    /** Round 343: a rival whose simulated move finishes leaves the score's simulated round, as the referee takes a
     *  finished car off the board (RaceGame.finishPlayer; isCrashingPlayer skips a finished car) and every forecast
     *  does (simOutcomeCore). Before, the round kept it as a phantom body: on its old cell when its twin finished
     *  onto a body, which the referee lets a finish land on (held), or past the track's end, where the run-up rule
     *  lets a finish land and the round's whole-segment test (aiMoveLegal) does not (off, and a human above the cap
     *  doing so, shed); on its landing when it finished onto a free one (free). Player 1 decides, and no part's
     *  rounds may change the live field. In those four the finisher is the round's first mover, and the round, read
     *  on the whole board and in the window perf_refround reads around the finisher, must be the round of the same
     *  field with the finisher already finished. That round answers for every car moving after the finisher as long
     *  as the finisher's body turned no car before it, and not for one moving before it, which still meets the
     *  finisher's body. Three more parts put a second car where the finish matters, beside the finisher of (free):
     *  (follow) moving after the finisher, it takes the landing the finisher left; (lead) moving before it, it
     *  keeps the landing the finisher then finishes onto; (wait) moving before it, it still finds the finisher's
     *  old cell held. The failures are reported together. */
    private static void testTwinFinishLeaves() throws Exception {
        final java.util.List<String> failures = new java.util.ArrayList<>();
        final RaceGame circle = circle();
        finishPart(failures, "(held) a finish onto a body", () -> finishOnCircle(circle, true));
        finishPart(failures, "(free) a finish onto a free landing", () -> finishOnCircle(circle, false));
        finishPart(failures, "(off) a finish past the track's end", () -> finishPastEnd(Player.Kind.AI1));
        finishPart(failures, "(shed) a human above the cap finishing past the end",
                () -> finishPastEnd(Player.Kind.HUMAN));
        finishPart(failures, "(follow) a car after the finisher takes the landing it left",
                () -> finishBesideCar(circle, false));
        finishPart(failures, "(lead) a car before the finisher keeps the landing it finishes onto",
                () -> finishBesideCar(circle, true));
        finishPart(failures, "(wait) a car before the finisher still meets its body", () -> finishAfterCar(circle));
        check(failures.isEmpty(),
                "the score's simulated round mishandled a finishing rival: " + String.join("; ", failures));
    }

    /** Round 343: one part of testTwinFinishLeaves. */
    private static void finishPart(final java.util.List<String> failures, final String name, final TwinPart part)
            throws Exception {
        try {
            System.out.println("Twin finish " + name + ": ok, " + part.run());
        } catch (final AssertionError | java.lang.reflect.InvocationTargetException e) {
            final String why = e instanceof AssertionError ? e.getMessage() : "the code under test threw " + e.getCause();
            System.out.println("Twin finish " + name + ": FAILED: " + why);
            failures.add(name + ": " + why);
        }
    }

    /** Round 343 (held, free): the rival of twin gates (d), on its final lap at (47, 10) doing 5 right and 2 up: all
     *  nine landings finish, and the twin takes the first, NW at (51, 7). With {@code held} a third car stands there
     *  at rest; it moves after the rival. */
    private static String finishOnCircle(final RaceGame g, final boolean held) throws Exception {
        final Player rival = held ? twinField(g, 47, 10, 5, -2, 1, 0, car(3, 51, 7, 0, 0))
                : twinField(g, 47, 10, 5, -2, 1, 0);
        final int[] from = rival.getPosition().clone(), to = landing(rival, Direction.NW);
        check(g.evaluateMove(rival.getLap(), rival.getNextGate(), from[0], from[1], to[0], to[1], held).finishes()
                && g.aiMoveLegal(from[0], from[1], to[0], to[1]),
                "fixture: the rival's NW move is no legal finish" + (held ? " onto the body" : ""));
        final RaceAi.CellOccupancy board = cells(g);
        if (held)
            board.add(to[0], to[1]);
        check(twin(g, rival, board) == Direction.NW, "fixture: the twin does not take the finishing NW landing");
        return finishRounds(g, rival, held ? from : to, held ? "its old cell" : "its landing");
    }

    /** Round 343 (off, shed): the step corridor's line stands at x = 172.5 and its track ends at x = 173. A rival
     *  at (165, 15) doing 10 right, or a human at (163, 15) doing 14 right, above the AI cap, crosses the line on
     *  its first acceleration, NW, and lands past the end. Player 1 decides at rest at (100, 15). */
    private static String finishPastEnd(final Player.Kind kind) throws Exception {
        final RaceGame g = stepCorridor();
        final boolean human = kind == Player.Kind.HUMAN;
        final Player rival = new Player("P2", 2, Color.RED, kind);
        rival.setPosition(new int[]{human ? 163 : 165, 15}); rival.setVelocity(new int[]{human ? 14 : 10, 0});
        rival.setNextGate(0);
        g.players = new Player[]{car(1, 100, 15, 0, 0), rival};
        g.reach.computeDistMap(); g.reach.computeReachability();
        g.subgamestate = 0;
        decisionFrame(g);
        final int[] from = rival.getPosition().clone(), to = landing(rival, Direction.NW);
        check(g.evaluateMove(0, 0, from[0], from[1], to[0], to[1], false).finishes()
                && !g.aiMoveLegal(from[0], from[1], to[0], to[1]),
                "fixture: the rival's NW move does not finish past the track's end");
        if (!human)
            check(twin(g, rival, cells(g)) == Direction.NW, "fixture: the twin does not take the finishing NW landing");
        return finishRounds(g, rival, from, "its old cell");
    }

    /** Round 343 (follow, lead): the finisher of (free) and a car on its first lap owing the line at (49, 8) doing
     *  1 right, which moves after the finisher or, {@code lead}, before it. Either way the round must be the round
     *  with the finisher already finished, which puts that car on (51, 7), the finisher's landing. */
    private static String finishBesideCar(final RaceGame g, final boolean lead) throws Exception {
        final Player other = car(lead ? 2 : 3, 49, 8, 1, 0), finisher = finishingCar(lead ? 3 : 2);
        other.leaveGrid();
        if (lead) finishField(g, other, finisher); else finishField(g, finisher, other);
        final int[] board = {0, 0, g.gameCols, g.gameRows};
        final String live = state(g);
        final java.util.List<String> round = roundCells(g, board), without = finishedRoundCells(g, finisher, board);
        check(state(g).equals(live), "the simulated rounds changed the live field");
        check(without.equals(java.util.List.of("51,7")),
                "fixture: with the finisher finished the other car does not take (51,7): " + without);
        check(round.equals(without), "the round " + round + " is not the round with the finisher finished, " + without);
        return "the round " + round + " is the round with the finisher finished";
    }

    /** Round 343 (wait): a car on its first lap owing the line at (45, 11) doing 1 right moves before the finisher
     *  of (free), whose body still stands on (47, 10) then: the round holds that car on (47, 11). The round with the
     *  finisher already finished, which drops the finisher before anyone moves, puts it on (47, 10). */
    private static String finishAfterCar(final RaceGame g) throws Exception {
        final Player other = car(2, 45, 11, 1, 0), finisher = finishingCar(3);
        other.leaveGrid();
        finishField(g, other, finisher);
        final int[] board = {0, 0, g.gameCols, g.gameRows};
        final String live = state(g);
        final java.util.List<String> round = roundCells(g, board), without = finishedRoundCells(g, finisher, board);
        check(state(g).equals(live), "the simulated rounds changed the live field");
        check(without.equals(java.util.List.of("47,10")),
                "fixture: with the finisher finished the other car does not take (47,10): " + without);
        check(round.equals(java.util.List.of("47,11")),
                "the round " + round + " is not the other car alone on (47,11), beside the finisher's body");
        return "the round " + round + " holds the other car beside the finisher's body (with the finisher finished: "
                + without + ")";
    }

    /** Round 343 (follow, lead, wait): the finisher of (free), on its final lap at (47, 10) doing 5 right and 2 up,
     *  as player {@code number}. */
    private static Player finishingCar(final int number) {
        final Player p = car(number, 47, 10, 5, -2);
        p.setLap(1); p.setNextGate(0); p.leaveGrid();
        return p;
    }

    /** Round 343 (follow, lead, wait): player 1 deciding as in twinField, then {@code cars} in the order the round
     *  moves them. */
    private static void finishField(final RaceGame g, final Player... cars) throws Exception {
        final Player mover = car(1, 48, 88, 0, 0);
        mover.setNextGate(2); mover.leaveGrid();
        final Player[] players = new Player[1 + cars.length];
        players[0] = mover;
        System.arraycopy(cars, 0, players, 1, cars.length);
        g.players = players;
        g.subgamestate = 0;
        decisionFrame(g);
    }

    /** Round 343: player 1's simulated round, read on the whole board and in the window perf_refround reads around
     *  the rival (its cell and its nine landings), must be the round of the same field with the rival already
     *  finished, which holds no body on {@code phantom}, where the round kept the rival before. */
    private static String finishRounds(final RaceGame g, final Player rival, final int[] phantom, final String where)
            throws Exception {
        final int[] p = rival.getPosition(), v = rival.getVelocity();
        final int cx = p[0] + v[0], cy = p[1] + v[1];
        final int[][] windows = {{0, 0, g.gameCols, g.gameRows},
                {Math.min(p[0], cx - 1), Math.min(p[1], cy - 1), Math.max(p[0], cx + 1), Math.max(p[1], cy + 1)}};
        final String cell = phantom[0] + "," + phantom[1], live = state(g);
        String seen = "";
        for (final int[] w : windows) {
            final String in = w[0] == 0 ? "" : " in the window " + Arrays.toString(w);
            final java.util.List<String> round = roundCells(g, w);
            check(state(g).equals(live), "the simulated round changed the live field" + in);
            final java.util.List<String> without = finishedRoundCells(g, rival, w);
            check(state(g).equals(live), "the round with the rival finished changed the live field" + in);
            check(!without.contains(cell), "fixture: the round with the rival finished holds " + where + " ("
                    + cell + ")" + in + ": " + without);
            check(round.equals(without), "the score's simulated round" + in + " is " + round
                    + (round.contains(cell) ? ", the finished rival kept on " + where + " (" + cell + ")," : "")
                    + " where the round with it finished, " + without + ", was expected");
            seen += (seen.isEmpty() ? "" : "; ") + round;
        }
        return "the round takes the rival off the board, as with it finished (" + seen + "), not on " + where + " ("
                + cell + ")";
    }

    /** Round 343: the cells of player 1's simulated round, its candidate on its own cell, inside the rectangle
     *  {@code w} (x0, y0, x1, y1); sorted. */
    private static java.util.List<String> roundCells(final RaceGame g, final int[] w) throws Exception {
        decisionFrame(g);
        final Class<?> type = Class.forName("tr.logic.RaceAi$TwoRoundWorkspace");
        final Method workspace = RaceAi.class.getDeclaredMethod("twoRoundWorkspace");
        workspace.setAccessible(true);
        final Method round = RaceAi.class.getDeclaredMethod("simulateTwoRounds", type, int.class, int.class,
                int.class, boolean.class, int.class, int.class, int.class, int.class);
        round.setAccessible(true);
        final int[] m = g.players[0].getPosition();
        final RaceAi.CellOccupancy cells = (RaceAi.CellOccupancy) get(round.invoke(g.ai, workspace.invoke(g.ai),
                1, m[0], m[1], true, w[0], w[1], w[2], w[3]), "world1Occupancy");
        final int[] xs = (int[]) get(cells, "xs"), ys = (int[]) get(cells, "ys");
        final java.util.List<String> held = new java.util.ArrayList<>();
        for (int k = 0, n = (int) get(cells, "size"); k < n; k++)
            if (xs[k] >= w[0] && xs[k] <= w[2] && ys[k] >= w[1] && ys[k] <= w[3])
                held.add(xs[k] + "," + ys[k]);
        java.util.Collections.sort(held);
        return held;
    }

    /** Round 343: roundCells with {@code rival} finished, off the board, as the referee leaves a finished car. */
    private static java.util.List<String> finishedRoundCells(final RaceGame g, final Player rival, final int[] w)
            throws Exception {
        final int place = rival.getFinishedPlace();
        rival.setFinishedPlace(1);
        try {
            return roundCells(g, w);
        } finally {
            rival.setFinishedPlace(place);
        }
    }

    /** Round 341: the Circle with player 1 deciding at rest on the bottom straight, past CP1 (its world has no
     *  grid) and owing CP2; player 2, the twin's rival, at (x, y) with velocity (vx, vy) on {@code lap} owing
     *  {@code gate}; then {@code others}. Player 1's slot is to move, and its decision frame is prepared, so
     *  every expected value is computed in the world the twin plays in. */
    private static Player twinField(final RaceGame g, final int x, final int y, final int vx, final int vy,
            final int lap, final int gate, final Player... others) throws Exception {
        final Player mover = car(1, 48, 88, 0, 0), rival = car(2, x, y, vx, vy);
        mover.setNextGate(2); mover.leaveGrid();
        rival.setLap(lap); rival.setNextGate(gate); rival.leaveGrid();
        final Player[] players = new Player[2 + others.length];
        players[0] = mover; players[1] = rival;
        System.arraycopy(others, 0, players, 2, others.length);
        g.players = players;
        g.subgamestate = 0;
        decisionFrame(g);
        check(!g.aiGridLegal, "fixture: player 1's frame models the grid, though it is past CP1");
        return rival;
    }

    /** Round 341: player 1's decision frame (every car's lap frame, the race's potential), then the twin's move
     *  for {@code rival} against {@code occupied}. */
    private static Direction twin(final RaceGame g, final Player rival, final RaceAi.CellOccupancy occupied)
            throws Exception {
        decisionFrame(g);
        final Method twin = RaceAi.class.getDeclaredMethod("pureMinTurnsMoveSim", int.class, int[].class, int[].class,
                RaceAi.CellOccupancy.class);
        twin.setAccessible(true);
        return (Direction) twin.invoke(g.ai, rival.getNumber() - 1, rival.getPosition().clone(),
                rival.getVelocity().clone(), occupied);
    }

    private static void decisionFrame(final RaceGame g) throws Exception {
        final Method frame = RaceAi.class.getDeclaredMethod("prepareDecisionFrame", int[].class, int[].class,
                int.class);
        frame.setAccessible(true);
        final Player mover = g.players[0];
        frame.invoke(g.ai, mover.getPosition(), mover.getVelocity(), mover.getNumber());
    }

    /** Round 341: where the score's simulated round puts {@code rival}: player 1's round with its candidate on
     *  its own cell, read inside the rival's nine landings (perf_refround's window). */
    private static int[] roundLanding(final RaceGame g, final Player rival) throws Exception {
        decisionFrame(g);
        final Class<?> type = Class.forName("tr.logic.RaceAi$TwoRoundWorkspace");
        final Method workspace = RaceAi.class.getDeclaredMethod("twoRoundWorkspace");
        workspace.setAccessible(true);
        final Method round = RaceAi.class.getDeclaredMethod("simulateTwoRounds", type, int.class, int.class, int.class,
                boolean.class, int.class, int.class, int.class, int.class);
        round.setAccessible(true);
        final int[] p = rival.getPosition(), v = rival.getVelocity(), m = g.players[0].getPosition();
        final int cx = p[0] + v[0], cy = p[1] + v[1];
        final RaceAi.CellOccupancy cells = (RaceAi.CellOccupancy) get(round.invoke(g.ai, workspace.invoke(g.ai),
                g.players[0].getNumber(), m[0], m[1], true, cx - 1, cy - 1, cx + 1, cy + 1), "world1Occupancy");
        int[] landed = null;
        for (final Direction d : Direction.values())
            if (cells.contains(cx + d.dx, cy + d.dy)) {
                check(landed == null, "the simulated round holds two of the rival's landings");
                landed = new int[]{cx + d.dx, cy + d.dy};
            }
        return landed;
    }

    private static RaceAi.CellOccupancy cells(final RaceGame g) {
        return new RaceAi.CellOccupancy(g.gameCols + 1, g.gameRows + 1);
    }

    private static int[] landing(final Player p, final Direction d) {
        final int[] pos = p.getPosition(), vel = p.getVelocity();
        return new int[]{pos[0] + vel[0] + d.dx, pos[1] + vel[1] + d.dy};
    }

    /** The referee's transition for {@code p}'s move {@code d} onto a free landing, in the AI's grid world. */
    private static RaceGame.MoveResult referee(final RaceGame g, final Player p, final Direction d) {
        final int[] pos = p.getPosition(), n = landing(p, d);
        return g.evaluateMove(p.getLap(), p.getNextGate(), pos[0], pos[1], n[0], n[1], false);
    }

    /** Can the twin move {@code p} by {@code d}: in the AI's speed range, legal in its world and free? */
    private static boolean freeLegal(final RaceGame g, final Player p, final Direction d,
            final RaceAi.CellOccupancy occupied) {
        final int[] pos = p.getPosition(), vel = p.getVelocity(), n = landing(p, d);
        return !RaceGame.aiVelocityOutOfRange(vel[0] + d.dx, vel[1] + d.dy)
                && g.aiMoveLegal(pos[0], pos[1], n[0], n[1]) && !occupied.contains(n[0], n[1]);
    }

    /** The exact distance at {@code p}'s landing by {@code d}, the gate credit the referee gives the move paid. */
    private static int turnsAfter(final RaceGame g, final Player p, final Direction d) {
        final RaceGame.MoveResult move = referee(g, p, d);
        check(move.legal(), "fixture: the referee refuses " + d + ", a landing legal in the AI's world");
        final int[] n = landing(p, d), vel = p.getVelocity();
        return move.finishes() ? 0 : g.optimalPotential().movesToFinish(
                OptimalPotential.remainingEvents(move.gateAfter(), move.lapAfter(), g.totalLaps),
                n[0], n[1], vel[0] + d.dx, vel[1] + d.dy);
    }

    /** The fastest of {@code p}'s free legal landings by turnsAfter, the first in Direction order on a tie. */
    private static Direction fastestLanding(final RaceGame g, final Player p, final RaceAi.CellOccupancy occupied) {
        Direction best = null;
        int bestTurns = Integer.MAX_VALUE;
        for (final Direction d : Direction.values())
            if (freeLegal(g, p, d, occupied) && turnsAfter(g, p, d) < bestTurns) {
                bestTurns = turnsAfter(g, p, d);
                best = d;
            }
        return best;
    }

    /** The free legal landings of {@code p} that tie for the fewest turnsAfter, in Direction order. */
    private static String fastestLandings(final RaceGame g, final Player p, final RaceAi.CellOccupancy occupied) {
        final int best = turnsAfter(g, p, fastestLanding(g, p, occupied));
        final java.util.List<String> names = new java.util.ArrayList<>();
        for (final Direction d : Direction.values())
            if (freeLegal(g, p, d, occupied) && turnsAfter(g, p, d) == best)
                names.add(d.toString());
        return String.join(", ", names);
    }

    /** The landing the gate maps alone rank first -- the turns to {@code p}'s next gate, which a crossing or
     *  touch restarts -- the first in Direction order on a tie. */
    private static Direction gateMapFastest(final RaceGame g, final Player p, final RaceAi.CellOccupancy occupied) {
        Direction best = null;
        int bestTurns = Integer.MAX_VALUE;
        for (final Direction d : Direction.values()) {
            final int[] n = landing(p, d), vel = p.getVelocity();
            final int turns = freeLegal(g, p, d, occupied)
                    ? g.reach.turnsToGate(p.getNextGate(), n[0], n[1], vel[0] + d.dx, vel[1] + d.dy)
                    : Integer.MAX_VALUE;
            if (turns < bestTurns) {
                bestTurns = turns;
                best = d;
            }
        }
        return best;
    }

    /** Round 224's S/F precedence: {@code p}'s first move in Direction order that crosses the line with a legal
     *  run-up onto a free legal landing that sheds its speed and can still reach CP1. */
    private static Direction firstPermittedCrossing(final RaceGame g, final Player p,
            final RaceAi.CellOccupancy occupied) {
        final int[] pos = p.getPosition(), vel = p.getVelocity();
        for (final Direction d : Direction.values()) {
            final int[] n = landing(p, d);
            final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
            if (g.crossesFinishLegally(pos[0], pos[1], n[0], n[1]) && freeLegal(g, p, d, occupied)
                    && g.reach.shedableLanding(n[0], n[1], nvx, nvy)
                    && g.reach.turnsToGate(1, n[0], n[1], nvx, nvy) != Integer.MAX_VALUE)
                return d;
        }
        return null;
    }

    /** Round 224's checkpoint precedence: {@code p}'s first move in Direction order that touches its next
     *  checkpoint onto a free legal landing that is alive and can still reach the gate after it. */
    private static Direction firstPermittedTouch(final RaceGame g, final Player p,
            final RaceAi.CellOccupancy occupied) {
        final int[] pos = p.getPosition(), vel = p.getVelocity();
        final int gate = p.getNextGate();
        for (final Direction d : Direction.values()) {
            final int[] n = landing(p, d);
            final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
            if (g.touchesGate(gate, pos[0], pos[1], n[0], n[1]) && freeLegal(g, p, d, occupied)
                    && g.reach.isAlive(n[0], n[1], nvx, nvy)
                    && g.reach.turnsToGate(gate == 1 ? 2 : 0, n[0], n[1], nvx, nvy) != Integer.MAX_VALUE)
                return d;
        }
        return null;
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
