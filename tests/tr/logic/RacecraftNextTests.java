package tr.logic;

import java.awt.Color;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.List;
import java.util.Properties;

/** Exact small fixtures for the second research batch; no campaign claims. */
public final class RacecraftNextTests {
    private RacecraftNextTests() {}
    public static void main(final String[] args) throws Exception {
        final RaceGame g = fixture();
        configuration(); diversity(g); progressive(g); model(); features(g); ledger(g);
        System.out.println("RacecraftNextTests: diversity, matched horizons, order/budget fairness, "
                + "place/time heads, relative features and V3 classification/restore OK");
    }
    private static RaceGame fixture() throws Exception {
        final Method m = SimulationBoundaryTests.class.getDeclaredMethod("straight");
        m.setAccessible(true); return (RaceGame) m.invoke(null);
    }
    private static Player car(final int n, final int x, final int y, final int vx, final int vy) {
        final Player p = new Player("P"+n, n, Color.RED, Player.Kind.AI1);
        p.setPosition(new int[]{x,y}); p.setVelocity(new int[]{vx,vy}); return p;
    }
    private static RacecraftConfig config(final String flags) {
        final Properties p = new Properties(); p.setProperty("racecraft.experiments",flags);
        return new RacecraftConfig(p);
    }
    private static void configuration() {
        check(config("diverse").opportunity && config("diverse").diverse,"diverse not independently usable");
        check(config("progressive").opportunity && config("progressive").progressive,"progressive gate");
        check(!config("").enabled(),"default activation");
        rejects(() -> config("lexicographic")); rejects(() -> config("progressive,progressive"));
        rejects(() -> new RacecraftSearch.Budget(-1));
    }
    private static void diversity(final RaceGame g) {
        g.players = new Player[]{car(1,30,10,0,0),car(2,32,10,0,0),car(3,60,10,0,0)};
        g.subgamestate=0;g.setQueryTurnCounter(0);g.racecraftQueryClassification(0,0);
        final RacecraftSearch.Board b = new RacecraftSearch.Board(g);
        final double[] scores = new double[9];for(int i=0;i<9;i++)scores[i]=i;
        boolean changed=false;
        for(final Direction champion:Direction.values()) {
            if(!b.transition(g,0,champion).legal())continue;
            final List<Direction> old=RacecraftNext.shortlist(g,b,0,champion,scores,config("opportunity"));
            final List<Direction> varied=RacecraftNext.shortlist(g,b,0,champion,scores,config("diverse"));
            check(varied.size()==old.size() && varied.get(0)==champion,"shortlist cap/baseline");
            check(varied.stream().distinct().count()==varied.size(),"duplicate shortlist");
            for(final Direction d:varied)check(b.transition(g,0,d).legal(),"illegal diverse action");
            check(varied.equals(RacecraftNext.shortlist(g,b,0,champion,scores,config("diverse"))),"nondeterministic selection");
            changed|=!varied.equals(old);
        }
        check(changed,"fixture did not replace a score-ranked alternative");
        check(b.turns==0 && b.x[0]==30 && g.players[0].getPosition()[0]==30,"diversity mutated root");
    }
    private static void progressive(final RaceGame g) {
        g.players = new Player[]{car(1,30,10,0,0),car(2,60,10,0,0)};
        final RacecraftSearch.Board b = new RacecraftSearch.Board(g);
        final List<Direction> actions=List.of(Direction.NONE,Direction.E);
        final RacecraftConfig c=config("progressive");
        final RacecraftSearch.Policy p=(board,i)->Direction.NONE;
        final RacecraftSearch.Budget five=new RacecraftSearch.Budget(5);
        final RacecraftNext.Comparison a=RacecraftNext.progressive(g,b,0,actions,c,p,five);
        check(a.values()!=null && a.rounds()==1 && five.spent==5 && five.exhausted,"lost complete first stage");
        final RacecraftNext.Comparison reverse=RacecraftNext.progressive(g,b,0,List.of(Direction.E,Direction.NONE),c,p,new RacecraftSearch.Budget(5));
        check(a.values()[0].equals(reverse.values()[1]) && a.values()[1].equals(reverse.values()[0]),"enumeration changed completed values");
        final RacecraftNext.Comparison shortRun=RacecraftNext.progressive(g,b,0,actions,c,p,new RacecraftSearch.Budget(3));
        check(shortRun.values()==null && shortRun.rounds()==0,"partial stage accepted");
        final RacecraftNext.Comparison zero=RacecraftNext.progressive(g,b,0,actions,c,p,new RacecraftSearch.Budget(0));
        check(zero.values()==null,"zero budget produced result");
        final RacecraftNext.Comparison full=RacecraftNext.progressive(g,b,0,actions,c,p,new RacecraftSearch.Budget(8));
        check(full.rounds()==2 && full.values()!=null,"second matched stage missing");
        final int[] calls={0};
        final RacecraftNext.Comparison unavailable=RacecraftNext.progressive(g,b,0,actions,c,(board,i)->++calls[0]>4?null:Direction.NONE,new RacecraftSearch.Budget(8));
        check(unavailable.rounds()==1 && unavailable.values()!=null,"later unavailable policy erased completed comparison");
        check(b.turns==0 && b.x[0]==30,"progressive mutated root");
        // Early terminal outcomes are fixed, not extended into phantom actions.
        g.players=new Player[]{car(1,171,10,2,0),car(2,40,10,0,0)};
        final RacecraftNext.Comparison terminal=RacecraftNext.progressive(g,new RacecraftSearch.Board(g),0,List.of(Direction.E,Direction.NONE),c,p,new RacecraftSearch.Budget(0));
        check(terminal.values()!=null && terminal.values()[0].terminal(),"terminal action consumed policy budget");
    }
    private static RacecraftConfig modelConfig(final double radius) {
        final Properties p=new Properties();p.setProperty("racecraft.experiments","lexicographic");
        p.setProperty("racecraft.model.version","2");p.setProperty("racecraft.model.features",RacecraftConfig.FEATURES_V2);
        p.setProperty("racecraft.model.trainingSha256","a".repeat(64));
        final String[] weights=new String[20];Arrays.fill(weights,"0");weights[0]="1";
        p.setProperty("racecraft.model.weights",String.join(",",weights));weights[0]="0";weights[1]="1";
        p.setProperty("racecraft.model.timeWeights",String.join(",",weights));p.setProperty("racecraft.model.placeRadius",Double.toString(radius));
        return new RacecraftConfig(p);
    }
    private static void model() {
        final RacecraftConfig c=modelConfig(0);
        final double[] first=new double[19],second=new double[19];first[1]=1;second[0]=1;
        check(RacecraftNext.modelBetter(c,first,second,8),"fast worse place beat slow better place");
        check(!RacecraftNext.modelBetter(c,second,first,8),"time compensated for place loss");
        second[0]=0;check(RacecraftNext.modelBetter(c,second,first,8),"equal-place time tie missing");
        check(!RacecraftNext.modelBetter(modelConfig(.6),second,first,8),"uncertain place treated as tie");
        check(RacecraftNext.predictedPlace(c,first,1)==1,"solo rank");
    }
    private static void features(final RaceGame g) {
        g.players=new Player[]{car(1,30,10,0,0),car(2,34,10,-1,0)};
        final RacecraftSearch.Board b=new RacecraftSearch.Board(g);
        final double[] f=RacecraftNext.features(g,b,0,Direction.NONE);
        check(f.length==19 && Arrays.equals(Arrays.copyOf(f,12),RacecraftSearch.features(g,b,0,Direction.NONE)),"v1 features changed");
        for(final double x:f)check(Double.isFinite(x) && Math.abs(x)<=1,"unbounded v2 feature");
        check(f[12]>0 && f[18]==1/7.0,"relative closing/field context missing");
        check(b.x[0]==30 && b.turns==0,"feature trial mutated state");
    }
    private static void ledger(final RaceGame g) {
        g.players=new Player[]{car(1,30,10,0,0),car(2,34,10,0,0),car(3,60,10,0,0)};
        final String cars=";30,10,0,0,0,0,0;-100000,-100000,0,0,3,0,0;60,10,0,0,0,0,0";
        MoveQueries.restoreBoard(g,"v3,0,10,1,0,1"+cars);
        check(new RacecraftSearch.Board(g).classificationKnown && g.racecraftFinishedLast()==1,"V3 ledger ignored");
        rejects(()->MoveQueries.restoreBoard(g,"v3,0,20,1,1,0"+cars));
        check(g.turnCount()==10 && g.racecraftFinishedLast()==1,"invalid request partially installed");
        MoveQueries.restoreBoard(g,"v2,0,10,1"+cars);
        check(!new RacecraftSearch.Board(g).classificationKnown && g.racecraftFinishedLast()==0,"V3 ledger leaked into V2");
    }
    private static void check(final boolean value,final String message) {if(!value)throw new AssertionError(message);}
    private static void rejects(final Runnable r) {try{r.run();}catch(final IllegalArgumentException e){return;}throw new AssertionError("expected rejection");}
}
