package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Rectangle2D;
import java.lang.reflect.Field;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Properties;

/** Independent forward-referee oracle for the computed-start scoring objective. */
final class StartPlacementTests {
    private StartPlacementTests() {}
    static void run() {
        for (final boolean gated : new boolean[]{false, true}) testScoring(gated);
        System.out.println("StartPlacementTests: exact solo/first-occupancy scoring, barriers and tie determinism OK");
    }
    private static void check(final boolean ok, final String message) {
        if (!ok) throw new AssertionError(message);
    }
    private static void set(final Object object, final String name, final Object value) {
        try {
            final Field field = object.getClass().getDeclaredField(name);
            field.setAccessible(true); field.set(object, value);
        } catch (final ReflectiveOperationException e) { throw new AssertionError(e); }
    }
    private static RaceGame corridor(final boolean gated) {
        final RaceGame g = new RaceGame(new Properties());
        g.gameCols = 10; g.gameRows = 4; g.totalLaps = 1;
        g.track = new Track();
        g.track.addLeft(0,0); g.track.addLeft(10,0);
        g.track.addRight(0,4); g.track.addRight(10,4);
        g.trackA = TrackGeometry.getToleranceExpandedShape(new Rectangle2D.Double(0,0,10,4));
        g.startZoneA = new Area(new Rectangle2D.Double(.5,.5,5,3));
        g.finishLine = new Line2D.Double(9,0,9,4);
        set(g, "finishFwdX", 1.0); set(g, "finishFwdY", 0.0);
        g.players = new Player[]{new Player("AI",1,Color.BLUE,Player.Kind.AI1),
                new Player("B",2,Color.RED,Player.Kind.HUMAN),
                new Player("C",3,Color.GREEN,Player.Kind.AI2),
                new Player("D",4,Color.BLACK,Player.Kind.AI1)};
        if (gated) {
            g.lapGates = new Line2D[]{g.finishLine, new Line2D.Double(6,0,6,4), new Line2D.Double(8,0,8,4)};
            set(g, "lapCrossGate", new Line2D.Double(9,.3,9,3.7));
            set(g, "lapFwdX", 1.0); set(g, "lapFwdY", 0.0);
        }
        return g;
    }
    private record State(int x, int y, int vx, int vy, int lap, int gate) {}
    private record Node(State state, int depth) {}
    /** Current bodies constrain the first move only; later moves use the solo
     * model, matching the documented objective rather than inventing rival moves. */
    private static int oracle(final RaceGame g, final int x, final int y) {
        final var queue = new ArrayDeque<Node>();
        final var seen = new HashSet<State>();
        queue.add(new Node(new State(x,y,0,0,0,1),0));
        while (!queue.isEmpty()) {
            final Node n = queue.remove(); final State s = n.state();
            for (final Direction d : Direction.values()) {
                final int vx = s.vx()+d.dx, vy = s.vy()+d.dy, nx = s.x()+vx, ny = s.y()+vy;
                if (RaceGame.aiVelocityOutOfRange(vx,vy)) continue;
                final boolean occupied = n.depth() == 0 && g.isCrashingPlayer(nx,ny,1);
                final RaceGame.MoveResult result = g.evaluateMove(s.lap(),s.gate(),s.x(),s.y(),nx,ny,occupied);
                if (!result.legal()) continue;
                if (result.finishes()) return n.depth()+1;
                if (nx<0 || ny<0 || nx>g.gameCols || ny>g.gameRows) continue;
                final State next = new State(nx,ny,vx,vy,result.lapAfter(),result.gateAfter());
                if (seen.add(next)) queue.add(new Node(next,n.depth()+1));
            }
        }
        return Integer.MAX_VALUE;
    }
    private static void testScoring(final boolean gated) {
        final RaceGame g = corridor(gated); final Player ai = g.players[0];
        try { StartPlacement.choose(g,ai,null); throw new AssertionError("Incomplete maps accepted"); }
        catch (final IllegalStateException expected) { /* Readiness barrier. */ }
        if (gated) g.prepareOptimalStartMap();
        else { g.reach.computeDistMap(); g.reach.computeReachability(); }
        // This unit fixture prepares only the map used by scoring. Full worker
        // readiness and ordering are tested separately against real game startup.
        set(g.reach,"reachabilityReady",true);
        final int[][] before = new int[6][4];
        for (int x=1;x<=5;x++) for (int y=1;y<=3;y++) {
            before[x][y] = StartPlacement.score(g,ai,x,y);
            check(before[x][y] == oracle(g,x,y), "Empty-field score is not the shortest referee route");
        }
        final int[] oldBest = StartPlacement.choose(g,ai,null);
        check(oldBest != null, "No reachable fixture start");
        g.players[1].setPosition(oldBest.clone());
        g.players[2].setPosition(new int[]{5,2});
        g.players[3].setPosition(new int[]{5,3});
        int minimum = Integer.MAX_VALUE; boolean blockedFirstMove = false;
        for (int x=1;x<=5;x++) for (int y=1;y<=3;y++) {
            final int score = StartPlacement.score(g,ai,x,y);
            if (g.isCrashingPlayer(x,y,1)) check(score == Integer.MAX_VALUE, "Occupied start was accepted");
            else {
                check(score == oracle(g,x,y), "First-step occupancy score differs from independent BFS");
                blockedFirstMove |= score > before[x][y]; minimum = Math.min(minimum,score);
            }
        }
        check(blockedFirstMove, "Fixture did not exercise a blocked first landing");
        final int[][] positions = Arrays.stream(g.players).map(p -> p.getPosition().clone()).toArray(int[][]::new);
        for (long seed=0;seed<10;seed++) {
            final int[] selected = StartPlacement.choose(g,ai,seed);
            check(selected != null && !Arrays.equals(selected,oldBest), "Stale/occupied starting choice reused");
            check(StartPlacement.score(g,ai,selected[0],selected[1]) == minimum, "Tie seed selected a worse-scored start");
            check(Arrays.equals(selected,StartPlacement.choose(g,ai,seed)), "Selection mutated its tie stream");
        }
        check(Arrays.deepEquals(positions,Arrays.stream(g.players).map(Player::getPosition).toArray(int[][]::new)), "Scoring mutated players");
        if (gated) {
            set(g,"startPotential",null);
            try { StartPlacement.choose(g,ai,null); throw new AssertionError("Missing exact map silently fell back"); }
            catch (final IllegalStateException expected) { /* No random fallback. */ }
        }
    }
}
