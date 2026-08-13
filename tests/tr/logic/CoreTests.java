package tr.logic;

import java.awt.Color;
import java.util.ArrayList;
import java.util.List;

/** Lightweight dependency-free regression tests for pure core helpers. */
public final class CoreTests {
    private CoreTests() {}

    public static void main(final String[] args) {
        testDirections();
        testPlayerKinds();
        testDefaultProperties();
        testPointParsing();
        testTrackNames();
        testBorderValidation();
        testEdgeLegalCache();
        testEndgameMemoKey();
        testDistinctCoverMatching();
        testRaceAiStateIsolation();
        testReachabilityFailurePropagation();
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


    private static void testTrackNames() {
        check(TrackIO.validTrackName("sprint"), "simple track name rejected");
        check(TrackIO.validTrackName("the_long_loop"), "underscore track name rejected");
        check(!TrackIO.validTrackName("../sprint"), "parent traversal track name accepted");
        check(!TrackIO.validTrackName("..\\sprint"), "Windows traversal track name accepted");
        check(!TrackIO.validTrackName("C:sprint"), "drive-qualified track name accepted");
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

    private static void testSegmentIntersection() {
        check(TrackGeometry.checkIntersect(p(0, 0), p(10, 10), p(0, 10), p(10, 0), (byte) 0),
                "crossing diagonals should intersect");
        check(!TrackGeometry.checkIntersect(p(0, 0), p(10, 0), p(0, 2), p(10, 2), (byte) 0),
                "parallel separated segments should not intersect");
        check(TrackGeometry.checkIntersect(p(0, 0), p(10, 0), p(5, 0), p(15, 0), (byte) 0),
                "collinear overlap should intersect");
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
