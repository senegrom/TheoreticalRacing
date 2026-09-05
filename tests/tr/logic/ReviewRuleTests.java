package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Rectangle2D;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.List;
import java.util.Properties;
import tr.gui.RaceUI;

/** Direct rule contracts: race traces alone cannot certify a referee. */
final class ReviewRuleTests {
    private ReviewRuleTests() {}

    static void run() {
        testFinishRunUp();
        testIllegalFinishesCrash();
        testClippedWallIntersection();
        testQueryIsolationAndTransitions();
        testGateConvergence();
        System.out.println("ReviewRuleTests: OK");
    }

    private static RaceGame notch(final int tip) {
        final RaceGame game = new RaceGame(new Properties());
        game.gameCols = 70;
        game.gameRows = 30;
        game.track = new Track();
        game.track.addLeft(0, 20);
        if (tip >= 0) {
            game.track.addLeft(53, 20);
            game.track.addLeft(54, tip);
            game.track.addLeft(55, 20);
        }
        game.track.addLeft(61, 20);
        game.track.addRight(0, 0);
        game.track.addRight(60, 0);
        game.trackA = TrackGeometry.getToleranceExpandedShape(
                TrackGeometry.newPrefilledPath(game.track.getLeft(), game.track.getRight()));
        game.startZoneA = new Area();
        game.finishLine = new Line2D.Double(61, 20, 60, 0);
        set(game, "finishFwdX", 1.0);
        set(game, "finishFwdY", 0.0);
        game.players = new Player[] {
            new Player("A", 1, Color.RED, Player.Kind.AI1),
            new Player("B", 2, Color.BLUE, Player.Kind.AI2),
            new Player("C", 3, Color.GREEN, Player.Kind.AI1)
        };
        game.players[0].setPosition(new int[]{51, 5});
        game.players[0].setVelocity(new int[]{9, 0});
        game.players[1].setPosition(new int[]{10, 5});
        game.players[2].setPosition(new int[]{20, 5});
        return game;
    }

    private static void testFinishRunUp() {
        for (final int tip : new int[]{4, 1}) {
            final RaceGame game = notch(tip);
            check(game.crossesFinish(51, 5, 61, 5), "fixture does not cross finish");
            check(!game.trackA.contains(54, 5), "notch is not outside track");
            check(!game.finishRunUpLegal(51, 5, 61, 5), "wall notch was missed: " + tip);
            final RaceGame.MoveResult result = game.evaluateMove(game.players[0], new int[]{51, 5}, new int[]{61, 5});
            check(!result.legal() && !result.finishes(), "illegal approach earns finish");
            check(!game.crossesFinishLegally(51, 5, 61, 5), "AI finish shortcut ignores wall");
        }
        final RaceGame open = notch(-1);
        check(open.finishRunUpLegal(51, 5, 61, 5), "legal post-finish exit was rejected");
        check(open.evaluateMove(open.players[0], new int[]{51, 5}, new int[]{61, 5}).finishes(),
                "legal crossing must finish");
    }

    private static void testIllegalFinishesCrash() {
        for (final int tip : new int[]{4, 1}) {
            final RaceGame game = notch(tip);
            game.setAutoMode(true); // no dialogs; three cars prevent race-end System.exit
            set(game, "rui", new RaceUI(30, 70));
            set(game, "gamestate", GameState.PLAY);
            try {
                final Method commit = RaceGame.class.getDeclaredMethod("commitMove", int[].class, int[].class, int[].class);
                commit.setAccessible(true);
                commit.invoke(game, new int[]{51, 5}, new int[]{10, 0}, new int[]{61, 5});
            } catch (final ReflectiveOperationException error) {
                throw new AssertionError(error);
            }
            check(game.players[0].getFinishedPlace() == 3, "illegal finisher was not ranked as crashed");
            check((int) get(game, "finishedFirst") == 0, "finish counter was incremented");
            check(get(game, "gameLog").toString().contains("CRASH place=3"), "referee did not record CRASH");
        }
    }

    private static void testClippedWallIntersection() {
        check(TrackGeometry.segmentCrossesPathBefore(0, 0, 10, 0, .8,
                List.of(new int[]{3, -1}, new int[]{3, 1})), "interior wall missed");
        check(!TrackGeometry.segmentCrossesPathBefore(0, 0, 10, 0, .8,
                List.of(new int[]{8, -1}, new int[]{8, 1})), "wall at finish incorrectly checked");
        check(!TrackGeometry.segmentCrossesPathBefore(0, 0, 10, 0, .8,
                List.of(new int[]{9, -1}, new int[]{9, 1})), "post-finish wall checked");
        check(TrackGeometry.segmentCrossesPathBefore(0, 0, 10, 0, .8,
                List.of(new int[]{3, 0}, new int[]{4, 1})), "border vertex clip missed");
        check(TrackGeometry.segmentCrossesPathBefore(0, 0, 10, 0, .8,
                List.of(new int[]{3, 0}, new int[]{4, 0})), "collinear overlap missed");
    }

    private static RaceGame lapGame() {
        final RaceGame game = notch(-1);
        game.totalLaps = 3;
        game.trackA = new Area(new Rectangle2D.Double(0, 0, 70, 30));
        game.lapGates = new Line2D[]{new Line2D.Double(60, 0, 60, 20),
                new Line2D.Double(30, 0, 30, 20), new Line2D.Double(40, 0, 40, 20)};
        set(game, "lapCrossGate", game.lapGates[0]);
        set(game, "lapFwdX", 1.0);
        set(game, "lapFwdY", 0.0);
        return game;
    }

    private static void testQueryIsolationAndTransitions() {
        final RaceGame game = lapGame();
        final String rivals = ";10,5,0,0,0,0,1;20,5,0,0,0,0,1";
        MoveQueries.restoreBoard(game, "v2,0,0,3;59,5,1,0,0,2,0" + rivals);
        check(game.onFinalLap(1), "V2 did not restore final lap");
        String answer = MoveQueries.candidates(game, 0, true);
        check(answer.charAt(4) == 'F' && answer.contains("FINISH,2,0,0"), "final lap does not finish");
        MoveQueries.restoreBoard(game, "v2,0,0,3;59,5,1,0,0,0,0" + rivals);
        answer = MoveQueries.candidates(game, 0, true);
        check(answer.charAt(4) != 'F' && answer.contains("LAP,1,1,0"), "non-final lap terminates oracle race");
        MoveQueries.restoreBoard(game, "v2,0,0,3;59,5,1,0,0,2,1" + rivals);
        check(MoveQueries.candidates(game, 0, true).charAt(4) != 'F', "owed checkpoint ignored");
        MoveQueries.restoreBoard(game, "0;59,5,1,0,0;10,5,0,0,0;20,5,0,0,0");
        check(game.players[0].getLap() == 0 && game.players[0].getNextGate() == 1,
                "legacy query inherited lap or gate");
        final int[] before = game.players[0].lapState();
        try {
            MoveQueries.restoreBoard(game, "v2,0,0,3;59,5,1,0,0,2,0;10,5,0,0,0,0,7;20,5,0,0,0,0,1");
            throw new AssertionError("invalid gate accepted");
        } catch (final IllegalArgumentException expected) {
            check(Arrays.equals(before, game.players[0].lapState()), "invalid request partially mutated board");
        }
        MoveQueries.restoreBoard(game, "v2,0,6751,3;59,5,1,0,0,0,0" + rivals);
        check(MoveQueries.candidates(game, 0, true).startsWith("TTTTTTTTT;"), "referee timeout was not replayed");
        MoveQueries.restoreBoard(game, "0;59,5,1,0,0;10,5,0,0,0;20,5,0,0,0");
        check(!game.raceTurnLimitReached(), "legacy query inherited race turn count");
    }

    private static void testGateConvergence() {
        final int[][] maps = new int[3][];
        final int passes = GateFixedPoint.converge(maps,
                (gate, next) -> new int[]{next == null ? 20 : Math.max(0, next[0] - 1)}, Arrays::equals, 32);
        check(passes > 3 && maps[0][0] == 0 && maps[1][0] == 0 && maps[2][0] == 0,
                "three passes were incorrectly accepted as a fixed point");
        try {
            GateFixedPoint.converge(new int[3][],
                    (gate, next) -> new int[]{next == null ? 0 : 1 - next[0]}, Arrays::equals, 4);
            throw new AssertionError("oscillating gate maps were accepted");
        } catch (final IllegalStateException expected) {
            check(expected.getMessage().contains("did not converge"), "unclear convergence failure");
        }
    }

    private static void set(final Object target, final String name, final Object value) {
        try {
            final Field field = target.getClass().getDeclaredField(name);
            field.setAccessible(true);
            field.set(target, value);
        } catch (final ReflectiveOperationException error) {
            throw new AssertionError(error);
        }
    }

    private static Object get(final Object target, final String name) {
        try {
            final Field field = target.getClass().getDeclaredField(name);
            field.setAccessible(true);
            return field.get(target);
        } catch (final ReflectiveOperationException error) {
            throw new AssertionError(error);
        }
    }

    private static void check(final boolean condition, final String message) {
        if (!condition)
            throw new AssertionError(message);
    }
}
