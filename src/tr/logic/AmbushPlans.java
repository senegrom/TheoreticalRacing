package tr.logic;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/** Target-first interception proposals. A mandatory cell is reported only after
 * a COMPLETE layer of the rival's mapped minimum-time graph. Inverse kinematics
 * then looks for an own route to that cell on the corresponding response cycle.
 * This is a mapped-route statement, not a physical or whole-race guarantee. */
final class AmbushPlans {
    private AmbushPlans() {}
    record Target(int x, int y, int ownPly) {}
    static List<Target> mandatory(final RaceGame game, final CreativePaths.Own initial,
            final int depth, final StrategyState.Budget budget) {
        final List<Target> result = new ArrayList<>();
        Set<CreativePaths.Own> layer = Set.of(initial);
        for (int ply = 1; ply <= depth; ply++) {
            final Set<CreativePaths.Own> next = new LinkedHashSet<>();
            boolean terminal = false;
            for (final CreativePaths.Own state : layer) {
                final int remaining = CreativePaths.distance(game, state);
                if (remaining == Integer.MAX_VALUE || remaining == 0) return List.copyOf(result);
                int successors = 0;
                for (final Direction a : Direction.values()) {
                    if (!budget.take()) return List.copyOf(result); // incomplete layer cannot imply a bottleneck
                    final CreativePaths.Own child = CreativePaths.step(game, state, a);
                    if (child != null && CreativePaths.distance(game, child) == remaining - 1) {
                        next.add(child); successors++; terminal |= child.finished();
                    }
                }
                if (successors == 0) return List.copyOf(result); // map/physical grid-world mismatch
            }
            if (next.isEmpty() || terminal) return List.copyOf(result);
            final CreativePaths.Own first = next.iterator().next();
            boolean common = true;
            for (final CreativePaths.Own state : next) common &= state.x() == first.x() && state.y() == first.y();
            if (common && ply >= 2) result.add(new Target(first.x(), first.y(), ply));
            layer = next;
        }
        return List.copyOf(result);
    }
    static List<List<Direction>> intercept(final RaceGame game, final CreativePaths.Own initial,
            final Target target, final StrategyState.Budget budget) {
        return intercept(game,initial,target,budget,0);
    }
    static List<List<Direction>> intercept(final RaceGame game, final CreativePaths.Own initial,
            final Target target, final StrategyState.Budget budget, final int allowance) {
        if(allowance<0||allowance>1) throw new IllegalArgumentException("investment allowance");
        final List<List<Direction>> result = new ArrayList<>();
        final int k = target.ownPly(), startDistance = CreativePaths.distance(game, initial);
        if (k < 1 || k > 3 || startDistance == Integer.MAX_VALUE) return List.of();
        // The finish velocity is not guessed from track geometry. Enumerate the
        // complete k-step acceleration band, ordered around the current velocity.
        for (int radius = 0; radius <= k && result.size() < 2; radius++)
            for (int dx = -radius; dx <= radius && result.size() < 2; dx++)
                for (int dy = -radius; dy <= radius && result.size() < 2; dy++) {
                    if (Math.max(Math.abs(dx), Math.abs(dy)) != radius) continue;
                    backward(game, initial, target.x(), target.y(), initial.vx() + dx, initial.vy() + dy,
                            k, new ArrayList<>(), startDistance + allowance, result, budget);
                    if (budget.left() == 0) return List.copyOf(result);
                }
        return List.copyOf(result);
    }
    private static void backward(final RaceGame game, final CreativePaths.Own initial,
            final int x, final int y, final int vx, final int vy, final int left,
            final List<Direction> reverse, final int reference, final List<List<Direction>> result,
            final StrategyState.Budget budget) {
        if (result.size() >= 2 || !budget.take()) return;
        if (RaceGame.aiVelocityOutOfRange(vx, vy) || Math.abs(vx - initial.vx()) > left
                || Math.abs(vy - initial.vy()) > left) return;
        final long slack = (long) left * (left + 1) / 2;
        if (Math.abs((long) x - initial.x() - (long) left * initial.vx()) > slack
                || Math.abs((long) y - initial.y() - (long) left * initial.vy()) > slack) return;
        if (left == 0) {
            if (x != initial.x() || y != initial.y() || vx != initial.vx() || vy != initial.vy()) return;
            final List<Direction> actions = new ArrayList<>();
            for (int i = reverse.size() - 1; i >= 0; i--) actions.add(reverse.get(i));
            final CreativePaths.Own end = CreativePaths.follow(game, initial, actions, budget);
            final int remaining = CreativePaths.distance(game, end);
            if (end != null && !end.finished() && remaining != Integer.MAX_VALUE
                    && (long) remaining + actions.size() <= reference && !result.contains(actions))
                result.add(List.copyOf(actions));
            return;
        }
        // x_(t-1) = x_t - v_t, v_(t-1) = v_t - a_t.
        final long px = (long) x - vx, py = (long) y - vy;
        if (px < 0 || py < 0 || px > game.gameCols || py > game.gameRows) return;
        for (final Direction a : Direction.values()) {
            reverse.add(a);
            backward(game, initial, (int) px, (int) py, vx - a.dx, vy - a.dy, left - 1,
                    reverse, reference, result, budget);
            reverse.remove(reverse.size() - 1);
            if (budget.left() == 0 || result.size() >= 2) return;
        }
    }
    static List<List<Direction>> propose(final RaceGame game, final StrategyState root,
            final int target, final int nodeCap) {
        if (target < 0 || nodeCap < 2) return List.of();
        final StrategyState.Budget graph = new StrategyState.Budget(nodeCap / 2);
        final List<Target> targets = mandatory(game, CreativePaths.Own.of(root.board.cars[target]), 3, graph);
        final StrategyState.Budget inverse = new StrategyState.Budget(nodeCap - graph.used());
        final List<List<Direction>> result = new ArrayList<>();
        for (final Target cell : targets) {
            for (final List<Direction> path : intercept(game, CreativePaths.Own.of(root.board.cars[root.slot()]), cell, inverse))
                if (!result.contains(path) && result.size() < 2) result.add(path);
            if (inverse.left() == 0) break;
        }
        return List.copyOf(result);
    }
}
