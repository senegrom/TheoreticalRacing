package tr.logic;

import java.util.ArrayList;
import java.util.List;

/** Small exact own-state operations for proposal generation. No traffic verdict
 * is inferred from a solo path: every proposal is replayed with reactive rivals. */
final class CreativePaths {
    private CreativePaths() {}
    record Own(int x, int y, int vx, int vy, int lap, int gate, boolean left, boolean finished) {
        static Own of(final int[] row) {
            return new Own(row[2], row[3], row[4], row[5], row[7], row[8], row[13] != 0, row[6] != 0);
        }
    }
    static Direction direction(final int dx, final int dy) {
        for (final Direction d : Direction.values()) if (d.dx == dx && d.dy == dy) return d;
        return null;
    }
    static Own step(final RaceGame game, final Own s, final Direction a) {
        if (s.finished() || a == null) return null;
        final long vx = (long) s.vx() + a.dx, vy = (long) s.vy() + a.dy;
        if (vx < Integer.MIN_VALUE || vx > Integer.MAX_VALUE || vy < Integer.MIN_VALUE || vy > Integer.MAX_VALUE
                || RaceGame.aiVelocityOutOfRange((int) vx, (int) vy)) return null;
        final long x = s.x() + vx, y = s.y() + vy;
        if (x < Integer.MIN_VALUE || x > Integer.MAX_VALUE || y < Integer.MIN_VALUE || y > Integer.MAX_VALUE) return null;
        final RaceGame.MoveResult m = game.evaluateMove(s.lap(), s.gate(), !s.left(), s.x(), s.y(), (int) x, (int) y, false);
        if (!m.legal()) return null;
        return new Own((int) x, (int) y, (int) vx, (int) vy, m.lapAfter(), m.gateAfter(),
                s.left() || game.startZoneA != null && !game.startZoneA.contains(x, y), m.finishes());
    }
    static int distance(final RaceGame game, final Own s) {
        if (s == null) return Integer.MAX_VALUE;
        if (s.finished()) return 0;
        if (game.lapGates == null) return game.reach.turnsToFinish(s.x(), s.y(), s.vx(), s.vy());
        final OptimalPotential p = game.optimalPotential();
        return p == null ? Integer.MAX_VALUE : p.movesToFinish(
                OptimalPotential.remainingEvents(s.gate(), s.lap(), game.totalLaps), s.x(), s.y(), s.vx(), s.vy());
    }
    static Own follow(final RaceGame game, final Own initial, final List<Direction> actions,
            final StrategyState.Budget budget) {
        Own state = initial;
        for (final Direction a : actions) {
            if (!budget.take()) return null;
            state = step(game, state, a);
            if (state == null) return null;
        }
        return state;
    }
    static List<Direction> pulse(final List<Direction> base, final int dx, final int dy) {
        if (base.size() != 4 || Math.abs(dx) > 1 || Math.abs(dy) > 1 || dx == 0 && dy == 0) return List.of();
        final int[] weights = {1, -1, -1, 1};
        final List<Direction> result = new ArrayList<>();
        for (int i = 0; i < 4; i++) {
            final Direction a = direction(base.get(i).dx + dx * weights[i], base.get(i).dy + dy * weights[i]);
            if (a == null) return List.of();
            result.add(a);
        }
        return List.copyOf(result);
    }
    static List<List<Direction>> feints(final RaceGame game, final StrategyState root,
            final List<Direction> base, final StrategyState.Budget budget) {
        if (base.size() != 4) return List.of();
        final Own initial = Own.of(root.board.cars[root.slot()]);
        final Own target = follow(game, initial, base, budget);
        if (target == null || target.finished()) return List.of();
        final List<List<Direction>> result = new ArrayList<>();
        for (final Direction axis : Direction.values()) {
            if (axis == Direction.NONE) continue;
            final List<Direction> trial = pulse(base, axis.dx, axis.dy);
            if (!trial.isEmpty() && target.equals(follow(game, initial, trial, budget))) result.add(trial);
        }
        return List.copyOf(result);
    }
}
