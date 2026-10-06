package tr.logic;

import java.awt.Color;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.List;

/** Mechanism witnesses, not a fleet-performance screen. */
public final class TrafficRacecraftTests {
    private TrafficRacecraftTests() {}
    public static void main(final String[] args) throws Exception {
        int failures = 0;
        for (final String test : new String[]{"stagedOrdering", "denial", "shortTransitions", "endpoints", "checkpointSubset", "manoeuvres", "memory"}) {
            try {
                TrafficRacecraftTests.class.getDeclaredMethod(test).invoke(null);
                System.out.println("Traffic witness " + test + ": OK");
            } catch (final java.lang.reflect.InvocationTargetException error) {
                failures++; error.getCause().printStackTrace();
            }
        }
        check(failures == 0, "traffic behavioural failures: " + failures);
        System.out.println("TrafficRacecraftTests: denial, ghost removal, own-decision cutoffs, checkpoint subset, bounded reactive manoeuvres and rc5 memory OK");
    }
    private static RaceGame straight(final String flags) throws Exception {
        final Method m=RacecraftNextTests.class.getDeclaredMethod("straight",String.class,String.class);
        m.setAccessible(true); return (RaceGame)m.invoke(null,flags,"1,2,3");
    }
    private static Player car(final int n,final int x,final int y,final int vx,final int vy) {
        final Player p=new Player("P"+n,n,Color.BLUE,Player.Kind.AI1);
        p.setPosition(new int[]{x,y});p.setVelocity(new int[]{vx,vy});p.leaveGrid();return p;
    }
    private static void prepare(final RaceGame g) throws Exception {
        final Player p=g.players[g.subgamestate];
        final Method m=RaceAi.class.getDeclaredMethod("prepareDecisionFrame",int[].class,int[].class,int.class);
        m.setAccessible(true);m.invoke(g.ai,p.getPosition(),p.getVelocity(),p.getNumber());
    }
    private static Object get(final Object o,final String name)throws Exception {
        final Field f=o.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(o);
    }
    private static void set(final Object o,final String name,final Object value)throws Exception {
        final Field f=o.getClass().getDeclaredField(name);f.setAccessible(true);f.set(o,value);
    }
    private static void stagedOrdering() {
        check(TrafficOpportunities.stagedBetter(10,0.25,1_000_001,0.10),"heuristic outranked winning place");
        check(!TrafficOpportunities.stagedBetter(1_000_001,0.01,10,0.25),"speed bought worse place");
        check(TrafficOpportunities.stagedBetter(3,0.3,5,0.1),"same-place time not primary");
        check(!TrafficOpportunities.stagedBetter(Integer.MAX_VALUE,0,5,1),"unknown result won staged selection");
    }
    private static void denial() throws Exception {
        final RaceGame g=straight("denial");
        g.players=new Player[]{car(1,50,18,4,0),car(2,51,17,3,2),car(3,10,5,0,0)};
        prepare(g);final String before=RacecraftReplay.snapshot(g);
        final Direction d=TrafficOpportunities.nominate(g,Direction.NE,12);
        check(d!=null,"pace-neutral denial witness not nominated");
        check(TrafficOpportunities.ownDistance(g,0,d)==TrafficOpportunities.ownDistance(g,0,Direction.NE),"denial paid own map time");
        check(TrafficOpportunities.replyCost(g,0,1,d)>TrafficOpportunities.replyCost(g,0,1,Direction.NE),"nominee did not remove cheapest reply");
        check(before.equals(RacecraftReplay.snapshot(g)),"nomination mutated board");
        g.subgamestate=2;check(TrafficOpportunities.nextLive(g,2)==0,"next-live selection did not wrap");
        g.players[0].setFinishedPlace(3);check(TrafficOpportunities.nextLive(g,2)==1,"retired slot was a denial target");
    }
    private static void shortTransitions() throws Exception {
        final RaceGame g=straight("short-transitions");
        g.players=new Player[]{car(1,60,10,1,0),car(2,71,10,1,0),car(3,30,7,0,0)};prepare(g);
        final String before=RacecraftReplay.snapshot(g);
        final int[][] x=Arrays.stream(g.players).map(p->p.getPosition().clone()).toArray(int[][]::new);
        final int[][] v=Arrays.stream(g.players).map(p->p.getVelocity().clone()).toArray(int[][]::new);
        final RaceAi.CellOccupancy occupied=new RaceAi.CellOccupancy(81,21);occupied.rebuild(x);
        final Method m=RaceAi.class.getDeclaredMethod("simulateRoundPass",int.class,int[][].class,int[][].class,
                RaceAi.CellOccupancy.class,int[][].class,int[][].class);m.setAccessible(true);
        m.invoke(g.ai,1,x,v,occupied,new int[3][2],new int[3][2]);
        check(x[1]==null && !occupied.contains(71,10),"finisher remained as a ghost blocker");
        check(before.equals(RacecraftReplay.snapshot(g)),"projection changed live state");
        // No preferred in-cap move, but real accelerations remain: never invent a parked body or crash.
        g.players[1]=car(2,20,12,14,0);
        g.players[2]=car(3,58,7,0,0); // keep this a traffic decision, inside the unchanged 20-cell rule
        prepare(g);
        final int[][] y=Arrays.stream(g.players).map(p->p.getPosition().clone()).toArray(int[][]::new);
        final int[][] w=Arrays.stream(g.players).map(p->p.getVelocity().clone()).toArray(int[][]::new);
        occupied.rebuild(y);m.invoke(g.ai,1,y,w,occupied,new int[3][2],new int[3][2]);
        check(y[1]!=null && y[1][0]>20,"search abstention erased or parked a physically mobile rival");
    }
    private static void endpoints() throws Exception {
        final Method m=RaceAi.class.getDeclaredMethod("tacticalForecast",int[].class,int[].class,int.class,Direction.class,int.class);m.setAccessible(true);
        for(int slot=0;slot<3;slot++) {
            final RaceGame ordinary=straight(""),aligned=straight("decision-endpoint");
            final int[] clocks=new int[2];int k=0;
            for(final RaceGame g:new RaceGame[]{ordinary,aligned}) {
                g.players=new Player[]{car(1,10,5,0,0),car(2,12,10,0,0),car(3,14,15,0,0)};
                g.subgamestate=slot;prepare(g);final String before=RacecraftReplay.snapshot(g);
                final Player p=g.players[slot];
                final TacticalComparison.Evaluation e=(TacticalComparison.Evaluation)m.invoke(g.ai,p.getPosition(),p.getVelocity(),slot+1,Direction.E,3);
                check(e.outcome().ownMoves()==3,"cutoff changed number of own moves");
                final Object[] work=(Object[])get(g.ai,"rolloutsByDepth");clocks[k++]=(int)get(work[1],"turns");
                check(before.equals(RacecraftReplay.snapshot(g)),"cutoff changed live state");
            }
            check(clocks[1]-clocks[0]==slot,"cutoff did not complete exactly the missing rival prefix");
            check(clocks[1]==9,"decision-aligned horizon not one common own-move boundary");
        }
    }
    private static void checkpointSubset() throws Exception {
        final RaceGame g=straight("checkpoint-traffic");prepare(g);
        final int[] values=new int[9];Arrays.fill(values,Integer.MAX_VALUE);
        values[Direction.E.ordinal()]=values[Direction.NE.ordinal()]=7;
        final Method m=RaceAi.class.getDeclaredMethod("checkpointTrafficChoice",int[].class,int[].class,int.class,
                Direction.class,int[].class,int.class);m.setAccessible(true);
        final Player p=g.players[0];
        final Direction d=(Direction)m.invoke(g.ai,p.getPosition(),p.getVelocity(),1,Direction.E,values,7);
        check(d==Direction.E||d==Direction.NE,"checkpoint comparison admitted a non-tie");
        check((int)get(g.ai,"trafficCheckpointTrials")==2,"eligible plateau not compared");
    }
    private static void manoeuvres() throws Exception {
        final RaceGame g=straight("manoeuvre");
        g.players=new Player[]{car(1,20,10,0,0),car(2,24,15,0,0),car(3,25,5,0,0)};prepare(g);
        final String before=RacecraftReplay.snapshot(g);
        final TrafficManoeuvres.Occupancy empty=new TrafficManoeuvres.Occupancy(new int[3],new int[3],new boolean[3],0);
        final TrafficManoeuvres.Search search=TrafficManoeuvres.propose(g,List.of(empty,empty,empty,empty),Direction.N,4,192);
        check(search.expanded()<=192 && !search.proposals().isEmpty(),"bounded graph found no complete overtaking proposal");
        for(final List<Direction> path:search.proposals()) {
            check(path.size()==4 && path.getFirst()!=Direction.N,"graph did not return a distinct four-action proposal");
            TrafficManoeuvres.forecast(g,RacecraftReplay.capture(g),path,12);
        }
        check(before.equals(RacecraftReplay.snapshot(g)),"reactive forecast changed live state/memory");
        check(TrafficManoeuvres.choose(g,Direction.E,null,4,0).forecasts()==0,"zero budget ran forecasts");
        // The nominal schedule can be wrong. A reactive replay must reject a blocked first action.
        g.players[1]=car(2,21,10,0,0);prepare(g);
        final TrafficManoeuvres.Forecast rejected=TrafficManoeuvres.forecast(g,RacecraftReplay.capture(g),List.of(Direction.E,Direction.E),12);
        check(!rejected.outcome().known(),"nominal occupancy schedule was mistaken for a safe path");
    }
    private static void memory() throws Exception {
        final RaceGame g=straight("manoeuvre");prepare(g);
        final FollowupPlans.Entry plan=FollowupPlans.Entry.traffic(List.of(Direction.E,Direction.N,Direction.NE),FollowupPlans.key(g));
        g.followups.put(0,plan);
        final String encoded=RacecraftReplay.snapshot(g);
        check(encoded.startsWith("rc5,"),"traffic suffix not versioned");
        check(RacecraftReplay.parse(g,encoded).encode().equals(encoded),"traffic memory did not round-trip");
        check(g.followups.copy().find(g).actions().equals(plan.actions()),"copy lost immutable suffix");
        set(g.ai,"pendingFirst",Direction.E);set(g.ai,"pendingFollowup",plan);set(g.ai,"decisionRootKey",FollowupPlans.key(g));
        g.ai.commitResearchPlan(Direction.N);check(g.followups.find(g)==null,"changed first action retained old manoeuvre");
        boolean refused=false;
        try { FollowupPlans.Entry.traffic(List.of(Direction.N,Direction.N,Direction.N,Direction.N),FollowupPlans.key(g)); }
        catch(final IllegalArgumentException expected){refused=true;}
        check(refused,"unbounded suffix accepted");
    }
    private static void check(final boolean value,final String message){if(!value)throw new AssertionError(message);}
}
