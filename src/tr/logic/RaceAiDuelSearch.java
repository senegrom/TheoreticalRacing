package tr.logic;

/** Bounded, opponent-policy-independent proofs for the last two live cars.
 * A candidate may set up a finish or blockade on its NEXT move, but only when
 * every physical rival reply loses. Unproved positions stay with the scorer.
 * All state is detached; even nested scorers can call this without restoration.
 */
final class RaceAiDuelSearch {
    private static final Direction[] DIRECTIONS = Direction.values();
    private static final int UNKNOWN = Integer.MAX_VALUE;

    private RaceAiDuelSearch() {}

    private record State(int x, int y, int vx, int vy, int lap, int gate) {
        static State of(final Player player) {
            final int[] p = player.getPosition(), v = player.getVelocity();
            return new State(p[0], p[1], v[0], v[1], player.getLap(), player.getNextGate());
        }

        State after(final Direction d, final RaceGame.MoveResult move) {
            return new State(x + vx + d.dx, y + vy + d.dy, vx + d.dx, vy + d.dy,
                    move.lapAfter(), move.gateAfter());
        }
    }

    /** Return a certified win within two of our own moves, otherwise null.
     * Prefer the smallest worst-case terminal horizon, then enum order.
     * The existing one-move tactic runs first in the production entry point.
     */
    static Direction winWithinTwoMoves(final RaceGame game, final int playerNumber) {
        return winWithinMoves(game, playerNumber, 2);
    }

    /** Try the old two-move certificate first, then one additional own move.
     * Budget exhaustion is an abstention, never a win. The extra search is
     * candidate-only; existing shorter certificates retain their move order. */
    static Direction winWithinThreeMoves(final RaceGame game, final int playerNumber) {
        final Direction shorter = winWithinTwoMoves(game, playerNumber);
        return shorter != null ? shorter : winWithinMoves(game, playerNumber, 3);
    }

    private static final class Budget {
        private int left = 20_000;
        private boolean exhausted;

        boolean take() {
            if (left-- > 0) return true;
            exhausted = true;
            return false;
        }
    }

    private static Direction winWithinMoves(final RaceGame game, final int playerNumber,
            final int ownMoves) {
        Player me = null, rival = null;
        for (final Player player : game.players) {
            if (player.isFinished())
                continue;
            if (player.getNumber() == playerNumber)
                me = player;
            else if (rival == null)
                rival = player;
            else
                return null;
        }
        if (me == null || rival == null || timedOut(game, game.turnCount()))
            return null;
        final State mine = State.of(me), theirs = State.of(rival);
        final long turn = game.turnCount();
        final Budget budget = new Budget();
        Direction best = null;
        int bestHorizon = UNKNOWN;
        // Finish before searching a setup, including combined checkpoint/flag
        // crossings and terminal landings beyond the ordinary track boundary.
        for (final Direction d : DIRECTIONS) {
            if (inPlanningDomain(mine, d) && move(game, mine, theirs, d).finishes())
                return d;
        }
        for (final Direction d : DIRECTIONS) {
            if (!inPlanningDomain(mine, d))
                continue;
            final RaceGame.MoveResult first = move(game, mine, theirs, d);
            if (!first.legal())
                continue;
            final int horizon = afterOurMove(game, mine.after(d, first), theirs, turn + 1, ownMoves - 1, budget);
            if (horizon < bestHorizon) {
                best = d;
                bestHorizon = horizon;
                if (horizon == 1)
                    break; // Rival retires next: no non-finishing move can win sooner.
            }
        }
        return budget.exhausted ? null : best;
    }

    /** Universal rival node. An illegal reply retires it and wins for us;
     * one finishing reply or unproved continuation invalidates this setup.
     * No AI velocity cap, reachability pruning or predicted-policy filtering
     * is allowed here: a human can use any of the nine physical accelerations.
     */
    private static int afterOurMove(final RaceGame game, final State mine, final State rival,
            final long turn, final int ownMovesLeft, final Budget budget) {
        if (!budget.take()) return UNKNOWN;
        if (timedOut(game, turn))
            return 1;
        int worst = 1;
        for (final Direction reply : DIRECTIONS) {
            final RaceGame.MoveResult result = move(game, rival, mine, reply);
            if (result.finishes())
                return UNKNOWN;
            if (!result.legal())
                continue;
            if (ownMovesLeft == 0)
                return UNKNOWN;
            final int continuation = ourMove(game, mine, rival.after(reply, result), turn + 1,
                    ownMovesLeft, budget);
            if (continuation == UNKNOWN)
                return UNKNOWN;
            worst = Math.max(worst, 1 + continuation);
        }
        return worst;
    }

    /** Existential own node: retain the shortest certified continuation.
     * A dead landing is useful only if the rival retires before we move again. */
    private static int ourMove(final RaceGame game, final State mine, final State rival,
            final long turn, final int ownMovesLeft, final Budget budget) {
        if (!budget.take()) return UNKNOWN;
        if (timedOut(game, turn))
            return UNKNOWN;
        int best = UNKNOWN;
        for (final Direction d : DIRECTIONS) {
            if (!inPlanningDomain(mine, d))
                continue;
            final RaceGame.MoveResult result = move(game, mine, rival, d);
            if (result.finishes())
                return 1;
            if (result.legal()) {
                final int tail = afterOurMove(game, mine.after(d, result), rival, turn + 1,
                        ownMovesLeft - 1, budget);
                if (tail != UNKNOWN) best = Math.min(best, 1 + tail);
            }
        }
        return best;
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

    /** The referee checks the counter BEFORE each move. Retired array slots
     * consume no moves but still count in the original roster's turn limit.
     * A long keeps projected arithmetic safe at the query protocol's int limit.
     */
    private static boolean timedOut(final RaceGame game, final long turn) {
        return game.lapGates != null && turn > (long) game.totalLaps * 750 * game.players.length;
    }
}
