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

        /** perf duelproof: the same landing, with the lap and gate after that a legal,
         *  non-finishing move's code holds (codeOf). */
        State after(final Direction d, final int code) {
            return new State(x + vx + d.dx, y + vy + d.dy, vx + d.dx, vy + d.dy,
                    lap + (code >>> LAP_STEP_SHIFT & 1), code >>> GATE_SHIFT & 3);
        }
    }

    /** Return a certified win within two of our own moves, otherwise null.
     * Prefer the smallest worst-case terminal horizon, then enum order.
     * The existing one-move tactic runs first in the production entry point.
     */
    static Direction winWithinTwoMoves(final RaceGame game, final int playerNumber) {
        return winWithinMoves(game, playerNumber, 2, null);
    }

    /** Try the old two-move certificate first, then one additional own move.
     * Budget exhaustion is an abstention, never a win. The extra search is
     * candidate-only; existing shorter certificates retain their move order. */
    static Direction winWithinThreeMoves(final RaceGame game, final int playerNumber) {
        final Direction shorter = winWithinTwoMoves(game, playerNumber);
        return shorter != null ? shorter : winWithinMoves(game, playerNumber, 3, null);
    }

    /** Round 240 (PROMOTED): one more own move again, shorter certificates
     * first. Budget exhaustion is an abstention, never a win. */
    static Direction winWithinFourMoves(final RaceGame game, final int playerNumber) {
        final Direction shorter = winWithinThreeMoves(game, playerNumber);
        return shorter != null ? shorter : winWithinMoves(game, playerNumber, 4, null);
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

    // perf duelproof: 'given' is check mode's Budget, so that it can compare node counts with
    // the tabled search; every other caller passes null and gets a new Budget as before.
    private static Direction winWithinMoves(final RaceGame game, final int playerNumber,
            final int ownMoves, final Budget given) {
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
        final Budget budget = given != null ? given : new Budget();
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

    // ------------------------------------------------------------------------ perf duelproof
    // perf duelproof (exact): RaceAiTactics.winNow with each car state's moves asked of the
    // referee once per call instead of once per visit.
    //
    // The proofs ask evaluateMove about single-car moves of a joint tree, and the same
    // question recurs: the root asks each own move twice (finish loop, main loop),
    // afterOurMove asks the rival's replies from one rival state once for every own line
    // above it, and the 2-, 3- and 4-move searches of a real decision repeat each other's
    // trees, after immediateWin asked the two root states. evaluateMove(lap, gate, x, y, nx,
    // ny, occupied) is a pure function of its arguments, the grid world (aiGridLegal, read
    // per call) and the course; within one winNow nothing writes any of them (aiGridLegal is
    // set only by prepareDecisionFrame, before winNow; the proofs only read the game and its
    // players), and the caches it fills are exact memos. It reads 'occupied' only in
    // legal = geometryLegal && (finishing || !occupied), so the blocked answer is the
    // unblocked one, except that a legal, non-finishing landing on the blocker's cell becomes
    // MoveResult(false, true, false, false, false, false, lap, gate). Of an answer the proofs
    // read only legal(), finishes(), and of a legal, non-finishing one lapAfter() and
    // gateAfter() (State.after). So a row per car state (x, y, vx, vy, lap, gate) keeps its
    // nine unblocked answers as codes, each asked of the referee at its first need (so never
    // more often than the original asks), and move() derives the blocked answer. The tabled
    // immediate win and searches are the originals line for line -- the same loops in the
    // same order, the same early exits, the same Budget taken at the same node entries --
    // with move() reading a row instead of calling the referee.

    /** -Dai.perf.noDuelProof=true: winNow runs the original code above (winNowOriginal), a
     *  same-jar CPU control. */
    static final boolean PERF_NO_DUEL_PROOF = Boolean.getBoolean("ai.perf.noDuelProof");
    /** The stage's self-check, -Dai.perf.check=true (the property RaceAi.PERF_CHECK reads):
     *  every table answer is compared with the referee's, every tabled search with the
     *  original search (its node count too), the tabled immediate win and the whole tabled
     *  winNow with the originals; the race continues with the originals' answers, and a
     *  difference prints a PERF-AWARE DUELPROOF MISMATCH line. */
    private static final boolean PERF_CHECK = Boolean.getBoolean("ai.perf.check");
    /** -Dai.perf.duelProofStats=true: the counters below, one PERF-STATS DUELPROOF line at
     *  exit. No decision reads them. */
    private static final boolean PERF_DUEL_PROOF_STATS = Boolean.getBoolean("ai.perf.duelProofStats");

    /** A referee answer as the proofs read it, six bits: KNOWN (0 means not asked yet),
     *  LEGAL, FINISHES, and for a legal, non-finishing move the lap step (lapAfter - lap,
     *  0 or 1) at LAP_STEP_SHIFT and the gate after (0..3) at GATE_SHIFT. A row packs a car
     *  state's nine codes into one long, direction d at bit CODE_BITS * d.ordinal(). */
    private static final int KNOWN = 1, LEGAL = 2, FINISHES = 4, LAP_STEP_SHIFT = 3, GATE_SHIFT = 4,
            CODE_BITS = 6, CODE_MASK = (1 << CODE_BITS) - 1;

    /** One thread's rows, reused by every winNow it runs: open() starts a new epoch, which
     *  empties the table in O(1) (a slot belongs to the epoch its stamp names). Open
     *  addressing with linear probing on the packed car state, at most ROW_CAP rows an
     *  epoch (load 3/4); past the cap, and for a state outside the key's range, move() asks
     *  the referee directly, as the original does. A 4-move chain expands at most
     *  2 * (1 + 9 + 81 + 729) = 1640 car states, under the cap. 4096 slots of 20 bytes: 80 KiB
     *  per thread that ever runs a duel proof (in the browser, the AI's one thread). */
    private static final class Table {
        private static final int BITS = 12, SLOTS = 1 << BITS, MASK = SLOTS - 1, ROW_CAP = SLOTS / 4 * 3;
        private final long[] keys = new long[SLOTS];
        private final long[] rows = new long[SLOTS];
        private final int[] stamps = new int[SLOTS];
        private int epoch, used;
        /** PERF_DUEL_PROOF_STATS only: this winNow's counts, flushed at its end. */
        private long searches, nodes, asks, evals, hits, blocked, bypass;

        void open() {
            if (++epoch == 0) {
                java.util.Arrays.fill(stamps, 0);
                epoch = 1;
            }
            used = 0;
        }

        /** The row of car state s, or -1 when s is outside the key's range (x and y in
         *  0..65535, vx and vy in -128..127, lap in 0..255, gate in 0..3: an injective
         *  58-bit key) or the table holds ROW_CAP rows. */
        int slot(final State s) {
            final int vx = s.vx + 128, vy = s.vy + 128;
            if ((s.x >>> 16 | s.y >>> 16 | vx >>> 8 | vy >>> 8 | s.lap >>> 8 | s.gate >>> 2) != 0)
                return -1;
            final long key = (long) s.x << 42 | (long) s.y << 26 | (long) vx << 18 | (long) vy << 10
                    | (long) s.lap << 2 | s.gate;
            int i = (int) (key * 0x9E3779B97F4A7C15L >>> 64 - BITS);
            while (stamps[i] == epoch) {
                if (keys[i] == key)
                    return i;
                i = i + 1 & MASK;
            }
            if (used == ROW_CAP)
                return -1;
            used++;
            stamps[i] = epoch;
            keys[i] = key;
            rows[i] = 0L;
            return i;
        }
    }

    /** Thread-confined: winNow runs on its game's AI thread and never re-enters itself. */
    private static final ThreadLocal<Table> TABLES = ThreadLocal.withInitial(Table::new);

    /** One tabled winNow: the game, the table, the mover, the two roots and the turn. */
    private record Proof(RaceGame game, Table table, int playerNumber, State mine, State theirs,
            long turn) {}

    /** A referee answer the six-bit code cannot hold: a lap step other than 0 or 1, or a gate
     *  after outside 0..3. Impossible today -- evaluateMove's lapAfter is lap + (crossing &&
     *  !finishing ? 1 : 0), and its gate after is in 0..2 on lap courses and the state's own
     *  gate on point-to-point ones, which onTable checks is in 0..3 for both roots -- but
     *  should evaluateMove change, the whole winNow is answered by the original code. */
    private static final class Unrepresentable extends RuntimeException {
        private static final long serialVersionUID = 1L;
        static final Unrepresentable INSTANCE = new Unrepresentable();

        private Unrepresentable() {
            super(null, null, false, false);
        }
    }

    /** RaceAiTactics.winNow on this thread's table (check mode: compared with the original,
     *  which the race then uses). */
    static Direction winNowTabled(final RaceGame game, final int playerNumber, final boolean realDecision) {
        final Direction tabled = onTable(game, playerNumber, realDecision);
        if (!PERF_CHECK)
            return tabled;
        final Direction original = RaceAiTactics.winNowOriginal(game, playerNumber, realDecision);
        if (tabled != original)
            System.err.println("PERF-AWARE DUELPROOF MISMATCH winNow p=" + playerNumber + " real="
                    + realDecision + " turn=" + game.turnCount() + " original=" + original
                    + " tabled=" + tabled);
        return original;
    }

    /** The original's legs share one scan: immediateWin and every winWithinMoves scan the
     *  players alike and abstain at a third live car or a missing mover or rival, and
     *  immediateWin's raceTurnLimitReached is the searches' timedOut(game, turnCount()); a
     *  board where they abstain answers null here without opening the table. Otherwise the
     *  legs run in the original's order on the two roots each of them would build (the game
     *  does not change during the call). */
    private static Direction onTable(final RaceGame game, final int playerNumber,
            final boolean realDecision) {
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
        if (me == null || rival == null || game.raceTurnLimitReached())
            return null;
        final State mine = State.of(me), theirs = State.of(rival);
        if (((mine.gate | theirs.gate) & ~3) != 0) {
            if (PERF_DUEL_PROOF_STATS)
                DUEL_PROOF_STATS.incrementAndGet(ST_FALLBACKS);
            return RaceAiTactics.winNowOriginal(game, playerNumber, realDecision);
        }
        final Table table = TABLES.get();
        table.open();
        final Proof p = new Proof(game, table, playerNumber, mine, theirs, game.turnCount());
        boolean fellBack = false;
        try {
            final Direction immediate = tabledImmediateWin(p);
            if (immediate != null)
                return immediate;
            if (!realDecision)
                return tabledWinWithin(p, 2);
            final Direction two = tabledWinWithin(p, 2);
            if (two != null)
                return two;
            final Direction three = tabledWinWithin(p, 3);
            return three != null ? three : tabledWinWithin(p, 4);
        } catch (final Unrepresentable e) {
            fellBack = true;
            return RaceAiTactics.winNowOriginal(game, playerNumber, realDecision);
        } finally {
            if (PERF_DUEL_PROOF_STATS)
                flushStats(table, fellBack);
        }
    }

    private static Direction tabledImmediateWin(final Proof p) {
        final Direction tabled = immediateWinOnRows(p);
        if (!PERF_CHECK)
            return tabled;
        final Direction original = RaceAiTactics.immediateWin(p.game, p.playerNumber);
        if (tabled != original)
            System.err.println("PERF-AWARE DUELPROOF MISMATCH immediate p=" + p.playerNumber + " turn="
                    + p.turn + " mine=" + p.mine + " theirs=" + p.theirs + " original=" + original
                    + " tabled=" + tabled);
        return original;
    }

    /** RaceAiTactics.immediateWin past its guards (onTable's), on the rows: its finish loop
     *  is the searches' root finish loop, its replies are the rival root's unblocked row,
     *  and the escape landing's move is one of the root's moves. */
    private static Direction immediateWinOnRows(final Proof p) {
        final State mine = p.mine, theirs = p.theirs;
        final int slot = p.table.slot(mine);
        for (final Direction d : DIRECTIONS) {
            if (inPlanningDomain(mine, d) && (move(p, slot, mine, theirs, d) & FINISHES) != 0)
                return d;
        }
        final int rivalSlot = p.table.slot(theirs);
        int escapeX = 0, escapeY = 0, escapes = 0;
        for (final Direction d : DIRECTIONS) {
            final int x = theirs.x + theirs.vx + d.dx, y = theirs.y + theirs.vy + d.dy;
            final int reply = unblocked(p, rivalSlot, theirs, d);
            if ((reply & FINISHES) != 0)
                return null;
            if ((reply & LEGAL) != 0) {
                if (++escapes > 1)
                    return null;
                escapeX = x;
                escapeY = y;
            }
        }
        if (escapes != 1)
            return null;
        final int vx = escapeX - mine.x, vy = escapeY - mine.y;
        if (RaceGame.aiVelocityOutOfRange(vx, vy))
            return null;
        for (final Direction d : DIRECTIONS) {
            if (vx != mine.vx + d.dx || vy != mine.vy + d.dy)
                continue;
            if ((move(p, slot, mine, theirs, d) & LEGAL) != 0)
                return d;
        }
        return null;
    }

    private static Direction tabledWinWithin(final Proof p, final int ownMoves) {
        final Budget budget = new Budget();
        final int left = budget.left;
        final Direction tabled = searchOnRows(p, ownMoves, budget);
        if (PERF_DUEL_PROOF_STATS) {
            p.table.searches++;
            p.table.nodes += left - budget.left;
        }
        if (!PERF_CHECK)
            return tabled;
        final Budget reference = new Budget();
        final Direction original = winWithinMoves(p.game, p.playerNumber, ownMoves, reference);
        if (tabled != original || budget.left != reference.left || budget.exhausted != reference.exhausted)
            System.err.println("PERF-AWARE DUELPROOF MISMATCH search p=" + p.playerNumber + " moves="
                    + ownMoves + " turn=" + p.turn + " mine=" + p.mine + " theirs=" + p.theirs
                    + " original=" + original + "/" + reference.left + "/" + reference.exhausted
                    + " tabled=" + tabled + "/" + budget.left + "/" + budget.exhausted);
        return original;
    }

    /** winWithinMoves past its guards (onTable's), on the rows. */
    private static Direction searchOnRows(final Proof p, final int ownMoves, final Budget budget) {
        final State mine = p.mine, theirs = p.theirs;
        final long turn = p.turn;
        final int slot = p.table.slot(mine), rivalSlot = p.table.slot(theirs);
        Direction best = null;
        int bestHorizon = UNKNOWN;
        for (final Direction d : DIRECTIONS) {
            if (inPlanningDomain(mine, d) && (move(p, slot, mine, theirs, d) & FINISHES) != 0)
                return d;
        }
        for (final Direction d : DIRECTIONS) {
            if (!inPlanningDomain(mine, d))
                continue;
            final int first = move(p, slot, mine, theirs, d);
            if ((first & LEGAL) == 0)
                continue;
            final int horizon = afterOurMoveOnRows(p, mine.after(d, first), theirs, rivalSlot,
                    turn + 1, ownMoves - 1, budget);
            if (horizon < bestHorizon) {
                best = d;
                bestHorizon = horizon;
                if (horizon == 1)
                    break; // Rival retires next: no non-finishing move can win sooner.
            }
        }
        return budget.exhausted ? null : best;
    }

    /** afterOurMove on the rows; rivalSlot is rival's row, which the caller looked up (a
     *  state's slot does not change within an epoch: rows are only added), so the leaves of
     *  one ourMove node share one lookup. */
    private static int afterOurMoveOnRows(final Proof p, final State mine, final State rival,
            final int rivalSlot, final long turn, final int ownMovesLeft, final Budget budget) {
        if (!budget.take()) return UNKNOWN;
        if (timedOut(p.game, turn))
            return 1;
        int worst = 1;
        for (final Direction reply : DIRECTIONS) {
            final int result = move(p, rivalSlot, rival, mine, reply);
            if ((result & FINISHES) != 0)
                return UNKNOWN;
            if ((result & LEGAL) == 0)
                continue;
            if (ownMovesLeft == 0)
                return UNKNOWN;
            final int continuation = ourMoveOnRows(p, mine, rival.after(reply, result), turn + 1,
                    ownMovesLeft, budget);
            if (continuation == UNKNOWN)
                return UNKNOWN;
            worst = Math.max(worst, 1 + continuation);
        }
        return worst;
    }

    /** ourMove on the rows. */
    private static int ourMoveOnRows(final Proof p, final State mine, final State rival,
            final long turn, final int ownMovesLeft, final Budget budget) {
        if (!budget.take()) return UNKNOWN;
        if (timedOut(p.game, turn))
            return UNKNOWN;
        final int slot = p.table.slot(mine), rivalSlot = p.table.slot(rival);
        int best = UNKNOWN;
        for (final Direction d : DIRECTIONS) {
            if (!inPlanningDomain(mine, d))
                continue;
            final int result = move(p, slot, mine, rival, d);
            if ((result & FINISHES) != 0)
                return 1;
            if ((result & LEGAL) != 0) {
                final int tail = afterOurMoveOnRows(p, mine.after(d, result), rival, rivalSlot,
                        turn + 1, ownMovesLeft - 1, budget);
                if (tail != UNKNOWN) best = Math.min(best, 1 + tail);
            }
        }
        return best;
    }

    /** The original move() as a code: mover's move d with blocker's cell occupied. From the
     *  row, the unblocked answer, blocked (KNOWN alone: illegal, not finishing) when it is a
     *  legal, non-finishing landing on that cell; a state without a row asks the referee. */
    private static int move(final Proof p, final int slot, final State mover, final State blocker,
            final Direction d) {
        final int x = mover.x + mover.vx + d.dx, y = mover.y + mover.vy + d.dy;
        final boolean occupied = x == blocker.x && y == blocker.y;
        if (slot < 0)
            return direct(p, mover, x, y, occupied);
        int code = row(p, slot, mover, d, x, y);
        if (occupied && (code & (LEGAL | FINISHES)) == LEGAL) {
            code = KNOWN;
            if (PERF_DUEL_PROOF_STATS)
                p.table.blocked++;
        }
        return PERF_CHECK ? checked(p, mover, d, x, y, occupied, code) : code;
    }

    /** Mover's move d with no cell occupied (immediateWin's replies), as a code. */
    private static int unblocked(final Proof p, final int slot, final State mover, final Direction d) {
        final int x = mover.x + mover.vx + d.dx, y = mover.y + mover.vy + d.dy;
        if (slot < 0)
            return direct(p, mover, x, y, false);
        final int code = row(p, slot, mover, d, x, y);
        return PERF_CHECK ? checked(p, mover, d, x, y, false, code) : code;
    }

    /** Row slot's code for move d (landing x, y), asked of the referee, unblocked, at its
     *  first need. */
    private static int row(final Proof p, final int slot, final State mover, final Direction d,
            final int x, final int y) {
        final Table t = p.table;
        final int shift = CODE_BITS * d.ordinal();
        int code = (int) (t.rows[slot] >>> shift) & CODE_MASK;
        if (code == 0) {
            code = codeOf(p.game.evaluateMove(mover.lap, mover.gate, mover.x, mover.y, x, y, false),
                    mover.lap);
            t.rows[slot] |= (long) code << shift;
            if (PERF_DUEL_PROOF_STATS)
                t.evals++;
        } else if (PERF_DUEL_PROOF_STATS) {
            t.hits++;
        }
        if (PERF_DUEL_PROOF_STATS)
            t.asks++;
        return code;
    }

    /** A state without a row: the original call itself. */
    private static int direct(final Proof p, final State mover, final int x, final int y,
            final boolean occupied) {
        if (PERF_DUEL_PROOF_STATS) {
            p.table.asks++;
            p.table.evals++;
            p.table.bypass++;
        }
        return codeOf(p.game.evaluateMove(mover.lap, mover.gate, mover.x, mover.y, x, y, occupied),
                mover.lap);
    }

    /** Check mode: the original call's code, which the search then uses; a table answer that
     *  differs prints a MISMATCH line. */
    private static int checked(final Proof p, final State mover, final Direction d, final int x,
            final int y, final boolean occupied, final int code) {
        final int original = codeOf(p.game.evaluateMove(mover.lap, mover.gate, mover.x, mover.y, x, y,
                occupied), mover.lap);
        if (original != code)
            System.err.println("PERF-AWARE DUELPROOF MISMATCH move p=" + p.playerNumber + " turn=" + p.turn
                    + " mover=" + mover + " d=" + d + " occupied=" + occupied + " table=" + code
                    + " original=" + original);
        return original;
    }

    /** The code of a referee answer (Unrepresentable if it does not fit). */
    private static int codeOf(final RaceGame.MoveResult r, final int lap) {
        if (!r.legal())
            return KNOWN;
        if (r.finishes())
            return KNOWN | LEGAL | FINISHES;
        final int step = r.lapAfter() - lap, gate = r.gateAfter();
        if (((step & ~1) | (gate & ~3)) != 0)
            throw Unrepresentable.INSTANCE;
        return KNOWN | LEGAL | step << LAP_STEP_SHIFT | gate << GATE_SHIFT;
    }

    /** PERF_DUEL_PROOF_STATS counters over the whole JVM: tabled winNows (duels), searches,
     *  nodes (Budget takes), asks (the original's evaluateMove calls), evals (the tabled
     *  path's), hits (row answers), blocked (answers derived as blocked), bypass (asks of
     *  states without a row), rows (rows claimed), maxRows (the most in one winNow),
     *  fallbacks (winNows answered by the original code). saved = asks - evals. */
    private static final String[] STAT_NAMES = {"duels", "searches", "nodes", "asks", "evals", "hits",
            "blocked", "bypass", "rows", "maxRows", "fallbacks"};
    private static final int ST_DUELS = 0, ST_SEARCHES = 1, ST_NODES = 2, ST_ASKS = 3, ST_EVALS = 4,
            ST_HITS = 5, ST_BLOCKED = 6, ST_BYPASS = 7, ST_ROWS = 8, ST_MAX_ROWS = 9, ST_FALLBACKS = 10;
    private static final java.util.concurrent.atomic.AtomicLongArray DUEL_PROOF_STATS =
            PERF_DUEL_PROOF_STATS ? duelProofCounters() : null;

    private static java.util.concurrent.atomic.AtomicLongArray duelProofCounters() {
        final java.util.concurrent.atomic.AtomicLongArray counts =
                new java.util.concurrent.atomic.AtomicLongArray(STAT_NAMES.length);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            final StringBuilder line = new StringBuilder("PERF-STATS DUELPROOF");
            for (int k = 0; k < STAT_NAMES.length; k++)
                line.append(' ').append(STAT_NAMES[k]).append('=').append(counts.get(k));
            line.append(" saved=").append(counts.get(ST_ASKS) - counts.get(ST_EVALS));
            System.err.println(line);
        }, "perf-stats-duelproof"));
        return counts;
    }

    private static void flushStats(final Table t, final boolean fellBack) {
        final java.util.concurrent.atomic.AtomicLongArray s = DUEL_PROOF_STATS;
        s.incrementAndGet(ST_DUELS);
        s.addAndGet(ST_SEARCHES, t.searches);
        s.addAndGet(ST_NODES, t.nodes);
        s.addAndGet(ST_ASKS, t.asks);
        s.addAndGet(ST_EVALS, t.evals);
        s.addAndGet(ST_HITS, t.hits);
        s.addAndGet(ST_BLOCKED, t.blocked);
        s.addAndGet(ST_BYPASS, t.bypass);
        s.addAndGet(ST_ROWS, t.used);
        s.accumulateAndGet(ST_MAX_ROWS, t.used, Math::max);
        if (fellBack)
            s.incrementAndGet(ST_FALLBACKS);
        t.searches = t.nodes = t.asks = t.evals = t.hits = t.blocked = t.bypass = 0;
    }
}
