package tr.logic;

import java.awt.Color;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Constructed mechanism witnesses, not performance claims. */
public final class RacecraftAdaptiveTests {
    private RacecraftAdaptiveTests() {}
    public static void main(final String[] args) throws Exception {
        adaptiveQuantifiers();
        adaptivePaceIntegration();
        rememberedPlan();
        committedMemoryAndReplay();
        recoveryScheduler();
        actualRecovery();
        horizonScheduling();
        actualEndpoint();
        isolation();
        System.out.println("RacecraftAdaptiveTests: adaptive AND/OR proof, committed/serialized follow-ups, recovery, common horizons and isolation OK");
    }

    private static RaceGame straight(final String flags) throws Exception {
        final Method m = RacecraftNextTests.class.getDeclaredMethod("straight", String.class, String.class);
        m.setAccessible(true);
        return (RaceGame) m.invoke(null, flags, "1,2,3");
    }
    private static Player car(final int id, final int x, final int y, final int vx, final int vy) {
        final Player p = new Player("P" + id, id, Color.BLUE, Player.Kind.AI1);
        p.setPosition(new int[]{x,y}); p.setVelocity(new int[]{vx,vy}); p.leaveGrid(); return p;
    }
    private static void prepare(final RaceGame g) throws Exception {
        final Player p = g.players[g.subgamestate];
        final Method m = RaceAi.class.getDeclaredMethod("prepareDecisionFrame", int[].class,int[].class,int.class);
        m.setAccessible(true); m.invoke(g.ai,p.getPosition(),p.getVelocity(),p.getNumber());
    }
    private static RaceGame adaptiveGame(final String flags) throws Exception {
        final RaceGame g = straight(flags);
        g.players = new Player[]{car(1,15,10,4,0),car(2,25,10,0,0)};
        g.subgamestate=0; prepare(g); return g;
    }

    private static void adaptiveQuantifiers() throws Exception {
        final RaceGame g=adaptiveGame("adaptive-escape");
        final String before=RacecraftReplay.snapshot(g);
        final RaceAiPrivateLane.ProofSession fixed = new RaceAiPrivateLane(g).begin(1,5,20000);
        final int distance=g.reach.turnsToFinish(20,10,5,0);
        check(!fixed.certifiesExact(20,10,5,0,distance,4,2),"fixture has a universally private route");
        final AdaptiveEscape.Session adaptive=new AdaptiveEscape.Session(g,1,20000);
        check(adaptive.certifies(20,10,5,0,2,2),"missed response-dependent escape certificate");
        final Player me=car(1,20,10,5,0);
        check(verifyReplies(g,me,g.players[1],2,2),"independent physical enumeration refutes certificate");
        check(!new AdaptiveEscape.Session(g,1,20000).certifies(20,10,5,0,1,9),
                "adaptive proof silently weakened the required escape count");
        final AdaptiveEscape.Session bounded=new AdaptiveEscape.Session(g,1,1);
        check(!bounded.certifies(20,10,5,0,2,2) && bounded.examined()<=1,"budget exhaustion became permission");
        check(before.equals(RacecraftReplay.snapshot(g)),"adaptive proof mutated live state");
        g.players=new Player[]{g.players[0],g.players[1],car(3,40,10,0,0)};
        check(!new AdaptiveEscape.Session(g,1,20000).certifies(20,10,5,0,2,2),"third car omitted from a proof");
    }

    /** Detached-player enumerator deliberately does not call the proof implementation. */
    private static boolean verifyReplies(final RaceGame g, final Player me, final Player rival,
            final int depth, final int required) {
        for(final Direction reply:Direction.values()) {
            final RaceGame.MoveResult r=physical(g,rival,me,reply);
            if(!r.legal())continue;
            if(r.finishes())return false;
            final Player after=advance(rival,reply,r);
            int count=0;
            final int current=g.reach.turnsToFinish(me.getPosition()[0],me.getPosition()[1],
                    me.getVelocity()[0],me.getVelocity()[1]);
            boolean finished=false;
            for(final Direction answer:Direction.values()) {
                if(RaceGame.aiVelocityOutOfRange(me.getVelocity()[0]+answer.dx,me.getVelocity()[1]+answer.dy))continue;
                final RaceGame.MoveResult a=physical(g,me,after,answer);
                if(!a.legal())continue;
                if(a.finishes()){finished=true;break;}
                final Player next=advance(me,answer,a);
                final int remaining=g.reach.turnsToFinish(next.getPosition()[0],next.getPosition()[1],
                        next.getVelocity()[0],next.getVelocity()[1]);
                if(remaining>=current)continue;
                if(depth>1&&!verifyReplies(g,next,after,depth-1,required))continue;
                if(++count>=required)break;
            }
            if(!finished&&count<required)return false;
        }
        return true;
    }
    private static RaceGame.MoveResult physical(final RaceGame g,final Player p,final Player other,final Direction d){
        final int[] x=p.getPosition(),v=p.getVelocity(),b=other.getPosition();
        final int nx=x[0]+v[0]+d.dx,ny=x[1]+v[1]+d.dy;
        return g.evaluateMove(p.getLap(),p.getNextGate(),!p.hasLeftGrid(),x[0],x[1],nx,ny,nx==b[0]&&ny==b[1]);
    }
    private static Player advance(final Player p,final Direction d,final RaceGame.MoveResult result){
        final int[] x=p.getPosition(),v=p.getVelocity();
        final Player next=car(p.getNumber(),x[0]+v[0]+d.dx,x[1]+v[1]+d.dy,v[0]+d.dx,v[1]+d.dy);
        final int[] ledger=p.lapState();ledger[0]=result.lapAfter();ledger[1]=result.gateAfter();
        next.restoreLapState(ledger);return next;
    }

    private static Direction pace(final RaceGame g)throws Exception{
        final double[] scores=new double[9],traps=new double[9]; final int[] times=new int[9];
        Arrays.fill(scores,Double.MAX_VALUE);Arrays.fill(times,Integer.MAX_VALUE);
        scores[Direction.W.ordinal()]=10; scores[Direction.E.ordinal()]=9;traps[Direction.E.ordinal()]=2;
        times[Direction.W.ordinal()]=g.reach.turnsToFinish(18,10,3,0);
        times[Direction.E.ordinal()]=g.reach.turnsToFinish(20,10,5,0);
        check(times[Direction.E.ordinal()]<times[Direction.W.ordinal()],"pace fixture is not faster");
        final Method m=RaceAi.class.getDeclaredMethod("privatePaceOverride",int[].class,int[].class,int.class,
                Direction.class,double[].class,double[].class,int[].class);m.setAccessible(true);
        return (Direction)m.invoke(g.ai,g.players[0].getPosition(),g.players[0].getVelocity(),1,Direction.W,scores,traps,times);
    }
    private static void adaptivePaceIntegration()throws Exception{
        check(pace(adaptiveGame(""))==Direction.W,"control gained an adaptive route");
        check(pace(adaptiveGame("adaptive-escape"))==Direction.E,"adaptive fallback did not reach the pace decision");
    }

    private static RacecraftOutcome live(final int ahead,final int time){
        return new RacecraftOutcome(RacecraftOutcome.Status.RUNNING,ahead,1,time);
    }
    private static TacticalComparison.Evaluation e(final RacecraftOutcome value){
        return new TacticalComparison.Evaluation(value,false);
    }
    private static void rememberedPlan(){
        final String key="a".repeat(64);
        final OpeningPlans.Selection result=OpeningPlans.choose(Direction.W,new Direction[]{Direction.W,Direction.N},4,false,
                (first,second)->new OpeningPlans.Trial(live(0,first==Direction.N&&second==Direction.SE?1:20),List.of(Direction.SE),key));
        check(result.move()==Direction.N&&result.followup()==Direction.SE&&key.equals(result.expectedKey()),
                "winning setup discarded its follow-up or expected board");
        final Map<Direction,TacticalComparison.Evaluation> values=new LinkedHashMap<>();
        values.put(Direction.W,e(live(0,10))); values.put(Direction.N,e(live(0,9)));
        final TacticalComparison.Selection retained=TacticalComparison.choose(Direction.N,values,List.of(Direction.W,Direction.N,Direction.SE),
                result.followup(),12,0,0,(d,h)->e(live(0,1)));
        check(retained.move()==Direction.SE&&retained.inheritedOffered()&&retained.trials()==1,
                "inherited action outside the shortlist was not evaluated");
        final TacticalComparison.Selection rejected=TacticalComparison.choose(Direction.N,values,List.of(Direction.W,Direction.N,Direction.SE),
                result.followup(),12,0,0,(d,h)->e(live(1,1)));
        check(rejected.move()==Direction.N,"inherited action was forced despite a worse place");
    }

    private static void committedMemoryAndReplay()throws Exception{
        final RaceGame g=straight("opening,followup");
        g.players=new Player[]{car(1,20,10,0,0),car(2,30,10,0,0)};g.subgamestate=0;
        final String key=FollowupPlans.key(g);
        g.followups.put(0,new FollowupPlans.Entry(Direction.E,key));
        final String before=RacecraftReplay.snapshot(g);
        check(before.startsWith("rc4,")&&g.followups.find(g)!=null,"pending action not captured");
        check(RacecraftReplay.parse(g,before).encode().equals(before),"pending-action snapshot does not round trip");
        final Direction first=g.ai.computeAiMove(),second=g.ai.computeAiMove();
        check(first==second&&before.equals(RacecraftReplay.snapshot(g)),"a query consumed or installed policy memory");
        g.setQueryTurnCounter(1);check(g.followups.find(g)==null,"clock mismatch reused a stale plan");g.setQueryTurnCounter(0);
        final int[] position=g.players[1].getPosition();g.players[1].setPosition(new int[]{31,10});
        check(g.followups.find(g)==null,"rival board mismatch reused a stale plan");g.players[1].setPosition(position);
        final int[] ledger=g.players[0].lapState();ledger[6]=0;g.players[0].restoreLapState(ledger);
        check(g.followups.find(g)==null,"grid entitlement omitted from plan identity");g.players[0].leaveGrid();
        final FollowupPlans copy=g.followups.copy();g.followups.put(0,null);
        check(copy.find(g)!=null,"policy-memory snapshot aliases live memory");g.followups=copy;
        final String request="cf4,300,"+first+"|"+RacecraftReplay.snapshot(g);
        final String answer=RacecraftReplay.answer(g,request);
        check(answer.contains(RacecraftReplay.sha(request))&&before.equals(RacecraftReplay.snapshot(g)),
                "counterfactual replay omitted policy memory or leaked it into the real game");
        set(g.ai,"pendingFirst",first);set(g.ai,"pendingFollowup",new FollowupPlans.Entry(Direction.SE,"b".repeat(64)));
        set(g.ai,"decisionRootKey",FollowupPlans.key(g));
        g.ai.commitResearchPlan(first);
        check(g.followups.encode(2).contains("SE~"+"b".repeat(64)),"committed setup did not install follow-up");
        set(g.ai,"pendingFirst",Direction.N);set(g.ai,"pendingFollowup",new FollowupPlans.Entry(Direction.E,"c".repeat(64)));
        set(g.ai,"decisionRootKey",FollowupPlans.key(g));g.ai.commitResearchPlan(Direction.W);
        check(g.followups.encode(2).equals("-"),"downstream override retained the wrong setup");
    }

    private static void recoveryScheduler(){
        final Map<Direction,TacticalComparison.Evaluation> values=new LinkedHashMap<>();
        values.put(Direction.NW,e(new RacecraftOutcome(RacecraftOutcome.Status.CRASHED,2,3,0)));
        values.put(Direction.N,e(new RacecraftOutcome(RacecraftOutcome.Status.CRASHED,2,4,0)));
        final TacticalComparison.Selection result=TacticalComparison.choose(Direction.NW,values,
                List.of(Direction.NW,Direction.N,Direction.SE),null,12,9,0,(d,h)->{
                    check(d==Direction.SE&&h==12,"recovery changed its policy horizon");
                    return e(new RacecraftOutcome(RacecraftOutcome.Status.CRASHED,1,5,0));
                });
        check(result.move()==Direction.SE&&result.recoveryExpanded(),"omitted better-ranked failure was not rescued");
        values.put(Direction.N,e(RacecraftOutcome.unknown()));
        check(TacticalComparison.choose(Direction.NW,values,List.of(Direction.SE),null,12,9,0,(d,h)->{
            throw new AssertionError("unknown was treated as a known crash");
        }).move()==Direction.NW,"unknown trigger changed decision");
    }
    private static Direction oneChoice(final RaceGame g)throws Exception{
        prepare(g);final Player me=g.players[0];final double[] scores=new double[9];Arrays.fill(scores,Double.MAX_VALUE);
        scores[Direction.NW.ordinal()]=0;
        final Method m=RaceAi.class.getDeclaredMethod("jointChooser",int[].class,int[].class,int.class,
                Direction.class,double[].class,double.class);m.setAccessible(true);
        return (Direction)m.invoke(g.ai,me.getPosition(),me.getVelocity(),1,Direction.NW,scores,0.0);
    }
    private static TacticalComparison.Evaluation forecast(final RaceGame g,final Direction d,final int rounds)throws Exception{
        final Player p=g.players[g.subgamestate];
        final Method m=RaceAi.class.getDeclaredMethod("tacticalForecast",int[].class,int[].class,int.class,Direction.class,int.class);
        m.setAccessible(true);return (TacticalComparison.Evaluation)m.invoke(g.ai,p.getPosition(),p.getVelocity(),p.getNumber(),d,rounds);
    }
    private static void actualRecovery()throws Exception{
        final RaceGame g=straight("recovery");
        g.players=new Player[]{car(1,20,17,0,-8),car(2,35,11,0,-7),car(3,60,10,0,0)};g.subgamestate=0;
        final Direction selected=oneChoice(g);
        check(selected!=Direction.NW,"recovery never evaluated actions excluded from a one-move shortlist");
        check(forecast(g,selected,12).outcome().betterThan(forecast(g,Direction.NW,12).outcome(),true),
                "recovery did not improve the comparable forecast");
    }
    private static void horizonScheduling(){
        final Map<Direction,TacticalComparison.Evaluation> values=new LinkedHashMap<>();
        values.put(Direction.W,new TacticalComparison.Evaluation(live(0,1),true));
        values.put(Direction.E,e(live(0,2)));
        final List<Integer> horizons=new ArrayList<>();
        final TacticalComparison.Selection result=TacticalComparison.choose(Direction.W,values,List.of(Direction.W,Direction.E),
                null,12,0,2,(d,h)->{horizons.add(h);return e(live(d==Direction.W?1:0,3));});
        check(result.move()==Direction.E&&horizons.equals(List.of(14,14))&&result.extensionRounds()==2,
                "endpoint extension compared unequal horizons or stopped before the tactical event");
        check(TacticalComparison.choose(Direction.W,values,List.of(Direction.W,Direction.E),null,12,0,2,
                (d,h)->e(RacecraftOutcome.unknown())).move()==Direction.W,"unknown extension supplied a better verdict");
    }
    private static void actualEndpoint()throws Exception{
        final RaceGame g=straight("tactical-extension");
        g.players=new Player[]{car(1,71,10,1,0),car(2,60,10,0,0)};g.subgamestate=1;prepare(g);
        final TacticalComparison.Evaluation shortValue=forecast(g,Direction.E,1);
        final TacticalComparison.Evaluation longValue=forecast(g,Direction.E,3);
        check(shortValue.imminentFinish()&&shortValue.outcome().ahead()==0,"imminent preceding-slot finisher was not detected");
        check(longValue.outcome().ahead()==1&&longValue.outcome().resolved(),"extension failed to classify the rival ahead");
    }
    private static void isolation()throws Exception{
        final String all="opening,followup,adaptive-escape,recovery,tactical-extension";
        final RaceGame candidate=straight(all),control=straight("");
        for(final RaceGame g:new RaceGame[]{candidate,control}){
            g.players=new Player[]{car(1,20,10,0,0),car(2,60,10,0,0)};g.subgamestate=0;
        }
        check(candidate.ai.computeAiMove()==control.ai.computeAiMove(),"new experiment bypassed the 20-cell solo rule");
        candidate.setQueryTurnCounter(4*candidate.players.length);
        check(!candidate.racecraftNext.enabled(candidate,1,RacecraftNext.Feature.FOLLOWUP),"inherited action escaped the opening phase");
        final RaceGame standalone=straight("followup");
        check(!standalone.racecraftNext.enabled(standalone,1,RacecraftNext.Feature.FOLLOWUP),"follow-up implicitly enabled opening search");
    }
    private static void set(final Object o,final String field,final Object value)throws Exception{
        final Field f=o.getClass().getDeclaredField(field);f.setAccessible(true);f.set(o,value);
    }
    private static void check(final boolean condition,final String message){if(!condition)throw new AssertionError(message);}
}
