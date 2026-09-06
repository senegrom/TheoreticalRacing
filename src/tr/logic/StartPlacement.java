package tr.logic;

import java.awt.geom.Rectangle2D;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/** Computed starting cells, shared by Swing and the browser.
 *
 * The score is the shortest finish after a first move legal against the cars
 * already placed, followed by the exact SOLO map. It is not a multiplayer
 * minimax solution or a prediction of cars which have not placed yet. The
 * starting square and first landing are both checked against current occupancy.
 * Seeded randomness breaks ties only; it never chooses a slower-scored cell.
 */
final class StartPlacement {
    private StartPlacement() {}

    private static void requireMaps(final RaceGame game) {
        if (!game.reach.isReady())
            throw new IllegalStateException("AI placement requires complete track maps");
        game.reach.ensureReachabilityReady();
        if (game.lapGates != null && game.preparedStartPotential() == null)
            throw new IllegalStateException("AI placement requires the exact full-race map");
    }

    static int score(final RaceGame game, final Player player, final int x, final int y) {
        requireMaps(game);
        if (x < 0 || y < 0 || x > game.gameCols || y > game.gameRows
                || !game.startZoneA.contains(x, y)
                || game.isCrashingPlayer(x, y, player.getNumber())) return Integer.MAX_VALUE;
        int best = Integer.MAX_VALUE;
        final int[] start = {x, y};
        for (final Direction d : Direction.values()) {
            final int nx = x + d.dx, ny = y + d.dy;
            final RaceGame.MoveResult move = game.evaluateMove(player, start, new int[]{nx, ny});
            if (!move.legal()) continue;
            if (move.finishes()) return 1;
            final int rest = game.lapGates == null
                    ? game.reach.turnsToFinish(nx, ny, d.dx, d.dy)
                    : game.preparedStartPotential().movesToFinish(
                            OptimalPotential.remainingEvents(move.gateAfter(), move.lapAfter(), game.totalLaps),
                            nx, ny, d.dx, d.dy);
            if (rest != Integer.MAX_VALUE) best = Math.min(best, rest + 1);
        }
        return best;
    }

    static int[] choose(final RaceGame game, final Player player, final Long seed) {
        requireMaps(game);
        final Rectangle2D bounds = game.startZoneA.getBounds2D();
        final List<int[]> bestCells = new ArrayList<>();
        int best = Integer.MAX_VALUE;
        for (int x = Math.max(0, (int) Math.floor(bounds.getMinX())); x <= Math.min(game.gameCols, (int) Math.ceil(bounds.getMaxX())); x++) {
            for (int y = Math.max(0, (int) Math.floor(bounds.getMinY())); y <= Math.min(game.gameRows, (int) Math.ceil(bounds.getMaxY())); y++) {
                final int score = score(game, player, x, y);
                if (score == Integer.MAX_VALUE || score > best) continue;
                if (score < best) { best = score; bestCells.clear(); }
                bestCells.add(new int[]{x, y});
            }
        }
        if (bestCells.isEmpty()) return null;
        // A local, stable tie stream lets Undo/replacement recompute against the
        // same occupancy without consuming or perturbing benchmark RNG state.
        final int choice = seed == null ? 0 : new Random(seed ^ ((long) player.getNumber() << 32)).nextInt(bestCells.size());
        return bestCells.get(choice);
    }
}
