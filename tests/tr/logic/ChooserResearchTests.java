package tr.logic;

import java.awt.Color;
import java.awt.geom.Line2D;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.Properties;
import tr.gui.RaceUI;

/** Deterministic contracts; none of these finite samples is a performance claim. */
public final class ChooserResearchTests {
    private ChooserResearchTests() {}
    public static void main(final String[] args) throws Exception {
        config(); ledger(); forecasts(); protocol(); cacheIdentity();
        System.out.println("ChooserResearchTests: budgets, policy levels, setup actions, terminal ledger, feature compatibility, audit isolation and cache targets OK");
    }
    private static void check(final boolean b, final String message) { if (!b) throw new AssertionError(message); }
    private static void rejects(final Runnable r) { try { r.run(); } catch (final IllegalArgumentException e) { return; } throw new AssertionError("invalid input accepted"); }
    private static void config() {
        check(!new ChooserConfig(new Properties()).enabled(), "default enabled");
        for (final String value : List.of("aware,aware", "aware,student", "unknown", "legacy-guarded,setup", "legacy-unchecked,legacy-guarded")) {
            final Properties p = new Properties(); p.setProperty("chooser.experiments", value); rejects(() -> new ChooserConfig(p));
        }
        final Properties p = new Properties(); p.setProperty("chooser.policyBudget", "-1"); rejects(() -> new ChooserConfig(p));
        p.clear(); p.setProperty("chooser.experiments", "student"); rejects(() -> new ChooserConfig(p));
        p.clear(); p.setProperty("chooser.audit", "yes"); rejects(() -> new ChooserConfig(p));
        p.clear(); p.setProperty("chooser.experiments", "aware,setup,terminal"); check(new ChooserConfig(p).setup, "flags not parsed");
        final ChooserResearch.Budget b = new ChooserResearch.Budget(1, 1); b.policy(); b.move();
        try { b.policy(); throw new AssertionError("policy bound ignored"); } catch (final ChooserResearch.Limit expected) { check(b.policies == 1, "budget overcount"); }
        try { b.move(); throw new AssertionError("move bound ignored"); } catch (final ChooserResearch.Limit expected) { check(b.moves == 1, "move budget overcount"); }
        final ChooserResearch.Outcome second = new ChooserResearch.Outcome(0, true, 2, 8, "FINISH");
        final ChooserResearch.Outcome third = new ChooserResearch.Outcome(0, true, 3, 2, "FINISH");
        check(ChooserResearch.better(second, third, true), "time bought a worse terminal place");
        check(!ChooserResearch.better(second, third, false), "ordinary comparison changed");
        check(!ChooserResearch.better(new ChooserResearch.Outcome(5, false, 1, 0, "RUNNING"), second, true), "estimate pretends resolved");
    }
    private static Player car(final int number, final int x, final int y, final int vx, final int vy) {
        final Player p = new Player("P" + number, number, Color.BLUE, Player.Kind.AI2);
        p.setPosition(new int[]{x, y}); p.setVelocity(new int[]{vx, vy}); return p;
    }
    private static RaceGame game(final String track, final Properties settings) throws Exception {
        final Properties p = new Properties(); try (InputStream in = Files.newInputStream(Path.of("tracks", track + ".track"))) { p.load(in); }
        p.putAll(settings); p.setProperty("lastTrackLeft", p.getProperty("trackLeft")); p.setProperty("lastTrackRight", p.getProperty("trackRight"));
        final TrackIO.TrackData data = TrackIO.loadLastTrackData(p); check(data != null, "fixture unreadable");
        final RaceGame g = new RaceGame(p); g.gameCols = data.gameX(); g.gameRows = data.gameY(); g.track = new Track();
        for (final int[] point : data.left()) g.track.addLeft(point[0], point[1]);
        for (final int[] point : data.right()) g.track.addRight(point[0], point[1]);
        set(g, "rui", new RaceUI(g.gameRows, g.gameCols));
        g.players = new Player[]{car(1, 18, 27, 0, 0), car(2, 17, 29, 0, 0)};
        final Method build = RaceGame.class.getDeclaredMethod("buildTrackGeometry"); build.setAccessible(true); build.invoke(g);
        g.reach.ensureReachabilityReady(); return g;
    }
    private static String state(final RaceGame g) {
        final StringBuilder s = new StringBuilder().append(g.subgamestate).append('/').append(g.turnCount()).append('/')
                .append(g.chooserFinishedFirst()).append('/').append(g.chooserFinishedLast());
        for (final Player p : g.players) s.append(Arrays.toString(p.getPosition())).append(Arrays.toString(p.getVelocity()))
                .append(Arrays.toString(p.lapState())).append(p.getFinishedPlace()).append(p.getHistory());
        return s.toString();
    }
    private static void ledger() throws Exception {
        final RaceGame g = game("hairpin", new Properties());
        g.players = new Player[]{car(1, 17, 25, 1, -2), car(2, 17, 24, 2, 2)};
        final ChooserResearch.Board b = new ChooserResearch.Board(g);
        check(b.step(g, 0, Direction.NONE).equals("CRASH"), "physical blockade not replayed");
        check(b.place[0] == 2 && b.place[1] == 1 && b.ownMoves[1] == 0 && b.over(), "survivor got phantom turn");
        rejects(() -> b.step(g, 1, Direction.NONE));
        final Properties p = new Properties(); p.setProperty("laps", "2");
        final RaceGame circle = game("circle", p);
        circle.players = new Player[]{car(1, 50, 8, 1, 0), car(2, 87, 48, 0, 0)}; circle.players[0].setNextGate(0);
        final ChooserResearch.Board lap = new ChooserResearch.Board(circle);
        check(lap.step(circle, 0, Direction.E).equals("LAP") && lap.place[0] == 0 && lap.lap[0] == 1, "non-final crossing classified");
        circle.players[0].incrementLap();
        final ChooserResearch.Board finish = new ChooserResearch.Board(circle);
        check(finish.step(circle, 0, Direction.E).equals("FINISH") && finish.place[0] == 1 && finish.ownMoves[0] == 1, "finish ledger lost");
        circle.setQueryTurnCounter(3001);
        final ChooserResearch.Board timeout = new ChooserResearch.Board(circle);
        check(timeout.step(circle, 0, Direction.E).equals("TIMEOUT") && timeout.place[0] == 2 && timeout.place[1] == 1, "timeout precedence");
        circle.players = new Player[]{car(1, 50, 8, 1, 0)};
        check(!new ChooserResearch.Board(circle).over(), "solo incorrectly terminal");
    }
    private static void forecasts() throws Exception {
        final RaceGame g = game("hairpin", new Properties());
        final String before = state(g); final Direction original = g.ai.computeAiMove();
        final ChooserResearch.Run baseline = g.ai.chooserForecast(original, 3, false, false, null, true, null);
        check(baseline.outcome != null && baseline.secondBoard != null && baseline.secondOptions.size() >= 1, "forecast incomplete");
        check(state(g).equals(before), "forecast mutated live state");
        check(baseline.state.ownMoves[0] == 3, "partial first cycle counted as extra own move");
        final Direction second = baseline.secondOptions.get(baseline.secondOptions.size() - 1);
        final ChooserResearch.Run setup = g.ai.chooserForecast(original, 3, false, false, second, true, new ChooserResearch.Budget(4096, 8192));
        check(setup.actualSecond == second && setup.steps.toString().contains("forced-second"), "setup action not executed");
        final ChooserResearch.Run upgraded = g.ai.chooserForecast(original, 2, true, false, null, true, new ChooserResearch.Budget(16000, 32000));
        check(upgraded.upgrades >= 1 && upgraded.upgrades <= 2, "upgrade count unbounded");
        check(upgraded.steps.toString().contains("level1-chooser"), "chooser-aware forecast not used");
        check(state(g).equals(before), "level1 mutated state");
        final ChooserResearch.Budget tiny = new ChooserResearch.Budget(1, 2);
        try { g.ai.chooserForecast(original, 12, true, false, null, true, tiny); throw new AssertionError("tiny budget not exhausted"); }
        catch (final ChooserResearch.Limit expected) { check(state(g).equals(before), "exhaustion corrupted live board"); }
        check((int) get(g.ai, "chooserPolicyDepth") == 0 && get(g.ai, "chooserRun") == null && get(g.ai, "chooserBudget") == null, "research context leaked");
        final String audit = g.ai.queryChooserAudit(); check(audit.contains("\"teacher\"") && audit.contains("\"committed-choice\""), "audit absent");
        check(g.ai.computeAiMove() == original && state(g).equals(before), "audit changed policy");
        final double[] v1 = ChooserFeatures.features(g, new ChooserResearch.Board(g), 0, original);
        final double[] v2 = ChooserFeatures.relative(g, new ChooserResearch.Board(g), 0, original);
        check(v1.length == 12 && v2.length == 19, "feature schemas changed");
        for (int i = 0; i < v2.length; i++) { check(Double.isFinite(v2[i]) && Math.abs(v2[i]) <= 1, "unbounded feature"); if (i < 12) check(v1[i] == v2[i], "legacy vector changed"); }
        final Properties zero = new Properties(); zero.setProperty("chooser.experiments", "aware,setup,terminal"); zero.setProperty("candidateSlots", "1,2"); zero.setProperty("chooser.policyBudget", "0");
        final RaceGame z = game("hairpin", zero); check(z.ai.computeAiMove() == original, "zero budget changed choice");
        final Properties disabled = new Properties(); disabled.setProperty("chooser.experiments", "aware,setup,terminal");
        check(game("hairpin", disabled).ai.computeAiMove() == original, "unselected experiments leaked");
    }
    private static void protocol() throws Exception {
        final RaceGame g = game("hairpin", new Properties());
        final String query = "v3,0,10,1,0,0;18,27,0,0,0,0,0;17,29,0,0,0,0,0";
        MoveQueries.restoreBoard(g, query); final String before = state(g);
        rejects(() -> MoveQueries.restoreBoard(g, query.replace(",0,0;18", ",1,0;18")));
        check(state(g).equals(before), "bad ledger partly mutated board");
        final String answer = MoveQueries.answer(g, query.replace("v3,", "chooser3,"));
        check(answer.startsWith("chooser3;{") && answer.contains("\"turn\":10"), "V3 diagnostic incomplete");
        MoveQueries.restoreBoard(g, "v3,0,11,1,0,1;18,27,0,0,0,0,0;-100000,-100000,0,0,2,0,0");
        check(g.chooserFinishedLast() == 1, "classified ledger absent");
        MoveQueries.restoreBoard(g, "v2,0,10,1;18,27,0,0,0,0,0;17,29,0,0,0,0,0");
        check(g.chooserFinishedLast() == 0 && g.chooserFinishedFirst() == 0, "legacy inherited ledger");
    }
    private static void cacheIdentity() throws Exception {
        final RaceGame g = game("hairpin", new Properties());
        final Method key = Reachability.class.getDeclaredMethod("reachCachePath"); key.setAccessible(true);
        final Object original = key.invoke(g.reach); final Line2D line = g.finishLine;
        g.finishLine = new Line2D.Double(line.getX1() + 1, line.getY1(), line.getX2() + 1, line.getY2());
        check(!original.equals(key.invoke(g.reach)), "finish target missing from cache key");
        g.finishLine = line; final double old = (double) get(g, "finishFwdX"); set(g, "finishFwdX", old + .5);
        check(!original.equals(key.invoke(g.reach)), "finish direction missing from cache key");
        set(g, "finishFwdX", old); check(original.equals(key.invoke(g.reach)), "restored identity differs");
    }
    private static Object get(final Object o, final String name) throws Exception { final Field f = o.getClass().getDeclaredField(name); f.setAccessible(true); return f.get(o); }
    private static void set(final Object o, final String name, final Object value) throws Exception { final Field f = o.getClass().getDeclaredField(name); f.setAccessible(true); f.set(o, value); }
}
