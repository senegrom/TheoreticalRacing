package tr.logic;

import java.awt.Color;
import java.lang.reflect.Method;

/** The strategy state must preserve the same gate, grid and timeout semantics
 * as the replay/referee parity fixtures; it is not another set of game rules. */
@SuppressWarnings("try")
public final class StrategyTransitionTests {
    private StrategyTransitionTests() {}
    private static void check(final boolean result, final String message) {
        if (!result) throw new AssertionError(message);
    }
    private static RaceGame midRace(final boolean pocket) throws Exception {
        final Method method=RacecraftFixTests.class.getDeclaredMethod("midRace",boolean.class);
        method.setAccessible(true);return (RaceGame)method.invoke(null,pocket);
    }
    public static void main(final String[] args) throws Exception {
        for (final boolean pocket : new boolean[]{false,true}) {
            final RaceGame game=midRace(pocket);
            final StrategyState root=StrategyState.capture(game);
            for (final Direction action:Direction.values()) {
                final StrategyState next=root.after(game,action);
                try(RacecraftReplay.Scope ignored=new RacecraftReplay.Scope(game,root.board)) {
                    final int actor=game.subgamestate;
                    RacecraftReplay.advance(game,action);
                    if(!RacecraftReplay.classifyLast(game)) {
                        int slot=actor;
                        do { slot=(slot+1)%game.players.length; } while(game.players[slot].isFinished());
                        game.subgamestate=slot;
                    }
                    check(next!=null && next.key().equals(FollowupPlans.key(game)),
                            "strategy progress/grid transition differs from referee: "+pocket+"/"+action);
                }
            }
            check(root.key().equals(FollowupPlans.key(game)),"strategy transition changed live ledger");
        }
        final Method fixture=RacecraftNextTests.class.getDeclaredMethod("straight",String.class,String.class);
        fixture.setAccessible(true);
        final RaceGame game=(RaceGame)fixture.invoke(null,"place-certificates,forced-sequence","1,2");
        final Method gates=RacecraftFixTests.class.getDeclaredMethod("gates",RaceGame.class);
        gates.setAccessible(true);gates.invoke(null,game);
        game.players=new Player[]{car(1,20),car(2,40)};
        game.players[1].incrementLap();game.setQueryTurnCounter(3000);
        final String before=RacecraftReplay.snapshot(game);
        final PlaceCertificates.Result trailing=PlaceCertificates.search(game,1,4,2000,true);
        check(!trailing.bounds().isEmpty() && trailing.bounds().values().stream().allMatch(b->b.place()==2),
                "strategy search invented a win when a more advanced rival reached timeout");
        check(before.equals(RacecraftReplay.snapshot(game)),"timeout proof mutated original board");
        game.players[0].incrementLap();game.players[1].restoreLapState(new int[]{0,1,0,0,0,0,1});
        final PlaceCertificates.Result leading=PlaceCertificates.search(game,1,4,2000,true);
        check(!leading.bounds().isEmpty() && leading.bounds().values().stream().allMatch(b->b.place()==1),
                "progress-based timeout victory was lost");
        System.out.println("StrategyTransitionTests: ordered checkpoints, grid entitlement, prior classifications and projected timeouts OK");
    }
    private static Player car(final int number,final int x) {
        final Player p=new Player("P"+number,number,Color.BLUE,Player.Kind.AI1);
        p.setPosition(new int[]{x,10});p.setVelocity(new int[]{0,0});p.leaveGrid();return p;
    }
}
