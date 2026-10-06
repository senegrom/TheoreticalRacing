package tr.logic;

/** Cheap offensive nominations. These are proposals, not opponent-delay proofs. */
final class TrafficOpportunities {
    private TrafficOpportunities() {}

    static int distance(final RaceGame game, final RaceGame.MoveResult move,
            final int x, final int y, final int vx, final int vy) {
        if (!move.legal()) return Integer.MAX_VALUE;
        if (move.finishes()) return 0;
        final OptimalPotential pot = game.optimalPotential();
        return game.lapGates == null ? game.reach.turnsToFinish(x, y, vx, vy)
                : pot == null ? Integer.MAX_VALUE : pot.movesToFinish(
                        OptimalPotential.remainingEvents(move.gateAfter(), move.lapAfter(), game.totalLaps),
                        x, y, vx, vy);
    }

    static RaceGame.MoveResult ownMove(final RaceGame game, final int self, final Direction action) {
        final Player me = game.players[self];
        final int[] x = me.getPosition(), v = me.getVelocity();
        return game.evaluateMove(me, x, new int[]{x[0] + v[0] + action.dx, x[1] + v[1] + action.dy});
    }

    static int ownDistance(final RaceGame game, final int self, final Direction action) {
        final Player me = game.players[self];
        final int[] x = me.getPosition(), v = me.getVelocity();
        final int vx = v[0] + action.dx, vy = v[1] + action.dy;
        if (RaceGame.aiVelocityOutOfRange(vx, vy)) return Integer.MAX_VALUE;
        return distance(game, ownMove(game, self, action), x[0] + vx, x[1] + vy, vx, vy);
    }

    static int nextLive(final RaceGame game, final int self) {
        for (int offset = 1; offset < game.players.length; offset++) {
            final int slot = (self + offset) % game.players.length;
            if (!game.players[slot].isFinished()) return slot;
        }
        return -1;
    }

    /** -1 means unavailable: no preferred physical reply or an unpriced legal reply.
     * A legal finish is one move regardless of post-finish landing occupancy. */
    static int replyCost(final RaceGame game, final int self, final int rival, final Direction action) {
        final Player me = game.players[self], other = game.players[rival];
        final int[] x = me.getPosition(), v = me.getVelocity();
        final int blockX = x[0] + v[0] + action.dx, blockY = x[1] + v[1] + action.dy;
        final int[] p = other.getPosition(), velocity = other.getVelocity();
        int best = Integer.MAX_VALUE;
        boolean unpriced = false;
        for (final Direction d : Direction.values()) {
            final int vx = velocity[0] + d.dx, vy = velocity[1] + d.dy;
            if (other.isAi() && RaceGame.aiVelocityOutOfRange(vx, vy)) continue;
            final int nx = p[0] + vx, ny = p[1] + vy;
            boolean occupied = nx == blockX && ny == blockY;
            for (int i = 0; i < game.players.length; i++) {
                final Player q = game.players[i];
                if (i != self && i != rival && !q.isFinished())
                    occupied |= q.getPosition()[0] == nx && q.getPosition()[1] == ny;
            }
            final RaceGame.MoveResult move = game.evaluateMove(other.getLap(), other.getNextGate(),
                    game.gridLegalFor(other), p[0], p[1], nx, ny, occupied);
            if (!move.legal()) continue;
            if (move.finishes()) return 1;
            final int remaining = distance(game, move, nx, ny, vx, vy);
            if (remaining == Integer.MAX_VALUE) unpriced = true;
            else best = Math.min(best, remaining + 1);
        }
        return unpriced || best == Integer.MAX_VALUE ? -1 : best;
    }

    static Direction nominate(final RaceGame game, final Direction nominal, final int maxRemaining) {
        final int self = game.subgamestate, rival = nextLive(game, self);
        if (rival < 0 || ownMove(game, self, nominal).finishes()) return null;
        final int mine = ownDistance(game, self, nominal);
        if (mine == Integer.MAX_VALUE || mine > maxRemaining) return null;
        final int baseline = replyCost(game, self, rival, nominal);
        if (baseline < 0) return null;
        Direction best = null;
        int bestReply = baseline;
        for (final Direction d : Direction.values()) {
            if (d == nominal || ownDistance(game, self, d) != mine || ownMove(game, self, d).finishes()) continue;
            final int reply = replyCost(game, self, rival, d);
            if (reply > bestReply) { bestReply = reply; best = d; }
        }
        return best;
    }

    static boolean stagedBetter(final int verdict, final double concession,
            final int incumbent, final double incumbentConcession) {
        return verdict >= 0 && verdict != Integer.MAX_VALUE
                && (incumbent < 0 || verdict < incumbent
                        || verdict == incumbent && concession < incumbentConcession);
    }
}
