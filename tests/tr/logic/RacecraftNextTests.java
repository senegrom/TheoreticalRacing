package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Rectangle2D;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.Properties;
import tr.gui.RaceUI;

/** No fleet-performance claim: structural contracts and independent referee replay. */
public final class RacecraftNextTests {
    private RacecraftNextTests() {}

    public static void main(final String[] args) throws Exception {
        outcomeOrder();
        configuration();
        crashLedger();
        finishTime();
        opening();
        placement();
        replay();
        System.out.println("RacecraftNextTests: outcome ordering, crash ranks, own time, opening budgets, placement isolation and referee tails OK");
    }

    private static RacecraftOutcome result(final RacecraftOutcome.Status status, final int ahead,
            final int elapsed, final int rest) {
        return new RacecraftOutcome(status, ahead, elapsed, rest);
    }

    private static void outcomeOrder() {
        final RacecraftOutcome sixth = result(RacecraftOutcome.Status.CRASHED, 5, 8, 0);
        final RacecraftOutcome eighth = result(RacecraftOutcome.Status.CRASHED, 7, 1, 0);
        check(sixth.betterThan(eighth, true), "failed to salvage a retirement place");
        check(!sixth.betterThan(eighth, false), "crash arm is not separable");
        check(!sixth.betterThan(RacecraftOutcome.unknown(), true), "unknown became a crash");
        check(RacecraftOutcome.retirementAhead(4, 2) == 5, "finishers improved a retiring car's rank");
        final RacecraftOutcome slowWinner = result(RacecraftOutcome.Status.FINISHED, 0, 9, 0);
        final RacecraftOutcome fastSecond = result(RacecraftOutcome.Status.FINISHED, 1, 2, 0);
        check(slowWinner.betterThan(fastSecond, true), "speed outranked place");
        check(result(RacecraftOutcome.Status.FINISHED, 0, 3, 0).betterThan(slowWinner, true),
                "finish time collapsed to zero");
        check(slowWinner.successful() && slowWinner.liveVerdict() > 0, "finish status is still inferred from zero");
        check(result(RacecraftOutcome.Status.RUNNING, 0, 7, Integer.MAX_VALUE).numericKey()
                == Integer.MAX_VALUE, "unknown route got a favorable time cap");
    }

    private static void configuration() {
        for (final String invalid : new String[]{"unknown", "opening,opening", "opening,"}) {
            final Properties p = new Properties(); p.setProperty("racecraftNext", invalid);
            boolean rejected = false;
            try { new RacecraftNext(p); } catch (final IllegalArgumentException e) { rejected = true; }
            check(rejected, "bad flags accepted");
        }
        final Properties zero = new Properties(); zero.setProperty("racecraftOpeningTrials", "0");
        check(new RacecraftNext(zero).openingTrials == 0, "zero-budget control missing");
    }

    private static RaceGame straight(final String flags, final String slots) throws Exception {
        final Properties props = new Properties();
        props.setProperty("racecraftNext", flags); props.setProperty("candidateSlots", slots);
        final RaceGame g = new RaceGame(props);
        g.gameCols = 80; g.gameRows = 20;
        g.track = new Track();
        g.track.addLeft(0, 1); g.track.addLeft(73, 1);
        g.track.addRight(0, 19); g.track.addRight(73, 19);
        g.trackA = new Area(new Rectangle2D.Double(0, 1, 73, 18));
        g.startZoneA = new Area(new Rectangle2D.Double(0, 1, 10, 18));
        g.finishLine = new Line2D.Double(72.5, 1, 72.5, 19);
        set(g, "finishFwdX", 1.0); set(g, "rui", new RaceUI(20, 80));
        g.players = new Player[]{car(1, 20, 8, 0, 0), car(2, 22, 10, 0, 0), car(3, 24, 12, 0, 0)};
        g.reach.computeDistMap(); g.reach.computeReachability();
        return g;
    }

    private static Player car(final int n, final int x, final int y, final int vx, final int vy) {
        final Player p = new Player("P" + n, n, Color.BLUE, Player.Kind.AI1);
        p.setPosition(new int[]{x, y}); p.setVelocity(new int[]{vx, vy}); return p;
    }

    private static RacecraftOutcome simulate(final RaceGame g, final int slot, final int rounds) throws Exception {
        g.subgamestate = slot;
        g.ai.querySimOutcome(slot, rounds, true, false, true, 3, new int[3]);
        return (RacecraftOutcome) get(g.ai, "lastResearchOutcome");
    }

    private static void crashLedger() throws Exception {
        final RaceGame g = straight("crash-rank", "1,2,3");
        g.players = new Player[]{car(1, 20, 2, 0, -12), car(2, 30, 2, 0, -12), car(3, 40, 10, 0, 0)};
        final RacecraftOutcome afterRival = simulate(g, 1, 2);
        check(afterRival != null && afterRival.crashed() && afterRival.ahead() == 1,
                "prior retirement not counted: " + afterRival);
        g.players[0] = car(1, 20, 10, 0, 0);
        final RacecraftOutcome first = simulate(g, 1, 2);
        check(first != null && first.crashed() && first.ahead() == 2,
                "first retirement has wrong rank: " + first);
        check(afterRival.betterThan(first, true), "simulated retirement order collapsed");
    }

    private static void finishTime() throws Exception {
        final RaceGame g = straight("rank-time", "1,2,3");
        g.players = new Player[]{car(1, 70, 10, 2, 0), car(2, 10, 6, 0, 0), car(3, 12, 14, 0, 0)};
        final RacecraftOutcome fast = simulate(g, 0, 10);
        g.players[0] = car(1, 60, 10, 2, 0);
        final RacecraftOutcome slow = simulate(g, 0, 10);
        check(fast.successful() && slow.successful() && fast.ahead() == slow.ahead()
                && fast.time() < slow.time(), "same-place finishes lost own time: " + fast + " / " + slow);
        check(fast.liveVerdict() > 0, "finishing time still zero");
    }

    private static void opening() throws Exception {
        final RaceGame g = straight("opening,rank-time,crash-rank", "1,2,3");
        final String before = RacecraftReplay.snapshot(g);
        check(g.ai.computeAiMove() != null, "opening produced no action");
        check(before.equals(RacecraftReplay.snapshot(g)), "opening changed live decision state");
        final int trials = (int) get(g.ai, "researchOpeningTrials");
        check(trials > 0 && trials <= g.racecraftNext.openingTrials, "opening budget not respected: " + trials);
        g.setQueryTurnCounter(4 * g.players.length);
        check(!RacecraftNext.opening(g, 1), "opening remained armed in mid-race");
        final RaceGame off = straight("opening,rank-time,crash-rank", "");
        final RaceGame base = straight("", "1,2,3");
        check(off.ai.computeAiMove() == base.ai.computeAiMove(), "flags without slots changed control");
        // Outside the canonical boundary the candidate must use the literal solo descent.
        g.players = new Player[]{car(1, 20, 10, 0, 0), car(2, 60, 10, 0, 0)};
        g.setQueryTurnCounter(0); g.subgamestate = 0;
        final Method solo = RaceAi.class.getDeclaredMethod("optimalAloneMove", int[].class, int[].class, int.class);
        solo.setAccessible(true);
        final Direction actual = g.ai.computeAiMove();
        check(actual == solo.invoke(g.ai, g.players[0].getPosition(), g.players[0].getVelocity(), 1),
                "candidate violated the solo boundary");
    }

    private static void placement() throws Exception {
        final RaceGame g = straight("start-ties", "3");
        g.players = new Player[]{car(1, 5, 5, 0, 0), car(2, 5, 15, 0, 0),
                car(3, Player.INIT_POS, Player.INIT_POS, 0, 0)};
        g.subgamestate = 2;
        final String before = RacecraftReplay.snapshot(g);
        final int[] stock = {5, 10}; final int[][] ties = {{5, 8}, {5, 10}, {5, 12}};
        final int[] result = RacecraftReplay.chooseStart(g, g.players[2], stock, ties);
        check(Arrays.stream(ties).anyMatch(p -> Arrays.equals(p, result)), "placement left solo-optimal tie set");
        check(before.equals(RacecraftReplay.snapshot(g)), "placement changed live players");
        g.subgamestate = 1;
        check(Arrays.equals(stock, RacecraftReplay.chooseStart(g, g.players[1], stock, ties)),
                "placement guessed a later unplaced car");
    }

    private static void replay() throws Exception {
        final RaceGame g = straight("", "");
        final String original = RacecraftReplay.snapshot(g);
        final RacecraftReplay.Board root = RacecraftReplay.parse(g, original);
        check(root.encode().equals(original), "rc3 round-trip lost state");
        final RacecraftReplay.Tail tail = RacecraftReplay.run(g, root, 0, Direction.E, 300, false);
        check(tail.complete() && tail.place() > 0 && !tail.trace().isEmpty(), "bounded fixture tail did not finish");
        check(original.equals(RacecraftReplay.snapshot(g)), "tail mutated live state");
        check(tail.equals(RacecraftReplay.run(g, root, 0, Direction.E, 300, false)), "tail depends on query history");
        check(!RacecraftReplay.run(g, root, 0, Direction.E, 1, false).complete(), "work limit became a completed label");
        boolean rejected = false;
        try { RacecraftReplay.parse(g, original.replace(root.identity, "invalid")); }
        catch (final IllegalArgumentException e) { rejected = true; }
        check(rejected && original.equals(RacecraftReplay.snapshot(g)), "invalid snapshot mutated the board");
        // Independently commit the exact recorded actions through the real referee.
        final RaceGame referee = straight("", "");
        referee.setAutoMode(true); referee.setAutoRaceEndHook(() -> {});
        final Path log = Files.createTempFile("racecraft-referee-", ".log");
        referee.setGameLogPath(log.toString()); set(referee, "gamestate", GameState.PLAY);
        final Method commit = RaceGame.class.getDeclaredMethod("commitMove", int[].class, int[].class, int[].class);
        commit.setAccessible(true);
        try {
            for (final String row : tail.trace()) {
                final String[] f = row.split(":"); final int slot = Integer.parseInt(f[0]);
                check(referee.subgamestate == slot, "tail uses a different cyclic order");
                final Player p = referee.players[slot]; final Direction d = Direction.valueOf(f[1]);
                final int[] x = p.getPosition().clone(), v = p.getVelocity();
                final int[] nv = {v[0] + d.dx, v[1] + d.dy}, nx = {x[0] + nv[0], x[1] + nv[1]};
                commit.invoke(referee, x, nv, nx);
                check(referee.turnCount() == Integer.parseInt(f[11])
                        && p.getFinishedPlace() == Integer.parseInt(f[7])
                        && p.getLap() == Integer.parseInt(f[8]) && p.getNextGate() == Integer.parseInt(f[9])
                        && (p.hasLeftGrid() ? 1 : 0) == Integer.parseInt(f[10]), "tail disagrees with referee: " + row);
            }
            check(RacecraftReplay.snapshot(referee).equals(tail.finalState()), "final referee classification/state differs");
        } finally { Files.deleteIfExists(log); }
        final String corpus = RacecraftReplay.answer(g, "cf3,300,-|" + original);
        check(corpus.contains("\"complete\":true") && corpus.contains("\"traceSha256\""), "corpus did not include complete tails");
        check(original.equals(RacecraftReplay.snapshot(g)), "corpus leaked its board");
    }

    private static Object get(final Object target, final String name) throws Exception {
        final Field f = target.getClass().getDeclaredField(name); f.setAccessible(true); return f.get(target);
    }
    private static void set(final Object target, final String name, final Object value) throws Exception {
        final Field f = target.getClass().getDeclaredField(name); f.setAccessible(true); f.set(target, value);
    }
    private static void check(final boolean condition, final String message) {
        if (!condition) throw new AssertionError(message);
    }
}
