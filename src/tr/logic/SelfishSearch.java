package tr.logic;

import java.util.LinkedHashMap;
import java.util.Map;

/** Small max-n terminal model: each actor optimizes its own place, then time.
 * It is an incentive model, NOT an adversarial certificate or a prediction that
 * humans/production policies always behave optimally. Unknown children invalidate
 * an opponent subgame; no convenient completion or focal-player tie breaking. */
final class SelfishSearch {
    private SelfishSearch() {}
    record Vector(int[] places, int[] moves) {
        Vector { places = places.clone(); moves = moves.clone(); }
        Vector step(final int actor) {
            final int[] next = moves.clone(); next[actor]++;
            return new Vector(places, next);
        }
    }
    record Result(Map<Direction, Vector> roots, int nodes) {
        Result { roots = java.util.Collections.unmodifiableMap(new LinkedHashMap<>(roots)); }
        Direction best(final int actor) {
            Direction action = null; Vector best = null;
            for (final Map.Entry<Direction, Vector> e : roots.entrySet())
                if (prefer(actor, e.getValue(), best)) { action = e.getKey(); best = e.getValue(); }
            return action;
        }
    }
    static boolean prefer(final int actor, final Vector candidate, final Vector incumbent) {
        return candidate != null && (incumbent == null || candidate.places()[actor] < incumbent.places()[actor]
                || candidate.places()[actor] == incumbent.places()[actor]
                && candidate.moves()[actor] < incumbent.moves()[actor]);
    }
    static Result search(final RaceGame game, final StrategyState root, final int plies, final int nodeCap) {
        if (plies < 1 || plies > 9 || nodeCap < 0) throw new IllegalArgumentException("invalid selfish budget");
        final StrategyState.Budget budget = new StrategyState.Budget(nodeCap);
        final Map<Direction, Vector> found = new LinkedHashMap<>();
        if (root.live() != 3 || root.timedOut(game)) return new Result(found, 0);
        for (final int[] row : root.board.cars) if (row[6] == 0 && (row[1] != Player.Kind.AI1.ordinal() && row[1] != Player.Kind.AI2.ordinal()))
            return new Result(found, 0);
        final Map<String, Vector> cache = new java.util.HashMap<>();
        for (final Direction action : Direction.values()) {
            if (!root.ownDomain(action) || !budget.take()) continue;
            final RaceGame.MoveResult move = root.evaluate(game, action);
            if (move == null || !move.legal()) continue;
            final StrategyState child = root.after(game, action);
            final Vector value = child == null ? null : solve(game, child, plies - 1, budget, cache);
            if (value != null) found.put(action, value.step(root.slot()));
            if (budget.left() == 0) break;
        }
        return new Result(found, budget.used());
    }
    private static Vector solve(final RaceGame game, final StrategyState input, final int plies,
            final StrategyState.Budget budget, final Map<String, Vector> cache) {
        if (!budget.take()) return null;
        final StrategyState state = input.timedOut(game) ? input.expire(game) : input;
        if (state.live() == 0) {
            final int[] places = new int[state.board.cars.length], moves = new int[places.length];
            for (int i = 0; i < places.length; i++) {
                places[i] = state.place(i);
                if (input.place(i) == 0 && state != input && state.board.cars[i][2] == Player.INIT_POS) moves[i] = 1;
            }
            return new Vector(places, moves);
        }
        if (plies == 0) return null;
        final String key = state.key() + ":" + plies;
        final Vector cached = cache.get(key);
        if (cached != null) return cached;
        final int actor = state.slot();
        // An immediate finish obtains the smallest attainable absolute place in
        // one move. All such actions remove the same body before the next turn.
        for (final Direction action : Direction.values()) {
            if (!state.ownDomain(action)) continue;
            final RaceGame.MoveResult m = state.evaluate(game, action);
            if (m != null && m.finishes()) {
                final Vector tail = solve(game, state.after(game, action), plies - 1, budget, cache);
                final Vector value = tail == null ? null : tail.step(actor);
                if (value != null) cache.put(key, value);
                return value;
            }
        }
        Vector best = null;
        for (final Direction action : Direction.values()) {
            if (!state.ownDomain(action)) continue;
            final StrategyState child = state.after(game, action);
            if (child == null) return null;
            final Vector tail = solve(game, child, plies - 1, budget, cache);
            if (tail == null) return null; // unknown is not a self-sacrificing or dominated response
            final Vector value = tail.step(actor);
            if (prefer(actor, value, best)) best = value; // exact ties retain fixed action order
        }
        if (best != null) cache.put(key, best);
        return best;
    }
}
