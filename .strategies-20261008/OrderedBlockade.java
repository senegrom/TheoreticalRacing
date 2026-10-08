package tr.logic;

/** Refines a positive distinct-car matching result by attempting to realize its
 * blockade in cyclic move order. Only exhaustive NO may clear the old veto.
 * Every live car participates; incomplete work retains the original result. */
final class OrderedBlockade {
    private OrderedBlockade() {}
    enum Verdict { POSSIBLE, IMPOSSIBLE, UNKNOWN }
    static Verdict check(final RaceGame game, final Direction first, final int[] cells,
            final int count, final StrategyState.Budget budget) {
        final StrategyState root = StrategyState.capture(game);
        if (root.live() < 3 || root.live() > 4 || count < 1 || count > 9
                || root.timedOut(game) || !root.ownDomain(first)) return Verdict.UNKNOWN;
        final RaceGame.MoveResult move = root.evaluate(game, first);
        if (move == null || !move.legal()) return Verdict.UNKNOWN;
        if (!budget.take()) return Verdict.UNKNOWN;
        final StrategyState next = root.after(game, first);
        return next == null ? Verdict.UNKNOWN : visit(game, next, root.slot(), cells.clone(), count, budget);
    }
    private static Verdict visit(final RaceGame game, final StrategyState state, final int self,
            final int[] cells, final int count, final StrategyState.Budget budget) {
        if (state.place(self) != 0) return Verdict.IMPOSSIBLE; // already classified: cannot be boxed
        if (!budget.take() || state.timedOut(game)) return Verdict.UNKNOWN;
        if (state.slot() == self) {
            for (int e = 0; e < count; e++) {
                boolean occupied = false;
                for (int i = 0; i < state.board.cars.length; i++) {
                    final int[] row = state.board.cars[i];
                    if (i != self && row[6] == 0 && row[2] == cells[2 * e] && row[3] == cells[2 * e + 1]) {
                        occupied = true; break;
                    }
                }
                if (!occupied) return Verdict.IMPOSSIBLE;
            }
            return Verdict.POSSIBLE;
        }
        boolean unknown = false;
        for (final Direction action : Direction.values()) {
            if (!budget.take()) return Verdict.UNKNOWN;
            final StrategyState next = state.after(game, action);
            if (next == null) { unknown = true; continue; }
            final Verdict verdict = visit(game, next, self, cells, count, budget);
            if (verdict == Verdict.POSSIBLE) return verdict;
            if (verdict == Verdict.UNKNOWN) unknown = true;
        }
        return unknown ? Verdict.UNKNOWN : Verdict.IMPOSSIBLE;
    }
}
