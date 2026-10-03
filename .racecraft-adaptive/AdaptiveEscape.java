package tr.logic;

/** Bounded AND/OR escape proof: each physical rival reply may receive a different
 * own answer. This is a finite-horizon certificate, not a promise to win a race.
 * The first version deliberately requires exactly two live cars. */
final class AdaptiveEscape {
    private static final Direction[] DIRECTIONS = Direction.values();
    private AdaptiveEscape() {}

    record State(int x, int y, int vx, int vy, int lap, int gate, boolean leftGrid) {
        static State of(final Player p) {
            return new State(p.getPosition()[0], p.getPosition()[1], p.getVelocity()[0],
                    p.getVelocity()[1], p.getLap(), p.getNextGate(), p.hasLeftGrid());
        }
        State after(final RaceGame game, final Direction d, final RaceGame.MoveResult move) {
            final int nx = x + vx + d.dx, ny = y + vy + d.dy;
            return new State(nx, ny, vx + d.dx, vy + d.dy, move.lapAfter(), move.gateAfter(),
                    leftGrid || game.startZoneA != null && !game.startZoneA.contains(nx, ny));
        }
    }

    static final class Session {
        private final RaceGame game;
        private final State original, rival;
        private final OptimalPotential potential;
        private final boolean supported;
        private int left;
        private int examined;

        Session(final RaceGame game, final int number, final int budget) {
            this.game = game;
            State me = null, opponent = null;
            int live = 0;
            for (final Player p : game.players) if (!p.isFinished()) {
                live++;
                if (p.getNumber() == number) me = State.of(p);
                else opponent = State.of(p);
            }
            original = me; rival = opponent;
            potential = game.optimalPotential();
            supported = live == 2 && me != null && opponent != null
                    && game.players[game.subgamestate].getNumber() == number
                    && (game.lapGates == null || potential != null);
            if (budget < 0) throw new IllegalArgumentException("negative adaptive budget");
            left = budget;
        }

        int examined() { return examined; }

        /** Budget is shared across candidates in this session. No incomplete
         * branch or map-unknown continuation can count as a successful answer. */
        boolean certifies(final int x, final int y, final int vx, final int vy,
                final int cycles, final int escapes) {
            if (!supported || cycles < 1 || cycles > 3 || escapes < 1 || escapes > 9
                    || RaceTimeout.reached(game, game.turnCount()) || left == 0) return false;
            Direction chosen = null;
            for (final Direction d : DIRECTIONS) if (original.vx + d.dx == vx && original.vy + d.dy == vy
                    && (long) original.x + vx == x && (long) original.y + vy == y) chosen = d;
            if (chosen == null || RaceGame.aiVelocityOutOfRange(vx, vy) || !spend()) return false;
            final RaceGame.MoveResult move = move(original, rival, chosen);
            if (move == null || !move.legal()) return false;
            if (move.finishes()) return true;
            final State after = original.after(game, chosen, move);
            if (distance(after) == Integer.MAX_VALUE) return false;
            return replies(after, rival, (long) game.turnCount() + 1, cycles, escapes);
        }

        private boolean spend() {
            if (left == 0) return false;
            left--; examined++; return true;
        }
        private int distance(final State s) {
            return game.lapGates == null ? game.reach.turnsToFinish(s.x, s.y, s.vx, s.vy)
                    : potential.movesToFinish(OptimalPotential.remainingEvents(s.gate, s.lap, game.totalLaps),
                            s.x, s.y, s.vx, s.vy);
        }
        private RaceGame.MoveResult move(final State mover, final State blocker, final Direction d) {
            final long nx = (long) mover.x + mover.vx + d.dx, ny = (long) mover.y + mover.vy + d.dy;
            if (nx < Integer.MIN_VALUE || nx > Integer.MAX_VALUE || ny < Integer.MIN_VALUE || ny > Integer.MAX_VALUE)
                return null;
            return game.evaluateMove(mover.lap, mover.gate, !mover.leftGrid,
                    mover.x, mover.y, (int) nx, (int) ny, nx == blocker.x && ny == blocker.y);
        }
        private boolean replies(final State me, final State opponent, final long turn,
                final int cycles, final int escapes) {
            if (RaceTimeout.reached(game, turn)) return false; // not a tactical permission from an expired clock
            for (final Direction d : DIRECTIONS) {
                if (!spend()) return false;
                // A human's physical acceleration is not bounded by the AI planning cap.
                final RaceGame.MoveResult reply = move(opponent, me, d);
                if (reply == null || !reply.legal()) continue; // retirement gives the sole survivor its place
                if (reply.finishes()) return false; // safety alone cannot justify giving away this duel
                if (!answers(me, opponent.after(game, d, reply), turn + 1, cycles, escapes)) return false;
            }
            return true;
        }
        private boolean answers(final State me, final State opponent, final long turn,
                final int cycles, final int escapes) {
            if (RaceTimeout.reached(game, turn)) return false;
            final int before = distance(me);
            if (before == Integer.MAX_VALUE) return false;
            int count = 0;
            for (final Direction d : DIRECTIONS) {
                if (RaceGame.aiVelocityOutOfRange(me.vx + d.dx, me.vy + d.dy)) continue;
                if (!spend()) return false;
                final RaceGame.MoveResult result = move(me, opponent, d);
                if (result == null || !result.legal()) continue;
                if (result.finishes()) return true;
                final State next = me.after(game, d, result);
                final int after = distance(next);
                if (after < 0 || after >= before) continue;
                if (cycles > 1 && !replies(next, opponent, turn + 1, cycles - 1, escapes)) continue;
                if (++count >= escapes) return true;
            }
            return false;
        }
    }
}
