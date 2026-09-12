package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Rectangle2D;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Properties;

/** Physical replies and the mover-first timeout also constrain the older deep proof. */
public final class EndgamePhysicalTests {
    private EndgamePhysicalTests() {}

    public static void main(final String[] args) throws Exception {
        final RaceGame game = new RaceGame(new Properties());
        game.gameCols = 80;
        game.gameRows = 20;
        game.track = new Track();
        game.track.addLeft(0, 1); game.track.addLeft(73, 1);
        game.track.addRight(0, 19); game.track.addRight(73, 19);
        game.trackA = new Area(new Rectangle2D.Double(0, 1, 73, 18));
        game.startZoneA = new Area();
        game.finishLine = new Line2D.Double(72.5, 1, 72.5, 19);
        set(game, "finishFwdX", 1.0);
        final Player me = new Player("Me", 1, Color.BLUE, Player.Kind.AI1);
        me.setPosition(new int[]{61, 7}); me.setVelocity(new int[]{11, 0});
        final Player rival = new Player("Human", 2, Color.RED, Player.Kind.HUMAN);
        rival.setPosition(new int[]{60, 13}); rival.setVelocity(new int[]{12, 0});
        game.players = new Player[]{me, rival};
        final RaceAi ai = new RaceAi(game);
        final Method rivalNode = node("egRival"), ownNode = node("egMy");
        final RaceGame.MoveResult reply = game.evaluateMove(0, 0, 60, 13, 73, 13, false);
        check(reply.legal() && reply.finishes(), "speed-13 refutation is not physical");
        reset(ai);
        check(!(boolean) rivalNode.invoke(ai, 61, 7, 11, 0, 60, 13, 12, 0, 19),
                "deep search ignored a legal finishing reply beyond its planning cap");
        reset(ai);
        check((boolean) rivalNode.invoke(ai, 61, 7, 11, 0, 60, 13, 0, 0, 19),
                "uncontested next-move finish was lost");

        game.lapGates = new Line2D[]{game.finishLine,
                new Line2D.Double(30, 1, 30, 19), new Line2D.Double(50, 1, 50, 19)};
        set(game, "lapCrossGate", game.finishLine);
        set(game, "lapFwdX", 1.0);
        final int limit = 750 * game.players.length;
        game.setQueryTurnCounter(limit - 1);
        reset(ai);
        check(!(boolean) rivalNode.invoke(ai, 61, 7, 11, 0, 60, 13, 0, 0, 19),
                "deep proof promised our move after our own timeout");
        reset(ai);
        check(!(boolean) ownNode.invoke(ai, 61, 7, 11, 0, 60, 13, 0, 0, 18),
                "an immediate finish overrode timeout precedence");
        game.setQueryTurnCounter(limit);
        reset(ai);
        check((boolean) rivalNode.invoke(ai, 61, 7, 11, 0, 60, 13, 12, 0, 19),
                "rival timeout must precede its otherwise finishing acceleration");
        game.setQueryTurnCounter(Integer.MAX_VALUE);
        reset(ai);
        check(!(boolean) ownNode.invoke(ai, 61, 7, 11, 0, 60, 13, 0, 0, 18),
                "projected turn counter overflowed");
        final RaceAi.EndgameState fast = new RaceAi.EndgameState(61,7,11,0,60,13,22,0,19,true);
        final RaceAi.EndgameState reverse = new RaceAi.EndgameState(61,7,11,0,60,13,-10,0,19,true);
        final HashMap<RaceAi.EndgameState, Boolean> memo = new HashMap<>();
        memo.put(fast, true);
        check(!memo.containsKey(reverse), "physical velocities collided in the memo");
        check(memo.get(new RaceAi.EndgameState(61,7,11,0,60,13,22,0,19,true)),
                "equivalent physical states do not share memo entries");
        System.out.println("EndgamePhysicalTests: physical replies, projected timeout and full-state keys OK");
    }

    private static Method node(final String name) throws Exception {
        final Method method = RaceAi.class.getDeclaredMethod(name,
                int.class,int.class,int.class,int.class,int.class,int.class,int.class,int.class,int.class);
        method.setAccessible(true);
        return method;
    }

    private static void reset(final RaceAi ai) throws Exception {
        set(ai, "egMemo", new HashMap<RaceAi.EndgameState, Boolean>());
        set(ai, "egNodes", 0);
    }

    private static void set(final Object object, final String name, final Object value) throws Exception {
        final Field field = object.getClass().getDeclaredField(name);
        field.setAccessible(true);
        field.set(object, value);
    }

    private static void check(final boolean condition, final String message) {
        if (!condition) throw new AssertionError(message);
    }
}
