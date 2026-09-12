package tr.logic;

import java.lang.reflect.Method;
import java.nio.file.Files;
import java.util.Arrays;
import static tr.logic.LifecycleTestSupport.*;

/** Model/referee differential checks, including turn wrap and optional outputs. */
public final class RolloutTerminationTests {
    private RolloutTerminationTests() {}

    private static long failureCost() throws Exception {
        final var f=RaceAi.class.getDeclaredField("ROLLOUT_FAILURE_COST");
        f.setAccessible(true); return f.getLong(null);
    }

    private static int simulate(final RaceGame game, final int mover, final int[] target,
            final boolean pending, final int rounds, final int[] tier, final long[] field,
            final int[] thread, final long[] rivals) throws Exception {
        game.ai.querySimOutcome(mover,0,false,false,false,0,null); // install a decision frame
        for (final Method method : RaceAi.class.getDeclaredMethods()) if (method.getName().equals("simulate")) {
            method.setAccessible(true);
            final int[] v=game.players[mover].getVelocity();
            return (int) method.invoke(game.ai,target[0],target[1],v[0],v[1],mover+1,rounds,
                    true,true,true,false,false,false,0,tier,field,thread,false,rivals,pending);
        }
        throw new AssertionError("rollout method missing");
    }

    private static void prepare(final RaceGame game) {
        game.reach.computeDistMap(); game.reach.computeReachability();
    }

    private static String state(final RaceGame game) throws Exception {
        final StringBuilder b=new StringBuilder(game.subgamestate+":"+game.turnCount()+":"+get(game,"gameLog"));
        for (final Player p : game.players) b.append(Arrays.toString(p.getPosition()))
                .append(Arrays.toString(p.getVelocity())).append(p.getFinishedPlace())
                .append(Arrays.toString(p.lapState())).append(p.getHistory().size());
        return b.toString();
    }

    private static void doomedSurvivors() throws Exception {
        for (int mover=0; mover<3; mover++) {
            final RaceGame game=straight(80,car(1,10,2,0,-4),car(2,30,2,0,-4),car(3,45,2,0,-4));
            prepare(game); game.subgamestate=mover;
            final String before=state(game);
            final int[] tier={-1},thread={0,0}; final long[] field={-1},rivals=new long[3];
            final int result=simulate(game,mover,game.players[mover].getPosition(),false,4,tier,field,thread,rivals);
            check(result==0 && tier[0]==3, "last survivor was forced to take another turn: " + mover);
            check(thread[0]==0 && thread[1]==0, "phantom own turn entered thread audit");
            check(field[0]==2*failureCost(), "retired rival field cost lost");
            for (int i=0;i<3;i++) check(rivals[i]==(i==mover ? -1 : failureCost()), "rival cost mismatch");
            check(before.equals(state(game)), "rollout mutated live board");
            final var log=Files.createTempFile("last-survivor-", ".log");
            try {
                game.setAutoMode(true); game.setAutoRaceEndHook(()->{}); game.setGameLogPath(log.toString());
                game.subgamestate=(mover+1)%3;
                for (int n=0;n<2;n++) commit(game,Direction.NONE);
                check(game.players[mover].getFinishedPlace()==1 && game.turnCount()==2,
                        "live referee disagrees on last survivor");
            } finally { Files.deleteIfExists(log); }
        }
    }

    private static void finishesAndTimeouts() throws Exception {
        final RaceGame game=straight(80,car(1,10,2,0,-4),car(2,70,10,3,0));
        prepare(game);
        final int[] tier={-1}; final long[] field={-1},rivals=new long[2];
        check(simulate(game,0,game.players[0].getPosition(),false,3,tier,field,null,rivals)==0,
                "rival finish did not classify survivor");
        check(tier[0]==3 && field[0]==0 && rivals[1]==1, "finish costs wrong");

        // The mover finishes immediately; the remaining doomed rival is classified, not simulated.
        game.players=new Player[]{car(1,70,10,3,0),car(2,10,2,0,-4)};
        for (int flags=0;flags<4;flags++) {
            final long[] f=(flags&1)==0 ? null : new long[]{-1};
            final long[] r=(flags&2)==0 ? null : new long[2];
            check(simulate(game,0,new int[]{73,10},true,3,tier,f,null,r)==0,"candidate finish lost");
            if (f!=null) check(f[0]==0,"classified rival accrued future failure cost");
            if (r!=null) check(r[0]==-1 && r[1]==0,"classified rival accrued phantom moves");
        }
        laps(game,1); game.setQueryTurnCounter(1501);
        game.players[0].setNextGate(0);
        check(simulate(game,0,new int[]{73,10},true,3,tier,null,null,null)==-1,
                "pending finish bypassed timeout");
        game.players=new Player[]{car(1,10,10,0,0),car(2,30,10,0,0),car(3,50,10,0,0)};
        game.setQueryTurnCounter(2251);
        check(simulate(game,0,new int[]{10,10},false,3,tier,field,null,new long[3])==0,
                "last timeout survivor simulated again");
        check(tier[0]==3 && field[0]==2*failureCost(),"timeout finalization mismatch");

        game.players[1].setFinishedPlace(3); game.players[2].setFinishedPlace(2);
        check(simulate(game,0,new int[]{10,10},false,0,tier,field,null,new long[3])==0,
                "already classified survivor needs a move");
        game.players=new Player[]{car(1,10,2,0,-4)};
        game.setQueryTurnCounter(0);
        check(simulate(game,0,new int[]{10,2},false,3,tier,null,null,null)==-1,
                "solo exception was lost");
    }

    public static void main(final String[] args) throws Exception {
        doomedSurvivors(); finishesAndTimeouts();
        System.out.println("RolloutTerminationTests: live/referee termination, wrap, finish, timeout, solo and output costs OK");
    }
}
