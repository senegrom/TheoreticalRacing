package tr.logic;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Bounded absolute-place certificates. Unknown is not a loss and a guaranteed
 * second never automatically dominates an unproved possible win. Search results
 * nominate actions to the existing evaluator unless they certify the duel win. */
final class PlaceCertificates {
    private PlaceCertificates() {}
    record Bound(int place, int ownMoves) {
        boolean betterThan(final Bound other) {
            return other == null || place < other.place || place == other.place && ownMoves < other.ownMoves;
        }
    }
    record Result(Map<Direction, Bound> bounds, int nodes, int forcedNodes) {
        Result { bounds = java.util.Collections.unmodifiableMap(new LinkedHashMap<>(bounds)); }
        Direction best() {
            Direction choice = null; Bound value = null;
            for (final Map.Entry<Direction, Bound> e : bounds.entrySet())
                if (e.getValue().betterThan(value)) { choice = e.getKey(); value = e.getValue(); }
            return choice;
        }
    }
    static Result search(final RaceGame game, final int ownDecisions, final int moveCap,
            final int nodeCap, final boolean extendForced) {
        final StrategyState root = StrategyState.capture(game);
        final Solver solver = new Solver(game, root.slot(), nodeCap, extendForced);
        final Map<Direction, Bound> results = new LinkedHashMap<>();
        if (root.live() < 2 || root.live() > 3 || ownDecisions < 1 || moveCap < 1 || root.timedOut(game))
            return new Result(results, 0, 0);
        for (final Direction action : root.legal(game, true)) {
            if (!solver.budget.take()) break;
            final StrategyState next = root.after(game, action);
            if (next == null) continue;
            final Bound tail = solver.solve(next, ownDecisions - 1, moveCap - 1);
            if (tail != null) results.put(action, new Bound(tail.place(), tail.ownMoves() + 1));
        }
        // Later incomplete alternatives cannot invalidate already completed proofs.
        return new Result(results, solver.budget.used(), solver.forcedNodes);
    }
    private static final class Solver {
        final RaceGame game;
        final int self;
        final boolean forced;
        final StrategyState.Budget budget;
        final Map<String, Bound> cache = new java.util.HashMap<>();
        int forcedNodes;
        Solver(final RaceGame game, final int self, final int nodes, final boolean forced) {
            this.game = game; this.self = self; this.forced = forced; budget = new StrategyState.Budget(nodes);
        }
        Bound solve(final StrategyState input, final int ownLeft, final int movesLeft) {
            if (input.place(self) != 0) return new Bound(input.place(self), 0);
            if (!budget.take()) return null;
            final StrategyState state = input.timedOut(game) ? input.expire(game) : input;
            if (state.place(self) != 0) return new Bound(state.place(self), 0);
            if (movesLeft <= 0) return null;
            final String key = state.key() + ':' + ownLeft + ':' + movesLeft;
            final Bound cached = cache.get(key);
            if (cached != null) return cached;
            final boolean ourTurn = state.slot() == self;
            final List<Direction> legal = state.legal(game, ourTurn);
            // A scorer preference or a finite-map filter must never define 'forced'.
            final boolean freePly = forced && legal.size() == 1;
            if (ourTurn && ownLeft == 0 && !freePly) return null;
            if (freePly) forcedNodes++;
            Bound best = null;
            final Direction[] actions = ourTurn && !legal.isEmpty() ? legal.toArray(Direction[]::new) : Direction.values();
            for (final Direction action : actions) {
                if (ourTurn && !state.ownDomain(action)) continue;
                if (!budget.take()) return ourTurn ? best : null;
                final StrategyState next = state.after(game, action);
                if (next == null) { if (!ourTurn) return null; else continue; }
                final Bound tail = solve(next, ownLeft - (ourTurn && !freePly ? 1 : 0), movesLeft - 1);
                if (tail == null) { if (!ourTurn) return null; else continue; }
                final Bound value = new Bound(tail.place(), tail.ownMoves() + (ourTurn ? 1 : 0));
                if (ourTurn ? value.betterThan(best) : best == null || best.betterThan(value)) best = value;
            }
            if (best != null) cache.put(key, best);
            return best;
        }
    }
}
