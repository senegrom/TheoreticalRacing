package tr.logic;

import java.awt.geom.Rectangle2D;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Random;

/** Shared, occupancy-independent analysis of every starting cell and first move.
 *
 * All players place in roster order. At each AI's turn only current occupancy is
 * applied to this immutable table; no starting positions are preselected. Keep
 * slower alternatives too: an earlier car may block the fastest first landing.
 * The objective is a legal first move followed by the exact SOLO continuation,
 * not a multiplayer minimax guarantee or a prediction of unplaced rivals.
 */
final class StartPlacement {
    private StartPlacement() {}

    private record Alternative(int x, int y, int turns, boolean finishes) {}
    private record Cell(int x, int y, List<Alternative> alternatives) {}

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

        private int score(final RaceGame game, final Player player, final Cell cell) {
            if (cell == null || game.isCrashingPlayer(cell.x(), cell.y(), player.getNumber()))
                return Integer.MAX_VALUE;
            for (final Alternative move : cell.alternatives()) {
                // The referee exempts the landing AFTER a terminal finish from
                // body collisions. Non-final lap crossings have no exemption.
                if (move.finishes() || !game.isCrashingPlayer(move.x(), move.y(), player.getNumber()))
                    return move.turns();
            }
            return Integer.MAX_VALUE;
        }
    }

    /** Called once by the existing preparation daemon, AFTER every route map,
     * BEFORE ready=true. Evaluate a detached fresh car; humans may place while
     * this runs, so reading/modifying the live roster here would be incorrect. */
    static Analysis prepare(final RaceGame game) {
        if (game.lapGates != null && game.preparedStartPotential() == null)
            throw new IllegalStateException("Starting alternatives require the exact full-race map");
        final Rectangle2D bounds = game.startZoneA.getBounds2D();
        final int xMin = Math.max(0, (int) Math.floor(bounds.getMinX()));
        final int xMax = Math.min(game.gameCols, (int) Math.ceil(bounds.getMaxX()));
        final int yMin = Math.max(0, (int) Math.floor(bounds.getMinY()));
        final int yMax = Math.min(game.gameRows, (int) Math.ceil(bounds.getMaxY()));
        final List<Cell> cells = new ArrayList<>();
        for (int x = xMin; x <= xMax; x++) {
            for (int y = yMin; y <= yMax; y++) {
                if (!game.startZoneA.contains(x, y)) continue;
                final List<Alternative> alternatives = new ArrayList<>();
                for (final Direction d : Direction.values()) {
                    final int nx = x + d.dx, ny = y + d.dy;
                    final RaceGame.MoveResult move = game.evaluateMove(0, 1, x, y, nx, ny, false);
                    if (!move.legal()) continue;
                    final int rest = move.finishes() ? 0 : game.lapGates == null
                            ? game.reach.turnsToFinish(nx, ny, d.dx, d.dy)
                            : game.preparedStartPotential().movesToFinish(
                                    OptimalPotential.remainingEvents(move.gateAfter(), move.lapAfter(), game.totalLaps),
                                    nx, ny, d.dx, d.dy);
                    if (rest != Integer.MAX_VALUE)
                        alternatives.add(new Alternative(nx, ny, rest + 1, move.finishes()));
                }
                alternatives.sort(Comparator.comparingInt(Alternative::turns));
                cells.add(new Cell(x, y, List.copyOf(alternatives)));
            }
        }
        return new Analysis(cells);
    }

    private static Analysis requireAnalysis(final RaceGame game, final Player player) {
        if (!game.reach.isReady())
            throw new IllegalStateException("AI placement requires complete track maps");
        game.reach.ensureReachabilityReady();
        if (game.lapGates != null && game.preparedStartPotential() == null)
            throw new IllegalStateException("AI placement requires the exact full-race map");
        final Analysis analysis = game.preparedStartAnalysis();
        if (analysis == null)
            throw new IllegalStateException("AI placement requires complete starting alternatives");
        if (player.isFinished() || player.getLap() != 0 || player.getNextGate() != 1
                || player.getVelocity()[0] != 0 || player.getVelocity()[1] != 0)
            throw new IllegalStateException("Starting analysis requires a fresh stationary player");
        return analysis;
    }

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
