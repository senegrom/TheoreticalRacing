package tr.logic;

/** Exact one-move tactics, not another score or opponent-policy prediction.
 * With two live cars the opponent moves next, even across the array wrap.
 * A legal move occupying its sole non-finishing landing forces its retirement;
 * the referee then classifies the survivor in the best remaining place.
 */
final class RaceAiTactics {
    private static final Direction[] DIRECTIONS = Direction.values();

    private RaceAiTactics() {}

    /** Return an immediate finish or a proven last-rival blockade; otherwise
     * abstain and leave the existing policy untouched. Does not mutate players,
     * progress, occupancy, caches of predictions, or the decision frame. */
    static Direction winNow(final RaceGame game, final int playerNumber) {
        if (game.raceTurnLimitReached())
            return null;
        Player me = null, rival = null;
        for (final Player p : game.players) {
            if (p.isFinished())
                continue;
            if (p.getNumber() == playerNumber)
                me = p;
            else if (rival == null)
                rival = p;
            else
                return null; // Another mover could vacate a blocker or finish first.
        }
        if (me == null || rival == null)
            return null;
        final int[] pos = me.getPosition(), vel = me.getVelocity();
        final int[] rp = rival.getPosition(), rv = rival.getVelocity();
        // Take the flag before considering a block. A checkpoint and the final
        // line may be passed on the SAME move, so use the full referee result.
        for (final Direction d : DIRECTIONS) {
            final int vx = vel[0] + d.dx, vy = vel[1] + d.dy;
            if (RaceGame.aiVelocityOutOfRange(vx, vy))
                continue;
            final int x = pos[0] + vx, y = pos[1] + vy;
            if (game.evaluateMove(me.getLap(), me.getNextGate(), pos[0], pos[1], x, y,
                    x == rp[0] && y == rp[1]).finishes())
                return d;
        }

        int escapeX = 0, escapeY = 0, escapes = 0;
        for (final Direction d : DIRECTIONS) {
            final int x = rp[0] + rv[0] + d.dx, y = rp[1] + rv[1] + d.dy;
            // Remove my OLD cell: I am about to vacate it. Count all physically
            // legal replies, including reachability-dead ones and accelerations
            // beyond the AI planning cap (a human may take those).
            final RaceGame.MoveResult reply = game.evaluateMove(rival.getLap(), rival.getNextGate(),
                    rp[0], rp[1], x, y, false);
            if (reply.finishes())
                return null; // A genuine finish cannot be blocked at its landing.
            if (reply.legal()) {
                if (++escapes > 1)
                    return null; // Distinct accelerations have distinct landings.
                escapeX = x;
                escapeY = y;
            }
        }
        if (escapes != 1)
            return null; // No tactical intervention is needed for an already boxed car.
        final int vx = escapeX - pos[0], vy = escapeY - pos[1];
        if (RaceGame.aiVelocityOutOfRange(vx, vy))
            return null;
        for (final Direction d : DIRECTIONS) {
            if (vx != vel[0] + d.dx || vy != vel[1] + d.dy)
                continue;
            if (game.evaluateMove(me.getLap(), me.getNextGate(), pos[0], pos[1], escapeX, escapeY,
                    escapeX == rp[0] && escapeY == rp[1]).legal())
                return d;
        }
        return null;
    }
}
