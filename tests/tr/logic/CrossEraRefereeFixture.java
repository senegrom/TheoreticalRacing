package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.Properties;
import tr.gui.RaceUI;

/** Inject geometric outcomes into the real referee to audit external classification.
 * Source positions are controlled before each move; this tests retirement and
 * turn ordering, not a particular policy or a physically continuous race. */
public final class CrossEraRefereeFixture {
    private CrossEraRefereeFixture() {}

    private static void set(final Object target, final String name, final Object value) throws Exception {
        final Field field = target.getClass().getDeclaredField(name);
        field.setAccessible(true);
        field.set(target, value);
    }

    public static void main(final String[] args) throws Exception {
        final Path directory = Files.createTempDirectory("cross-era-referee-");
        final Path log = directory.resolve("race.log");
        final RaceGame game = new RaceGame(new Properties());
        game.setAutoMode(true);
        game.setAutoRaceEndHook(() -> {});
        game.setGameLogPath(log.toString());
        game.gameCols = 10;
        game.gameRows = 10;
        game.track = new Track();
        game.track.addLeft(0, 10);
        game.track.addLeft(10, 10);
        game.track.addRight(0, 0);
        game.track.addRight(10, 0);
        game.trackA = TrackGeometry.getToleranceExpandedShape(
                TrackGeometry.newPrefilledPath(game.track.getLeft(), game.track.getRight()));
        game.startZoneA = new Area();
        game.finishLine = new Line2D.Double(10, 10, 10, 0);
        set(game, "finishFwdX", 1.0);
        set(game, "finishFwdY", 0.0);
        set(game, "rui", new RaceUI(10, 10));
        set(game, "gamestate", GameState.PLAY);
        game.players = new Player[8];
        for (int i = 0; i < 8; i++) {
            final Player p = new Player("Player " + (i + 1), i + 1, Color.BLUE, Player.Kind.AI2);
            p.setPosition(new int[]{i + 1, 5});
            game.players[i] = p;
        }
        final Method commit = RaceGame.class.getDeclaredMethod("commitMove", int[].class, int[].class, int[].class);
        commit.setAccessible(true);
        for (final char outcome : args[0].toCharArray()) {
            if (Arrays.stream(game.players).allMatch(Player::isFinished)) break;
            final int i = game.subgamestate;
            final Player player = game.players[i];
            final int[] pos = outcome == 'F' ? new int[]{9, i + 1}
                    : outcome == 'X' ? new int[]{i + 1, 0} : new int[]{i + 1, 5};
            final int[] vel = outcome == 'F' ? new int[]{1, 0}
                    : outcome == 'X' ? new int[]{0, -1} : new int[]{0, 0};
            player.setPosition(pos);
            player.setVelocity(new int[]{0, 0});
            commit.invoke(game, pos, vel, new int[]{pos[0] + vel[0], pos[1] + vel[1]});
        }
        System.out.println("CLASSIFICATION=" + Arrays.toString(
                Arrays.stream(game.players).mapToInt(Player::getFinishedPlace).toArray()));
        System.out.println("COMMITTED_TURNS=" + game.turnCount());
        Files.deleteIfExists(log);
        Files.deleteIfExists(directory);
        System.exit(0);
    }
}
