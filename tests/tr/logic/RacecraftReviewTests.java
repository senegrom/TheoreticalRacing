package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Rectangle2D;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.Properties;
import tr.gui.RaceUI;

/** Contract tests, not evidence of a fleet-wide place improvement. */
public final class RacecraftReviewTests {
    private RacecraftReviewTests() {}
    public static void main(final String[] args) throws Exception {
        testConfiguration();
        testShortlist();
        testProjectedOrder();
        testDuelCertificates();
        testCrossingDoesNotCancelChooser();
        System.out.println("RacecraftReviewTests: OK");
    }
    private static void testConfiguration() {
        final Properties p = new Properties();
        check(!RacecraftReview.Config.from(p).audit, "audit enabled by default");
        for (final RacecraftReview.Feature feature : RacecraftReview.Feature.values())
            check(!RacecraftReview.Config.from(p).has(feature), "experiment enabled by default");
        p.setProperty("racecraftReview", "crossing,duel-anytime");
        final RaceGame control = new RaceGame(p);
        check(!RacecraftReview.enabled(control, 1, RacecraftReview.Feature.CROSSING), "flags bypass candidate slots");
        p.setProperty("candidateSlots", "1");
        final RaceGame candidate = new RaceGame(p);
        check(RacecraftReview.enabled(candidate, 1, RacecraftReview.Feature.CROSSING), "candidate not enabled");
        check(!RacecraftReview.enabled(candidate, 2, RacecraftReview.Feature.CROSSING), "unselected slot changed");
        check(!RacecraftReview.enabled(candidate, 1, RacecraftReview.Feature.SELECTIVE), "independent flags coupled");
        for (final String invalid : new String[]{"typo", "crossing,", ",duel-cache"}) {
            p.setProperty("racecraftReview", invalid);
            expectInvalid(p);
        }
        p.setProperty("racecraftReview", "all");
        for (final RacecraftReview.Feature feature : RacecraftReview.Feature.values())
            check(RacecraftReview.Config.from(p).has(feature), "all omits a feature");
        p.setProperty("racecraftReviewAudit", "perhaps");
        expectInvalid(p);
    }
    private static void expectInvalid(final Properties p) {
        boolean rejected = false;
        try { RacecraftReview.Config.from(p); } catch (final IllegalArgumentException expected) { rejected = true; }
        check(rejected, "invalid experiment configuration was silently accepted");
    }
    private static void testShortlist() {
        final double[] scores = new double[Direction.values().length];
        Arrays.fill(scores, Double.MAX_VALUE);
        scores[Direction.NW.ordinal()] = 0;
        scores[Direction.N.ordinal()] = 0;
        scores[Direction.NE.ordinal()] = 0.5;
        scores[Direction.S.ordinal()] = 1.5;
        scores[Direction.SW.ordinal()] = 3;
        final double[] before = scores.clone();
        check(Arrays.equals(RacecraftReview.shortlist(scores, 0, false),
                new Direction[]{Direction.NW, Direction.N, Direction.NE}), "control shortlist changed");
        check(Arrays.equals(RacecraftReview.shortlist(scores, 0, true),
                new Direction[]{Direction.NW, Direction.N, Direction.NE, Direction.S}), "diverse proposal wrong");
        check(Arrays.equals(scores, before), "shortlist mutated live scores");
        scores[Direction.S.ordinal()] = Double.NaN;
        check(RacecraftReview.shortlist(scores, 0, true).length == 3, "nonfinite candidate admitted");
    }
    private static void testProjectedOrder() {
        check(RacecraftReview.projectedAhead(1, 2, new int[]{5, 5, 5}, new boolean[]{true, true, true}) == 3,
                "equal-time endpoint ignored turn order or finished rivals");
        check(RacecraftReview.projectedAhead(0, 0, new int[]{9, 3, 1}, new boolean[]{true, true, false}) == 1,
                "crashed/retired rival counted as projected finisher");
        check(RacecraftReview.projectedAhead(0, 0, new int[]{9, Integer.MAX_VALUE}, new boolean[]{true, true}) == -1,
                "missing route value promoted to a place estimate");
        check(RacecraftReview.improvesTiedForecast(14, 14, 19, 18), "strict improvement in tied model rejected");
        check(!RacecraftReview.improvesTiedForecast(14, 15, 19, 18), "nominal regression accepted");
        check(!RacecraftReview.improvesTiedForecast(14, 14, -1, 18), "unknown stronger world used as proof");
        check(!RacecraftReview.improvesTiedForecast(14, 14, 19, 19), "model agreement changed policy");
    }
    private static void testDuelCertificates() throws Exception {
        final Method fixture = RaceAiDuelSearchTests.class.getDeclaredMethod("game", String.class);
        fixture.setAccessible(true);
        final Method verify = RaceAiDuelSearchTests.class.getDeclaredMethod("winsAfter", RaceGame.class,
                Player.class, Player.class, Direction.class, long.class, int.class);
        verify.setAccessible(true);
        final Method snapshot = RaceAiDuelSearchTests.class.getDeclaredMethod("snapshot", RaceGame.class);
        snapshot.setAccessible(true);
        final int[][] states = {
            {10,14,4,0,12,15,5,0}, {14,15,3,-1,11,16,6,-1},
            {11,18,3,1,9,23,5,-3}, {9,21,5,-1,15,23,2,-3},
            {15,8,2,1,10,13,6,1}, {10,9,4,1,13,14,5,0},
            {9,22,6,1,11,26,5,-1}, {8,23,6,-1,8,21,6,0}
        };
        int retained = 0, verified = 0;
        for (final int[] s : states) {
            final RaceGame g = (RaceGame) fixture.invoke(null, "1");
            g.players[0] = car(1, s[0], s[1], s[2], s[3]);
            g.players[1] = car(2, s[4], s[5], s[6], s[7]);
            final Object before = snapshot.invoke(null, g);
            for (int limit = 1; limit <= 256; limit++) {
                final RaceAiDuelSearch.SearchResult old = RaceAiDuelSearch.search(g, 1, 2, limit, false, false);
                final RaceAiDuelSearch.SearchResult now = RaceAiDuelSearch.search(g, 1, 2, limit, true, false);
                if (now.retainedProof()) {
                    check(old.move() == null && old.completedProof(), "control did not discard the same certificate");
                    check((boolean) verify.invoke(null, g, g.players[0], g.players[1], now.move(), 0L, 2),
                            "retained proof has a physical refutation");
                    retained++;
                    break;
                }
            }
            for (final int depth : new int[]{2, 3, 4}) {
                final RaceAiDuelSearch.SearchResult uncached = RaceAiDuelSearch.search(g, 1, depth, 200_000, true, false);
                final RaceAiDuelSearch.SearchResult cached = RaceAiDuelSearch.search(g, 1, depth, 200_000, true, true);
                check(!uncached.exhausted() && !cached.exhausted(), "equivalence fixture exhausted its generous budget");
                check(uncached.move() == cached.move(), "complete cached/uncached searches disagree");
                if (cached.move() != null) {
                    check((boolean) verify.invoke(null, g, g.players[0], g.players[1], cached.move(), 0L, depth),
                            "memoized certificate has a physical refutation");
                    verified++;
                }
            }
            check(before.equals(snapshot.invoke(null, g)), "duel experiment mutated its live board");
            final RaceAiDuelSearch.SearchResult exhausted = RaceAiDuelSearch.search(g, 1, 2, 0, true, true);
            check(exhausted.move() == null, "zero-budget nonterminal state invented a win");
        }
        check(retained > 0 && verified > 0, "duel checks were vacuous");
        System.out.println("Review duel checks: " + retained + " retained witnesses; " + verified + " verified cached certificates");
    }
    private static void testCrossingDoesNotCancelChooser() throws Exception {
        final RaceGame control = crossingFixture(false), candidate = crossingFixture(true);
        final int[] pos = candidate.players[0].getPosition(), vel = candidate.players[0].getVelocity();
        check(candidate.crossesFinishLegally(99, 10, 101, 10), "fixture does not cross the line");
        check(!candidate.evaluateMove(0, 1, 99, 10, 101, 10, false).finishes(),
                "checkpoint-owed fixture accidentally finishes");
        check(!candidate.evaluateMove(0, 0, 99, 10, 101, 10, false).finishes(),
                "non-final lap crossing accidentally finishes");
        check(candidate.evaluateMove(1, 0, 99, 10, 101, 10, false).finishes(), "actual finish not recognized");
        final double[] scores = new double[Direction.values().length];
        Arrays.fill(scores, Double.MAX_VALUE);
        scores[Direction.W.ordinal()] = 0;
        scores[Direction.NONE.ordinal()] = 0.5;
        final Method prepare = RaceAi.class.getDeclaredMethod("prepareDecisionFrame", int[].class, int[].class, int.class);
        prepare.setAccessible(true);
        final Method chooser = RaceAi.class.getDeclaredMethod("jointChooser", int[].class, int[].class,
                int.class, Direction.class, double[].class, double.class);
        chooser.setAccessible(true);
        final Method snapshot = RaceAiDuelSearchTests.class.getDeclaredMethod("snapshot", RaceGame.class);
        snapshot.setAccessible(true);
        for (final RaceGame g : new RaceGame[]{control, candidate}) {
            prepare.invoke(g.ai, pos, vel, 1);
            final Object before = snapshot.invoke(null, g);
            final RacecraftReview.Trace trace = new RacecraftReview.Trace(g, 1);
            set(g.ai, "reviewTrace", trace);
            chooser.invoke(g.ai, pos, vel, 1, Direction.W, scores, 0.0);
            check(trace.evaluations == (g == candidate ? 2 : 1), "nonterminal crossing aborted the candidate comparison");
            check(before.equals(snapshot.invoke(null, g)), "chooser mutated the live race");
            check(trace.json(Direction.W).contains("\"replayReady\":false"), "forecast mislabeled as referee state");
        }
    }
    private static RaceGame crossingFixture(final boolean enabled) throws Exception {
        final Properties props = new Properties();
        props.setProperty("candidateSlots", "1");
        if (enabled) props.setProperty("racecraftReview", "crossing");
        final RaceGame g = new RaceGame(props);
        g.gameCols = 180; g.gameRows = 20;
        g.track = new Track();
        g.track.addLeft(0, 1); g.track.addLeft(173, 1);
        g.track.addRight(0, 19); g.track.addRight(173, 19);
        g.trackA = new Area(new Rectangle2D.Double(0, 1, 173, 18));
        g.startZoneA = new Area();
        g.finishLine = new Line2D.Double(100.5, 1, 100.5, 19);
        g.lapGates = new Line2D[]{g.finishLine,
                new Line2D.Double(120, 1, 120, 19), new Line2D.Double(140, 1, 140, 19)};
        g.totalLaps = 2;
        set(g, "finishFwdX", 1.0); set(g, "lapFwdX", 1.0);
        set(g, "lapCrossGate", g.finishLine);
        set(g, "rui", new RaceUI(g.gameRows, g.gameCols));
        g.players = new Player[]{car(1, 99, 10, 2, 0), car(2, 90, 14, 1, 0)};
        for (final Player p : g.players) p.setNextGate(1);
        g.reach.computeDistMap();
        g.reach.computeReachability();
        return g;
    }
    private static Player car(final int number, final int x, final int y, final int vx, final int vy) {
        final Player p = new Player("P" + number, number, Color.BLUE, Player.Kind.AI1);
        p.setPosition(new int[]{x, y}); p.setVelocity(new int[]{vx, vy});
        return p;
    }
    private static void set(final Object target, final String name, final Object value) throws Exception {
        final Field field = target.getClass().getDeclaredField(name);
        field.setAccessible(true); field.set(target, value);
    }
    private static void check(final boolean condition, final String message) {
        if (!condition) throw new AssertionError(message);
    }
}
