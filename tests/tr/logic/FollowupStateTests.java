package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Rectangle2D;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

/** Plan-state parity against independent committed transitions, not a model-score test. */
public final class FollowupStateTests {
    private FollowupStateTests() {}

    public static void main(final String[] args) throws Exception {
        cyclicProjection();
        classifiedProjection();
        checkpointProjection();
        actualForecastPrefix();
        undoRestoresMemory();
        System.out.println("FollowupStateTests: cyclic/progress/classification/grid prefix keys, actual forecast prefix and Undo memory OK");
    }

    private static RaceGame straight() throws Exception {
        final Method m = RacecraftNextTests.class.getDeclaredMethod("straight", String.class, String.class);
        m.setAccessible(true);
        return (RaceGame) m.invoke(null, "opening,followup", "1,2,3,4,5");
    }
    private static Player car(final int id, final int x, final int y, final int vx, final int vy) {
        final Player p = new Player("P" + id,id,Color.BLUE,Player.Kind.AI1);
        p.setPosition(new int[]{x,y}); p.setVelocity(new int[]{vx,vy}); p.leaveGrid(); return p;
    }
    private static void next(final RaceGame game) {
        final int original = game.subgamestate;
        int slot = original;
        do { slot = (slot + 1) % game.players.length; } while (game.players[slot].isFinished());
        game.subgamestate = slot;
    }
    private static void step(final RaceGame game, final FollowupPlans.Projection projection, final Direction d) {
        final int slot = game.subgamestate;
        final Player p = game.players[slot]; final int[] x = p.getPosition(),v = p.getVelocity();
        final int vx = v[0] + d.dx, vy = v[1] + d.dy, nx = x[0] + vx, ny = x[1] + vy;
        final RaceGame.MoveResult move = game.evaluateMove(p,x,new int[]{nx,ny});
        projection.step(slot,move,nx,ny,vx,vy);
        RacecraftReplay.advance(game,d);
        next(game);
    }
    private static void equalKey(final RaceGame game, final FollowupPlans.Projection projection) {
        final String expected = projection.key(game.turnCount(),game.subgamestate);
        check(expected != null && expected.equals(FollowupPlans.key(game)),
                "projected physical state or classification differs from committed referee transitions");
    }

    private static void cyclicProjection() throws Exception {
        for (int root = 0; root < 3; root++) {
            final RaceGame g = straight();
            g.players = new Player[]{car(1,20,8,1,0),car(2,30,10,1,0),car(3,40,12,1,0)};
            g.subgamestate = root;
            final FollowupPlans.Projection projection = new FollowupPlans.Projection(g);
            for (int k=0;k<3;k++) step(g,projection,Direction.E);
            check(g.subgamestate==root && g.turnCount()==3,"cyclic fixture did not reach the next own decision");
            equalKey(g,projection);
        }
    }

    private static void classifiedProjection() throws Exception {
        final RaceGame g=straight();
        g.players=new Player[]{car(1,Player.INIT_POS,Player.INIT_POS,0,0),car(2,20,10,1,0),
                car(3,71,12,1,0),car(4,40,2,0,-4),car(5,50,14,0,0)};
        g.players[0].setFinishedPlace(1);g.researchClassification(1,0);g.subgamestate=1;
        final FollowupPlans.Projection projection=new FollowupPlans.Projection(g);
        step(g,projection,Direction.E);
        step(g,projection,Direction.E); // rival finishes second
        step(g,projection,Direction.N); // different rival retires fifth
        step(g,projection,Direction.NONE);
        check(g.players[2].getFinishedPlace()==2 && g.players[3].getFinishedPlace()==5,
                "classification fixture changed");
        check(g.subgamestate==1,"retired roster slot was not skipped");
        equalKey(g,projection);
    }

    private static void checkpointProjection() throws Exception {
        final RaceGame g=straight();
        g.lapGates=new Line2D[]{g.finishLine,new Line2D.Double(30,1,30,19),new Line2D.Double(50,1,50,19)};
        set(g,"lapCrossGate",g.finishLine);set(g,"lapFwdX",1.0);g.totalLaps=2;
        g.startZoneA=new Area(new Rectangle2D.Double(0,1,30,18));
        g.players=new Player[]{car(1,29,10,1,0),car(2,40,14,0,0)};
        g.players[0].restoreLapState(new int[]{0,1,5,6,7,8,0});g.subgamestate=0;
        final FollowupPlans.Projection projection=new FollowupPlans.Projection(g);
        step(g,projection,Direction.E);step(g,projection,Direction.NONE);
        check(g.players[0].getNextGate()==2 && g.players[0].hasLeftGrid(),
                "fixture did not collect a checkpoint and leave the grid");
        equalKey(g,projection);
    }

    private static void actualForecastPrefix() throws Exception {
        for (int root=0;root<3;root++) {
            final RaceGame forecast=straight(), referee=straight();
            for (final RaceGame g:new RaceGame[]{forecast,referee}) {
                g.players=new Player[]{car(1,20,8,1,0),car(2,23,10,1,0),car(3,26,12,1,0)};
                g.subgamestate=root;
                final Player p=g.players[root];
                final Method prepare=RaceAi.class.getDeclaredMethod("prepareDecisionFrame",int[].class,int[].class,int.class);
                prepare.setAccessible(true);prepare.invoke(g.ai,p.getPosition(),p.getVelocity(),p.getNumber());
            }
            final Method run=RaceAi.class.getDeclaredMethod("researchForecast",int[].class,int[].class,int.class,
                    Direction.class,int.class,Direction.class);run.setAccessible(true);
            final Player me=forecast.players[root];
            run.invoke(forecast.ai,me.getPosition(),me.getVelocity(),me.getNumber(),Direction.E,3,Direction.SE);
            final Field field=RaceAi.class.getDeclaredField("openingExpectedKey");field.setAccessible(true);
            final String expected=(String)field.get(forecast.ai);
            RacecraftReplay.advance(referee,Direction.E);next(referee);
            for (int k=0;k<2;k++) {
                final Direction d=referee.ai.researchScorer();
                RacecraftReplay.advance(referee,d);next(referee);
            }
            check(expected!=null&&expected.equals(FollowupPlans.key(referee)),
                    "stored next-board key differs from the actual first-cycle scorer model at slot "+root);
        }
    }

    private static void undoRestoresMemory() throws Exception {
        final RaceGame g=straight();
        g.followups.put(0,new FollowupPlans.Entry(Direction.SE,FollowupPlans.key(g)));
        final String original=g.followups.encode(g.players.length);
        final Class<?> type=Class.forName("tr.logic.RaceGame$MoveSnapshot");
        final Constructor<?> constructor=type.getDeclaredConstructor(RaceGame.class);constructor.setAccessible(true);
        final Object snapshot=constructor.newInstance(g);
        g.followups.put(0,null);g.followups.put(1,new FollowupPlans.Entry(Direction.W,"f".repeat(64)));
        final Method restore=type.getDeclaredMethod("restore",RaceGame.class);restore.setAccessible(true);restore.invoke(snapshot,g);
        check(g.followups.encode(g.players.length).equals(original),"Undo lost or aliased pending plans");
        g.followups.put(0,null);restore.invoke(snapshot,g);
        check(g.followups.encode(g.players.length).equals(original),"Undo snapshot was consumed by the first restore");
    }
    private static void set(final Object target,final String name,final Object value)throws Exception{
        final Field field=target.getClass().getDeclaredField(name);field.setAccessible(true);field.set(target,value);
    }
    private static void check(final boolean condition,final String message){if(!condition)throw new AssertionError(message);}
}
