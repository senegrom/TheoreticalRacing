package tr.logic;

import java.awt.geom.PathIterator;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.List;

/** Offline race tails and a bounded placement model. All hypothetical players
 * are detached; live objects, classification, clock and grid world are restored.
 * rc3 carries the decision-relevant ledger, including exact leftGrid and places.
 * UI history is not a policy input and is deliberately not serialized.
 */
final class RacecraftReplay {
    private RacecraftReplay() {}

    static final class Board {
        final int turn, laps, slot, first, last;
        final String identity;
        final int[][] cars;
        Board(final int turn, final int laps, final int slot, final int first, final int last,
                final String identity, final int[][] cars) {
            this.turn = turn; this.laps = laps; this.slot = slot; this.first = first; this.last = last;
            this.identity = identity;
            this.cars = Arrays.stream(cars).map(int[]::clone).toArray(int[][]::new);
        }
        Board withStart(final int self, final int x, final int y) {
            final int[][] copy = Arrays.stream(cars).map(int[]::clone).toArray(int[][]::new);
            copy[self][2] = x; copy[self][3] = y;
            return new Board(turn, laps, 0, first, last, identity, copy);
        }
        String encode() {
            final StringBuilder out = new StringBuilder("rc3,").append(turn).append(',').append(laps)
                    .append(',').append(slot).append(',').append(first).append(',').append(last)
                    .append(',').append(identity);
            for (final int[] car : cars) {
                out.append(';');
                for (int j = 0; j < car.length; j++) { if (j > 0) out.append(','); out.append(car[j]); }
            }
            return out.toString();
        }
    }

    static Board capture(final RaceGame game) {
        final int[][] cars = new int[game.players.length][14];
        for (int i = 0; i < cars.length; i++) {
            final Player p = game.players[i];
            final int[] row = cars[i];
            row[0] = p.getNumber(); row[1] = p.getKind().ordinal();
            row[2] = p.getPosition()[0]; row[3] = p.getPosition()[1];
            row[4] = p.getVelocity()[0]; row[5] = p.getVelocity()[1];
            row[6] = p.getFinishedPlace();
            System.arraycopy(p.lapState(), 0, row, 7, 7);
        }
        return new Board(game.turnCount(), game.totalLaps, game.subgamestate,
                game.researchFinishedFirst(), game.researchFinishedLast(), identity(game), cars);
    }

    static String snapshot(final RaceGame game) { return capture(game).encode(); }

    static Board parse(final RaceGame game, final String text) {
        if (text.length() > 16384) throw new IllegalArgumentException("rc3 too long");
        final String[] parts = text.split(";", -1), h = parts[0].split(",", -1);
        if (parts.length != game.players.length + 1 || h.length != 7 || !h[0].equals("rc3"))
            throw new IllegalArgumentException("invalid rc3 header/roster");
        final int turn = Integer.parseInt(h[1]), laps = Integer.parseInt(h[2]);
        final int slot = Integer.parseInt(h[3]), first = Integer.parseInt(h[4]), last = Integer.parseInt(h[5]);
        final int n = game.players.length;
        if (turn < 0 || turn > Integer.MAX_VALUE - 100001 || laps != game.totalLaps
                || slot < 0 || slot >= n || first < 0 || last < 0 || first + last >= n
                || !identity(game).equals(h[6])) throw new IllegalArgumentException("rc3 context mismatch");
        final int[][] rows = new int[n][14];
        final boolean[] ranks = new boolean[n + 1];
        int completed = 0;
        for (int i = 0; i < n; i++) {
            final String[] values = parts[i + 1].split(",", -1);
            if (values.length != 14) throw new IllegalArgumentException("invalid rc3 car");
            for (int j = 0; j < values.length; j++) rows[i][j] = Integer.parseInt(values[j]);
            final int[] r = rows[i];
            if (r[0] != game.players[i].getNumber() || r[1] != game.players[i].getKind().ordinal()
                    || r[6] < 0 || r[6] > n || r[7] < 0 || r[7] > laps || r[8] < 0 || r[8] > 2
                    || r[13] < 0 || r[13] > 1 || Math.abs((long) r[4]) > 100000
                    || Math.abs((long) r[5]) > 100000)
                throw new IllegalArgumentException("invalid rc3 car ledger");
            for (int j = 9; j <= 12; j++) if (r[j] < 0)
                throw new IllegalArgumentException("negative trace ledger");
            if (r[6] != 0) {
                if (ranks[r[6]] || r[6] > first && r[6] <= n - last)
                    throw new IllegalArgumentException("inconsistent rc3 classification");
                ranks[r[6]] = true; completed++;
            } else {
                if (r[2] < 0 || r[2] > game.gameCols || r[3] < 0 || r[3] > game.gameRows
                        || r[7] == laps) throw new IllegalArgumentException("invalid live rc3 car");
                for (int j = 0; j < i; j++) if (rows[j][6] == 0 && rows[j][2] == r[2] && rows[j][3] == r[3])
                    throw new IllegalArgumentException("duplicate live rc3 cell");
            }
        }
        if (completed != first + last || rows[slot][6] != 0)
            throw new IllegalArgumentException("incomplete rc3 classification");
        return new Board(turn, laps, slot, first, last, h[6], rows);
    }

    /** Geometry and behavior controls, not incidental audit/file paths. */
    static String identity(final RaceGame game) {
        final StringBuilder s = new StringBuilder("racecraft-rc3-v1;").append(game.gameCols).append(',')
                .append(game.gameRows).append(';').append(game.totalLaps).append(';')
                .append(game.researchFinishIdentity()).append(';')
                .append(game.racecraftNext.signature());
        if (game.track != null) {
            for (final int[] p : game.track.getLeft()) s.append('L').append(Arrays.toString(p));
            for (final int[] p : game.track.getRight()) s.append('R').append(Arrays.toString(p));
        }
        if (game.finishLine != null) s.append(';').append(game.finishLine.getX1()).append(',')
                .append(game.finishLine.getY1()).append(',').append(game.finishLine.getX2()).append(',')
                .append(game.finishLine.getY2());
        final double[] points = new double[6];
        if (game.startZoneA != null) for (final PathIterator it = game.startZoneA.getPathIterator(null);
                !it.isDone(); it.next()) {
            Arrays.fill(points, 0.0); s.append(';').append(it.currentSegment(points)).append(Arrays.toString(points));
        }
        for (final Player p : game.players) s.append(';').append(p.getNumber()).append(':')
                .append(p.getKind()).append(':').append(game.candidatePolicy(p.getNumber()));
        return sha(s.toString());
    }

    static String sha(final String text) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                .digest(text.getBytes(StandardCharsets.UTF_8))); }
        catch (final NoSuchAlgorithmException e) { throw new AssertionError(e); }
    }

    /** Replaces only detached player objects, never mutating live histories. */
    private static final class Scope implements AutoCloseable {
        final RaceGame game;
        final Player[] players;
        final int slot, turn, first, last;
        final boolean grid, replay;
        Scope(final RaceGame game, final Board board) {
            this.game = game; players = game.players; slot = game.subgamestate; turn = game.turnCount();
            first = game.researchFinishedFirst(); last = game.researchFinishedLast();
            grid = game.aiGridLegal; replay = game.racecraftReplay;
            final Player[] detached = new Player[players.length];
            for (int i = 0; i < detached.length; i++) {
                final Player original = players[i]; final int[] row = board.cars[i];
                final Player p = new Player(original.getName(), original.getNumber(), original.getColor(), original.getKind());
                p.setPosition(new int[]{row[2], row[3]}); p.setVelocity(new int[]{row[4], row[5]});
                p.setFinishedPlace(row[6]); p.restoreLapState(Arrays.copyOfRange(row, 7, 14));
                detached[i] = p;
            }
            game.players = detached; game.subgamestate = board.slot; game.setQueryTurnCounter(board.turn);
            game.researchClassification(board.first, board.last); game.racecraftReplay = true;
        }
        @Override public void close() {
            game.players = players; game.subgamestate = slot; game.setQueryTurnCounter(turn);
            game.researchClassification(first, last); game.aiGridLegal = grid; game.racecraftReplay = replay;
        }
    }

    record Tail(boolean complete, int place, int ownMoves, RacecraftOutcome outcome,
            String finalState, List<String> trace) {
        Tail { trace = List.copyOf(trace); }
    }

    /** Same transition/classification rules as commitMove, without UI or timers.
     * Tests replay the very same actions through the live commitMove referee. */
    static String advance(final RaceGame game, final Direction d) {
        final Player p = game.players[game.subgamestate];
        if (p.isFinished()) throw new IllegalStateException("retired mover");
        final int[] x = p.getPosition(), v = p.getVelocity();
        final int[] nv = {v[0] + d.dx, v[1] + d.dy}, nx = {x[0] + nv[0], x[1] + nv[1]};
        final boolean timeout = game.raceTurnLimitReached();
        final RaceGame.MoveResult result = timeout ? null : game.evaluateMove(p, x, nx);
        int first = game.researchFinishedFirst(), last = game.researchFinishedLast();
        final String status = timeout ? "TIMEOUT" : result.finishes() ? "FINISH"
                : !result.legal() ? "CRASH" : result.lapCross() ? "LAP" : "OK";
        if (!timeout) {
            if (result.passCp1()) { p.setNextGate(2); p.passGate(1); }
            if (result.passCp2()) { p.setNextGate(0); p.passGate(2); }
        }
        if (timeout || !result.legal() || result.finishes()) {
            p.setFinishedPlace(!timeout && result.finishes() ? ++first : game.players.length - last++);
            p.logPosition(nx); p.setPosition(new int[]{Player.INIT_POS, Player.INIT_POS});
            p.setVelocity(new int[]{0, 0});
        } else {
            if (result.lapCross()) { p.incrementLap(); p.setNextGate(1); }
            p.setPosition(nx); p.setVelocity(nv); p.logPosition(nx);
            if (result.lapCross()) p.passGate(0);
            if (game.startZoneA != null && !game.startZoneA.contains(nx[0], nx[1])) p.leaveGrid();
        }
        game.setQueryTurnCounter(game.turnCount() + 1);
        game.researchClassification(first, last);
        return game.subgamestate + ":" + d + ":" + nx[0] + ":" + nx[1] + ":" + nv[0] + ":" + nv[1]
                + ":" + status + ":" + p.getFinishedPlace() + ":" + p.getLap() + ":" + p.getNextGate()
                + ":" + (p.hasLeftGrid() ? 1 : 0) + ":" + game.turnCount();
    }

    private static boolean classifyLast(final RaceGame game) {
        Player survivor = null; int live = 0;
        for (final Player p : game.players) if (!p.isFinished()) { live++; survivor = p; }
        if (live == 0) return true;
        if (live == 1 && game.players.length > 1) {
            final int first = game.researchFinishedFirst() + 1;
            survivor.setFinishedPlace(first);
            game.researchClassification(first, game.researchFinishedLast());
            return true;
        }
        return false;
    }

    static Tail run(final RaceGame game, final Board root, final int self, final Direction first,
            final int maxMoves, final boolean scorerOnly) {
        if (maxMoves < 1 || self < 0 || self >= root.cars.length)
            throw new IllegalArgumentException("invalid tail budget/mover");
        final List<String> trace = new ArrayList<>();
        try (Scope ignored = new Scope(game, root)) {
            final RaceAi policy = new RaceAi(game);
            int own = 0; boolean complete = classifyLast(game), firstAction = true;
            RacecraftOutcome.Status focalStatus = RacecraftOutcome.Status.RUNNING;
            for (int step = 0; step < maxMoves && !complete; step++) {
                final int slot = game.subgamestate;
                if (game.players[slot].isFinished()) throw new IllegalStateException("retired tail slot");
                if (!game.players[slot].isAi()) throw new IllegalArgumentException("real-policy tails require AI-only rosters");
                final Direction action = game.raceTurnLimitReached() ? Direction.NONE
                        : firstAction && first != null ? first
                        : scorerOnly ? policy.researchScorer() : policy.computeAiMove();
                if (action == null) return new Tail(false, 0, own, RacecraftOutcome.unknown(), snapshot(game), trace);
                firstAction = false;
                if (slot == self) own++;
                final String transition = advance(game, action);
                trace.add(transition);
                if (slot == self && game.players[self].isFinished()) focalStatus = transition.contains(":FINISH:")
                        ? RacecraftOutcome.Status.FINISHED : RacecraftOutcome.Status.CRASHED;
                complete = classifyLast(game);
                if (complete && focalStatus == RacecraftOutcome.Status.RUNNING && game.players[self].isFinished())
                    focalStatus = RacecraftOutcome.Status.CLASSIFIED;
                if (!complete) {
                    int next = slot;
                    do { next = (next + 1) % game.players.length; } while (game.players[next].isFinished());
                    game.subgamestate = next;
                }
            }
            final Player me = game.players[self];
            final int place = me.getFinishedPlace();
            final int remaining;
            if (place != 0) remaining = 0;
            else {
                final int[] x = me.getPosition(), v = me.getVelocity();
                final OptimalPotential potential = game.optimalPotential();
                remaining = game.lapGates == null ? game.reach.turnsToFinish(x[0], x[1], v[0], v[1])
                        : potential == null ? Integer.MAX_VALUE : potential.movesToFinish(
                                OptimalPotential.remainingEvents(me.getNextGate(), me.getLap(), game.totalLaps),
                                x[0], x[1], v[0], v[1]);
            }
            final int ahead = place != 0 ? place - 1 : game.researchFinishedFirst();
            final RacecraftOutcome outcome = new RacecraftOutcome(focalStatus, ahead, own, remaining);
            return new Tail(complete, place, own, outcome, snapshot(game), trace);
        }
    }

    /** Only the final AI placer: no guessed future placements or hidden RNG. */
    static int[] chooseStart(final RaceGame game, final Player player, final int[] stock, final int[][] ties) {
        final int self = player.getNumber() - 1;
        if (ties.length < 2 || game.subgamestate != game.players.length - 1 || self != game.subgamestate
                || game.turnCount() != 0) return stock;
        for (final Player p : game.players) {
            if (!p.isAi() || p.isFinished() || p.getLap() != 0 || p.getVelocity()[0] != 0 || p.getVelocity()[1] != 0
                    || p.getNumber() != player.getNumber() && p.getPosition()[0] == Player.INIT_POS) return stock;
        }
        final Board root = capture(game);
        final int budget = 3 * game.players.length;
        final Tail baseline = run(game, root.withStart(self, stock[0], stock[1]), self, null, budget, true);
        if (!baseline.outcome().known()) return stock;
        RacecraftOutcome best = baseline.outcome(); int[] selected = stock;
        int trials = 1;
        for (final int[] cell : ties) {
            if (Arrays.equals(cell, stock)) continue;
            if (trials++ >= 4) break;
            final Tail trial = run(game, root.withStart(self, cell[0], cell[1]), self, null, budget, true);
            if (trial.outcome().betterThan(best, false)) { best = trial.outcome(); selected = cell.clone(); }
        }
        return selected;
    }

    /** cf3,maxMoves,observedAction|rc3...; observed '-' is for constructed tests.
     * Always run every legal first action and the observed control to completion
     * or an explicitly marked work limit. Never treat a truncated tail as a label. */
    static String answer(final RaceGame game, final String line) {
        final int divider = line.indexOf('|');
        if (divider < 0 || line.length() > 17000) throw new IllegalArgumentException("invalid cf3 request");
        final String[] h = line.substring(0, divider).split(",", -1);
        if (h.length != 3) throw new IllegalArgumentException("cf3 requires bound and observed action");
        final int bound = Integer.parseInt(h[1]);
        if (bound < 1 || bound > 100000) throw new IllegalArgumentException("cf3 bound out of range");
        final Board root = parse(game, line.substring(divider + 1));
        final Direction actual;
        try (Scope ignored = new Scope(game, root)) { actual = new RaceAi(game).computeAiMove(); }
        if (!h[2].equals("-") && !h[2].equals(actual.name()))
            throw new IllegalArgumentException("observed action does not replay; reject this corpus case");
        final StringBuilder json = new StringBuilder("{\"schema\":3,\"baseline\":\"").append(actual)
                .append("\",\"rootIdentity\":\"").append(root.identity).append("\",\"trials\":[");
        boolean comma = false;
        for (final Direction d : Direction.values()) {
            final boolean legal;
            try (Scope ignored = new Scope(game, root)) {
                final Player p = game.players[root.slot]; final int[] x = p.getPosition(), v = p.getVelocity();
                legal = !game.raceTurnLimitReached() && !RaceGame.aiVelocityOutOfRange(v[0] + d.dx, v[1] + d.dy)
                        && game.evaluateMove(p, x, new int[]{x[0] + v[0] + d.dx, x[1] + v[1] + d.dy}).legal();
            }
            if (!legal && d != actual) continue;
            final Tail result = run(game, root, root.slot, d, bound, false);
            if (comma) json.append(','); comma = true;
            json.append("{\"action\":\"").append(d).append("\",\"legal\":").append(legal)
                    .append(",\"complete\":").append(result.complete()).append(",\"place\":").append(result.place())
                    .append(",\"ownMoves\":").append(result.ownMoves()).append(",\"status\":\"")
                    .append(result.outcome().status()).append("\",\"traceSha256\":\"")
                    .append(sha(String.join("\n", result.trace()))).append("\",\"trace\":[");
            for (int k = 0; k < result.trace().size(); k++) {
                if (k > 0) json.append(','); json.append('"').append(result.trace().get(k)).append('"');
            }
            json.append("],\"finalState\":\"").append(result.finalState()).append("\"}");
        }
        return json.append("]}").toString();
    }
}
