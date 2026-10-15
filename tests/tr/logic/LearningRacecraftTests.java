package tr.logic;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Constructed behavioural witnesses, not performance or promotion evidence. */
@SuppressWarnings("try")
public final class LearningRacecraftTests {
    private LearningRacecraftTests() {}
    private static void check(final boolean value,final String reason) { if(!value) throw new AssertionError(reason); }
    private static RaceGame fixture(final String flags) throws Exception {
        final Method method=RacecraftNextTests.class.getDeclaredMethod("straight",String.class,String.class);
        method.setAccessible(true);
        final RaceGame game=(RaceGame)method.invoke(null,flags,"1,2,3");
        for(final Player p:game.players) p.restoreLapState(new int[]{0,1,0,0,0,0,1});
        return game;
    }
    private static void pose(final Player p,final int x,final int y,final int vx,final int vy,final int lap) {
        p.setPosition(new int[]{x,y});p.setVelocity(new int[]{vx,vy});p.restoreLapState(new int[]{lap,1,0,0,0,0,1});
    }
    private static void repair() throws Exception {
        final RaceGame game=fixture("forecast-repair");game.players=java.util.Arrays.copyOf(game.players,2);
        pose(game.players[0],20,8,0,0,0);pose(game.players[1],22,8,0,0,0);
        final RacecraftReplay.Board root=RacecraftReplay.capture(game);
        final String before=RacecraftReplay.snapshot(game);
        final LearningForecast.Policy misleading=(g,strong)->g.subgamestate==1?(strong?Direction.N:Direction.W):Direction.E;
        final LearningForecast.Result crude=LearningForecast.run(game,root,List.of(Direction.E),2,-1,
                new LearningForecast.Settings(0,2,0,false),misleading);
        final LearningForecast.Result repaired=LearningForecast.run(game,root,List.of(Direction.E),2,-1,
                new LearningForecast.Settings(2,2,0,false),misleading);
        check(crude.outcome().status()==RacecraftOutcome.Status.CLASSIFIED,"fixture did not manufacture last-survivor reward");
        check(repaired.repairs()>0&&repaired.outcome().status()==RacecraftOutcome.Status.RUNNING,"rival escape was not replayed");
        check(before.equals(RacecraftReplay.snapshot(game)),"forecast mutated live state");
        final LearningForecast.Failure history=new LearningForecast.Failure(1,List.of(
                new LearningForecast.Decision("old",1,true),new LearningForecast.Decision("other",0,true),new LearningForecast.Decision("crash",1,true)));
        check("old".equals(LearningForecast.refine(history,Set.of("crash"),1)),"rewind did not reach preceding decision of failed car");
        check(LearningForecast.refine(history,Set.of("crash"),0)==null,"rewind exceeded configured depth");
    }
    private static void selfRepair() throws Exception {
        final RaceGame game=fixture("forecast-repair");game.players=java.util.Arrays.copyOf(game.players,2);
        pose(game.players[0],20,8,0,0,0);pose(game.players[1],26,8,0,0,0);
        final LearningForecast.Policy weak=(g,strong)->g.subgamestate==1?Direction.NONE:
                strong&&g.players[0].getPosition()[0]>21?Direction.N:Direction.E;
        final RacecraftReplay.Board root=RacecraftReplay.capture(game);
        final LearningForecast.Result old=LearningForecast.run(game,root,List.of(Direction.E),3,-1,
                new LearningForecast.Settings(0,0,0,false),weak);
        final LearningForecast.Result fixed=LearningForecast.run(game,root,List.of(Direction.E),3,-1,
                new LearningForecast.Settings(1,0,0,false),weak);
        check(old.outcome().crashed()&&fixed.outcome().status()==RacecraftOutcome.Status.RUNNING,
                "own cheap doom was not repaired at the failed decision");
        check(fixed.repairs()==1,"self repair budget not observed");
    }
    private static void memory() throws Exception {
        final RaceGame game=fixture("corner-memory");
        pose(game.players[0],25,8,3,0,0);pose(game.players[1],60,14,0,0,0);pose(game.players[2],50,16,0,0,0);
        final Class<?> snapshot=Class.forName("tr.logic.RaceGame$MoveSnapshot");
        final Constructor<?> constructor=snapshot.getDeclaredConstructor(RaceGame.class);constructor.setAccessible(true);
        final Object undo=constructor.newInstance(game);
        final String empty=game.learningMemory.encode(3);
        game.ai.computeAiMove();game.ai.computeAiMove();
        check(empty.equals(game.learningMemory.encode(3)),"queries taught memory");
        for(final Direction action:List.of(Direction.E,Direction.S,Direction.N,Direction.E)) {
            game.subgamestate=0;game.ai.commitResearchPlan(action);RacecraftReplay.advance(game,action);
        }
        final LearningMemory.Pose entry=new LearningMemory.Pose(25,8,3,0,1,1,true);
        check(!game.learningMemory.remembered(0,entry).isEmpty(),"successful curved sequence was not retained across laps");
        check(game.learningMemory.remembered(0,new LearningMemory.Pose(25,8,3,0,0,1,true)).isEmpty(),"same-lap hindsight reused");
        final String encoded=game.learningMemory.encode(3);
        check(encoded.equals(LearningMemory.parse(encoded,3).encode(3)),"learning state round trip");
        game.totalLaps=3;pose(game.players[0],22,8,3,0,1);game.subgamestate=0;
        final RacecraftReplay.Board root=RacecraftReplay.capture(game);
        check(root.encode().startsWith("rc7,"),"archive omitted from replay snapshot");
        check(root.encode().equals(RacecraftReplay.parse(game,root.encode()).encode()),"rc7 roundtrip");
        final LearningForecast.Result learned=LearningForecast.run(game,root,List.of(Direction.NONE),5,-1,
                new LearningForecast.Settings(0,0,0,true),(g,strong)->Direction.NONE);
        check(learned.memories()>0&&learned.prefix().get(1)==Direction.E,"remembered suffix never entered projected driving");
        check(root.encode().equals(RacecraftReplay.snapshot(game)),"detached learning mutated archive");
        final Method restore=snapshot.getDeclaredMethod("restore",RaceGame.class);restore.setAccessible(true);restore.invoke(undo,game);
        check(game.learningMemory.encode(3).equals(empty),"Undo failed to restore experience");
    }
    private static void investment() throws Exception {
        final RaceGame game=fixture("time-investment");
        final CreativePaths.Own initial=new CreativePaths.Own(65,8,1,0,0,1,true,false);
        final AmbushPlans.Target target=new AmbushPlans.Target(68,8,2);
        final List<List<Direction>> free=AmbushPlans.intercept(game,initial,target,new StrategyState.Budget(20000),0);
        final List<List<Direction>> paid=AmbushPlans.intercept(game,initial,target,new StrategyState.Budget(20000),1);
        check(free.isEmpty()&&!paid.isEmpty(),"one-move attack was still filtered as pace-neutral");
        for(final List<Direction> path:paid) {
            final CreativePaths.Own end=CreativePaths.follow(game,initial,path,new StrategyState.Budget(20));
            check(end!=null&&CreativePaths.distance(game,end)+path.size()==CreativePaths.distance(game,initial)+1,"attack exceeded debt cap");
        }
        check(LearningChooser.better(new RacecraftOutcome(RacecraftOutcome.Status.FINISHED,0,7,0),
                new RacecraftOutcome(RacecraftOutcome.Status.FINISHED,1,6,0)),"time investment ranked speed before place");
    }
    private static void event() throws Exception {
        final RaceGame game=fixture("event-aware");game.players=java.util.Arrays.copyOf(game.players,2);
        pose(game.players[0],20,8,0,0,0);pose(game.players[1],22,8,0,0,0);
        check(LearningForecast.commitment(game,StrategyState.capture(game)),"contested commitment trigger absent");
        final LearningForecast.Result forecast=LearningForecast.run(game,RacecraftReplay.capture(game),List.of(Direction.N),3,1,
                new LearningForecast.Settings(0,0,1,false),(g,strong)->Direction.N);
        check(forecast.eventCalls()==1,"event upgrade failed to fire once at the later commitment");
    }
    private static void proof() throws Exception {
        final RaceGame game=fixture("proof-number");game.players=java.util.Arrays.copyOf(game.players,2);
        pose(game.players[0],69,8,2,0,0);pose(game.players[1],40,12,1,0,0);
        final StrategyState root=StrategyState.capture(game);
        final String before=RacecraftReplay.snapshot(game);
        final ProofNumberSearch.Result shortGoal=ProofNumberSearch.search(game,root,1,2000);
        check(shortGoal.plan()==null&&shortGoal.refuted(),"one-move deadline incorrectly won");
        final ProofNumberSearch.Result win=ProofNumberSearch.search(game,root,2,5000);
        check(win.plan()!=null&&win.action()!=null,"proof-number controller missed two-move win");
        check(ProofNumberSearch.verify(game,root,0,win.plan(),2,new StrategyState.Budget(20000)),"stored response plan failed independent verification");
        final ProofNumberSearch.Result unknown=ProofNumberSearch.search(game,root,2,0);
        check(unknown.plan()==null&&!unknown.refuted(),"work exhaustion became a disproof or win");
        check(before.equals(RacecraftReplay.snapshot(game)),"proof search mutated state");
        final String encoded=win.plan().encode();check(ProofNumberSearch.Plan.parse(encoded).encode().equals(encoded),"proof plan roundtrip");
        game.learningMemory.proof(0,win.plan());
        final String saved=RacecraftReplay.snapshot(game);check(saved.equals(RacecraftReplay.parse(game,saved).encode()),"proof missing from rc7");
    }
    private static void league() throws Exception {
        final RaceGame game=fixture("");game.players=java.util.Arrays.copyOf(game.players,2);
        pose(game.players[0],71,8,2,0,0);pose(game.players[1],66,12,1,0,0);
        final String snapshot=RacecraftReplay.snapshot(game);
        final String query="league1,30,champion/g_0_20_4|"+snapshot;
        final String first=OpponentLeague.answer(game,query),again=OpponentLeague.answer(game,query);
        check(first.equals(again)&&first.contains("\"complete\":true"),"league is incomplete or nondeterministic");
        check(first.contains(RacecraftReplay.sha(query)),"league response is not request bound");
        check(snapshot.equals(RacecraftReplay.snapshot(game)),"league mutated live board");
        boolean rejected=false;try { OpponentLeague.Profile.parse("g_0_21_4"); } catch(final IllegalArgumentException e) { rejected=true; }
        check(rejected,"invalid rival genome accepted");
    }
    private static void requestBounds() throws Exception {
        final RaceGame game=fixture("");
        game.players=new Player[9];
        final java.util.Map<String,ProofNumberSearch.Answer> records=new java.util.TreeMap<>();
        for(int i=0;i<512;i++) records.put(String.format("%064x",i),new ProofNumberSearch.Answer(Direction.E,2));
        // Structural parser fixture only: these records are NOT certified
        // by a search and proof-number is OFF for every actor.
        for(int i=0;i<9;i++) {
            game.players[i]=new Player("P"+(i+1),i+1,java.awt.Color.BLUE,Player.Kind.AI1);
            pose(game.players[i],69,2+2*i,4,0,0);
            game.learningMemory.proof(i,new ProofNumberSearch.Plan(1,50,records));
        }
        final String root=RacecraftReplay.snapshot(game);
        check(root.length()>280000,"large-state fixture does not cross legacy request bound");
        check(root.equals(RacecraftReplay.parse(game,root).encode()),"maximum-slot learning state failed parsing");
        final String answer=TacticBreeder.answer(game,"breed1,30,-|"+root);
        check(answer.contains("\"complete\":true"),"legacy breeder rejected complete bounded learning state");
        check(root.equals(RacecraftReplay.snapshot(game)),"large-state breeder altered live policy memory");
    }
    public static void main(final String[] args) throws Exception {
        repair();selfRepair();memory();investment();event();proof();league();requestBounds();
        System.out.println("LearningRacecraftTests: repair, memory, investment, event, proof and league witnesses OK");
    }
}
