package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Rectangle2D;
import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Properties;
import java.util.Random;
import tr.gui.RaceUI;

/** The owner's computed-start rule (2026-10-02, CLAUDE.md) against an
 *  independent forward-referee oracle. */
final class StartPlacementTests {
    private StartPlacementTests() {}
    static void run() {
        for (final boolean gated : new boolean[]{false, true}) testScoring(gated);
        testTerminalOccupancy();
        testOverBudget();
        System.out.println("StartPlacementTests: the computed-start rule (exact solo value from rest, taken cells"
                + " and nothing else, x-then-y and seeded ties, the first-checkpoint map over budget), shared"
                + " analysis, live occupancy and barriers OK");
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
    private static Object get(final Object object, final String name) {
        try {
            final Field field = object.getClass().getDeclaredField(name);
            field.setAccessible(true); return field.get(object);
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
    /** The exact solo value from rest: the fewest referee moves to the finish.
     *  With {@code firstMoveBlocked} the first move may not land on a placed
     *  car's cell -- the objective the owner's rule replaced, since those cars
     *  move first; it only proves the fixture exercises the difference. */
    private static int oracle(final RaceGame g, final int x, final int y, final boolean firstMoveBlocked) {
        final var queue = new ArrayDeque<Node>();
        final var seen = new HashSet<State>();
        queue.add(new Node(new State(x,y,0,0,0,1),0));
        while (!queue.isEmpty()) {
            final Node n = queue.remove(); final State s = n.state();
            for (final Direction d : Direction.values()) {
                final int vx = s.vx()+d.dx, vy = s.vy()+d.dy, nx = s.x()+vx, ny = s.y()+vy;
                if (RaceGame.aiVelocityOutOfRange(vx,vy)) continue;
                final boolean occupied = firstMoveBlocked && n.depth() == 0 && g.isCrashingPlayer(nx,ny,1);
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
    private static void testTerminalOccupancy() {
        final RaceGame g = corridor(false);
        g.finishLine = new Line2D.Double(5.5,0,5.5,4);
        g.reach.computeDistMap(); g.reach.computeReachability(); g.prepareOptimalStartMap();
        set(g.reach,"reachabilityReady",true);
        // Cars on all three landings beyond the finish: a free cell keeps its
        // value from rest whatever lands where, here an immediate finish.
        for (int i=1;i<=3;i++) g.players[i].setPosition(new int[]{6,i});
        check(StartPlacement.score(g,g.players[0],5,2)==1, "Cars beyond the finish blocked a legal immediate finish");
        g.players[1].setPosition(new int[]{5,2});
        check(StartPlacement.score(g,g.players[0],5,2)==Integer.MAX_VALUE, "Occupied starting cell accepted");
        g.players[1].setFinishedPlace(1);
        check(StartPlacement.score(g,g.players[0],5,2)==1, "Finished car still blocked a starting cell");
    }

    private static void testScoring(final boolean gated) {
        final RaceGame g = corridor(gated); final Player ai = g.players[0];
        try { StartPlacement.choose(g,ai,null); throw new AssertionError("Incomplete maps accepted"); }
        catch (final IllegalStateException expected) { /* Readiness barrier. */ }
        if (gated) g.prepareOptimalStartMap();
        else { g.reach.computeDistMap(); g.reach.computeReachability(); g.prepareOptimalStartMap(); }
        // This unit fixture prepares only the map used by scoring. Full worker
        // readiness and ordering are tested separately against real game startup.
        set(g.reach,"reachabilityReady",true);
        final StartPlacement.Analysis shared = g.preparedStartAnalysis();
        check(shared != null, "Shared start analysis was not prepared");
        g.prepareOptimalStartMap();
        check(shared == g.preparedStartAnalysis(), "Repeated preparation rebuilt the start analysis");
        final int[][] before = new int[6][4];
        int emptyBest = Integer.MAX_VALUE;
        for (int x=1;x<=5;x++) for (int y=1;y<=3;y++) {
            before[x][y] = StartPlacement.score(g,ai,x,y);
            check(before[x][y] == oracle(g,x,y,false), "Empty-field score is not the shortest referee route");
            emptyBest = Math.min(emptyBest, before[x][y]);
        }
        // Equally good cells go to the seed's draw, or without a seed to the first
        // in x-then-y order -- never to a replay of the race among them (the
        // owner rejected start-ties, 2026-10-02).
        final List<int[]> ties = new ArrayList<>();
        for (int x=1;x<=5;x++) for (int y=1;y<=3;y++) if (before[x][y] == emptyBest) ties.add(new int[]{x,y});
        check(ties.size() >= 2, "Fixture has no tie among its best cells");
        final int[] oldBest = StartPlacement.choose(g,ai,null);
        check(Arrays.equals(oldBest, ties.get(0)), "Without a seed the tie did not go to the first best cell in x-then-y order");
        for (long seed=0;seed<10;seed++)
            check(Arrays.equals(StartPlacement.choose(g,ai,seed),
                    ties.get(new Random(seed ^ ((long) ai.getNumber() << 32)).nextInt(ties.size()))),
                    "A seeded tie is not the seed's draw among the best cells");
        g.players[1].setPosition(oldBest.clone());
        g.players[2].setPosition(new int[]{5,2});
        g.players[3].setPosition(new int[]{5,3});
        int minimum = Integer.MAX_VALUE; boolean witnessed = false;
        for (int x=1;x<=5;x++) for (int y=1;y<=3;y++) {
            final int score = StartPlacement.score(g,ai,x,y);
            if (g.isCrashingPlayer(x,y,1)) check(score == Integer.MAX_VALUE, "Occupied start was accepted");
            else {
                // The earlier cars' cells are taken and nothing else about them
                // counts: they move first, so a free cell keeps its solo value.
                check(score == before[x][y], "Another car's cell changed a free cell's value");
                witnessed |= oracle(g,x,y,true) > score; minimum = Math.min(minimum,score);
            }
        }
        check(witnessed, "Fixture has no free cell whose best first landing another car holds");
        final int[][] positions = Arrays.stream(g.players).map(p -> p.getPosition().clone()).toArray(int[][]::new);
        for (long seed=0;seed<10;seed++) {
            final int[] selected = StartPlacement.choose(g,ai,seed);
            check(selected != null && !Arrays.equals(selected,oldBest), "Stale/occupied starting choice reused");
            check(StartPlacement.score(g,ai,selected[0],selected[1]) == minimum, "Tie seed selected a worse-scored start");
            check(Arrays.equals(selected,StartPlacement.choose(g,ai,seed)), "Selection mutated its tie stream");
        }
        check(Arrays.deepEquals(positions,Arrays.stream(g.players).map(Player::getPosition).toArray(int[][]::new)), "Scoring mutated players");
        // Every identity gets the same static analysis, but freshly filtered
        // scores. A finished body is ignored just as it is by the live referee.
        for (final Player player : g.players) {
            final int[] selected = StartPlacement.choose(g, player, 3L);
            check(selected != null && g.preparedStartAnalysis() == shared, "Analysis copied for another AI");
            check(StartPlacement.score(g, player, selected[0], selected[1]) != Integer.MAX_VALUE,
                    "Candidate came from another player's occupancy mask");
        }
        for (int i = 1; i < g.players.length; i++)
            g.players[i].setPosition(new int[]{Player.INIT_POS,Player.INIT_POS});
        check(Arrays.equals(oldBest, StartPlacement.choose(g,ai,null)), "Undo left cells permanently taken");
        check(shared == g.preparedStartAnalysis(), "Undo rebuilt shared geometry analysis");
        // Results are defensive values, never mutable coordinates in the table.
        final int[] mutable = StartPlacement.choose(g,ai,null); mutable[0] = -100;
        check(Arrays.equals(oldBest, StartPlacement.choose(g,ai,null)), "Caller corrupted the shared table");
        for (final int[] invalid : new int[][]{{-1,1},{1,-1},{11,1},{1,5},{Integer.MAX_VALUE,1},{0,0}})
            check(StartPlacement.score(g,ai,invalid[0],invalid[1]) == Integer.MAX_VALUE, "Invalid start admitted");
        // The production cache builder ignores even an occupied complete start
        // zone. Sharing must never bake the first player's occupancy into it.
        g.players[1].setPosition(oldBest.clone());
        final StartPlacement.Analysis withBodyPresent = StartPlacement.prepare(g);
        g.players[1].setPosition(new int[]{Player.INIT_POS,Player.INIT_POS});
        set(g,"startPlacementAnalysis",withBodyPresent);
        check(Arrays.equals(oldBest,StartPlacement.choose(g,ai,null)), "Live body contaminated base analysis");
        set(g,"startPlacementAnalysis",null);
        try { StartPlacement.choose(g,ai,null); throw new AssertionError("Missing start analysis accepted"); }
        catch (final IllegalStateException expected) { /* Full-analysis barrier, not random fallback. */ }
        set(g,"startPlacementAnalysis",shared);
        ai.setVelocity(new int[]{1,0});
        try { StartPlacement.choose(g,ai,null); throw new AssertionError("Reused starting analysis for a moving player"); }
        catch (final IllegalStateException expected) { /* This table is only for fresh starts. */ }
        ai.setVelocity(new int[]{0,0});
    }

    /** Over budget the start is still computed (the owner, 2026-10-02): by the
     *  next best map, the exact distance to the first checkpoint, which the
     *  cars then race by -- on the two-lap Circle with the exact map capped. */
    private static void testOverBudget() {
        final String cap = System.getProperty("tr.optimalBuildBytes");
        RaceGame.clearOptimalMemoForTests();
        System.setProperty("tr.optimalBuildBytes", "0");
        try {
            final RaceGame g = circle();
            check(g.preparedStartPotential() == null, "The capped fixture built the exact map");
            check(g.preparedStartAnalysis() != null, "Over budget no start was computed");
            final Player ai = g.players[0];
            final Rectangle2D bounds = g.startZoneA.getBounds2D();
            int best = Integer.MAX_VALUE, cells = 0;
            int[] first = null;
            for (int x = (int) Math.floor(bounds.getMinX()); x <= (int) Math.ceil(bounds.getMaxX()); x++)
                for (int y = (int) Math.floor(bounds.getMinY()); y <= (int) Math.ceil(bounds.getMaxY()); y++) {
                    if (!g.startZoneA.contains(x, y)) continue;
                    cells++;
                    final int value = g.reach.turnsToGate(1, x, y, 0, 0);
                    check(StartPlacement.score(g, ai, x, y) == value,
                            "Over budget a cell's score is not its distance to the first checkpoint from rest");
                    if (value < best) { best = value; first = new int[]{x, y}; }
                }
            check(cells > 1 && best != Integer.MAX_VALUE, "The Circle's grid does not reach its first checkpoint");
            check(Arrays.equals(StartPlacement.choose(g, ai, null), first), "Over budget the AI did not take a best cell");
            final Method log = RaceGame.class.getDeclaredMethod("initGameLog");
            log.setAccessible(true); log.invoke(g);
            check(get(g, "gameLog").toString().contains("# start-placement informed (first-checkpoint map"),
                    "The log does not say the start was computed on the first-checkpoint map");
        } catch (final ReflectiveOperationException | IOException e) {
            throw new AssertionError(e);
        } finally {
            if (cap == null) System.clearProperty("tr.optimalBuildBytes");
            else System.setProperty("tr.optimalBuildBytes", cap);
            RaceGame.clearOptimalMemoForTests();
        }
    }

    /** The Circle from the checkout, two laps, its real geometry and maps. */
    private static RaceGame circle() throws IOException, ReflectiveOperationException {
        final Properties p = new Properties();
        try (InputStream in = Files.newInputStream(Path.of("tracks/circle.track"))) { p.load(in); }
        p.setProperty("laps", "2");
        p.setProperty("lastTrackLeft", p.getProperty("trackLeft"));
        p.setProperty("lastTrackRight", p.getProperty("trackRight"));
        final TrackIO.TrackData data = TrackIO.loadLastTrackData(p);
        check(data != null, "invalid Circle fixture");
        final RaceGame g = new RaceGame(p);
        g.totalLaps = 2; g.gameCols = data.gameX(); g.gameRows = data.gameY();
        g.track = new Track();
        for (final int[] xy : data.left()) g.track.addLeft(xy[0], xy[1]);
        for (final int[] xy : data.right()) g.track.addRight(xy[0], xy[1]);
        set(g, "rui", new RaceUI(g.gameRows, g.gameCols));
        g.players = new Player[]{new Player("A", 1, Color.BLUE, Player.Kind.AI1),
                new Player("B", 2, Color.RED, Player.Kind.AI2)};
        final Method build = RaceGame.class.getDeclaredMethod("buildTrackGeometry");
        build.setAccessible(true); build.invoke(g);
        g.reach.ensureReachabilityReady();
        return g;
    }
}
