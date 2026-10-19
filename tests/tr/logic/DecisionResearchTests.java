package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Rectangle2D;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import tr.gui.RaceUI;

/** Constructed witnesses establish contracts, not fleet performance. */
@SuppressWarnings("try")
public final class DecisionResearchTests {
    private DecisionResearchTests() {}
    public static void main(final String[] args) throws Exception {
        configuration(); responseCycle(); snapshots(); plansAndUndo(); models(); conditional(); tails();
        System.out.println("DecisionResearchTests: complete response cycles, exact grid/plan snapshots, commit/Undo, "
                + "shadow/OOD models, contingent execution and bounded referee tails OK");
    }
    private static Properties props(final String flags) {
        final Properties p = new Properties();
        p.setProperty("racecraftFeatures", flags); p.setProperty("candidateSlots", "1,2");
        p.setProperty("nPlayers", "2"); p.setProperty("laps", "1");
        return p;
    }
    private static void configuration() throws Exception {
        rejects(() -> new DecisionResearch(props("invented")), "unknown flag accepted");
        final Properties p = props("response-cycle"); p.setProperty("racecraftTrials", "0");
        final RaceGame zero = straight(p); check(!zero.research.enabled(zero, 1), "zero budget active");
        final Properties geometry = props("response-cycle");
        final String originalProfile = new DecisionResearch(geometry).policyId;
        geometry.setProperty("lastTrackLeft", "1,2;3,4"); geometry.setProperty("gameX", "99");
        check(new DecisionResearch(geometry).policyId.equals(originalProfile), "geometry prevented cross-track learning");
        p.remove("candidateSlots"); p.setProperty("racecraftTrials", "24");
        final RaceGame noSlots = straight(p); check(!noSlots.research.enabled(noSlots, 1), "no-slot candidate active");
    }
    private static String forecastTrace(final RaceGame g) throws Exception {
        g.subgamestate = 1;
        prepare(g.ai, g.players[1]); g.ai.simTrace = true;
        final PrintStream old = System.err; final ByteArrayOutputStream output = new ByteArrayOutputStream();
        try (PrintStream stream = new PrintStream(output, true, StandardCharsets.UTF_8)) {
            System.setErr(stream);
            check(g.ai.researchForecast(Direction.E, 0) >= 0, "fixture forecast died");
        } finally { System.setErr(old); g.ai.simTrace = false; }
        return output.toString(StandardCharsets.UTF_8);
    }
    private static void responseCycle() throws Exception {
        final RaceGame base = straight(props("")), next = straight(props("response-cycle"));
        final String a = forecastTrace(base), b = forecastTrace(next);
        final long ar = a.lines().filter(s -> s.startsWith("SIMTRACE r=") && s.contains(" i=0 ")).count();
        final long br = b.lines().filter(s -> s.startsWith("SIMTRACE r=") && s.contains(" i=0 ")).count();
        final long am = a.lines().filter(s -> s.startsWith("SIMTRACE r=") && s.contains(" i=1 ")).count();
        final long bm = b.lines().filter(s -> s.startsWith("SIMTRACE r=") && s.contains(" i=1 ")).count();
        check(ar == 11 && br == 12, "final preceding-rival response missing: " + ar + "/" + br);
        check(am == 11 && bm == 11, "response cycle added an own action: " + am + "/" + bm);
        check(b.contains("SIMTRACE r=12 i=0"), "partial response round missing");
        check(!b.contains("SIMTRACE r=12 i=1"), "mover acted twice at boundary");
    }
    private static void snapshots() throws Exception {
        final RaceGame g = straight(props("contingent"));
        // Identical on-grid pose before CP1, two different legal histories.
        g.startZoneA = new Area(new Rectangle2D.Double(0, 0, 40, 20));
        final String before = ResearchBoard.capture(g).encode();
        g.players[0].leaveGrid();
        final ResearchBoard left = ResearchBoard.capture(g);
        check(!before.equals(left.encode()), "snapshot inferred away leftGrid");
        check(ResearchBoard.parse(g, left.encode()).cars[0][11] == 1, "explicit grid entitlement lost");
        final Player[] original = g.players;
        final String key = left.physicalKey();
        try (ResearchBoard.Scope scope = new ResearchBoard.Scope(g, ResearchBoard.parse(g, before))) {
            check(!g.players[0].hasLeftGrid(), "scope kept wrong grid entitlement");
            g.setQueryTurnCounter(20); g.research.plans = DecisionResearch.Plans.empty();
        }
        check(g.players == original && ResearchBoard.capture(g).physicalKey().equals(key), "scope leaked state");
        rejects(() -> ResearchBoard.parse(g, left.encode().replace("rp3,0,0,", "rp3,0,-1,")), "negative clock accepted");
        rejects(() -> ResearchBoard.parse(g, left.encode().replace(left.context, "0".repeat(64))), "wrong world accepted");
        rejects(() -> ResearchBoard.parse(g, left.encode().replaceFirst(";10,8,", ";99999,8,")), "out-of-board state accepted");
        final String plans = "0:" + key + ":5";
        check(DecisionResearch.Plans.parse(plans, 2).encode().equals(plans), "plan encoding failed");
        rejects(() -> DecisionResearch.Plans.parse(plans + "|" + plans, 2), "duplicate plan accepted");
        check(ResearchBoard.capture(g).physicalKey().equals(key), "invalid input mutated game");
    }
    private static void plansAndUndo() throws Exception {
        final RaceGame g = straight(props("contingent"));
        final ResearchBoard root = ResearchBoard.capture(g);
        final Map<String, Direction> table = Map.of(root.physicalKey(), Direction.E);
        g.research.plans = g.research.plans.with(0, table);
        check(g.research.response(g) == Direction.E && g.research.response(g) == Direction.E, "hint consumed plan");
        check(g.ai.computeAiMove() == Direction.E, "matching response was not executed by policy");
        final String encoded = ResearchBoard.capture(g).encode();
        check(ResearchBoard.parse(g, encoded).plans.encode().equals(g.research.plans.encode()), "rp3 lost plans");
        final Class<?> type = Class.forName("tr.logic.RaceGame$MoveSnapshot");
        final Constructor<?> constructor = type.getDeclaredConstructor(RaceGame.class); constructor.setAccessible(true);
        final Object undo = constructor.newInstance(g);
        g.research.commit(g, g.ai, Direction.E);
        check(g.research.response(g) == null, "commit failed to consume response");
        final Method restore = type.getDeclaredMethod("restore", RaceGame.class); restore.setAccessible(true); restore.invoke(undo, g);
        check(g.research.response(g) == Direction.E, "Undo lost response");
        final DecisionResearch.Plans savedPlans = g.research.plans;
        g.research.plans = savedPlans.with(1, Map.of("a".repeat(64), Direction.E));
        check(g.research.response(g) == null, "opponent policy memory did not invalidate plan");
        g.research.plans = savedPlans;
        g.setQueryTurnCounter(1); check(g.research.response(g) == null, "clock-stale response accepted"); g.setQueryTurnCounter(0);
        g.ai.researchProposal = new DecisionResearch.Proposal(root.physicalKey(), Direction.E, table);
        g.research.commit(g, g.ai, Direction.W); check(g.research.plans.seats().get(0).isEmpty(), "different actual action installed proposal");
        g.research.commit(g, g.ai, Direction.E); check(g.research.response(g) == Direction.E, "matching proposal not committed");
        // A stored manoeuvre cannot violate the literal solo rule.
        g.players[1].setPosition(new int[]{100, 14});
        final Direction solo = g.ai.computeAiMove();
        Direction different = Direction.NONE; if (different == solo) different = Direction.S;
        g.research.plans = g.research.plans.with(0, Map.of(ResearchBoard.capture(g).physicalKey(), different));
        check(g.ai.computeAiMove() == solo, "contingent response overrode solo rule");
    }
    private static String vector(final double value) {
        final String[] a = new String[DecisionResearch.FEATURES]; Arrays.fill(a, Double.toString(value)); return String.join(",", a);
    }
    private static Properties model(final String policy) {
        final Properties p = new Properties(); p.setProperty("schema", "paired-ridge-1");
        p.setProperty("engine", DecisionResearch.engineId()); p.setProperty("policy", policy);
        for (final String key : List.of("mean", "place", "time")) p.setProperty(key, vector(0));
        p.setProperty("scale", vector(1)); p.setProperty("low", vector(-1000)); p.setProperty("high", vector(1000));
        final String[] w = vector(0).split(","); w[16] = "-1"; p.setProperty("place", String.join(",", w)); return p;
    }
    private static void models() throws Exception {
        for (final boolean shadow : new boolean[]{false, true}) {
            final Properties p = props(shadow ? "paired-shadow" : "paired-value");
            final Properties m = model(straight(p).research.policyId);
            for (final String key : m.stringPropertyNames()) p.setProperty("racecraftModel." + key, m.getProperty(key));
            final RaceGame g = straight(p);
            final long[] values = new long[9]; Arrays.fill(values, -1); values[4] = 10; values[5] = 10;
            final String root = ResearchBoard.capture(g).physicalKey();
            final DecisionResearch.Choice choice = g.research.choose(g, g.ai, Direction.NONE,
                    new Direction[]{Direction.NONE, Direction.E}, values, Direction.NONE);
            check(choice.action() == (shadow ? Direction.NONE : Direction.E), "shadow/application contract failed");
            check(g.research.modelChanges == 1, "model did not record disagreement");
            check(root.equals(ResearchBoard.capture(g).physicalKey()), "feature extraction leaked game state");
            final double[] x = new double[18]; x[0] = 2000; check(g.research.model.predict(x) == null, "OOD model prediction accepted");
            x[0] = Double.NaN; check(g.research.model.predict(x) == null, "NaN feature accepted");
            m.setProperty("engine", "0".repeat(64)); check(PairedValueModel.fromProperties(m, g.research.policyId) == null, "stale model accepted");
            m.setProperty("scale", vector(0)); rejects(() -> PairedValueModel.fromProperties(m, g.research.policyId), "zero scale accepted");
        }
    }
    private static void conditional() throws Exception {
        final ContingentPlans.Forecast a = new ContingentPlans.Forecast(true, 0, 20, null, null);
        final ContingentPlans.Forecast b = new ContingentPlans.Forecast(true, 1, 1, null, null);
        final ContingentPlans.Forecast u = new ContingentPlans.Forecast(false, 0, 0, null, null);
        check(ContingentPlans.better(a, b), "conditional comparison is not rank-first");
        check(!ContingentPlans.improvesBothWorlds(new ContingentPlans.Forecast[]{a, b}, new ContingentPlans.Forecast[]{b, a}),
                "one-world regression accepted");
        check(!ContingentPlans.improvesBothWorlds(new ContingentPlans.Forecast[]{a, u}, new ContingentPlans.Forecast[]{b, b}),
                "unknown world accepted");
        final RaceGame g = straight(props("contingent"));
        final ResearchBoard root = ResearchBoard.capture(g);
        // Injected policy refuses the planned second action. The forecast must
        // reject, not silently assume that action while executing another one.
        final ContingentPlans.Forecast ignored = ContingentPlans.run(g, root, Direction.NONE, Direction.E, 1, 0,
                (game, ai, strong) -> Direction.NONE);
        check(!ignored.known(), "unexecuted second action pretended successful");
        check(root.physicalKey().equals(ResearchBoard.capture(g).physicalKey()), "conditional forecast leaked state");
        check(ContingentPlans.choose(g, root, Direction.NONE, List.of(Direction.NONE, Direction.E), 3).trials() == 0,
                "incomplete two-world budget admitted");
        // A deliberately weak reacting policy provides a positive, independently
        // constructed witness. The proposal must survive REAL commit and the
        // intervening rival turn and be executed by the actual policy hook.
        final ContingentPlans.Result proposal = ContingentPlans.choose(g, root, Direction.NONE,
                List.of(Direction.NONE, Direction.E), 12, (game, ai, strong) -> {
                    final Direction stored = game.research.response(game);
                    return stored == null ? Direction.NONE : stored;
                });
        check(proposal.proposal() != null && proposal.trials() <= 12, "no bounded contingent witness found");
        g.ai.researchProposal = proposal.proposal();
        g.research.commit(g, g.ai, proposal.proposal().action());
        ResearchBoard.advance(g, proposal.proposal().action(), new String[2], new int[2]); ResearchBoard.next(g);
        ResearchBoard.advance(g, Direction.NONE, new String[2], new int[2]); ResearchBoard.next(g);
        final Direction stored = g.research.response(g);
        check(stored != null && g.ai.computeAiMove() == stored, "accepted proposal was not actually executed");
    }
    private static void tails() throws Exception {
        final RaceGame g = straight(props("")); final ResearchBoard initial = ResearchBoard.capture(g);
        final String limited = ResearchQueries.answer(g, "tail3|1|5|" + initial.encode());
        check(limited.contains("\"complete\":false"), "budget exhaustion labelled a result");
        check(initial.physicalKey().equals(ResearchBoard.capture(g).physicalKey()), "tail leaked state");
        g.players[0].setPosition(new int[]{170, 8}); g.players[0].setVelocity(new int[]{3, 0});
        final String request = "tail3|5|4|" + ResearchBoard.capture(g).encode();
        final String result = ResearchQueries.answer(g, request);
        check(result.contains("\"complete\":true") && result.contains("\"places\":[1, 2]"), "finish/classification precedence wrong");
        check(result.contains("\"FINISH\",\"SURVIVOR\""), "survivor mislabelled as a finisher");
        check(result.contains(ResearchBoard.sha256(request)), "tail omitted request binding");
    }
    private static RaceGame straight(final Properties props) throws Exception {
        final RaceGame g = new RaceGame(props); g.gameCols = 180; g.gameRows = 20;
        g.track = new Track(); g.track.addLeft(0, 1); g.track.addLeft(173, 1);
        g.track.addRight(0, 19); g.track.addRight(173, 19);
        g.trackA = new Area(new Rectangle2D.Double(0, 1, 173, 18)); g.startZoneA = new Area();
        g.finishLine = new Line2D.Double(172.5, 1, 172.5, 19); set(g, "finishFwdX", 1.0);
        set(g, "rui", new RaceUI(g.gameRows, g.gameCols));
        g.players = new Player[]{car(1, 10, 8), car(2, 16, 14)};
        g.reach.computeDistMap(); g.reach.computeReachability(); return g;
    }
    private static Player car(final int number, final int x, final int y) {
        final Player p = new Player("P" + number, number, Color.BLUE, Player.Kind.AI1);
        p.setPosition(new int[]{x, y}); p.setVelocity(new int[]{0, 0}); p.setNextGate(1); return p;
    }
    private static void prepare(final RaceAi ai, final Player p) throws Exception {
        final Method m = RaceAi.class.getDeclaredMethod("prepareDecisionFrame", int[].class, int[].class, int.class);
        m.setAccessible(true); m.invoke(ai, p.getPosition(), p.getVelocity(), p.getNumber());
    }
    private static void set(final Object o, final String key, final Object value) throws Exception {
        final Field f = o.getClass().getDeclaredField(key); f.setAccessible(true); f.set(o, value);
    }
    interface Checked { void run() throws Exception; }
    private static void rejects(final Checked r, final String text) throws Exception {
        try { r.run(); } catch (final IllegalArgumentException expected) { return; } throw new AssertionError(text);
    }
    private static void check(final boolean condition, final String text) { if (!condition) throw new AssertionError(text); }
}
