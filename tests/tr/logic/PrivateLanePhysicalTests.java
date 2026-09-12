package tr.logic;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Properties;
import java.util.Set;
import tr.gui.RaceUI;
import static tr.logic.LifecycleTestSupport.*;

/** Independent physical-reply enumeration checks the targeted private-lane oracle. */
public final class PrivateLanePhysicalTests {
    private PrivateLanePhysicalTests() {}

    private record State(int x, int y, int vx, int vy, int lap, int gate) {}

    private static Object occupancy(final RaceGame game, final int budget) throws Exception {
        final Object proof = new RaceAiPrivateLane(game).begin(1, 5, budget);
        final Object rectangles = get(proof, "rectangles");
        final Class<?> type = Class.forName("tr.logic.RaceAiPrivateLane$ExactRivalReach");
        final Constructor<?> constructor = type.getDeclaredConstructor(RaceGame.class,
                Reachability.class, int.class, rectangles.getClass(), int.class);
        constructor.setAccessible(true);
        return constructor.newInstance(game, game.reach, 1, rectangles, budget);
    }

    private static boolean may(final Object oracle, final int ply, final int x, final int y) throws Exception {
        final Method method = oracle.getClass().getDeclaredMethod("mayOccupy", int.class, int.class, int.class);
        method.setAccessible(true); return (boolean) method.invoke(oracle, ply, x, y);
    }

    private static void speedAndCertificate() throws Exception {
        final RaceGame game = straight(180, car(1,10,10,11,0), car(2,20,10,12,0), car(3,16,10,12,0));
        game.reach.computeDistMap(); game.reach.computeReachability();
        final RaceAiPrivateLane.ProofSession proof = new RaceAiPrivateLane(game).begin(1,5,512);
        final int turns = game.reach.turnsToFinish(21,10,11,0);
        check(game.evaluateMove(0,0,20,10,33,10,false).legal(), "speed-13 reply must be legal");
        check(may(occupancy(game,512),1,33,10), "speed-13 physical reply dropped");
        check(!proof.certifiesApproximate(21,10,11,0,turns,3,3), "fixture has a rectangle certificate");
        check(!proof.certifiesExact(21,10,11,0,turns,4,3), "false private-lane certificate survived");
        // Both signs and speeds already outside the planner's packed range.
        for (final int v : new int[]{-44,-13,-12,12,13,44}) {
            game.players = new Player[]{car(1,5,5,0,0),car(2,85,10,v,0)};
            final int x = 85 + v + Integer.signum(v);
            check(may(occupancy(game,512),1,x,10), "physical velocity encoded incorrectly: " + v);
        }
    }

    private static void progressAndBudget() throws Exception {
        final RaceGame game = straight(80,car(1,5,5,0,0),car(2,71,10,1,0));
        laps(game,2); game.players[1].setNextGate(0);
        game.trackA = new java.awt.geom.Area(new java.awt.geom.Rectangle2D.Double(0,1,79,18));
        final RaceGame.MoveResult lap = game.evaluateMove(0,0,71,10,73,10,false);
        check(lap.legal() && lap.lapCross() && !lap.finishes(), "not an ordinary lap crossing");
        check(may(occupancy(game,512),1,73,10), "ordinary lap crossing lost its live body");
        game.players[1].restoreLapState(new int[]{1,0,0,0,0,0});
        check(!may(occupancy(game,512),1,73,10), "actual final finish retained a live body");
        game.players[1].setNextGate(1);
        check(may(occupancy(game,512),1,73,10), "owed checkpoint was treated as a finish");
        game.players[1] = car(2,29,10,44,0); game.players[1].setNextGate(1);
        final RaceGame.MoveResult combined = game.evaluateMove(0,1,29,10,73,10,false);
        check(combined.passCp1() && combined.passCp2() && combined.lapCross() && !combined.finishes(),
                "combined checkpoint/lap fixture malformed");
        check(may(occupancy(game,512),1,73,10), "combined nonterminal event lost rival");
        // Same coordinates/velocity but different lap progress must not merge.
        final Player terminal = car(2,71,10,1,0), continuing = car(3,71,10,1,0);
        terminal.restoreLapState(new int[]{1,0,0,0,0,0}); continuing.setNextGate(0);
        game.players = new Player[]{game.players[0],terminal,continuing};
        check(may(occupancy(game,512),1,73,10), "progress-distinct rivals merged");
        final Object exhausted = occupancy(game,0);
        check(may(exhausted,1,73,10), "budget exhaustion became proof of absence");
        check(!may(exhausted,1,5,5), "rectangle exclusion lost with empty budget");
    }

    private static void bundledCircle() throws Exception {
        final Properties data = new Properties();
        try (var in = Files.newInputStream(Path.of("tracks/circle.track"))) { data.load(in); }
        final RaceGame game = new RaceGame(new Properties());
        game.totalLaps = 2;
        game.gameCols = Integer.parseInt(data.getProperty("gameX"));
        game.gameRows = Integer.parseInt(data.getProperty("gameY"));
        game.track = new Track();
        for (final int[] p : TrackIO.parsePointList(data.getProperty("trackLeft"))) game.track.addLeft(p[0],p[1]);
        for (final int[] p : TrackIO.parsePointList(data.getProperty("trackRight"))) game.track.addRight(p[0],p[1]);
        set(game,"rui",new RaceUI(game.gameRows,game.gameCols));
        game.players = new Player[]{car(1,80,50,0,0),car(2,50,8,1,0)};
        game.players[1].setNextGate(0);
        final Method build = RaceGame.class.getDeclaredMethod("buildTrackGeometry");
        build.setAccessible(true); build.invoke(game);
        game.reach.aliveW = game.gameCols + 1; game.reach.aliveH = game.gameRows + 1;
        game.reach.aliveVMAX = 12; game.reach.aliveSpan = 25;
        check(may(occupancy(game,512),1,52,8), "bundled Circle lap seam dropped rival");
    }

    private static void enumeratePhysicalReplies() throws Exception {
        final RaceGame game = straight(180,car(1,5,5,0,0),car(2,80,10,0,0));
        laps(game,2);
        int checked = 0;
        for (final int velocity : new int[]{-14,-12,0,12,14}) {
            final Player rival = car(2,80,10,velocity,0);
            rival.setNextGate(1); game.players[1] = rival;
            final Object oracle = occupancy(game,100_000);
            Set<State> frontier = Set.of(new State(80,10,velocity,0,0,1));
            for (int ply=1; ply<=3; ply++) {
                final Set<State> next = new HashSet<>();
                final Set<String> cells = new HashSet<>();
                for (final State s : frontier) for (final Direction d : Direction.values()) {
                    final int vx=s.vx()+d.dx, vy=s.vy()+d.dy, x=s.x()+vx, y=s.y()+vy;
                    final RaceGame.MoveResult move=game.evaluateMove(s.lap(),s.gate(),s.x(),s.y(),x,y,false);
                    if (move.legal() && !move.finishes()) {
                        next.add(new State(x,y,vx,vy,move.lapAfter(),move.gateAfter()));
                        cells.add(x+","+y);
                    }
                }
                for (final String cell : cells) {
                    final String[] xy=cell.split(",");
                    check(may(oracle,ply,Integer.parseInt(xy[0]),Integer.parseInt(xy[1])),
                            "reachable cell rejected at ply " + ply + ": " + cell);
                    checked++;
                }
                frontier=next;
            }
        }
        System.out.println("Private-lane independent physical occupancy checks: " + checked);
    }

    public static void main(final String[] args) throws Exception {
        speedAndCertificate(); progressAndBudget(); bundledCircle(); enumeratePhysicalReplies();
        System.out.println("PrivateLanePhysicalTests: physical speeds, lap/checkpoint state and fail-closed budgets OK");
    }
}
