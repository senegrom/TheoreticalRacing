package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Rectangle2D;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

/** Constructed mechanisms and failure boundaries, not fleet-performance claims. */
public final class CreativeRacecraftTests {
    private CreativeRacecraftTests() {}
    static final String FLAGS = "pace-feints,ambush,traffic-judo,selfish-search,two-judge";
    public static void main(final String[] args) throws Exception {
        pulses(); inverseAndMandatory(); judo(); incentives(); twoJudges(); forecasts(); breeder(); controls();
        System.out.println("CreativeRacecraftTests: pulses, complete-layer ambushes, inverse paths, released gaps, selfish terminal vectors, matched judges, reactive forecasts and breeder tails OK");
    }
    private static RaceGame straight(final String flags) throws Exception {
        final Method m = RacecraftNextTests.class.getDeclaredMethod("straight", String.class, String.class);
        m.setAccessible(true); return (RaceGame) m.invoke(null, flags, "1,2,3,4");
    }
    private static Player car(final int id, final int x, final int y, final int vx, final int vy) {
        final Player p = new Player("P" + id, id, Color.BLUE, Player.Kind.AI1);
        p.setPosition(new int[]{x, y}); p.setVelocity(new int[]{vx, vy}); p.leaveGrid(); return p;
    }
    private static void set(final Object object, final String name, final Object value) throws Exception {
        final Field f = object.getClass().getDeclaredField(name); f.setAccessible(true); f.set(object, value);
    }
    private static void check(final boolean ok, final String message) { if (!ok) throw new AssertionError(message); }
    private static void pulses() throws Exception {
        final List<Direction> coast = List.of(Direction.NONE, Direction.NONE, Direction.NONE, Direction.NONE);
        for (final Direction axis : Direction.values()) if (axis != Direction.NONE) {
            final List<Direction> pulse = CreativePaths.pulse(coast, axis.dx, axis.dy);
            int vx = 4, vy = 2, x = 0, y = 0;
            for (final Direction d : pulse) { vx += d.dx; vy += d.dy; x += vx; y += vy; }
            check(pulse.size() == 4 && x == 16 && y == 8 && vx == 4 && vy == 2, "pulse changed endpoint/time");
        }
        check(CreativePaths.pulse(List.of(Direction.E, Direction.E, Direction.E, Direction.E), 1, 0).isEmpty(),
                "pulse exceeded the physical acceleration domain");
        final RaceGame g = straight("pace-feints");
        g.players[0] = car(1, 20, 10, 4, 0);
        final StrategyState root = StrategyState.capture(g);
        final String before = RacecraftReplay.snapshot(g);
        final List<List<Direction>> paths = CreativePaths.feints(g, root, coast, new StrategyState.Budget(1000));
        check(!paths.isEmpty(), "no endpoint-preserving pulse in an open straight");
        final CreativePaths.Own original = CreativePaths.follow(g, CreativePaths.Own.of(root.board.cars[0]), coast, new StrategyState.Budget(100));
        for (final List<Direction> path : paths)
            check(original.equals(CreativePaths.follow(g, CreativePaths.Own.of(root.board.cars[0]), path, new StrategyState.Budget(100))),
                    "feint lost velocity/progress/grid equivalence");
        check(CreativePaths.feints(g, root, coast, new StrategyState.Budget(0)).isEmpty(), "empty budget produced a feint");
        check(before.equals(RacecraftReplay.snapshot(g)), "feint generator mutated live state");
    }
    private static void inverseAndMandatory() throws Exception {
        final RaceGame g = straight("ambush");
        final CreativePaths.Own initial = new CreativePaths.Own(20, 10, 4, 0, 0, 1, true, false);
        final List<List<Direction>> paths = AmbushPlans.intercept(g, initial, new AmbushPlans.Target(31, 10, 2), new StrategyState.Budget(20000));
        check(!paths.isEmpty(), "inverse search missed the two-acceleration interception");
        for (final List<Direction> path : paths) {
            final CreativePaths.Own end = CreativePaths.follow(g, initial, path, new StrategyState.Budget(100));
            check(path.size() == 2 && end != null && end.x() == 31 && end.y() == 10, "inverse kinematics fabricated a route");
            check((long) CreativePaths.distance(g, end) + path.size() <= CreativePaths.distance(g, initial), "ambush sacrificed solo pace");
        }
        g.trackA = new Area(new Rectangle2D.Double(0, 9.75, 73, 0.5)); g.startZoneA = new Area();
        set(g, "legalRaster", null); set(g, "subRaster", null); g.clearPointContainmentCacheForCurrentThread();
        final CreativePaths.Own narrow = new CreativePaths.Own(9, 10, 0, 0, 0, 1, true, false);
        final List<AmbushPlans.Target> cells = AmbushPlans.mandatory(g, narrow, 3, new StrategyState.Budget(1000));
        check(cells.contains(new AmbushPlans.Target(12, 10, 2)), "missed complete-layer compulsory exit");
        check(AmbushPlans.mandatory(g, narrow, 3, new StrategyState.Budget(10)).isEmpty(), "partial layer was labelled compulsory");
    }
    private static void judo() throws Exception {
        final RaceGame g = straight("traffic-judo");
        g.players = new Player[]{car(1,20,10,0,0), car(2,19,10,0,0), car(3,28,12,0,0)};
        final StrategyState root = StrategyState.capture(g);
        final StrategyState blocked = root.after(g, Direction.NONE), released = root.after(g, Direction.S);
        check(CreativeForecast.target(root) == 1, "target ignored real move order");
        check(TrafficJudo.newlyAvailable(g, blocked, released, Direction.E), "vacating did not unlock the physical gap");
        check(!TrafficJudo.newlyAvailable(g, released, blocked, Direction.E), "blocking was labelled gap release");
        check(TrafficJudo.propose(g, root, Direction.NONE, 0).isEmpty(), "zero-budget judo searched");
        final String before = RacecraftReplay.snapshot(g);
        final CreativeForecast.Reply reply = CreativeForecast.firstReply(g, released);
        check(reply != null && reply.slot() == 1 && before.equals(RacecraftReplay.snapshot(g)), "rival-response query changed the real board");
    }
    private static void incentives() throws Exception {
        final SelfishSearch.Vector blocks = new SelfishSearch.Vector(new int[]{2,3,1}, new int[]{2,1,1});
        final SelfishSearch.Vector races = new SelfishSearch.Vector(new int[]{1,2,3}, new int[]{3,2,2});
        check(SelfishSearch.prefer(1, races, blocks), "rival sacrificed its place to hurt us");
        check(!SelfishSearch.prefer(2, races, blocks), "search optimized the focal car at another actor's turn");
        final SelfishSearch.Vector tie = new SelfishSearch.Vector(new int[]{3,2,1}, new int[]{1,2,1});
        check(!SelfishSearch.prefer(1, tie, races), "equal opponent outcomes were broken for the focal car");
        final RaceGame g = straight("selfish-search");
        g.players = new Player[]{car(1,70,5,3,0), car(2,70,10,3,0), car(3,70,15,3,0)};
        final StrategyState root = StrategyState.capture(g);
        final SelfishSearch.Result result = SelfishSearch.search(g, root, 3, 2000);
        final Direction best = result.best(0);
        check(best != null && result.roots().get(best).places()[0] == 1, "terminal selfish search missed immediate first");
        check(SelfishSearch.search(g, root, 3, 0).roots().isEmpty(), "unknown search manufactured an incentive outcome");
        check(result.nodes() <= 2000 && root.board.encode().equals(RacecraftReplay.snapshot(g)), "selfish search leaked budget/state");
    }
    private static CreativeForecast.Result value(final int place, final int time) {
        return new CreativeForecast.Result(new RacecraftOutcome(RacecraftOutcome.Status.FINISHED, place, time, 0),
                List.of(), List.of(), null, null, 0);
    }
    private static void twoJudges() {
        final List<Direction> old = List.of(Direction.E), extra = List.of(Direction.N);
        final List<List<Direction>> calls = new ArrayList<>();
        final CreativeTactics.Judgement rejected = CreativeTactics.check(old, extra, path -> {
            calls.add(path); return path.equals(old) ? value(0,10) : value(1,1);
        });
        check(!rejected.accepted() && calls.equals(List.of(old, extra)), "checker reused a generator value or favoured speed over place");
        check(CreativeTactics.check(old, extra, path -> path.equals(old) ? value(1,1) : value(0,10)).accepted(), "checker rejected a better-place result");
        final CreativeForecast.Result unknown = new CreativeForecast.Result(RacecraftOutcome.unknown(), List.of(), List.of(), null, null, 0);
        check(!CreativeTactics.check(old, extra, path -> path.equals(old) ? unknown : value(0,1)).accepted(), "unknown incumbent became checking evidence");
        check(CreativeTactics.better(new RacecraftOutcome(RacecraftOutcome.Status.CRASHED,1,3,0),
                new RacecraftOutcome(RacecraftOutcome.Status.FINISHED,2,1,0)), "creative comparisons ignored classified place");
        final List<CreativeTactics.Proposal> offered = CreativeTactics.roundRobin(List.of(
                List.of(new CreativeTactics.Proposal("a",extra),new CreativeTactics.Proposal("a",List.of(Direction.S))),
                List.of(new CreativeTactics.Proposal("b",List.of(Direction.W)))), 2, old);
        check(offered.size() == 2 && offered.get(1).source().equals("b"), "first generator monopolized the forecast budget");
    }
    private static void forecasts() throws Exception {
        final RaceGame g = straight(FLAGS);
        g.players = new Player[]{car(1,20,8,3,0),car(2,26,10,3,0),car(3,30,12,2,0)};
        final RacecraftReplay.Board root = RacecraftReplay.capture(g);
        final CreativeForecast.Result cheap = CreativeForecast.run(g, root, List.of(Direction.E), 4, CreativeForecast.Model.SCORER, 1);
        final CreativeForecast.Result checked = CreativeForecast.run(g, root, List.of(Direction.E), 4, CreativeForecast.Model.FULL_FIRST, 1);
        check(cheap.fullCalls() == 0 && checked.fullCalls() > 0 && checked.fullCalls() <= 2, "first-response model exceeded its bound");
        check(checked.outcome().known() && checked.nextKey() != null && checked.ownPrefix().size() == 4, "bounded model failed an ordinary straight");
        check(root.encode().equals(RacecraftReplay.snapshot(g)), "strong model changed live state or pending memory");
        final CreativeForecast.Result repeat = CreativeForecast.run(g, root, List.of(Direction.E), 4, CreativeForecast.Model.FULL_FIRST, 1);
        check(repeat.outcome().equals(checked.outcome()) && repeat.nextKey().equals(checked.nextKey()), "checking depends on previous query history");
    }
    private static void breeder() throws Exception {
        final RaceGame g = straight("");
        g.players = new Player[]{car(1,68,5,3,0),car(2,66,10,3,0),car(3,64,15,3,0)};
        final RacecraftReplay.Board root = RacecraftReplay.capture(g);
        final TacticBreeder.Trial control = TacticBreeder.run(g, root, List.of(), 100);
        final RacecraftReplay.Tail ordinary = RacecraftReplay.run(g, root, 0, null, 100, false);
        check(control.tail().complete() && control.tail().trace().equals(ordinary.trace())
                && control.tail().finalState().equals(ordinary.finalState()), "breeder control differs from real-policy race tail");
        final TacticBreeder.Trial mutation = TacticBreeder.run(g, root, List.of(Direction.W,Direction.E), 100);
        check(mutation.validPrefix() && mutation.tail().complete() && mutation.forcedExecuted() == 2, "legal multi-action mutation was not executed");
        check(root.encode().equals(RacecraftReplay.snapshot(g)), "breeder query mutated live state");
        final String request = "breed1,100,-|" + root.encode();
        final String answer = TacticBreeder.answer(g, request);
        check(answer.contains(RacecraftReplay.sha(request)) && answer.contains("\"complete\":true"), "breeder response lacks full request identity");
        check(!TacticBreeder.run(g, root, List.of(), 1).tail().complete(), "truncated breeding tail became a label");
    }
    private static void controls() throws Exception {
        final RaceGame g = straight(FLAGS);
        final Properties props = new Properties(); props.setProperty("racecraftNext", FLAGS); props.setProperty("racecraftCreativeNodes", "0");
        final RacecraftNext zero = new RacecraftNext(props);
        for (final RacecraftNext.Feature f : RacecraftNext.Feature.values()) if (RacecraftNext.creative(f))
            check(!zero.enabled(g,1,f), "zero creative budget enabled " + f);
        check(!zero.creativeEnabled(g,1), "zero-budget driver active");
        final String before = RacecraftReplay.snapshot(g);
        final Direction a = g.ai.computeAiMove(), b = g.ai.computeAiMove();
        check(a == b && before.equals(RacecraftReplay.snapshot(g)), "hint/query installed a creative plan");
    }
}
