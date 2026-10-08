package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Path2D;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

/** Independent referee parity plus positive/negative strategy mechanism witnesses.
 * These are contract tests, not a fleet-performance claim. */
@SuppressWarnings("try")
public final class StrategyResearchTests {
    private StrategyResearchTests() {}
    public static void main(final String[] args) throws Exception {
        int failures = 0;
        for (final String name : new String[]{"stateParity", "suffixes", "responses", "threeCars", "forced", "blockades", "portfolio", "gating"}) {
            try {
                StrategyResearchTests.class.getDeclaredMethod(name).invoke(null);
                System.out.println("Strategy witness " + name + ": OK");
            } catch (final java.lang.reflect.InvocationTargetException error) {
                failures++;error.getCause().printStackTrace();
            }
        }
        check(failures == 0, "strategy contract failures: " + failures);
    }
    private static RaceGame board(final String flags) throws Exception {
        final Method fixture = RacecraftNextTests.class.getDeclaredMethod("straight", String.class, String.class);
        fixture.setAccessible(true); return (RaceGame) fixture.invoke(null, flags, "1,2,3");
    }
    private static Player car(final int n, final int x, final int y, final int vx, final int vy) {
        final Player p = new Player("P" + n, n, Color.BLUE, Player.Kind.AI1);
        p.setPosition(new int[]{x,y}); p.setVelocity(new int[]{vx,vy}); p.leaveGrid(); return p;
    }
    private static void prepare(final RaceGame g) throws Exception {
        final Method m = RaceAi.class.getDeclaredMethod("prepareDecisionFrame", int[].class, int[].class, int.class);
        m.setAccessible(true); final Player p = g.players[g.subgamestate];
        m.invoke(g.ai, p.getPosition(), p.getVelocity(), p.getNumber());
    }
    private static void set(final Object target, final String name, final Object value) throws Exception {
        final Field f = target.getClass().getDeclaredField(name); f.setAccessible(true); f.set(target,value);
    }
    private static void check(final boolean test, final String message) { if (!test) throw new AssertionError(message); }

    private static void stateParity() throws Exception {
        final RaceGame g = board("");
        for (final Player[] cars : new Player[][]{
                {car(1,20,8,1,0),car(2,22,10,0,0),car(3,24,12,0,0)},
                {car(1,71,10,2,0),car(2,30,2,0,-12),car(3,40,10,0,0)},
                {car(1,20,10,0,0),car(2,20,11,0,0),car(3,25,12,0,0)}}) {
            g.players = cars;
            for (int self = 0; self < 3; self++) {
                g.subgamestate = self;
                final StrategyState root = StrategyState.capture(g);
                for (final Direction d : Direction.values()) {
                    final StrategyState expected = root.after(g,d);
                    try (RacecraftReplay.Scope ignored = new RacecraftReplay.Scope(g,root.board)) {
                        RacecraftReplay.advance(g,d);
                        if (!RacecraftReplay.classifyLast(g)) {
                            int next=self; do { next=(next+1)%3; } while(g.players[next].isFinished());
                            g.subgamestate=next;
                        }
                        check(expected != null && expected.key().equals(FollowupPlans.key(g)),"detached transition diverged: "+self+"/"+d);
                    }
                }
            }
        }
    }
    private static void suffixes() throws Exception {
        final RaceGame g = board("suffix-manoeuvres");
        g.players = new Player[]{car(1,20,10,0,0),car(2,25,15,0,0),car(3,26,5,0,0)}; prepare(g);
        final TrafficManoeuvres.Occupancy empty = new TrafficManoeuvres.Occupancy(new int[3],new int[3],new boolean[3],0);
        final List<TrafficManoeuvres.Occupancy> schedule=List.of(empty,empty,empty,empty);
        final TrafficManoeuvres.Search result=TrafficManoeuvres.propose(g,schedule,Direction.E,4,192);
        check(result.expanded()<=192 && result.proposals().size()<=3,"suffix graph budget exceeded");
        final List<List<Direction>> same=result.proposals().stream().filter(p->p.get(0)==Direction.E).toList();
        check(same.size()==2 && !same.get(0).equals(same.get(1)),"nominal-first alternative histories discarded");
        final String before=RacecraftReplay.snapshot(g);
        for(final List<Direction> path:same) check(TrafficManoeuvres.forecast(g,RacecraftReplay.capture(g),path,12).outcome().known(),"suffix not evaluated reactively");
        check(before.equals(RacecraftReplay.snapshot(g)),"suffix evaluation mutated live state");
        // Installing a better suffix must not require changing the first action.
        final FollowupPlans.Entry tail=FollowupPlans.Entry.traffic(same.get(0).subList(1,4),"a".repeat(64));
        set(g.ai,"pendingFirst",Direction.E);set(g.ai,"pendingFollowup",tail);set(g.ai,"decisionRootKey",FollowupPlans.key(g));
        g.ai.commitResearchPlan(Direction.E);
        check(g.followups.encode(3).contains("M_"),"unchanged first action lost its improved suffix");
        check(SuffixManoeuvres.propose(g,schedule,Direction.E,4,0).proposals().isEmpty(),"zero suffix budget active");
    }
    private static void responses() throws Exception {
        final RaceGame g=board("response-strategy");
        g.players=new Player[]{car(1,15,10,4,0),car(2,25,10,0,0)};prepare(g);
        final StrategyState root=StrategyState.capture(g);
        final StrategyState.Budget budget=new StrategyState.Budget(40000);
        final ResponseStrategies.Tree proof=ResponseStrategies.certify(g,root,Direction.E,2,2,budget);
        check(proof!=null && !proof.empty(),"adaptive witness has no executable strategy");
        check(proof.size()<=ResponseStrategies.MAX_STATES && budget.used()<=40000,"response bounds exceeded");
        check(ResponseStrategies.Tree.parse(proof.encode()).encode().equals(proof.encode()),"response table not canonical");
        final StrategyState first=root.after(g,Direction.E);
        for(final Direction reply:Direction.values()) {
            final StrategyState state=first.after(g,reply);
            if(state.place(0)!=0)continue;
            final ResponseStrategies.Node node=proof.at(state.key());
            check(node!=null && Integer.bitCount(node.mask())>=2,"a physical reply lacks the required answers");
            for(final Direction d:Direction.values())if(node.permits(d)) {
                check(state.evaluate(g,d).legal(),"recorded response is not legal");
                check(ResponseStrategies.continuation(g,state,d,node,new StrategyState.Budget(40000))!=null,"recorded response fails independent reconstruction");
            }
        }
        final StrategyState observed=first.after(g,Direction.NONE);
        try(RacecraftReplay.Scope ignored=new RacecraftReplay.Scope(g,observed.board)) {
            g.followups.put(0,FollowupPlans.Entry.response(proof,root.key()));
            final String before=RacecraftReplay.snapshot(g);
            check(before.startsWith("rc6,") && RacecraftReplay.parse(g,before).encode().equals(before),"response memory not in replay protocol");
            final Direction a=g.ai.computeAiMove(),b=g.ai.computeAiMove();
            check(a==b && before.equals(RacecraftReplay.snapshot(g)),"query consumed response memory");
            final ResponseStrategies.Node node=proof.at(observed.key());
            check(node.permits(a) || ResponseStrategies.continuation(g,observed,a,node,new StrategyState.Budget(40000))!=null,"production abandoned its response obligation");
            final String request="cf4,300,"+a+"|"+before;
            final String answer=RacecraftReplay.answer(g,request);
            check(answer.contains(RacecraftReplay.sha(request)) && before.equals(RacecraftReplay.snapshot(g)),
                    "response-memory replay lost request binding or mutated live state");
            g.ai.computeAiMove();
            g.ai.commitResearchPlan(a);
            check(!g.followups.encode(2).equals("-"),"committed response lost the remaining strategy");
        }
        check(ResponseStrategies.certify(g,root,Direction.E,2,2,new StrategyState.Budget(0))==null,"exhaustion created response permission");
        boolean invalid=false;try{ResponseStrategies.Tree.parse(proof.encode()+"!"+proof.encode().split("!")[0]);}catch(final IllegalArgumentException expected){invalid=true;}
        check(invalid,"duplicate response keys accepted");
    }
    private static void threeCars() throws Exception {
        final RaceGame g=board("place-certificates");
        g.players=new Player[]{car(1,70,10,0,0),car(2,71,5,2,0),car(3,60,15,0,0)};prepare(g);
        final String before=RacecraftReplay.snapshot(g);
        final PlaceCertificates.Result result=PlaceCertificates.search(g,3,12,40000,false);
        check(result.bounds().containsKey(Direction.E) && result.bounds().get(Direction.E).place()==2,"missed guaranteed second-place witness");
        check(before.equals(RacecraftReplay.snapshot(g)),"place search mutated state");
        final PlaceCertificates.Result tiny=PlaceCertificates.search(g,3,12,0,false);
        check(tiny.bounds().isEmpty(),"unknown search acquired a finishing place");
        // Absolute rank includes racers already classified at the front and back.
        final Player finished=car(1,0,0,0,0);finished.setFinishedPlace(1);
        final Player crashed=car(5,0,0,0,0);crashed.setFinishedPlace(5);
        g.players=new Player[]{finished,car(2,70,10,0,0),car(3,71,5,2,0),car(4,60,15,0,0),crashed};
        g.subgamestate=1;g.researchClassification(1,1);prepare(g);
        final PlaceCertificates.Result absolute=PlaceCertificates.search(g,3,12,40000,false);
        check(absolute.bounds().get(Direction.E).place()==3,"three-car solver reset existing classifications");
    }
    private static void forced() throws Exception {
        final RaceGame g=board("forced-sequence");
        final Path2D.Double strip=new Path2D.Double();
        strip.moveTo(1,.3);strip.lineTo(37,18.3);strip.lineTo(37,18.7);strip.lineTo(1,.7);strip.closePath();
        g.trackA=new Area(strip);g.startZoneA=new Area();
        set(g,"legalRaster",null);set(g,"subRaster",null);g.clearPointContainmentCacheForCurrentThread();
        g.finishLine=new Line2D.Double(22.5,0,22.5,20);
        g.players=new Player[]{car(1,10,5,2,1),car(2,6,3,2,1)};prepare(g);
        final StrategyState root=StrategyState.capture(g);
        check(root.legal(g,false).equals(List.of(Direction.NONE)),"thin oblique lane is not physically forced: "+root.legal(g,false));
        final PlaceCertificates.Result ordinary=PlaceCertificates.search(g,1,16,12000,false);
        final PlaceCertificates.Result extended=PlaceCertificates.search(g,1,16,12000,true);
        check(ordinary.bounds().isEmpty(),"ordinary horizon unexpectedly resolves forced lane");
        check(extended.bounds().containsKey(Direction.NONE) && extended.bounds().get(Direction.NONE).place()==1
                && extended.bounds().get(Direction.NONE).ownMoves()==7 && extended.forcedNodes()>0,"forced extension missed a seven-own-move win");
        check(PlaceCertificates.search(g,1,4,12000,true).bounds().isEmpty(),"physical move cap ignored");
    }
    private static void blockades() throws Exception {
        final RaceGame g=board("ordered-blockade");
        final int[] cells={12,10,13,10};
        g.players=new Player[]{car(1,10,10,0,0),car(2,11,10,2,0),car(3,12,10,2,0)};prepare(g);
        check(RaceAi.hasDistinctCover(new int[]{1,3},2),"matching precursor absent");
        check(OrderedBlockade.check(g,Direction.NONE,cells,2,new StrategyState.Budget(12000))==OrderedBlockade.Verdict.IMPOSSIBLE,
                "accepted mutually inconsistent blocker schedule");
        g.players=new Player[]{car(1,10,10,0,0),car(2,12,10,2,0),car(3,11,10,2,0)};prepare(g);
        check(OrderedBlockade.check(g,Direction.NONE,cells,2,new StrategyState.Budget(12000))==OrderedBlockade.Verdict.POSSIBLE,
                "changing move order did not permit the real blockade");
        check(OrderedBlockade.check(g,Direction.NONE,cells,2,new StrategyState.Budget(0))==OrderedBlockade.Verdict.UNKNOWN,
                "exhaustion cleared seal veto");
    }
    private static void portfolio() throws Exception {
        final RaceGame g=board("continuation-policies");
        g.players=new Player[]{car(1,20,10,1,0),car(2,25,10,0,0),car(3,27,15,0,0)};prepare(g);
        final String before=RacecraftReplay.snapshot(g);
        for(final Direction first:List.of(Direction.NE,Direction.SE))for(final ContinuationPortfolio.Profile p:ContinuationPortfolio.Profile.values()){
            final List<Direction> path=ContinuationPortfolio.prefix(g,RacecraftReplay.capture(g),first,p);
            check(!path.isEmpty()&&path.get(0)==first&&path.size()<=4,"unexecutable own-policy proposal");
            TrafficManoeuvres.forecast(g,RacecraftReplay.capture(g),path,12);
        }
        final ContinuationPortfolio.Choice choice=ContinuationPortfolio.choose(g,Direction.NE,Direction.SE,null);
        check(choice.forecasts()>0 && choice.forecasts()<=6,"portfolio comparison budget invalid");
        check(before.equals(RacecraftReplay.snapshot(g)),"portfolio altered real opponent state");
        check(ContinuationPortfolio.choose(g,Direction.E,Direction.E,null).forecasts()==0,"agreement activated portfolio");
    }
    private static void gating() throws Exception {
        final java.util.Properties p=new java.util.Properties();
        p.setProperty("racecraftNext","suffix-manoeuvres,response-strategy,place-certificates,forced-sequence,continuation-policies,ordered-blockade");
        p.setProperty("racecraftStrategyNodes","0");
        final RacecraftNext options=new RacecraftNext(p);
        final RaceGame g=board("");
        for(final RacecraftNext.Feature feature:RacecraftNext.Feature.values())
            check(!options.enabled(g,1,feature),"zero work budget did not disable "+feature);
    }
}
