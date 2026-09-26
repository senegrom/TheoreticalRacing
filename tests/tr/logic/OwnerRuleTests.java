package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Rectangle2D;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Properties;
import tr.gui.RaceUI;

/** The owner's rules (CLAUDE.md): rank first, the single-player rule and the
 *  grid rule, plus the round-279 fixes that make the AI conform to them. */
public final class OwnerRuleTests {
    private OwnerRuleTests() {}

    public static void main(final String[] args) throws Exception {
        testRankVerdict();
        testSoloBoundary();
        testPointToPointSolo();
        testFinishingMove();
        testLappedRival();
        testGridRule();
        System.out.println("OwnerRuleTests: rank-first verdicts, the 20-cell single-player boundary in lap and"
                + " point-to-point races, finishing crossings, lapped rivals and the grid rule OK");
    }

    /** Round 279 (round 275): a point-to-point course builds no exact potential,
     *  so the single-player rule descends the reachability map -- the exact
     *  distance to its one crossing: the legal landing the map puts closest to
     *  the line, and the crossing itself once it is in reach. */
    private static void testPointToPointSolo() throws Exception {
        final RaceGame g = straight();
        check(g.optimalPotential() == null, "a point-to-point course built an exact potential");
        final Player me = car(1, 50, 10, 3, 0);
        g.players = new Player[]{me, car(2, 72, 5, 0, 0)};
        final Direction solo = aloneMove(g, me);
        check(solo != null, "no solo descent on a point-to-point course");
        int best = Integer.MAX_VALUE, taken = Integer.MAX_VALUE;
        for (final Direction d : Direction.values()) {
            final int vx = 3 + d.dx, vy = d.dy;
            if (RaceGame.aiVelocityOutOfRange(vx, vy) || !g.aiMoveLegal(50, 10, 50 + vx, 10 + vy))
                continue;
            final int value = g.reach.turnsToFinish(50 + vx, 10 + vy, vx, vy);
            best = Math.min(best, value);
            if (d == solo)
                taken = value;
        }
        check(best < Integer.MAX_VALUE && taken == best, "the solo move is not the map's closest landing");
        check(decide(g, me) == solo, "with the nearest rival 22 cells away the car left the solo descent");
        final Player late = car(1, 168, 10, 4, 0);
        g.players = new Player[]{late, car(2, 60, 10, 0, 0)};
        final Direction last = aloneMove(g, late);
        check(last != null && g.crossesFinishLegally(168, 10, 172 + last.dx, 10 + last.dy),
                "a car one move from the line did not take the crossing");
    }

    /** Round 279 (round 272): in a lap race a crossing of the line with a
     *  checkpoint or a lap still owed is an ordinary move, not the finish; on a
     *  point-to-point course every legal crossing finishes. */
    private static void testFinishingMove() throws Exception {
        final Method prepare = RaceAi.class.getDeclaredMethod("prepareDecisionFrame", int[].class, int[].class, int.class);
        prepare.setAccessible(true);
        final Method finishing = RaceAi.class.getDeclaredMethod("finishingMove", int.class, int.class, int.class, int.class);
        finishing.setAccessible(true);
        final RaceGame g = lapStraight();
        final Player me = car(1, 168, 10, 5, 0);
        g.players = new Player[]{me, car(2, 60, 10, 0, 0)};
        check(g.crossesFinishLegally(168, 10, 173, 10), "the fixture's line is not crossed");
        for (final int gate : new int[]{1, 2, 0}) {
            me.setNextGate(gate);
            prepare.invoke(g.ai, me.getPosition(), me.getVelocity(), 1);
            check((boolean) finishing.invoke(g.ai, 168, 10, 173, 10) == (gate == 0),
                    "with gate " + gate + " next the crossing's finish verdict is wrong");
        }
        g.totalLaps = 2;
        prepare.invoke(g.ai, me.getPosition(), me.getVelocity(), 1);
        check(!(boolean) finishing.invoke(g.ai, 168, 10, 173, 10), "a crossing with a lap still owed finished the race");
        final RaceGame p = straight();
        final Player q = car(1, 168, 10, 5, 0);
        p.players = new Player[]{q, car(2, 60, 10, 0, 0)};
        prepare.invoke(p.ai, q.getPosition(), q.getVelocity(), 1);
        check((boolean) finishing.invoke(p.ai, 168, 10, 173, 10), "a point-to-point crossing did not finish the race");
    }

    /** Round 279 (round 277): the seal fights for places, so a car the mover has
     *  lapped -- a full lap of gate events or more behind -- is neither its
     *  target nor part of the field it counts, however near the line it is. */
    private static void testLappedRival() throws Exception {
        final RaceGame g = lapStraight();
        g.totalLaps = 2;
        final Player me = car(1, 50, 10, 3, 0);
        me.incrementLap();
        final Player lapped = car(2, 160, 10, 0, 0);
        final Player behind = car(3, 100, 10, 0, 0);
        behind.setNextGate(2);
        g.players = new Player[]{me, lapped, behind};
        final Method isLapped = RaceAi.class.getDeclaredMethod("lappedByMover", Player.class, int.class);
        isLapped.setAccessible(true);
        check((boolean) isLapped.invoke(g.ai, lapped, 1), "a car a full lap behind was not lapped");
        check(!(boolean) isLapped.invoke(g.ai, behind, 1), "a car less than a lap behind was counted as lapped");
        final Method count = RaceAi.class.getDeclaredMethod("placeRivalsRemaining", int.class);
        count.setAccessible(true);
        check((int) count.invoke(g.ai, 1) == 1, "the seal still counts a lapped car as a rival for places");
        final Method target = RaceAi.class.getDeclaredMethod("decisivePlaceRival", int.class);
        target.setAccessible(true);
        final Method nearest = RaceAi.class.getDeclaredMethod("decisiveRival", int.class);
        nearest.setAccessible(true);
        check((int) nearest.invoke(g.ai, 1) == 1, "the fixture's lapped car is not the one nearest the line");
        check((int) target.invoke(g.ai, 1) == 2, "the seal targets a car it has lapped");
        final RaceGame p = straight();
        p.players = new Player[]{car(1, 50, 10, 3, 0), car(2, 160, 10, 0, 0)};
        check(!(boolean) isLapped.invoke(p.ai, p.players[1], 1), "a point-to-point race has laps");
    }

    /** The owner's grid rule (2026-09-24): the starting grid is legal ground for
     *  a car until it first leaves it -- any number of moves inside it first --
     *  and the AI models it by the deciding car's own first checkpoint. */
    private static void testGridRule() throws Exception {
        final RaceGame g = gridStraight();
        final Player me = g.players[0];
        check(g.gridLegalFor(me), "a car standing on the grid was not grid-legal");
        check(g.evaluateMove(me, new int[]{5, 2}, new int[]{5, 0}).legal(), "a car on the grid could not step into its pocket");
        me.setPosition(new int[]{5, 0});
        check(g.evaluateMove(me, new int[]{5, 0}, new int[]{7, 0}).legal(), "a second move inside the grid was refused");
        me.leaveGrid();
        me.setPosition(new int[]{8, 2});
        check(!g.gridLegalFor(me), "a car that left the grid stayed grid-legal");
        check(!g.evaluateMove(me, new int[]{8, 2}, new int[]{8, 0}).legal(), "a car that left the grid landed in the pocket");
        check(g.evaluateMove(me, new int[]{8, 2}, new int[]{9, 3}).legal(), "ordinary track inside the grid became illegal");
        final Player scattered = car(3, 11, 2, 0, 0);
        check(!g.gridLegalFor(scattered), "a car off the grid was grid-legal");
        check(g.evaluateMove(scattered, new int[]{11, 2}, new int[]{12, 3}).legal(), "the fixture's track is not legal");
        check(!g.evaluateMove(scattered, new int[]{11, 2}, new int[]{10, 0}).legal(), "a car that never stood on the grid landed in the pocket");
        final Player restored = car(4, 5, 2, 0, 0);
        restored.restoreLapState(me.lapState());
        check(restored.hasLeftGrid(), "the undo lap state lost the left-grid flag");
        g.aiGridLegal = true;
        check(g.aiMoveLegal(8, 2, 8, 0), "the AI's world with the grid refused the pocket");
        g.aiGridLegal = false;
        check(!g.aiMoveLegal(8, 2, 8, 0), "the AI's world without the grid allowed the pocket");
        check(g.aiMoveLegal(8, 2, 9, 3), "the AI's world without the grid refused ordinary track");
        g.aiGridLegal = true;
    }

    /** A straight whose upper wall starts at x = 11, so a grid jutting out below
     *  the corridor (its row y = 0) opens onto the track, as on the real courses. */
    private static RaceGame gridStraight() throws Exception {
        final RaceGame g = new RaceGame(new Properties());
        g.gameCols = 180; g.gameRows = 20;
        g.track = new Track();
        g.track.addLeft(11, 1); g.track.addLeft(173, 1);
        g.track.addRight(0, 19); g.track.addRight(173, 19);
        g.trackA = new Area(new Rectangle2D.Double(0, 1, 173, 18));
        g.startZoneA = new Area(new Rectangle2D.Double(0, -0.5, 10.5, 3.5));
        g.finishLine = new Line2D.Double(172.5, 1, 172.5, 19);
        set(g, "finishFwdX", 1.0);
        set(g, "rui", new RaceUI(g.gameRows, g.gameCols));
        g.players = new Player[]{car(1, 5, 2, 0, 0), car(2, 60, 10, 0, 0)};
        g.reach.computeDistMap();
        g.reach.computeReachability();
        return g;
    }

    /** Rank first: a live verdict carries the rivals that finished ahead of the
     *  mover, place before time; with nobody ahead it is the old verdict. */
    private static void testRankVerdict() {
        final int s = RaceAi.VERDICT_PLACE_STRIDE;
        check(RaceAi.rankVerdict(0, 0) == 0 && RaceAi.rankVerdict(0, 17) == 17, "a verdict with nobody ahead changed");
        check(RaceAi.rankVerdict(1, 0) == s, "a finish behind one rival read as a win");
        check(RaceAi.rankVerdict(1, 0) > RaceAi.rankVerdict(0, s - 1), "one place down ranked above a slower open race");
        check(RaceAi.rankVerdict(2, 3) > RaceAi.rankVerdict(1, 900), "two places down ranked above one place down");
        check(RaceAi.rankVerdict(1, 5) < RaceAi.rankVerdict(1, 6), "time no longer breaks a tie in place");
        check(RaceAi.rankVerdict(3, Integer.MAX_VALUE) == Integer.MAX_VALUE, "an unreachable verdict overflowed");
        check(RaceAi.rankVerdict(7, s + 5) == 8 * s - 1, "time spilled into the place digit");
        check(RaceAi.rankVerdict(2, 41) % s == 41, "the time part of a verdict is lost");
    }

    /** No live rival within AI1_CHOOSER_MAXDIST (20) Chebyshev cells: the exact
     *  solo descent. 20 cells is inside the rule, 21 outside, and a finished
     *  rival never counts. A one-lap race with checkpoints, where the exact
     *  potential exists (point-to-point courses: testPointToPointSolo). */
    private static void testSoloBoundary() throws Exception {
        final RaceGame g = lapStraight();
        final Field radius = RaceAi.class.getDeclaredField("AI1_CHOOSER_MAXDIST");
        radius.setAccessible(true);
        final int r = radius.getInt(null);
        check(r == 20, "the rule's radius is not 20 cells: " + r);
        final Method within = RaceAi.class.getDeclaredMethod("rivalWithinCheb", int.class, int.class, int.class, int.class);
        within.setAccessible(true);
        final Player me = car(1, 50, 10, 3, 0);
        g.players = new Player[]{me, car(2, 70, 5, 0, 0)};
        check((boolean) within.invoke(g.ai, 50, 10, 1, r), "a rival exactly 20 cells away was outside the rule");
        g.players = new Player[]{me, car(2, 71, 5, 0, 0)};
        check(!(boolean) within.invoke(g.ai, 50, 10, 1, r), "a rival 21 cells away counted");
        final Direction solo = aloneMove(g, me);
        check(solo != null, "no solo descent on the fixture");
        check(decide(g, me) == solo, "with the nearest rival 21 cells away the car left the solo descent");
        final Player done = car(2, 55, 10, 0, 0);
        done.setFinishedPlace(1);
        g.players = new Player[]{me, done};
        check(!(boolean) within.invoke(g.ai, 50, 10, 1, r), "a finished rival counted as live");
        check(decide(g, me) == aloneMove(g, me), "a finished rival pulled the car off the solo descent");
    }

    private static Direction decide(final RaceGame g, final Player me) throws Exception {
        g.subgamestate = 0;
        final Method m = RaceAi.class.getDeclaredMethod("optimalMoveAI1", int[].class, int[].class, int.class);
        m.setAccessible(true);
        return (Direction) m.invoke(g.ai, me.getPosition(), me.getVelocity(), me.getNumber());
    }

    private static Direction aloneMove(final RaceGame g, final Player me) throws Exception {
        final Method prepare = RaceAi.class.getDeclaredMethod("prepareDecisionFrame", int[].class, int[].class, int.class);
        prepare.setAccessible(true);
        prepare.invoke(g.ai, me.getPosition(), me.getVelocity(), me.getNumber());
        final Method m = RaceAi.class.getDeclaredMethod("optimalAloneMove", int[].class, int[].class, int.class);
        m.setAccessible(true);
        return (Direction) m.invoke(g.ai, me.getPosition(), me.getVelocity(), me.getNumber());
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
        g.players = new Player[]{car(1, 10, 10, 0, 0), car(2, 30, 10, 0, 0)};
        g.reach.computeDistMap();
        g.reach.computeReachability();
        return g;
    }

    /** straight() as a one-lap race: CP1 at x = 120, CP2 at 140, the line at 172.5. */
    private static RaceGame lapStraight() throws Exception {
        final RaceGame g = straight();
        g.lapGates = new Line2D[]{g.finishLine,
                new Line2D.Double(120, 1, 120, 19), new Line2D.Double(140, 1, 140, 19)};
        set(g, "lapCrossGate", g.finishLine);
        set(g, "lapFwdX", 1.0);
        g.totalLaps = 1;
        return g;
    }

    private static Player car(final int number, final int x, final int y, final int vx, final int vy) {
        final Player p = new Player("P" + number, number, Color.BLUE, Player.Kind.AI1);
        p.setPosition(new int[]{x, y});
        p.setVelocity(new int[]{vx, vy});
        p.setNextGate(1);
        return p;
    }

    private static void set(final Object o, final String name, final Object value) throws Exception {
        final Field f = o.getClass().getDeclaredField(name);
        f.setAccessible(true);
        f.set(o, value);
    }

    private static void check(final boolean condition, final String message) {
        if (!condition) throw new AssertionError(message);
    }
}
