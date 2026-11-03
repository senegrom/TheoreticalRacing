package tr.logic;

import java.awt.geom.Rectangle2D;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/** The owner's computed-start rule (2026-10-02, CLAUDE.md; later placements
 * 2026-11-01): one shared, occupancy-independent value for every starting cell,
 * and the first moves that achieve it.
 *
 * All players place in roster order, the order they then race in. At each AI's
 * turn the cells the earlier cars took are refused and nothing else about those
 * cars counts: they move first. A free cell scores its exact single-player value
 * from rest -- the cheapest legal first move plus the exact solo continuation --
 * with no preselected positions. Where the exact full-race map is over budget,
 * the continuation is the next best map, the exact distance to the first
 * checkpoint, which the cars then race by.
 *
 * Round 339 (the owner, 2026-11-01: "Cars should also consider where other cars
 * may place."): any free starting cell may be taken by a later car, AI or human,
 * and that car still stands there when this one first moves. Among its best cells
 * a car keeps the least exposed launch: none of its fastest first moves lands on a
 * free starting cell; else at least one lands elsewhere, so no later placement can
 * close it; else any best cell. The last car to place keeps all its best cells.
 * Which cell a later car takes is never predicted, nothing is simulated, and where
 * the earlier cars go is never priced.
 * Against the speed-round-3 champion as arm 364, all on computed starts: eight-car
 * fields -0.279 +- 0.028 places (seeds 1-10) and -0.354 +- 0.029 on held-out seeds
 * 11-20, a lone car among eight -0.254 +- 0.027, four-car fields -0.097 +- 0.012,
 * duels -0.008 +- 0.007; random and scattered starts never reach the placement.
 */
final class StartPlacement {
    private StartPlacement() {}

    /** A start cell and its value from rest in turns; MAX_VALUE when no legal
     *  first move continues. Round 339: its launch, the Direction-ordinal bits of
     *  the first moves that achieve that value -- never a finishing move (the
     *  referee exempts it from bodies) nor waiting (the car keeps its own cell). */
    private record Cell(int x, int y, int turns, int launch) {}

    /** Owned by one RaceGame and safely published through reachability readiness.
     * No live Player, occupancy mask, selected cell or mutable map is retained. */
    static final class Analysis {
        private final List<Cell> cells;
        private Analysis(final List<Cell> cells) { this.cells = List.copyOf(cells); }

        private Cell find(final int x, final int y) {
            int low = 0, high = cells.size() - 1;
            while (low <= high) {
                final int mid = (low + high) >>> 1;
                final Cell cell = cells.get(mid);
                final int order = cell.x() == x ? Integer.compare(cell.y(), y) : Integer.compare(cell.x(), x);
                if (order == 0) return cell;
                if (order < 0) low = mid + 1;
                else high = mid - 1;
            }
            return null;
        }

        /** A taken cell is refused; a free one keeps its value from rest. */
        private int score(final RaceGame game, final Player player, final Cell cell) {
            return cell == null || game.isCrashingPlayer(cell.x(), cell.y(), player.getNumber())
                    ? Integer.MAX_VALUE : cell.turns();
        }

        /** Round 339: the launch's exposure to later placements -- 0 when none of the
         *  cell's fastest first moves lands on a free starting cell, 2 when every
         *  one does, else 1. A cell another car holds is not free: in a placement
         *  only an earlier car holds one, and it moves first. */
        private int exposure(final RaceGame game, final Player player, final Cell cell) {
            int moves = 0, exposed = 0;
            for (final Direction d : Direction.values()) {
                if ((cell.launch() & (1 << d.ordinal())) == 0) continue;
                moves++;
                final int lx = cell.x() + d.dx, ly = cell.y() + d.dy;
                if (find(lx, ly) != null && !game.isCrashingPlayer(lx, ly, player.getNumber())) exposed++;
            }
            return exposed == 0 ? 0 : exposed < moves ? 1 : 2;
        }
    }

    /** Called once by the existing preparation daemon, AFTER every route map,
     * BEFORE ready=true. Evaluate a detached fresh car; humans may place while
     * this runs, so reading/modifying the live roster here would be incorrect. */
    static Analysis prepare(final RaceGame game) {
        final OptimalPotential potential = game.preparedStartPotential();
        final Rectangle2D bounds = game.startZoneA.getBounds2D();
        final int xMin = Math.max(0, (int) Math.floor(bounds.getMinX()));
        final int xMax = Math.min(game.gameCols, (int) Math.ceil(bounds.getMaxX()));
        final int yMin = Math.max(0, (int) Math.floor(bounds.getMinY()));
        final int yMax = Math.min(game.gameRows, (int) Math.ceil(bounds.getMaxY()));
        final List<Cell> cells = new ArrayList<>();
        for (int x = xMin; x <= xMax; x++) {
            for (int y = yMin; y <= yMax; y++) {
                if (!game.startZoneA.contains(x, y)) continue;
                int best = Integer.MAX_VALUE, launch = 0;
                for (final Direction d : Direction.values()) {
                    final int nx = x + d.dx, ny = y + d.dy;
                    final RaceGame.MoveResult move = game.evaluateMove(0, 1, true, x, y, nx, ny, false);
                    if (!move.legal()) continue;
                    // Over budget (potential null on a lap race), the turns to the
                    // first checkpoint: a first move that collects it has none left.
                    final int rest = move.finishes() ? 0 : game.lapGates == null
                            ? game.reach.turnsToFinish(nx, ny, d.dx, d.dy)
                            : potential == null
                            ? move.gateAfter() != 1 ? 0 : game.reach.turnsToGate(1, nx, ny, d.dx, d.dy)
                            : potential.movesToFinish(
                                    OptimalPotential.remainingEvents(move.gateAfter(), move.lapAfter(), game.totalLaps),
                                    nx, ny, d.dx, d.dy);
                    if (rest == Integer.MAX_VALUE) continue;
                    // Round 339: the launch, every first move that achieves the value.
                    // A finishing move is exempt from bodies and waiting keeps the
                    // car's own cell (a turn more), so neither joins.
                    final int bit = move.finishes() || d == Direction.NONE ? 0 : 1 << d.ordinal();
                    if (rest + 1 < best) { best = rest + 1; launch = bit; }
                    else if (rest + 1 == best) launch |= bit;
                }
                cells.add(new Cell(x, y, best, launch));
            }
        }
        return new Analysis(cells);
    }

    private static Analysis requireAnalysis(final RaceGame game, final Player player) {
        if (!game.reach.isReady())
            throw new IllegalStateException("AI placement requires complete track maps");
        game.reach.ensureReachabilityReady();
        final Analysis analysis = game.preparedStartAnalysis();
        if (analysis == null)
            throw new IllegalStateException("AI placement requires the complete start analysis");
        if (player.isFinished() || player.getLap() != 0 || player.getNextGate() != 1
                || player.getVelocity()[0] != 0 || player.getVelocity()[1] != 0)
            throw new IllegalStateException("Starting analysis requires a fresh stationary player");
        return analysis;
    }

    /** One cell's score, behind requireAnalysis's checks: the tests' entry point
     *  (choose scores cells through the analysis directly). */
    static int score(final RaceGame game, final Player player, final int x, final int y) {
        final Analysis analysis = requireAnalysis(game, player);
        return analysis.score(game, player, analysis.find(x, y));
    }

    /** Round 339: one cell's launch exposure (0, 1 or 2; MAX_VALUE outside the
     *  table), behind requireAnalysis's checks: the tests' entry point. */
    static int exposure(final RaceGame game, final Player player, final int x, final int y) {
        final Analysis analysis = requireAnalysis(game, player);
        final Cell cell = analysis.find(x, y);
        return cell == null ? Integer.MAX_VALUE : analysis.exposure(game, player, cell);
    }

    static int[] choose(final RaceGame game, final Player player, final Long seed) {
        final Analysis analysis = requireAnalysis(game, player);
        final List<Cell> bestCells = new ArrayList<>();
        int best = Integer.MAX_VALUE;
        for (final Cell cell : analysis.cells) {
            final int score = analysis.score(game, player, cell);
            if (score == Integer.MAX_VALUE || score > best) continue;
            if (score < best) { best = score; bestCells.clear(); }
            bestCells.add(cell);
        }
        if (bestCells.isEmpty()) return null;
        // Round 339 (the owner, 2026-11-01): whenever a car places after this one,
        // only the least exposed best cells stay; the last car to place keeps all of them.
        final List<Cell> pool = carFollows(game, player)
                ? leastExposed(analysis, game, player, bestCells) : bestCells;
        // The pool's cells are equally good: a stable x-then-y order and a local
        // seed stream break their tie, which preserves Undo without perturbing
        // benchmark RNG.
        final int choice = seed == null ? 0 : new Random(seed ^ ((long) player.getNumber() << 32)).nextInt(pool.size());
        final Cell selected = pool.get(choice);
        return new int[]{selected.x(), selected.y()};
    }

    /** Round 339: does a roster slot follow this player's? That car places after it. */
    private static boolean carFollows(final RaceGame game, final Player player) {
        final Player[] roster = game.players;
        for (int i = 0; i < roster.length; i++)
            if (roster[i] == player) return i < roster.length - 1;
        return false;
    }

    /** Round 339: the cells of the least exposure, in their x-then-y order. */
    private static List<Cell> leastExposed(final Analysis analysis, final RaceGame game, final Player player,
                                           final List<Cell> cells) {
        final List<Cell> pool = new ArrayList<>();
        int least = Integer.MAX_VALUE;
        for (final Cell cell : cells) {
            final int exposure = analysis.exposure(game, player, cell);
            if (exposure > least) continue;
            if (exposure < least) { least = exposure; pool.clear(); }
            pool.add(cell);
        }
        return pool;
    }
}
