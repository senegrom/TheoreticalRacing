package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.io.IOException;
import tr.gui.RaceUI;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Properties;
import java.util.Random;

/** Soundness contracts for exact last-rival racecraft, independent of AI scores. */
final class RaceAiTacticsTests {
    private static final Direction[] DIRECTIONS = Direction.values();
    private RaceAiTacticsTests() {}

    static void run() {
        testSlotOrderAndRetiredPlayers();
        testFinishAndNonFinalCrossings();
        testHumanReplyBeyondPlanningCap();
        testLiveRefereeClassification();
        testPhysicalReplyDomainAndImmutability();
        System.out.println("RaceAiTacticsTests: OK");
    }

    private static RaceGame hairpin() {
        final RaceGame g = new RaceGame(new Properties());
        g.gameCols = 80;
        g.gameRows = 30;
        g.track = new Track();
        for (final int[] p : new int[][]{{5,27},{3,14},{6,3},{74,3},{77,14},{75,27}})
            g.track.addLeft(p[0], p[1]);
        for (final int[] p : new int[][]{{18,27},{15,16},{19,12},{61,12},{65,16},{62,27}})
            g.track.addRight(p[0], p[1]);
        g.trackA = TrackGeometry.getToleranceExpandedShape(
                TrackGeometry.newPrefilledPath(g.track.getLeft(), g.track.getRight()));
        g.startZoneA = new Area();
        g.finishLine = new Line2D.Double(75,27,62,27);
        set(g, "finishFwdY", 1.0);
        g.players = new Player[]{car(1,16,12,3,0), car(2,15,14,5,-1)};
        return g;
    }

    private static Player car(final int number, final int x, final int y, final int vx, final int vy) {
        final Player p = new Player("P" + number, number, Color.BLUE, Player.Kind.AI1);
        p.setPosition(new int[]{x,y});
        p.setVelocity(new int[]{vx,vy});
        return p;
    }

    private static void testSlotOrderAndRetiredPlayers() {
        final RaceGame g = hairpin();
        check(RaceAiTactics.winNow(g, 1) == Direction.NONE, "missed sole-landing blockade");
        assertWin(g, 0, Direction.NONE);
        // Same physical situation across the last-slot -> first-slot boundary.
        g.players = new Player[]{car(1,15,14,5,-1), car(2,16,12,3,0)};
        g.subgamestate = 1;
        check(RaceAiTactics.winNow(g, 2) == Direction.NONE, "array wrap hid the next rival");
        assertWin(g, 1, Direction.NONE);
        final Player third = car(3,30,8,0,0);
        g.players = new Player[]{g.players[0],g.players[1],third};
        check(RaceAiTactics.winNow(g, 2) == null, "two-car proof used in a three-car field");
        third.setFinishedPlace(3);
        check(RaceAiTactics.winNow(g, 2) == Direction.NONE, "retired car hid the duel");
        final int[] oldPosition = g.players[1].getPosition();
        g.players[1].setPosition(new int[]{40,8});
        check(RaceAiTactics.winNow(g, 2) == null, "unreachable blocking cell accepted");
        g.players[1].setPosition(oldPosition);
        g.players[1].setFinishedPlace(2);
        check(RaceAiTactics.winNow(g, 2) == null, "retired mover allowed to play");
    }

    private static void testFinishAndNonFinalCrossings() {
        final RaceGame g = hairpin();
        g.lapGates = new Line2D[]{g.finishLine,
                new Line2D.Double(25,3,25,12), new Line2D.Double(55,3,55,12)};
        set(g, "lapCrossGate", g.finishLine);
        set(g, "lapFwdY", 1.0);
        g.totalLaps = 99;
        check(RaceAiTactics.winNow(g, 1) == Direction.NONE,
                "a proven knockout should not depend on the number of laps remaining");
        assertWin(g, 0, Direction.NONE);
        // A true finishing reply is un-blockable, including beyond the board.
        g.totalLaps = 1;
        g.players = new Player[]{car(1,70,23,0,0),car(2,70,26,0,5)};
        g.players[1].setNextGate(0);
        check(RaceAiTactics.winNow(g, 1) == null, "genuine rival finish treated as blockable");
        g.players = new Player[]{car(1,70,26,0,5),car(2,70,23,0,0)};
        g.players[0].setNextGate(0);
        final Direction finish = RaceAiTactics.winNow(g, 1);
        check(finish != null && result(g, g.players[0], finish, -1,-1).finishes(),
                "own immediate finish lost precedence");
        g.totalLaps = 99;
        check(RaceAiTactics.winNow(g, 1) == null, "non-final off-road crossing called a win");
        g.setQueryTurnCounter(99 * 750 * g.players.length + 1);
        check(RaceAiTactics.winNow(g, 1) == null, "timeout precedence ignored");
        // Passing CP2 and S/F together completes the race, even though gate != 0.
        g.setQueryTurnCounter(0);
        g.totalLaps = 1;
        g.lapGates[2] = new Line2D.Double(65,25,75,25);
        g.players = new Player[]{car(1,70,24,0,4),car(2,70,20,0,0)};
        g.players[0].setNextGate(2);
        final Direction combined = RaceAiTactics.winNow(g, 1);
        check(combined != null && result(g,g.players[0],combined,-1,-1).finishes(),
                "CP2 plus finish was mistaken for a continuing lap");
    }

    private static void testHumanReplyBeyondPlanningCap() {
        final RaceGame g = hairpin();
        g.players[0] = car(1,64,6,-3,5);
        final Player human = new Player("Human",2,Color.RED,Player.Kind.HUMAN);
        human.setPosition(new int[]{72,23});
        human.setVelocity(new int[]{-12,-12});
        g.players[1] = human;
        int bounded = 0, physical = 0;
        for (final Direction d : DIRECTIONS) {
            if (result(g,human,d,-1,-1).legal()) {
                physical++;
                if (!RaceGame.aiVelocityOutOfRange(-12+d.dx,-12+d.dy)) bounded++;
            }
        }
        check(bounded == 1 && physical == 3, "human speed-boundary fixture lost its extra replies");
        check(RaceAiTactics.winNow(g,1) == null,
                "planner cap invented a winning block against a human with two more replies");
    }

    private static void testLiveRefereeClassification() {
        for (final int mover : new int[]{0,1}) {
            final RaceGame g = hairpin();
            g.players[mover] = car(mover+1,15,22,2,2);
            g.players[1-mover] = car(2-mover,17,25,1,-2);
            g.subgamestate = mover;
            g.setAutoMode(true);
            g.setAutoRaceEndHook(() -> {}); // Never exit the test JVM on race end.
            set(g,"rui",new RaceUI(30,80));
            set(g,"gamestate",GameState.PLAY);
            Path directory = null;
            try {
                directory = Files.createTempDirectory("racecraft-referee-");
                final Path log = directory.resolve("race.log");
                g.setGameLogPath(log.toString());
                final Method commit = RaceGame.class.getDeclaredMethod("commitMove",
                        int[].class,int[].class,int[].class);
                commit.setAccessible(true);
                check(RaceAiTactics.winNow(g,mover+1) == Direction.NONE, "winning fixture changed");
                commit.invoke(g,new int[]{15,22},new int[]{2,2},new int[]{17,24});
                check(g.subgamestate == 1-mover, "wrong next active driver across array wrap");
                // Any of the opponent's nine actions crashes. Commit SW to
                // the occupied cell and verify actual referee classification.
                commit.invoke(g,new int[]{17,25},new int[]{0,-1},new int[]{17,24});
                check(g.players[mover].getFinishedPlace() == 1
                        && g.players[1-mover].getFinishedPlace() == 2,
                        "blockade did not secure the best remaining place");
                check(Files.readString(log).contains("# results\n"), "race did not end immediately");
            } catch (final ReflectiveOperationException | IOException error) {
                throw new AssertionError(error);
            } finally {
                if (directory != null) {
                    try {
                        Files.deleteIfExists(directory.resolve("race.log"));
                        Files.delete(directory);
                    } catch (final IOException error) {
                        throw new AssertionError(error);
                    }
                }
            }
        }
    }

    private static void testPhysicalReplyDomainAndImmutability() {
        final RaceGame g = hairpin();
        final ArrayList<int[]> cells = new ArrayList<>();
        for (int x = 3; x <= 77; x++)
            for (int y = 3; y <= 27; y++)
                if (g.trackA.contains(x,y))
                    cells.add(new int[]{x,y});
        final Random random = new Random(20260906L);
        int blocks = 0, finishes = 0;
        for (int trial = 0; trial < 12_000; trial++) {
            final Player p = g.players[0], r = g.players[1];
            r.setPosition(cells.get(random.nextInt(cells.size())).clone());
            // Deliberately exercise +/-12 and replies at +/-13: a planning
            // domain boundary is NOT a wall, especially against human drivers.
            r.setVelocity(new int[]{random.nextInt(25)-12,random.nextInt(25)-12});
            p.setPosition(cells.get(random.nextInt(cells.size())).clone());
            int tx = r.getPosition()[0] + r.getVelocity()[0];
            int ty = r.getPosition()[1] + r.getVelocity()[1];
            p.setVelocity(new int[]{Math.max(-12,Math.min(12,tx-p.getPosition()[0])),
                    Math.max(-12,Math.min(12,ty-p.getPosition()[1]))});
            if (Arrays.equals(p.getPosition(),r.getPosition()))
                continue;
            final int[][] before = {p.getPosition().clone(),p.getVelocity().clone(),p.lapState(),
                    r.getPosition().clone(),r.getVelocity().clone(),r.lapState()};
            final int clock = g.turnCount();
            final Direction d = RaceAiTactics.winNow(g,1);
            check(Arrays.deepEquals(before,new int[][]{p.getPosition(),p.getVelocity(),p.lapState(),
                    r.getPosition(),r.getVelocity(),r.lapState()}) && clock == g.turnCount(),
                    "tactical probe mutated the board");
            if (d != null) {
                assertWin(g,0,d);
                if (result(g,p,d,r.getPosition()[0],r.getPosition()[1]).finishes())
                    finishes++;
                else
                    blocks++;
            }
        }
        check(blocks > 0 && finishes > 0, "random soundness checks were vacuous");
    }

    /** Enumerate all nine rival accelerations through the actual referee. */
    private static void assertWin(final RaceGame g, final int mover, final Direction d) {
        final Player p = g.players[mover], r = g.players[1-mover];
        final int[] rp = r.getPosition();
        final RaceGame.MoveResult ours = result(g,p,d,rp[0],rp[1]);
        check(ours.legal(), "winning move itself crashes");
        if (ours.finishes())
            return;
        final int x = p.getPosition()[0]+p.getVelocity()[0]+d.dx;
        final int y = p.getPosition()[1]+p.getVelocity()[1]+d.dy;
        for (final Direction reply : DIRECTIONS)
            check(!result(g,r,reply,x,y).legal(), "rival has a legal reply to alleged knockout");
    }

    private static RaceGame.MoveResult result(final RaceGame g, final Player p,
            final Direction d, final int blockerX, final int blockerY) {
        final int[] x=p.getPosition(),v=p.getVelocity();
        final int nx=x[0]+v[0]+d.dx,ny=x[1]+v[1]+d.dy;
        return g.evaluateMove(p.getLap(),p.getNextGate(),x[0],x[1],nx,ny,
                nx==blockerX && ny==blockerY);
    }

    private static void set(final Object target, final String field, final Object value) {
        try {
            final Field f=RaceGame.class.getDeclaredField(field);
            f.setAccessible(true);
            f.set(target,value);
        } catch (final ReflectiveOperationException e) {
            throw new AssertionError(e);
        }
    }
    private static void check(final boolean value, final String message) {
        if (!value) throw new AssertionError(message);
    }
}
