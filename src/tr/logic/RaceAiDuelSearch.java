package tr.logic;

import java.util.HashMap;
import java.util.Map;

/** Bounded proofs against every physical reply of the last live rival.
 * Experimental retention/caching is per decision and never changes the referee. */
final class RaceAiDuelSearch {
    private static final Direction[] DIRECTIONS = Direction.values();
    private static final int UNKNOWN = Integer.MAX_VALUE;
    private static final int DEFAULT_BUDGET = 20_000;

    private RaceAiDuelSearch() {}

    private record State(int x, int y, int vx, int vy, int lap, int gate) {
        static State of(final Player p) {
            final int[] xy = p.getPosition(), v = p.getVelocity();
            return new State(xy[0], xy[1], v[0], v[1], p.getLap(), p.getNextGate());
        }
        State after(final Direction d, final RaceGame.MoveResult m) {
            return new State(x + vx + d.dx, y + vy + d.dy, vx + d.dx, vy + d.dy,
                    m.lapAfter(), m.gateAfter());
        }
    }

    /** The table belongs to one game, grid-rule world and horizon attempt.
     * Both cars, side to move, exact clock and remaining depth distinguish nodes. */
    private record Key(State mine, State rival, long turn, int ownMovesLeft, boolean ourTurn) {}

    record SearchResult(Direction move, int nodes, int cacheHits, boolean exhausted,
            boolean completedProof, boolean retainedProof) {}

    private static final class Budget {
        private int left;
        private int nodes;
        private int cacheHits;
        private boolean exhausted;
        private final Map<Key, Integer> memo;

        Budget(final int limit, final boolean cache) {
            if (limit < 0) throw new IllegalArgumentException("negative duel budget");
            left = limit;
            memo = cache ? new HashMap<>() : null;
        }
        boolean take() {
            if (left > 0) {
                left--;
                nodes++;
                return true;
            }
            exhausted = true;
            return false;
        }
        Integer get(final Key key) {
            final Integer value = memo == null ? null : memo.get(key);
            if (value != null) cacheHits++;
            return value;
        }
        int store(final Key key, final int value) {
            // UNKNOWN without exhaustion means only "no certificate at this depth",
            // never a game-theoretic loss. Incomplete searches are not cached.
            if (memo != null && !exhausted) memo.put(key, value);
            return value;
        }
        SearchResult result(final Direction best, final boolean retain) {
            final Direction move = exhausted && !retain ? null : best;
            return new SearchResult(move, nodes, cacheHits, exhausted, best != null,
                    exhausted && best != null && retain);
        }
    }

    static Direction winWithinTwoMoves(final RaceGame game, final int playerNumber) {
        return search(game, playerNumber, 2, DEFAULT_BUDGET, false, false).move();
    }

    static Direction winWithinThreeMoves(final RaceGame game, final int playerNumber) {
        final Direction shorter = winWithinTwoMoves(game, playerNumber);
        return shorter != null ? shorter
                : search(game, playerNumber, 3, DEFAULT_BUDGET, false, false).move();
    }

    static Direction winWithinFourMoves(final RaceGame game, final int playerNumber) {
        final Direction shorter = winWithinThreeMoves(game, playerNumber);
        return shorter != null ? shorter
                : search(game, playerNumber, 4, DEFAULT_BUDGET, false, false).move();
    }

    /** Candidate-only variants, also used for behavior-invisible root diagnostics. */
    static Direction winWithinFourMoves(final RaceGame game, final int playerNumber,
            final boolean retain, final boolean cache, final boolean audit) {
        for (int depth = 2; depth <= 4; depth++) {
            final SearchResult result = search(game, playerNumber, depth, DEFAULT_BUDGET, retain, cache);
            if (audit) {
                System.err.println("RACECRAFT_DUEL {\"schema\":1,\"turn\":" + game.turnCount()
                        + ",\"player\":" + playerNumber + ",\"depth\":" + depth
                        + ",\"nodes\":" + result.nodes() + ",\"cacheHits\":" + result.cacheHits()
                        + ",\"exhausted\":" + result.exhausted()
                        + ",\"completedProof\":" + result.completedProof()
                        + ",\"retainedProof\":" + result.retainedProof() + "}");
            }
            if (result.move() != null) return result.move();
        }
        return null;
    }

    /** Package-visible budget seam for independent, low-budget soundness tests. */
    static SearchResult search(final RaceGame game, final int playerNumber, final int ownMoves,
            final int limit, final boolean retain, final boolean cache) {
        if (ownMoves < 1 || ownMoves > 4) throw new IllegalArgumentException("duel depth outside 1..4");
        final Budget budget = new Budget(limit, cache);
        Player me = null, rival = null;
        for (final Player p : game.players) {
            if (p.isFinished()) continue;
            if (p.getNumber() == playerNumber) me = p;
            else if (rival == null) rival = p;
            else return budget.result(null, retain);
        }
        if (me == null || rival == null || timedOut(game, game.turnCount()))
            return budget.result(null, retain);
        final State mine = State.of(me), theirs = State.of(rival);
        // A genuine finish needs no tree budget; all initial finishes precede setups.
        for (final Direction d : DIRECTIONS)
            if (inPlanningDomain(mine, d) && move(game, mine, theirs, d).finishes())
                return budget.result(d, retain);
        Direction best = null;
        int bestHorizon = UNKNOWN;
        for (final Direction d : DIRECTIONS) {
            if (!inPlanningDomain(mine, d)) continue;
            final RaceGame.MoveResult first = move(game, mine, theirs, d);
            if (!first.legal()) continue;
            final int horizon = afterOurMove(game, mine.after(d, first), theirs,
                    (long) game.turnCount() + 1, ownMoves - 1, budget);
            if (horizon < bestHorizon) {
                best = d;
                bestHorizon = horizon;
                if (horizon == 1) break;
            }
            if (budget.exhausted) break;
        }
        // Exhaustion cannot refute an earlier, fully completed existential proof.
        // Default control deliberately retains the old abstention for measurement.
        return budget.result(best, retain);
    }

    /** Universal node: EVERY physical reply must lose. One unknown refutes a proof. */
    private static int afterOurMove(final RaceGame game, final State mine, final State rival,
            final long turn, final int ownMovesLeft, final Budget budget) {
        final Key key = budget.memo == null ? null : new Key(mine, rival, turn, ownMovesLeft, false);
        final Integer cached = budget.get(key);
        if (cached != null) return cached;
        if (!budget.take()) return UNKNOWN;
        if (timedOut(game, turn)) return budget.store(key, 1);
        int worst = 1;
        for (final Direction reply : DIRECTIONS) {
            // No AI speed cap or reachability filtering on the rival's physical replies.
            final RaceGame.MoveResult result = move(game, rival, mine, reply);
            if (result.finishes()) return budget.store(key, UNKNOWN);
            if (!result.legal()) continue;
            if (ownMovesLeft == 0) return budget.store(key, UNKNOWN);
            final int continuation = ourMove(game, mine, rival.after(reply, result), turn + 1,
                    ownMovesLeft, budget);
            if (continuation == UNKNOWN) return budget.store(key, UNKNOWN);
            worst = Math.max(worst, 1 + continuation);
        }
        return budget.store(key, worst);
    }

    /** Existential node: a completed winning continuation survives an unfinished sibling. */
    private static int ourMove(final RaceGame game, final State mine, final State rival,
            final long turn, final int ownMovesLeft, final Budget budget) {
        final Key key = budget.memo == null ? null : new Key(mine, rival, turn, ownMovesLeft, true);
        final Integer cached = budget.get(key);
        if (cached != null) return cached;
        if (!budget.take()) return UNKNOWN;
        if (timedOut(game, turn)) return budget.store(key, UNKNOWN);
        int best = UNKNOWN;
        for (final Direction d : DIRECTIONS) {
            if (!inPlanningDomain(mine, d)) continue;
            final RaceGame.MoveResult result = move(game, mine, rival, d);
            if (result.finishes()) return budget.store(key, 1);
            if (result.legal()) {
                final int tail = afterOurMove(game, mine.after(d, result), rival, turn + 1,
                        ownMovesLeft - 1, budget);
                if (tail != UNKNOWN) best = Math.min(best, 1 + tail);
            }
            if (budget.exhausted) break;
        }
        return budget.store(key, best);
    }

    private static boolean inPlanningDomain(final State state, final Direction d) {
        return !RaceGame.aiVelocityOutOfRange(state.vx + d.dx, state.vy + d.dy);
    }

    private static RaceGame.MoveResult move(final RaceGame game, final State mover,
            final State blocker, final Direction d) {
        final int x = mover.x + mover.vx + d.dx, y = mover.y + mover.vy + d.dy;
        return game.evaluateMove(mover.lap, mover.gate, mover.x, mover.y, x, y,
                x == blocker.x && y == blocker.y);
    }

    private static boolean timedOut(final RaceGame game, final long turn) {
        return game.lapGates != null && turn > (long) game.totalLaps * 750 * game.players.length;
    }
}
