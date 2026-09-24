package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Rectangle2D;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Properties;
import tr.gui.RaceUI;

/** The owner's rules (CLAUDE.md): rank first, and the single-player rule. */
public final class OwnerRuleTests {
    private OwnerRuleTests() {}

    public static void main(final String[] args) throws Exception {
        testRankVerdict();
        testSoloBoundary();
        System.out.println("OwnerRuleTests: rank-first verdicts and the 20-cell single-player boundary OK");
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
     *  potential exists (point-to-point courses build none: round 275). */
    private static void testSoloBoundary() throws Exception {
        final RaceGame g = straight();
        g.finishLine = new Line2D.Double(172.5, 1, 172.5, 19);
        g.lapGates = new Line2D[]{g.finishLine,
                new Line2D.Double(120, 1, 120, 19), new Line2D.Double(140, 1, 140, 19)};
        set(g, "lapCrossGate", g.finishLine);
        set(g, "lapFwdX", 1.0);
        g.totalLaps = 1;
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
