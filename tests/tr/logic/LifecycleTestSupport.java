package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Rectangle2D;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Properties;
import tr.gui.RaceUI;

/** Detached, tiny fixtures shared by the lifecycle/referee regressions. */
final class LifecycleTestSupport {
    private LifecycleTestSupport() {}

    static RaceGame straight(final int width, final Player... players) throws Exception {
        final RaceGame game = new RaceGame(new Properties());
        game.gameCols = width; game.gameRows = 20;
        game.track = new Track();
        game.track.addLeft(0, 1); game.track.addLeft(width - 7, 1);
        game.track.addRight(0, 19); game.track.addRight(width - 7, 19);
        game.trackA = new Area(new Rectangle2D.Double(0, 1, width - 7, 18));
        game.startZoneA = new Area();
        game.finishLine = new Line2D.Double(width - 7.5, 1, width - 7.5, 19);
        set(game, "finishFwdX", 1.0);
        set(game, "rui", new RaceUI(20, width));
        set(game, "gamestate", GameState.PLAY);
        set(game, "startZoneGone", true);
        game.players = players;
        // Occupancy-only queries need dimensions, not a synthetic speed restriction.
        game.reach.aliveW = width + 1; game.reach.aliveH = 21;
        game.reach.aliveVMAX = 12; game.reach.aliveSpan = 25;
        return game;
    }

    static Player car(final int n, final int x, final int y, final int vx, final int vy) {
        final Player player = new Player("P" + n, n, Color.BLUE, Player.Kind.AI1);
        player.setPosition(new int[]{x, y}); player.setVelocity(new int[]{vx, vy});
        return player;
    }

    static void laps(final RaceGame game, final int laps) throws Exception {
        game.totalLaps = laps;
        game.lapGates = new Line2D[]{game.finishLine,
                new Line2D.Double(30, 1, 30, 19), new Line2D.Double(50, 1, 50, 19)};
        set(game, "lapCrossGate", game.finishLine); set(game, "lapFwdX", 1.0);
    }

    static Object get(final Object object, final String name) throws Exception {
        final Field field = object.getClass().getDeclaredField(name);
        field.setAccessible(true); return field.get(object);
    }

    static void set(final Object object, final String name, final Object value) throws Exception {
        final Field field = object.getClass().getDeclaredField(name);
        field.setAccessible(true); field.set(object, value);
    }

    static void commit(final RaceGame game, final Direction direction) throws Exception {
        final Player player = game.players[game.subgamestate];
        final int[] p = player.getPosition(), v = player.getVelocity();
        final int[] nextV = {v[0] + direction.dx, v[1] + direction.dy};
        final Method commit = RaceGame.class.getDeclaredMethod("commitMove", int[].class, int[].class, int[].class);
        commit.setAccessible(true);
        commit.invoke(game, p, nextV, new int[]{p[0] + nextV[0], p[1] + nextV[1]});
    }

    static void check(final boolean condition, final String message) {
        if (!condition) throw new AssertionError(message);
    }
}
