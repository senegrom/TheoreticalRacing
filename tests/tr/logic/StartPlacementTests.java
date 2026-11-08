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
import java.util.SplittableRandom;
import tr.gui.RaceUI;

/** The owner's computed-start rule (2026-10-02, CLAUDE.md; later placements
 *  2026-11-01, round 339; earlier launches 2026-11-04, round 342) against
 *  independent forward-referee oracles. */
final class StartPlacementTests {
    private StartPlacementTests() {}
    static void run() {
        for (final boolean gated : new boolean[]{false, true}) testScoring(gated);
        for (final boolean gated : new boolean[]{false, true}) testLaunchExposure(gated);
        for (final boolean gated : new boolean[]{false, true}) testEarlierLaunches(gated);
        testFinishingLaunch();
        testTerminalOccupancy();
        testOverBudget();
        testDraw();
        System.out.println("StartPlacementTests: the computed-start rule (exact solo value from rest, taken cells"
                + " refused, x-then-y and seeded ties, the first-checkpoint map over budget), shared"
                + " analysis, live occupancy and barriers, and the least exposed launch with the earlier cars'"
                + " launches held OK");
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
    /** The fewest referee moves to the finish from any state, alone. */
    private static int fromState(final RaceGame g, final State start) {
        final var queue = new ArrayDeque<Node>();
        final var seen = new HashSet<State>();
        queue.add(new Node(start,0)); seen.add(start);
        while (!queue.isEmpty()) {
            final Node n = queue.remove(); final State s = n.state();
            for (final Direction d : Direction.values()) {
                final int vx = s.vx()+d.dx, vy = s.vy()+d.dy, nx = s.x()+vx, ny = s.y()+vy;
                if (RaceGame.aiVelocityOutOfRange(vx,vy)) continue;
                final RaceGame.MoveResult result = g.evaluateMove(s.lap(),s.gate(),s.x(),s.y(),nx,ny,false);
                if (!result.legal()) continue;
                if (result.finishes()) return n.depth()+1;
                if (nx<0 || ny<0 || nx>g.gameCols || ny>g.gameRows) continue;
                final State next = new State(nx,ny,vx,vy,result.lapAfter(),result.gateAfter());
                if (seen.add(next)) queue.add(new Node(next,n.depth()+1));
            }
        }
        return Integer.MAX_VALUE;
    }
    /** The launch by brute force: the landings of the first moves from rest
     *  that achieve the cell's referee value without finishing. */
    private static List<int[]> fastestLandings(final RaceGame g, final int x, final int y) {
        final int value = oracle(g,x,y,false);
        final List<int[]> landings = new ArrayList<>();
        for (final Direction d : Direction.values()) {
            final int nx = x+d.dx, ny = y+d.dy;
            final RaceGame.MoveResult result = g.evaluateMove(0,1,x,y,nx,ny,false);
            if (!result.legal() || result.finishes()) continue;
            final int rest = fromState(g, new State(nx,ny,d.dx,d.dy,result.lapAfter(),result.gateAfter()));
            if (rest != Integer.MAX_VALUE && rest+1 == value) landings.add(new int[]{nx,ny});
        }
        return landings;
    }
    /** Independent launch exposure for car {@code number}: how many fastest
     *  landings are starting cells no other car holds (0 none, 2 all, else 1). */
    private static int exposureOracle(final RaceGame g, final int x, final int y, final int number) {
        final List<int[]> landings = fastestLandings(g,x,y);
        int exposed = 0;
        for (final int[] l : landings) if (g.startZoneA.contains(l[0],l[1]) && !g.isCrashingPlayer(l[0],l[1],number)) exposed++;
        return exposed == 0 ? 0 : exposed < landings.size() ? 1 : 2;
    }

    /** Round 339 (the owner, 2026-11-01): a car also considers where the cars
     *  after it may place. Any free starting cell may be taken by a later car,
     *  which still stands there when this one first moves, so among its best cells
     *  every car with a car after it keeps the least exposed launch; which cell a
     *  later car takes is never predicted. Round 342 (the owner, 2026-11-04): a
     *  launch is also exposed where it lands on a landing of an earlier car's
     *  fastest first moves, which that car may stand on (C+). Four computer cars,
     *  against the independent referee oracles. */
    private static void testLaunchExposure(final boolean gated) {
        final RaceGame g = corridor(gated);
        g.players[1] = new Player("B",2,Color.RED,Player.Kind.AI1);
        if (gated) g.prepareOptimalStartMap();
        else { g.reach.computeDistMap(); g.reach.computeReachability(); g.prepareOptimalStartMap(); }
        set(g.reach,"reachabilityReady",true);
        final Player ai = g.players[0], second = g.players[1], third = g.players[2], last = g.players[3];
        final int[][] alone = new int[6][4];
        int best = Integer.MAX_VALUE;
        for (int x=1;x<=5;x++) for (int y=1;y<=3;y++) {
            alone[x][y] = StartPlacement.exposure(g,ai,x,y);
            check(alone[x][y] == exposureOracle(g,x,y,1), "Launch exposure is not the referee's");
            best = Math.min(best, StartPlacement.score(g,ai,x,y));
        }
        check(StartPlacement.exposure(g,ai,6,1) == Integer.MAX_VALUE, "A cell off the grid has a launch exposure");
        final List<int[]> ties = new ArrayList<>(), pool = new ArrayList<>();
        int least = Integer.MAX_VALUE;
        for (int x=1;x<=5;x++) for (int y=1;y<=3;y++) if (StartPlacement.score(g,ai,x,y) == best) {
            ties.add(new int[]{x,y}); least = Math.min(least, alone[x][y]);
        }
        for (final int[] c : ties) if (alone[c[0]][c[1]] == least) pool.add(c);
        // The boxed launch. The first best cell, (3,1), was the rule's pick before
        // round 339: both its fastest first moves land on free starting cells,
        // (4,1) and (4,2), so two of the three cars placing after it can box it,
        // and it loses a move. The car takes (5,1), whose fastest first moves leave
        // the grid, where no car can place.
        final int[] old = ties.get(0), now = StartPlacement.choose(g,ai,null);
        check(Arrays.equals(old,new int[]{3,1}), "The first best cell is not (3,1)");
        check(Arrays.equals(now,pool.get(0)) && Arrays.equals(now,new int[]{5,1}),
                "Without a seed the car did not take the first least exposed best cell");
        check(alone[old[0]][old[1]] == 2 && least == 0, "Fixture has no boxed launch beside an unexposed one");
        final List<int[]> box = fastestLandings(g,old[0],old[1]);
        check(box.size() == 2, "The first best cell does not launch onto exactly two starting cells");
        for (int i=0;i<box.size();i++) g.players[i+1].setPosition(box.get(i).clone());
        check(oracle(g,old[0],old[1],true) > best, "The later cars did not box the first best cell");
        check(oracle(g,now[0],now[1],true) == best, "The later cars boxed the car's start");
        final List<int[]> launch = fastestLandings(g,now[0],now[1]);
        check(!launch.isEmpty(), "The car's start has no launch");
        for (final int[] landing : launch)
            check(!g.startZoneA.contains(landing[0],landing[1]), "A later placement could close the car's launch");
        for (int i=1;i<g.players.length;i++) g.players[i].setPosition(new int[]{Player.INIT_POS,Player.INIT_POS});
        // Equally good cells -- the same value and exposure -- go to the seed's draw.
        // Every car with a car after it draws among its least exposed best cells;
        // the last car to place keeps all its best cells.
        for (long seed=0;seed<10;seed++) {
            for (final Player car : new Player[]{ai, second, third})
                check(Arrays.equals(StartPlacement.choose(g,car,seed),
                        pool.get(drawOracle(seed, car.getNumber(), pool.size()))),
                        "A seeded car with a car after it is not the seed's draw among its least exposed best cells");
            check(Arrays.equals(StartPlacement.choose(g,last,seed),
                    ties.get(drawOracle(seed, last.getNumber(), ties.size()))),
                    "The last car to place weighed placements no car will make");
        }
        // An earlier car's cell is not free: that car moves first and leaves it. With
        // the first two cars on (5,1) and (5,2), the launch from (4,1) lands only on
        // their cells, so the car in slot 3 takes it, where the first best free cell
        // is (3,1). Round 342: those cars may stand where their fastest first moves
        // land, (6,1), (6,2) and (6,3), so (5,3), whose launch onto (6,2) and (6,3) no
        // later placement can block, is exposed in full: seeded too, the car takes
        // (4,1), where round 339's rule drew between (4,1) and (5,3).
        ai.setPosition(new int[]{5,1}); second.setPosition(new int[]{5,2});
        final List<int[]> earlier = new ArrayList<>(fastestLandings(g,5,1));
        earlier.addAll(fastestLandings(g,5,2));
        boolean cleared = false;
        final List<int[]> free = new ArrayList<>(), kept = new ArrayList<>(), kept339 = new ArrayList<>();
        int tier = Integer.MAX_VALUE, tier339 = Integer.MAX_VALUE;
        for (int x=1;x<=5;x++) for (int y=1;y<=3;y++) {
            if (g.isCrashingPlayer(x,y,3)) continue;
            final int exposure = StartPlacement.exposure(g,third,x,y), plus = plusOracle(g,x,y,3,earlier);
            check(exposure == exposureOracle(g,x,y,3), "Launch exposure is not the referee's beside earlier cars");
            check(StartPlacement.exposurePlus(g,third,x,y) == plus, "C+ exposure is not the referee's beside earlier cars");
            cleared |= exposure < alone[x][y];
            if (StartPlacement.score(g,third,x,y) != best) continue;
            free.add(new int[]{x,y});
            if (plus < tier) { tier = plus; kept.clear(); }
            if (plus == tier) kept.add(new int[]{x,y});
            if (exposure < tier339) { tier339 = exposure; kept339.clear(); }
            if (exposure == tier339) kept339.add(new int[]{x,y});
        }
        check(cleared, "Fixture has no launch an earlier car clears");
        check(Arrays.equals(free.get(0),new int[]{3,1}), "The first best free cell in slot 3 is not (3,1)");
        check(kept.size() == 1 && kept339.size() == 2 && Arrays.equals(kept339.get(1),new int[]{5,3})
                && plusOracle(g,5,3,3,earlier) == 2, "Fixture has no unexposed launch the earlier cars' launches close");
        final int[][] positions = Arrays.stream(g.players).map(p -> p.getPosition().clone()).toArray(int[][]::new);
        final int[] behind = StartPlacement.choose(g,third,null);
        check(Arrays.equals(behind,new int[]{4,1}) && Arrays.equals(behind,kept.get(0))
                && StartPlacement.exposure(g,third,4,1) == 0 && StartPlacement.exposurePlus(g,third,4,1) == 0,
                "The car in slot 3 did not take the launch the earlier cars clear");
        for (long seed=0;seed<10;seed++)
            check(Arrays.equals(StartPlacement.choose(g,third,seed),
                    kept.get(drawOracle(seed, third.getNumber(), kept.size()))),
                    "A seeded car in slot 3 took a launch the earlier cars' launches close");
        check(Arrays.equals(behind,StartPlacement.choose(g,third,null)), "Choice is not a pure function");
        check(Arrays.deepEquals(positions,Arrays.stream(g.players).map(Player::getPosition).toArray(int[][]::new)),
                "Exposure mutated players");
        // A later human may place too: with a human in the last slot the car in
        // slot 3 still keeps its launch clear of the cells it may take.
        g.players[3] = new Player("H",4,Color.BLACK,Player.Kind.HUMAN);
        check(Arrays.equals(StartPlacement.choose(g,third,null),behind), "A later human was not a car that may place");
        g.players[3] = last;
        // The tiers stay apart. With the first two cars on (5,2) and (5,3), (4,1) and
        // (4,2) keep a fastest first move that neither a placement nor an earlier
        // car's fastest first move can close, yet still launch onto a free starting
        // cell; (4,3) launches only onto the earlier cars' cells, which they leave. The
        // car takes (4,3), where merging the tiers would take (4,1) and the first best
        // free cell is (3,1); seeded, it draws among the unexposed best cells alone.
        // Round 342: (5,1), unexposed before, launches onto (6,1) and (6,2), where the
        // earlier cars' fastest first moves land, so it no longer joins them.
        ai.setPosition(new int[]{5,2}); second.setPosition(new int[]{5,3});
        earlier.clear(); earlier.addAll(fastestLandings(g,5,2)); earlier.addAll(fastestLandings(g,5,3));
        final List<int[]> bestFree = new ArrayList<>(), unexposed = new ArrayList<>(), unexposed339 = new ArrayList<>();
        int lowest = Integer.MAX_VALUE, firstUnclosable = -1, firstUnexposed = -1;
        for (int x=1;x<=5;x++) for (int y=1;y<=3;y++) {
            if (g.isCrashingPlayer(x,y,3) || StartPlacement.score(g,third,x,y) != best) continue;
            final int exposure = plusOracle(g,x,y,3,earlier), round339 = exposureOracle(g,x,y,3);
            check(StartPlacement.exposurePlus(g,third,x,y) == exposure, "C+ exposure is not the referee's beside earlier cars");
            check(StartPlacement.exposure(g,third,x,y) == round339, "Launch exposure is not the referee's beside earlier cars");
            if (exposure == 1 && firstUnclosable < 0) firstUnclosable = bestFree.size();
            if (exposure == 0 && firstUnexposed < 0) firstUnexposed = bestFree.size();
            bestFree.add(new int[]{x,y}); lowest = Math.min(lowest,exposure);
            if (exposure == 0) unexposed.add(new int[]{x,y});
            if (round339 == 0) unexposed339.add(new int[]{x,y});
        }
        check(lowest == 0 && firstUnclosable >= 0 && firstUnexposed > firstUnclosable && unexposed.size() < bestFree.size(),
                "Fixture has no unclosable exposed launch before an unexposed one");
        check(Arrays.equals(bestFree.get(0),new int[]{3,1}), "The first best free cell in slot 3 is not (3,1)");
        check(Arrays.equals(StartPlacement.choose(g,third,null),unexposed.get(0))
                && Arrays.equals(unexposed.get(0),new int[]{4,3}), "The car merged the unexposed and unclosable tiers");
        check(unexposed.size() == 1 && unexposed339.size() == 2 && Arrays.equals(unexposed339.get(1),new int[]{5,1}),
                "Fixture has no unexposed launch the earlier cars' launches close");
        for (long seed=0;seed<10;seed++)
            check(Arrays.equals(StartPlacement.choose(g,third,seed),
                    unexposed.get(drawOracle(seed, third.getNumber(), unexposed.size()))),
                    "A seeded car in slot 3 is not the seed's draw among its least exposed best cells");
        // Undo takes the earlier cars back: the same car then chooses as alone.
        for (final Player player : g.players) player.setPosition(new int[]{Player.INIT_POS,Player.INIT_POS});
        check(Arrays.equals(StartPlacement.choose(g,third,null),pool.get(0)), "Undo did not restore the same choice");
    }
    /** Round 342 (C+; the owner, 2026-11-04): every car with a car after it also
     *  holds the landings of the earlier cars' fastest first moves, which those cars
     *  may stand on when it first moves, whether they are computers or humans. For
     *  every cell the first car may take, with that car a computer and then a human,
     *  against the independent oracles: the car in slot 2 takes the first of its
     *  best free cells of least C+ exposure and draws over them seeded, which moves
     *  it off round 339's choice where the first car stands on (5,1), (5,2) or (5,3);
     *  the last car keeps all its best cells. */
    private static void testEarlierLaunches(final boolean gated) {
        for (final Player.Kind kind : new Player.Kind[]{Player.Kind.AI1, Player.Kind.HUMAN}) testEarlierLaunches(gated, kind);
    }
    private static void testEarlierLaunches(final boolean gated, final Player.Kind firstKind) {
        final RaceGame g = corridor(gated);
        g.players[0] = new Player("A",1,Color.BLUE,firstKind);
        g.players[1] = new Player("B",2,Color.RED,Player.Kind.AI1);
        if (gated) g.prepareOptimalStartMap();
        else { g.reach.computeDistMap(); g.reach.computeReachability(); g.prepareOptimalStartMap(); }
        set(g.reach,"reachabilityReady",true);
        final Player first = g.players[0], second = g.players[1], last = g.players[3];
        final List<int[]> moved = new ArrayList<>();
        int placed = 0;
        for (int fx=1;fx<=5;fx++) for (int fy=1;fy<=3;fy++) {
            for (final Player p : g.players) p.setPosition(new int[]{Player.INIT_POS,Player.INIT_POS});
            if (oracle(g,fx,fy,false) == Integer.MAX_VALUE) continue;
            first.setPosition(new int[]{fx,fy});
            final List<int[]> earlier = fastestLandings(g,fx,fy);
            final List<int[]> ties = bestFree(g,second);
            if (ties.isEmpty()) continue;
            placed++;
            final List<int[]> plus = new ArrayList<>(), round339 = new ArrayList<>();
            int leastPlus = Integer.MAX_VALUE, least = Integer.MAX_VALUE;
            for (final int[] c : ties) {
                final int p = plusOracle(g,c[0],c[1],2,earlier), e = exposureOracle(g,c[0],c[1],2);
                check(StartPlacement.exposurePlus(g,second,c[0],c[1]) == p, "C+ exposure is not the referee's");
                check(StartPlacement.exposure(g,second,c[0],c[1]) == e,
                        "Launch exposure is not the referee's beside an earlier car");
                if (p < leastPlus) { leastPlus = p; plus.clear(); }
                if (p == leastPlus) plus.add(c);
                if (e < least) { least = e; round339.clear(); }
                if (e == least) round339.add(c);
            }
            check(Arrays.equals(StartPlacement.choose(g,second,null),plus.get(0)),
                    "The car in slot 2 did not hold the earlier car's launch");
            for (long seed=0;seed<10;seed++)
                check(Arrays.equals(StartPlacement.choose(g,second,seed),
                        plus.get(drawOracle(seed, second.getNumber(), plus.size()))),
                        "A seeded car in slot 2 is not the seed's draw among its least C+ exposed best cells");
            if (!Arrays.equals(plus.get(0),round339.get(0))) moved.add(new int[]{fx,fy});
            // The last car to place weighs neither later placements nor earlier launches.
            final List<int[]> lastTies = bestFree(g,last);
            check(Arrays.equals(StartPlacement.choose(g,last,null),lastTies.get(0)),
                    "The last car to place weighed the earlier car's launch or later placements");
            for (long seed=0;seed<10;seed++)
                check(Arrays.equals(StartPlacement.choose(g,last,seed),
                        lastTies.get(drawOracle(seed, last.getNumber(), lastTies.size()))),
                        "A seeded last car is not the seed's draw among all its best cells");
        }
        for (final Player p : g.players) p.setPosition(new int[]{Player.INIT_POS,Player.INIT_POS});
        check(placed == 15 && moved.size() == 3 && Arrays.equals(moved.get(0),new int[]{5,1})
                && Arrays.equals(moved.get(1),new int[]{5,2}) && Arrays.equals(moved.get(2),new int[]{5,3}),
                "The earlier launches that move the car in slot 2 are not those from (5,1), (5,2) and (5,3)");
    }
    /** The free cells of the best referee value from rest for {@code car}, in
     *  x-then-y order: the oracle's values and the referee's occupancy. */
    private static List<int[]> bestFree(final RaceGame g, final Player car) {
        final List<int[]> ties = new ArrayList<>();
        int best = Integer.MAX_VALUE;
        for (int x=1;x<=5;x++) for (int y=1;y<=3;y++) {
            if (g.isCrashingPlayer(x,y,car.getNumber())) continue;
            final int s = oracle(g,x,y,false);
            if (s == Integer.MAX_VALUE || s > best) continue;
            if (s < best) { best = s; ties.clear(); }
            ties.add(new int[]{x,y});
        }
        return ties;
    }
    /** Independent C+ exposure for car {@code number}: a fastest landing is held where
     *  it is a starting cell no other car holds or one of {@code earlier}'s landings. */
    private static int plusOracle(final RaceGame g, final int x, final int y, final int number,
            final List<int[]> earlier) {
        final List<int[]> landings = fastestLandings(g,x,y);
        int exposed = 0;
        for (final int[] l : landings) {
            boolean held = g.startZoneA.contains(l[0],l[1]) && !g.isCrashingPlayer(l[0],l[1],number);
            for (final int[] e : earlier) held |= Arrays.equals(e,l);
            if (held) exposed++;
        }
        return exposed == 0 ? 0 : exposed < landings.size() ? 1 : 2;
    }
    /** Round 344: the seed's draw, independently -- car {@code number}'s output of the
     *  seed's SplitMix64 stream, the JDK's own (java.util.SplittableRandom), reduced to the
     *  pool, unsigned. */
    private static int drawOracle(final long seed, final int number, final int size) {
        final SplittableRandom stream = new SplittableRandom(seed);
        long z = 0;
        for (int i = 0; i < number; i++) z = stream.nextLong();
        return (int) Long.remainderUnsigned(z, size);
    }
    /** Round 344 (the owner, 2026-11-06: "fix and investigate"): the first output of
     *  new Random(seed ^ (long) number << 32) gave a car the same position in a pool of
     *  2, 4, 8 or 16 cells in every small seed. The seed's draw is the JDK's SplitMix64, and over each
     *  window the screens race (seeds 1-5, 6-10, 11-20, 21-30) every car 1-9 takes more
     *  than one cell of every pool of 2 to 16 cells; the known answers pin it. */
    private static void testDraw() {
        for (int car = 1; car <= 9; car++) for (int size = 1; size <= 64; size++)
            for (long seed = -50; seed <= 50; seed++)
                check(StartPlacement.draw(seed, car, size) == drawOracle(seed, car, size),
                        "The seed's draw is not the car's output of the seed's SplitMix64 stream");
        for (final long seed : new long[]{Long.MIN_VALUE, -1L, 1L << 32, Long.MAX_VALUE})
            for (int car = 1; car <= 9; car++)
                check(StartPlacement.draw(seed, car, 7) == drawOracle(seed, car, 7), "The draw fails at an extreme seed");
        for (final long[] window : new long[][]{{1, 5}, {6, 10}, {11, 20}, {21, 30}})
            for (int car = 1; car <= 9; car++) for (int size = 2; size <= 16; size++) {
                final HashSet<Integer> cells = new HashSet<>();
                for (long seed = window[0]; seed <= window[1]; seed++) cells.add(StartPlacement.draw(seed, car, size));
                check(cells.size() > 1, "Car " + car + " takes one cell of " + size + " in every seed "
                        + window[0] + "-" + window[1]);
            }
        check(StartPlacement.draw(1, 1, 2) == 1 && StartPlacement.draw(1, 1, 3) == 2 && StartPlacement.draw(1, 1, 8) == 1
                && StartPlacement.draw(1, 2, 8) == 7 && StartPlacement.draw(2, 1, 8) == 6
                && StartPlacement.draw(-7, 4, 8) == 2, "The seed's draw changed its known answers");
    }
    /** Round 339: a finishing move is exempt from bodies, so it never joins a launch.
     *  With the finish line through the grid, the cells whose fastest first moves
     *  all finish onto free starting cells are not exposed, and a car standing on
     *  such a landing leaves them their value from rest (the referee's rule). */
    private static void testFinishingLaunch() {
        final RaceGame g = corridor(false);
        g.finishLine = new Line2D.Double(4.5,0,4.5,4);
        g.reach.computeDistMap(); g.reach.computeReachability(); g.prepareOptimalStartMap();
        set(g.reach,"reachabilityReady",true);
        final Player ai = g.players[0];
        for (int y=1;y<=3;y++) {
            check(StartPlacement.score(g,ai,4,y) == 1 && oracle(g,4,y,false) == 1, "The grid's immediate finish is not its value from rest");
            check(g.startZoneA.contains(5,y) && StartPlacement.exposure(g,ai,4,y) == 0, "A finishing launch was exposed");
        }
        g.players[1].setPosition(new int[]{5,2});
        check(oracle(g,4,2,true) == 1 && StartPlacement.exposure(g,ai,4,2) == 0, "A car beyond the line blocked a finishing launch");
        g.players[1].setPosition(new int[]{Player.INIT_POS,Player.INIT_POS});
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
        // Equally good cells -- the same value and, since cars place after this one,
        // the same launch exposure (round 339) -- go to the seed's draw, or without a
        // seed to the first in x-then-y order; never to a replay of the race among
        // them (the owner rejected start-ties, 2026-10-02).
        int leastExposure = Integer.MAX_VALUE;
        for (int x=1;x<=5;x++) for (int y=1;y<=3;y++)
            if (before[x][y] == emptyBest) leastExposure = Math.min(leastExposure, StartPlacement.exposure(g,ai,x,y));
        final List<int[]> ties = new ArrayList<>();
        for (int x=1;x<=5;x++) for (int y=1;y<=3;y++)
            if (before[x][y] == emptyBest && StartPlacement.exposure(g,ai,x,y) == leastExposure) ties.add(new int[]{x,y});
        check(ties.size() >= 2, "Fixture has no tie among its least exposed best cells");
        final int[] oldBest = StartPlacement.choose(g,ai,null);
        check(Arrays.equals(oldBest, ties.get(0)),
                "Without a seed the tie did not go to the first least exposed best cell in x-then-y order");
        for (long seed=0;seed<10;seed++)
            check(Arrays.equals(StartPlacement.choose(g,ai,seed),
                    ties.get(drawOracle(seed, ai.getNumber(), ties.size()))),
                    "A seeded tie is not the seed's draw among the least exposed best cells");
        g.players[1].setPosition(oldBest.clone());
        g.players[2].setPosition(new int[]{5,2});
        g.players[3].setPosition(new int[]{5,3});
        int minimum = Integer.MAX_VALUE; boolean witnessed = false;
        for (int x=1;x<=5;x++) for (int y=1;y<=3;y++) {
            final int score = StartPlacement.score(g,ai,x,y);
            if (g.isCrashingPlayer(x,y,1)) check(score == Integer.MAX_VALUE, "Occupied start was accepted");
            else {
                // The earlier cars' cells are taken, and a free cell's value ignores
                // those cars: they move first, so it keeps its solo value.
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
            check(cells > 1 && best != Integer.MAX_VALUE && first != null, "The Circle's grid does not reach its first checkpoint");
            // Round 339: the launch on the first-checkpoint map -- the first moves whose
            // distance to the first checkpoint achieves the cell's from rest (a move that
            // collects it has none left) -- is exposed where it lands on a free starting cell.
            int exposedCells = 0, leastExposure = Integer.MAX_VALUE;
            int[] firstLeast = null;
            for (int x = (int) Math.floor(bounds.getMinX()); x <= (int) Math.ceil(bounds.getMaxX()); x++)
                for (int y = (int) Math.floor(bounds.getMinY()); y <= (int) Math.ceil(bounds.getMaxY()); y++) {
                    if (!g.startZoneA.contains(x, y)) continue;
                    final int value = g.reach.turnsToGate(1, x, y, 0, 0);
                    int moves = 0, exposed = 0;
                    for (final Direction d : Direction.values()) {
                        final int nx = x + d.dx, ny = y + d.dy;
                        final RaceGame.MoveResult move = g.evaluateMove(0, 1, true, x, y, nx, ny, false);
                        if (d == Direction.NONE || !move.legal() || move.finishes()) continue;
                        final int rest = move.gateAfter() != 1 ? 0 : g.reach.turnsToGate(1, nx, ny, d.dx, d.dy);
                        if (rest == Integer.MAX_VALUE || rest + 1 != value) continue;
                        moves++;
                        if (g.startZoneA.contains(nx, ny) && !g.isCrashingPlayer(nx, ny, ai.getNumber())) exposed++;
                    }
                    final int expected = exposed == 0 ? 0 : exposed < moves ? 1 : 2;
                    check(StartPlacement.exposure(g, ai, x, y) == expected,
                            "Over budget a launch's exposure is not the first-checkpoint map's");
                    if (expected > 0) exposedCells++;
                    if (value == best && expected < leastExposure) { leastExposure = expected; firstLeast = new int[]{x, y}; }
                }
            check(exposedCells > 0, "The Circle's grid has no exposed launch");
            // B places after A, so A takes the first of its least exposed best cells,
            // not the first best cell, the rule's pick before round 339.
            check(!Arrays.equals(firstLeast, first), "The Circle's first best cell is already its least exposed");
            check(Arrays.equals(StartPlacement.choose(g, ai, null), firstLeast),
                    "Over budget the AI did not take its first least exposed best cell");
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
