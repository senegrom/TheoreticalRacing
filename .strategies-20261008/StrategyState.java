package tr.logic;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Immutable, clocked referee state shared by bounded strategy searches.
 * Opponents have physical accelerations, not the AI's planning speed cap.
 * UI trails and pending suggestions do not change the physical state key. */
@SuppressWarnings("try")
final class StrategyState {
    final RacecraftReplay.Board board;
    StrategyState(final RacecraftReplay.Board board) { this.board = board; }
    static StrategyState capture(final RaceGame game) { return new StrategyState(RacecraftReplay.capture(game)); }
    int slot() { return board.slot; }
    int live() { int n = 0; for (final int[] r : board.cars) if (r[6] == 0) n++; return n; }
    int place(final int self) { return board.cars[self][6]; }
    String key() { return FollowupPlans.key(board); }
    boolean timedOut(final RaceGame game) { return RaceTimeout.reached(game, board.turn); }
    boolean ownDomain(final Direction d) {
        final int[] r = board.cars[slot()];
        return !RaceGame.aiVelocityOutOfRange(r[4] + d.dx, r[5] + d.dy);
    }
    int distance(final RaceGame game, final int self) {
        final int[] r = board.cars[self];
        if (r[6] != 0) return 0;
        if (game.lapGates == null) return game.reach.turnsToFinish(r[2], r[3], r[4], r[5]);
        final OptimalPotential pot = game.optimalPotential();
        return pot == null ? Integer.MAX_VALUE : pot.movesToFinish(
                OptimalPotential.remainingEvents(r[8], r[7], board.laps), r[2], r[3], r[4], r[5]);
    }
    RaceGame.MoveResult evaluate(final RaceGame game, final Direction d) {
        final int[] r = board.cars[slot()];
        final long x = (long) r[2] + r[4] + d.dx, y = (long) r[3] + r[5] + d.dy;
        if (x < Integer.MIN_VALUE || x > Integer.MAX_VALUE || y < Integer.MIN_VALUE || y > Integer.MAX_VALUE)
            return null; // unavailable, never manufactured retirement evidence
        boolean occupied = false;
        for (int i = 0; i < board.cars.length; i++) if (i != slot()) {
            final int[] other = board.cars[i];
            occupied |= other[6] == 0 && other[2] == x && other[3] == y;
        }
        return game.evaluateMove(r[7], r[8], r[13] == 0, r[2], r[3], (int) x, (int) y, occupied);
    }
    /** Includes physically legal map-dead continuations; only our planning
     * domain can clip velocities. Illegal replies are still explicit transitions. */
    List<Direction> legal(final RaceGame game, final boolean ourDomain) {
        final List<Direction> result = new ArrayList<>();
        for (final Direction d : Direction.values()) {
            if (ourDomain && !ownDomain(d)) continue;
            final RaceGame.MoveResult move = evaluate(game, d);
            if (move != null && move.legal()) result.add(d);
        }
        return List.copyOf(result);
    }
    StrategyState after(final RaceGame game, final Direction d) {
        if (timedOut(game) || place(slot()) != 0 || board.turn == Integer.MAX_VALUE) return null;
        final RaceGame.MoveResult move = evaluate(game, d);
        if (move == null) return null;
        final int[][] rows = Arrays.stream(board.cars).map(int[]::clone).toArray(int[][]::new);
        final int[] r = rows[slot()];
        final int vx = r[4] + d.dx, vy = r[5] + d.dy, nx = r[2] + vx, ny = r[3] + vy;
        int first = board.first, last = board.last;
        if (move.passCp1()) r[8] = 2;
        if (move.passCp2()) r[8] = 0;
        if (!move.legal() || move.finishes()) {
            r[6] = move.finishes() ? ++first : rows.length - last++;
            r[2] = r[3] = Player.INIT_POS; r[4] = r[5] = 0;
        } else {
            r[2] = nx; r[3] = ny; r[4] = vx; r[5] = vy;
            if (move.lapCross()) { r[7]++; r[8] = 1; }
            if (game.startZoneA != null && !game.startZoneA.contains(nx, ny)) r[13] = 1;
        }
        int live = 0, survivor = -1;
        for (int i = 0; i < rows.length; i++) if (rows[i][6] == 0) { live++; survivor = i; }
        if (live == 1 && rows.length > 1) { rows[survivor][6] = first + 1; live = 0; }
        int next = slot();
        if (live > 0) do { next = (next + 1) % rows.length; } while (rows[next][6] != 0);
        return new StrategyState(new RacecraftReplay.Board(board.turn + 1, board.laps, next,
                first, last, board.identity, rows));
    }
    /** Share atomic progress classification rather than infer a timeout winner. */
    StrategyState expire(final RaceGame game) {
        if (!timedOut(game)) return this;
        try (RacecraftReplay.Scope ignored = new RacecraftReplay.Scope(game, board)) {
            RacecraftReplay.expire(game);
            return capture(game);
        }
    }
    static final class Budget {
        private int left;
        private int used;
        Budget(final int limit) { if (limit < 0) throw new IllegalArgumentException("negative strategy budget"); left = limit; }
        boolean take() { if (left == 0) return false; left--; used++; return true; }
        int used() { return used; }
        int left() { return left; }
    }
}
