package tr.logic;

import java.awt.Color;
import java.awt.geom.Line2D;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Behavioral witnesses for the peer review, separate from fleet-performance evidence. */
public final class RacecraftFixTests {
    private RacecraftFixTests() {}

    public static void main(final String[] args) throws Exception {
        timeoutCertificate();
        timeoutReferee();
        openingCoverage();
        actualCrashChooser();
        phaseIsolation();
        System.out.println("RacecraftFixTests: progress timeouts, live referee parity, actual chooser crash salvage, rotated opening plans and flag isolation OK");
    }

    private static RaceGame straight(final String flags) throws Exception {
        final Method m = RacecraftNextTests.class.getDeclaredMethod("straight", String.class, String.class);
        m.setAccessible(true);
        return (RaceGame) m.invoke(null, flags, "1,2,3");
    }
    private static Player car(final int id, final int x, final int y, final int vx, final int vy) {
        final Player p = new Player("P"+id,id,Color.BLUE,Player.Kind.AI1);
        p.setPosition(new int[]{x,y}); p.setVelocity(new int[]{vx,vy}); p.leaveGrid(); return p;
    }
    private static void gates(final RaceGame g) throws Exception {
        g.lapGates = new Line2D[]{g.finishLine,new Line2D.Double(30,1,30,19),new Line2D.Double(50,1,50,19)};
        set(g,"lapCrossGate",g.finishLine); set(g,"lapFwdX",1.0); g.totalLaps=2;
    }

    private static void timeoutCertificate() throws Exception {
        final RaceGame g=straight(""); gates(g);
        g.players=new Player[]{car(1,20,10,0,0),car(2,40,10,0,0)};
        g.players[1].incrementLap(); g.setQueryTurnCounter(3000);
        final String before=RacecraftReplay.snapshot(g);
        check(RaceAiDuelSearch.winWithinTwoMoves(g,1)==null,
                "counterexample: trailing car certified a win when next rival turn hits limit");
        check(before.equals(RacecraftReplay.snapshot(g)),"duel changed live board");
        g.players[0].incrementLap(); g.players[1].restoreLapState(new int[]{0,1,0,0,0,0,1});
        check(RaceAiDuelSearch.winWithinTwoMoves(g,1)!=null,"projected timeout win by progress was lost");
        final RaceTimeout.Progress late=RaceTimeout.progress(g,1,1,20,10,0,0,1);
        final RaceTimeout.Progress early=RaceTimeout.progress(g,1,1,20,10,0,0,0);
        check(early.compareTo(late)<0,"cyclic tie not resolved in next-mover order");
        g.players=new Player[]{g.players[0],g.players[1],car(3,60,5,0,0),car(4,60,15,0,0)};
        g.players[2].setFinishedPlace(3); g.players[3].setFinishedPlace(4);
        check(!RaceTimeout.reached(g,3001) && RaceTimeout.reached(g,6001),"retired slots changed original roster turn limit");
    }

    private static void timeoutReferee() throws Exception {
        final RaceGame model=straight("rank-time"); gates(model);
        model.players=new Player[]{car(1,20,10,0,0),car(2,40,10,0,0)};
        model.players[1].incrementLap(); model.subgamestate=0; model.setQueryTurnCounter(3001);
        final RacecraftReplay.Board root=RacecraftReplay.capture(model);
        final RacecraftReplay.Tail tail=RacecraftReplay.run(model,root,0,null,20,false);
        check(tail.complete() && tail.place()==2 && tail.outcome().status()==RacecraftOutcome.Status.TIMED_OUT,
                "timeout replay did not rank the more advanced rival first");
        check(tail.trace().size()==1,"two-car timeout invented racing moves");
        model.ai.querySimOutcome(0,2,true,false,true,3,new int[3]);
        final RacecraftOutcome result=(RacecraftOutcome)get(model.ai,"lastResearchOutcome");
        check(result.resolved() && !result.crashed() && result.ahead()==1,"rollout timeout became a crash/win");
        check(root.encode().equals(RacecraftReplay.snapshot(model)),"timeout forecast changed live board");
        final RaceGame referee=straight("rank-time"); gates(referee);
        referee.players=new Player[]{car(1,20,10,0,0),car(2,40,10,0,0)};
        referee.players[1].incrementLap(); referee.setQueryTurnCounter(3001);
        referee.setAutoMode(true); referee.setAutoRaceEndHook(()->{});
        final Path log=Files.createTempFile("review-timeout-", ".log");
        referee.setGameLogPath(log.toString()); set(referee,"gamestate",GameState.PLAY);
        final Method commit=RaceGame.class.getDeclaredMethod("commitMove",int[].class,int[].class,int[].class);
        commit.setAccessible(true);
        try {
            final int[] x=referee.players[0].getPosition();
            commit.invoke(referee,x,new int[]{0,0},x);
            check(tail.finalState().equals(RacecraftReplay.snapshot(referee)),"timeout tail and live referee differ");
        } finally { Files.deleteIfExists(log); }
    }

    private static Direction rotate(final Direction d, final int count) {
        int x=d.dx,y=d.dy;
        for(int k=0;k<count;k++){ final int old=x; x=-y; y=old; }
        for(final Direction candidate:Direction.values()) if(candidate.dx==x&&candidate.dy==y)return candidate;
        throw new AssertionError("no rotated acceleration");
    }

    private static void openingCoverage() {
        for(int rotation=0;rotation<4;rotation++) {
            final Direction nominal=rotate(Direction.W,rotation), setup=rotate(Direction.N,rotation);
            final Direction follow=rotate(Direction.SE,rotation);
            final int[] turns=new int[9]; Arrays.fill(turns,-1);
            turns[follow.ordinal()]=1; turns[Direction.NONE.ordinal()]=20;
            final List<Direction> legal=OpeningPlans.ordered(turns,0,0);
            check(legal.getFirst()==follow,"compass order outranked continuation score");
            final List<Direction> visited=new ArrayList<>();
            final OpeningPlans.Selection pick=OpeningPlans.choose(nominal,new Direction[]{nominal,setup},4,false,(first,second)->{
                if(second!=null){ check(legal.contains(second),"an illegal follow-up consumed budget"); visited.add(second); }
                final boolean improvement=first==setup && second==follow;
                return new OpeningPlans.Trial(new RacecraftOutcome(RacecraftOutcome.Status.RUNNING,
                        0,2,improvement?2:20),legal);
            });
            check(pick.move()==setup && pick.trials()==4 && visited.contains(follow),
                    "bounded opening missed the unique rotated second-action setup");
        }
        check(OpeningPlans.choose(Direction.E,new Direction[]{Direction.N},0,false,(a,b)->{
            throw new AssertionError("zero budget called model");
        }).move()==Direction.E,"zero-budget control changed move");
    }

    private static Direction chooser(final RaceGame g) throws Exception {
        final Player p=g.players[0];
        final Method prepare=RaceAi.class.getDeclaredMethod("prepareDecisionFrame",int[].class,int[].class,int.class);
        prepare.setAccessible(true); prepare.invoke(g.ai,p.getPosition(),p.getVelocity(),1);
        final Method method=RaceAi.class.getDeclaredMethod("jointChooser",int[].class,int[].class,int.class,
                Direction.class,double[].class,double.class); method.setAccessible(true);
        final double[] scores=new double[9]; Arrays.fill(scores,Double.MAX_VALUE);
        scores[Direction.NW.ordinal()]=0; scores[Direction.SE.ordinal()]=0;
        return (Direction)method.invoke(g.ai,p.getPosition(),p.getVelocity(),1,Direction.NW,scores,0.0);
    }

    private static void actualCrashChooser() throws Exception {
        final RaceGame candidate=straight("crash-rank"), control=straight("");
        for(final RaceGame g:new RaceGame[]{candidate,control}) {
            g.players=new Player[]{car(1,20,17,0,-8),car(2,35,11,0,-7),car(3,60,10,0,0)};
            g.subgamestate=0;
        }
        check(chooser(control)==Direction.NW,"control no longer keeps first all-failed candidate");
        check(chooser(candidate)==Direction.SE,"actual chooser failed to salvage second rather than third place");
    }

    private static void phaseIsolation() throws Exception {
        final RaceGame opening=straight("opening"), control=straight("");
        for(final RaceGame g:new RaceGame[]{opening,control})g.setQueryTurnCounter(4*g.players.length);
        check(!opening.racecraftNext.enabled(opening,1,RacecraftNext.Feature.OPENING),"opening flag active after its phase");
        check(opening.ai.computeAiMove()==control.ai.computeAiMove(),"opening-only changed mid-race policy");
        for(final RaceGame g:new RaceGame[]{opening,control}) {
            g.players=new Player[]{car(1,20,10,0,0),car(2,60,10,0,0)};g.setQueryTurnCounter(0);
        }
        check(opening.ai.computeAiMove()==control.ai.computeAiMove(),"solo conformance differs across experiment flags");
    }
    private static Object get(final Object o,final String key)throws Exception{final Field f=o.getClass().getDeclaredField(key);f.setAccessible(true);return f.get(o);}
    private static void set(final Object o,final String key,final Object value)throws Exception{final Field f=o.getClass().getDeclaredField(key);f.setAccessible(true);f.set(o,value);}
    private static void check(final boolean condition,final String message){if(!condition)throw new AssertionError(message);}
}
