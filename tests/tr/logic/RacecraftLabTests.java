package tr.logic;

import java.awt.Color;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.Properties;

/** Research modes must not redefine the referee or silently activate controls. */
public final class RacecraftLabTests {
    private RacecraftLabTests() {}

    public static void main(final String[] args) throws Exception {
        configuration();
        final RaceGame straight = fixture(SimulationBoundaryTests.class, "straight");
        interaction(straight);
        classification(straight);
        forecasts(straight);
        blockade();
        progress();
        featuresAndGating(straight);
        System.out.println("RacecraftLabTests: flags, physical slot graph, place/time ordering, budgets, "
                + "terminal transitions, feature schema and control isolation OK");
    }

    private static void configuration() {
        check(!new RacecraftConfig(new Properties()).enabled(), "experiments enabled by default");
        for (final String bad : new String[]{"all", "interaction,", "learned", "interaction,interaction"}) {
            final Properties p = props(bad);
            rejects(() -> new RacecraftConfig(p));
        }
        final Properties p = props("refresh,opportunity,encounter");
        final RacecraftConfig c = new RacecraftConfig(p);
        check(c.interaction && c.refresh && c.opportunity && c.encounter && !c.learned, "independent flags lost");
        p.setProperty("racecraft.policyBudget", "-1");
        rejects(() -> new RacecraftConfig(p));
        final Properties model = model();
        check(new RacecraftConfig(model).score(new double[12]) == 0, "linear ranker not deterministic");
        model.setProperty("racecraft.model.weights", "NaN,0,0,0,0,0,0,0,0,0,0,0");
        rejects(() -> new RacecraftConfig(model));
        model.setProperty("racecraft.model.weights", "0");
        rejects(() -> new RacecraftConfig(model));
    }

    private static void interaction(final RaceGame g) {
        g.players = new Player[]{car(1,20,10,0,0), car(2,20,18,0,0), car(3,44,10,-12,0)};
        RacecraftSearch.Board b = new RacecraftSearch.Board(g);
        final String before = fingerprint(g);
        RacecraftTraffic.Graph graph = RacecraftTraffic.graph(g, b, 0);
        final boolean[] selected = new boolean[3];
        graph.select(0, 1, 10, selected);
        check(selected[2] && !selected[1], "far interacting rival lost to near noninteracting car");
        check(graph.complete && graph.transitions <= 2048, "graph not bounded");
        check(fingerprint(g).equals(before) && b.live() == 3, "attention graph mutated/removed a car");
        g.players = new Player[]{car(1,20,10,0,0),car(2,26,10,0,0),car(3,32,10,0,0),car(4,20,18,0,0)};
        b = new RacecraftSearch.Board(g);
        graph = RacecraftTraffic.graph(g, b, 0);
        check(graph.edge[0][2] == 0 && graph.indirect(0,2) > 0, "indirect influencer not identified");
        final boolean[] two = new boolean[4];
        graph.select(0,2,10,two);
        check(two[1] && two[2] && !two[3], "attention cap not spent on direct and indirect competitors");
        graph.select(0,0,10,two);
        check(!two[0] && !two[1] && !two[2] && !two[3], "zero cap ignored");
        // Refresh builds from the NEW projected positions, not the starting graph.
        b.x[2] = 100;
        check(RacecraftTraffic.graph(g,b,1).indirect(0,2) == 0, "refresh retained stale membership");
        check(Arrays.deepEquals(graph.edge, RacecraftTraffic.graph(g, new RacecraftSearch.Board(g),0).edge),
                "graph is nondeterministic");
    }

    private static void classification(final RaceGame g) throws Exception {
        g.players = new Player[]{car(1,10,10,0,0),car(2,30,2,0,-4),car(3,45,2,0,-4)};
        g.subgamestate=0; g.setQueryTurnCounter(0);
        final RacecraftSearch.Board b = new RacecraftSearch.Board(g);
        b.step(g,0,Direction.NONE); b.step(g,1,Direction.NONE); b.step(g,2,Direction.NONE);
        check(b.over() && b.place[0]==1 && b.place[1]==3 && b.place[2]==2, "survivor classification wrong");
        check(b.turns==3 && b.ownMoves[0]==1, "phantom survivor move");
        rejects(() -> b.step(g,0,Direction.NONE));
        // A single-car race must really cross the finish.
        g.players = new Player[]{car(1,171,10,2,0)};
        final RacecraftSearch.Board solo=new RacecraftSearch.Board(g);
        check(!solo.over(), "solo auto-classified");
        solo.step(g,0,Direction.E);
        check(solo.place[0]==1 && solo.over(), "solo finish lost");
        g.players = new Player[]{car(1,171,10,2,0),car(2,30,10,0,0)};
        final Method gates=SimulationBoundaryTests.class.getDeclaredMethod("gates",RaceGame.class);
        gates.setAccessible(true); gates.invoke(null,g);
        g.setQueryTurnCounter(1501);
        final RacecraftSearch.Board timed=new RacecraftSearch.Board(g);
        timed.step(g,0,Direction.E);
        check(timed.place[0]==2 && timed.place[1]==1, "finish overrode timeout");
        g.lapGates=null; g.setQueryTurnCounter(0);
        // Query-only sentinel markers don't contain a finish-versus-crash ledger.
        // Such a board cannot supply a trusted absolute-place prediction.
        g.players[1].setFinishedPlace(77);
        check(!new RacecraftSearch.Board(g).classificationKnown, "sentinel invented a place ledger");
    }

    private static void forecasts(final RaceGame g) {
        g.players = new Player[]{car(1,10,10,0,0),car(2,30,2,0,-4),car(3,45,2,0,-4)};
        final RacecraftSearch.Board root = new RacecraftSearch.Board(g);
        final RacecraftConfig c = new RacecraftConfig(props("opportunity,encounter"));
        final RacecraftSearch.Budget zero = new RacecraftSearch.Budget(0);
        RacecraftSearch.Forecast f=RacecraftSearch.forecast(g,root,0,Direction.NONE,c,(b,i)->Direction.NONE,zero);
        check(f.exhausted() && f.value()==null, "budget exhaustion became success/death");
        final RacecraftSearch.Budget two = new RacecraftSearch.Budget(2);
        f=RacecraftSearch.forecast(g,root,0,Direction.NONE,c,(b,i)->Direction.NONE,two);
        check(!f.exhausted() && f.value().place()==1 && f.value().ownTime()==1 && two.spent==2,
                "complete classified forecast incorrect");
        check(root.turns==0 && root.live()==3, "trial mutated root");
        check(new RacecraftSearch.Value(1,500,false).compareTo(new RacecraftSearch.Value(2,1,false))<0,
                "own time outranked place");
        check(new RacecraftSearch.Value(1,20,false).compareTo(new RacecraftSearch.Value(1,21,false))<0,
                "time tie-break wrong");
        // Stationary, interacting cars cannot resolve the shared landing contest.
        g.players=new Player[]{car(1,30,10,0,0),car(2,32,10,0,0),car(3,60,10,0,0)};
        final RacecraftSearch.Budget budget=new RacecraftSearch.Budget(100);
        f=RacecraftSearch.forecast(g,new RacecraftSearch.Board(g),0,Direction.NONE,c,(b,i)->Direction.NONE,budget);
        check(f.extensions()==1 && budget.spent<=100, "selective encounter did not extend/bound work");
        g.players[1].setPosition(new int[]{90,10});
        f=RacecraftSearch.forecast(g,new RacecraftSearch.Board(g),0,Direction.NONE,c,(b,i)->Direction.NONE,
                new RacecraftSearch.Budget(100));
        check(f.extensions()==0, "quiet position received a broad horizon extension");
    }

    private static void blockade() throws Exception {
        final RaceGame g=fixture(RaceAiTacticsTests.class,"hairpin");
        g.players=new Player[]{car(1,16,27,1,-2),car(2,15,22,2,2)};
        final RacecraftSearch.Forecast f=RacecraftSearch.forecast(g,new RacecraftSearch.Board(g),0,Direction.NONE,
                new RacecraftConfig(props("opportunity")),(b,i)->Direction.NONE,new RacecraftSearch.Budget(6));
        check(f.value()!=null && f.value().place()==2 && f.board().place[1]==1,
                "legal map-dead winning blockade erased");
    }

    private static void progress() throws Exception {
        final RaceGame g=fixture(SimulationFollowupTests.class,"circle");
        g.totalLaps=2;
        g.players=new Player[]{car(1,50,8,1,0),car(2,87,48,0,0)};
        g.players[0].setNextGate(0); g.players[1].setNextGate(1);
        RacecraftSearch.Board b=new RacecraftSearch.Board(g);
        b.step(g,0,Direction.E);
        check(b.alive[0] && b.lap[0]==1 && b.gate[0]==1, "non-final crossing vanished");
        g.players[0].incrementLap();
        b=new RacecraftSearch.Board(g); b.step(g,0,Direction.E);
        check(b.place[0]==1 && b.place[1]==2, "actual final crossing not terminal");
    }

    private static void featuresAndGating(final RaceGame g) throws Exception {
        g.players=new Player[]{car(1,30,10,2,0),car(2,33,12,1,0),car(3,80,10,1,0)};
        g.subgamestate=0;
        final String before=fingerprint(g);
        final RacecraftSearch.Board b=new RacecraftSearch.Board(g);
        final double[] f=RacecraftSearch.features(g,b,0,Direction.E);
        check(f.length==12 && Arrays.stream(f).allMatch(v->Double.isFinite(v) && Math.abs(v)<=1), "bad feature shape");
        check(RacecraftSearch.featureProtocol(g).split(";",-1)[2].split("\\|",-1).length==9,
                "feature protocol missing a direction");
        check(fingerprint(g).equals(before), "feature query changed live state");
        final Direction baseline=g.ai.computeAiMove();
        final Field config=RaceGame.class.getDeclaredField("racecraft"); config.setAccessible(true);
        config.set(g,new RacecraftConfig(props("interaction,refresh,opportunity,encounter")));
        check(g.ai.computeAiMove()==baseline, "flags without a candidate slot changed champion");
        final Field slots=RaceGame.class.getDeclaredField("candidateSlots"); slots.setAccessible(true);
        ((boolean[])slots.get(g))[2]=true;
        check(g.ai.computeAiMove()==baseline, "other candidate slot leaked into control decision");
        ((boolean[])slots.get(g))[1]=true;
        final Direction experimental=g.ai.computeAiMove();
        check(experimental!=null && fingerprint(g).equals(before), "enabled real decision mutated board");
        check(!((boolean)get(g.ai,"racecraftRoot")) && (int)get(g.ai,"decisionDepth")==0
                && (int)get(g.ai,"simDepth")==0, "experiment scope leaked after a real decision");
        ((boolean[])slots.get(g))[1]=false;
        check(g.ai.computeAiMove()==baseline, "control changed after an experimental query");
    }

    private static Properties props(final String flags) {
        final Properties p=new Properties(); p.setProperty("racecraft.experiments",flags); return p;
    }
    private static Properties model() {
        final Properties p=props("learned"); p.setProperty("racecraft.model.version","1");
        p.setProperty("racecraft.model.features",RacecraftConfig.FEATURES);
        p.setProperty("racecraft.model.trainingSha256","a".repeat(64));
        p.setProperty("racecraft.model.weights","0,0,0,0,0,0,0,0,0,0,0,0"); return p;
    }
    private static Player car(final int n, final int x, final int y, final int vx, final int vy) {
        final Player p=new Player("P"+n,n,Color.BLUE,Player.Kind.AI1);
        p.setPosition(new int[]{x,y}); p.setVelocity(new int[]{vx,vy}); return p;
    }
    private static RaceGame fixture(final Class<?> type,final String name) throws Exception {
        final Method m=type.getDeclaredMethod(name); m.setAccessible(true); return (RaceGame)m.invoke(null);
    }
    private static Object get(final Object o,final String name) throws Exception {
        final Field f=o.getClass().getDeclaredField(name); f.setAccessible(true); return f.get(o);
    }
    private static String fingerprint(final RaceGame g) {
        final StringBuilder s=new StringBuilder().append(g.turnCount()).append(':').append(g.subgamestate);
        for(final Player p:g.players) s.append(Arrays.toString(p.getPosition())).append(Arrays.toString(p.getVelocity()))
                .append(Arrays.toString(p.lapState())).append(p.getFinishedPlace()).append(p.getHistory());
        return s.toString();
    }
    private static void rejects(final Runnable r) {
        try {r.run();} catch(final IllegalArgumentException expected) {return;}
        throw new AssertionError("Invalid operation/config accepted");
    }
    private static void check(final boolean ok,final String message) {if(!ok) throw new AssertionError(message);}
}
