package tr.logic;

import java.awt.geom.Rectangle2D;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/** The owner's computed-start rule (2026-10-02, CLAUDE.md): one shared,
 * occupancy-independent value for every starting cell.
 *
 * All players place in roster order, the order they then race in. At each AI's
 * turn the cells the earlier cars took are refused and nothing else about those
 * cars counts: they move first. A free cell scores its exact single-player value
 * from rest -- the cheapest legal first move plus the exact solo continuation --
 * with no prediction of unplaced rivals and no preselected positions. Where the
 * exact full-race map is over budget, the continuation is the next best map, the
 * exact distance to the first checkpoint, which the cars then race by.
 */
final class StartPlacement {
    private StartPlacement() {}

    /** A start cell and its value from rest in turns; MAX_VALUE when no legal
     *  first move continues. */
    private record Cell(int x, int y, int turns) {}

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
                int best = Integer.MAX_VALUE;
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
                    if (rest != Integer.MAX_VALUE)
                        best = Math.min(best, rest + 1);
                }
                cells.add(new Cell(x, y, best));
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
        // Stable x-then-y tie order and a local seed stream preserve Undo and
        // existing computed-start fixtures without perturbing benchmark RNG.
        final int choice = seed == null ? 0 : new Random(seed ^ ((long) player.getNumber() << 32)).nextInt(bestCells.size());
        final Cell selected = bestCells.get(choice);
        return new int[]{selected.x(), selected.y()};
    }
}
