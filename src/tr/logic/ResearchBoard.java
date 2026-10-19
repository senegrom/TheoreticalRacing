package tr.logic;

import java.awt.Shape;
import java.awt.geom.PathIterator;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Complete, build/world/profile-bound snapshots for research. The detached
 * transition calls the live move referee and shares its timeout comparator.
 * A horizon/budget stop is UNKNOWN, never a finish or a forced-win certificate. */
final class ResearchBoard {
    final int slot, turns, laps, first, last;
    final int[][] cars;
    final String context;
    final DecisionResearch.Plans plans;

    private ResearchBoard(final int slot, final int turns, final int laps, final int first,
            final int last, final int[][] cars, final String context, final DecisionResearch.Plans plans) {
        this.slot = slot; this.turns = turns; this.laps = laps;
        this.first = first; this.last = last; this.cars = cars; this.context = context; this.plans = plans;
    }

    static ResearchBoard capture(final RaceGame game) {
        final int[][] cars = new int[game.players.length][12];
        for (int i = 0; i < cars.length; i++) {
            final Player p = game.players[i];
            cars[i][0] = p.getPosition()[0]; cars[i][1] = p.getPosition()[1];
            cars[i][2] = p.getVelocity()[0]; cars[i][3] = p.getVelocity()[1];
            cars[i][4] = p.getFinishedPlace();
            System.arraycopy(p.lapState(), 0, cars[i], 5, 7);
        }
        return new ResearchBoard(game.subgamestate, game.turnCount(), game.totalLaps,
                game.researchFinishedFirst(), game.researchFinishedLast(), cars,
                context(game), game.research.plans);
    }

    /** Grid entitlement is cars[i][11]; no inference from current position. */
    String encode() {
        final StringBuilder b = new StringBuilder("rp3,").append(slot).append(',').append(turns)
                .append(',').append(laps).append(',').append(first).append(',').append(last)
                .append(',').append(context).append(',').append(plans.encode());
        appendCars(b);
        return b.toString();
    }

    String physicalKey() {
        final StringBuilder b = new StringBuilder(context).append(',').append(slot).append(',')
                .append(turns).append(',').append(laps).append(',').append(first).append(',').append(last);
        // Display trace indices are not policy state and may be trimmed by UI.
        for (final int[] car : cars) {
            b.append(';');
            for (int i = 0; i <= 6; i++) b.append(car[i]).append(',');
            b.append(car[11]);
        }
        // The mover's own table contains this key and is therefore excluded;
        // every OTHER actor's pending policy state is a real assumption.
        for (int i = 0; i < cars.length; i++) if (i != slot)
            b.append('|').append(i).append(':').append(new java.util.TreeMap<>(plans.seats().get(i)));
        return sha256(b.toString());
    }

    private void appendCars(final StringBuilder b) {
        for (final int[] car : cars) {
            b.append(';');
            for (int j = 0; j < car.length; j++) b.append(j == 0 ? "" : ",").append(car[j]);
        }
    }

    static ResearchBoard parse(final RaceGame game, final String text) {
        if (text.length() > 16384) throw new IllegalArgumentException("research snapshot too long");
        final String[] parts = text.split(";", -1), h = parts[0].split(",", -1);
        if (parts.length != game.players.length + 1 || h.length != 8 || !h[0].equals("rp3"))
            throw new IllegalArgumentException("invalid research snapshot shape");
        final int slot = Integer.parseInt(h[1]), turns = Integer.parseInt(h[2]), laps = Integer.parseInt(h[3]);
        final int first = Integer.parseInt(h[4]), last = Integer.parseInt(h[5]), n = game.players.length;
        if (slot < 0 || slot >= n || turns < 0 || laps != game.totalLaps || first < 0 || last < 0
                || first + last > n || !h[6].equals(context(game)))
            throw new IllegalArgumentException("research snapshot context/ledger mismatch");
        final DecisionResearch.Plans plans = DecisionResearch.Plans.parse(h[7], n);
        final int[][] cars = new int[n][12];
        final boolean[] places = new boolean[n + 1];
        int retired = 0;
        for (int i = 0; i < n; i++) {
            final String[] row = parts[i + 1].split(",", -1);
            if (row.length != 12) throw new IllegalArgumentException("research car requires 12 fields");
            for (int j = 0; j < 12; j++) cars[i][j] = Integer.parseInt(row[j]);
            final int[] c = cars[i];
            if (c[4] < 0 || c[4] > n || c[5] < 0 || c[5] > laps || c[6] < 0 || c[6] > 2
                    || c[11] < 0 || c[11] > 1 || RaceGame.aiVelocityOutOfRange(c[2], c[3]))
                throw new IllegalArgumentException("invalid research car kinematics or progress");
            for (int j = 7; j <= 10; j++)
                if (c[j] < 0 || c[j] > turns) throw new IllegalArgumentException("invalid trace ledger");
            if (c[4] == 0) {
                if (c[5] == laps || c[0] < 0 || c[1] < 0 || c[0] > game.gameCols || c[1] > game.gameRows)
                    throw new IllegalArgumentException("invalid live research car");
                for (int j = 0; j < i; j++)
                    if (cars[j][4] == 0 && cars[j][0] == c[0] && cars[j][1] == c[1])
                        throw new IllegalArgumentException("duplicate live research cell");
            } else {
                retired++;
                if (places[c[4]] || c[0] != Player.INIT_POS || c[1] != Player.INIT_POS || c[2] != 0 || c[3] != 0)
                    throw new IllegalArgumentException("invalid retired research car");
                places[c[4]] = true;
            }
        }
        // A pre-decision snapshot has no automatically classified survivor yet.
        if (retired != first + last || cars[slot][4] != 0)
            throw new IllegalArgumentException("snapshot is not a live decision");
        for (int p = 1; p <= n; p++)
            if (places[p] != (p <= first || p > n - last))
                throw new IllegalArgumentException("snapshot finishing/retirement ledger is inconsistent");
        final ResearchBoard board = new ResearchBoard(slot, turns, laps, first, last, cars, h[6], plans);
        if (!board.encode().equals(text)) throw new IllegalArgumentException("noncanonical research snapshot");
        return board;
    }

    static String context(final RaceGame g) {
        final StringBuilder b = new StringBuilder(DecisionResearch.engineId()).append(';')
                .append(g.research.replayId).append(';').append(g.gameCols).append(',').append(g.gameRows)
                .append(',').append(g.totalLaps).append(';').append(Arrays.toString(g.crossingIdentity()))
                .append(';').append(g.lapIdentity());
        if (g.track != null) {
            for (final int[] p : g.track.getLeft()) b.append(Arrays.toString(p));
            b.append('|');
            for (final int[] p : g.track.getRight()) b.append(Arrays.toString(p));
        }
        shape(b, g.trackA); shape(b, g.startZoneA);
        for (final Player p : g.players)
            b.append(';').append(p.getNumber()).append(':').append(p.getKind()).append(':')
                    .append(g.candidatePolicy(p.getNumber()));
        return sha256(b.toString());
    }

    private static void shape(final StringBuilder b, final Shape shape) {
        b.append('|');
        if (shape == null) return;
        final double[] coords = new double[6];
        for (final PathIterator it = shape.getPathIterator(null); !it.isDone(); it.next()) {
            Arrays.fill(coords, 0.0);
            b.append(it.currentSegment(coords)).append(Arrays.toString(coords));
        }
    }

    static String sha256(final String text) {
        try {
            return java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(text.getBytes(StandardCharsets.UTF_8)));
        } catch (final NoSuchAlgorithmException impossible) { throw new AssertionError(impossible); }
    }

    /** Scope restores references, clocks, classification, AI grid frame and plan
     * state even on failure. A fresh AI handles a detached continuation. */
    static final class Scope implements AutoCloseable {
        private final RaceGame game;
        private final Player[] players;
        private final int slot, turns, first, last, nested;
        private final boolean grid, allowResponse;
        private final DecisionResearch.Plans plans;
        Scope(final RaceGame game, final ResearchBoard board) {
            this.game = game; players = game.players; slot = game.subgamestate;
            turns = game.turnCount(); first = game.researchFinishedFirst(); last = game.researchFinishedLast();
            grid = game.aiGridLegal; plans = game.research.plans;
            nested = game.research.suppressed; allowResponse = game.research.allowResponse;
            final Player[] copy = new Player[players.length];
            for (int i = 0; i < copy.length; i++) {
                final Player original = players[i]; final int[] c = board.cars[i];
                copy[i] = new Player(original.getName(), original.getNumber(), original.getColor(), original.getKind());
                copy[i].setPosition(new int[]{c[0], c[1]}); copy[i].setVelocity(new int[]{c[2], c[3]});
                copy[i].setFinishedPlace(c[4]); copy[i].restoreLapState(Arrays.copyOfRange(c, 5, 12));
                // Trace lengths affect only display marks, but exact snapshots retain them.
                for (final int[] p : original.getHistory()) copy[i].getHistory().add(p.clone());
            }
            game.players = copy; game.subgamestate = board.slot; game.setQueryTurnCounter(board.turns);
            game.researchLedger(board.first, board.last); game.research.plans = board.plans;
            game.research.detached++;
        }
        @Override public void close() {
            game.players = players; game.subgamestate = slot; game.setQueryTurnCounter(turns);
            game.researchLedger(first, last); game.aiGridLegal = grid; game.research.plans = plans;
            game.research.suppressed = nested; game.research.allowResponse = allowResponse; game.research.detached--;
        }
    }

    static List<Direction> legal(final RaceGame game) {
        final Player p = game.players[game.subgamestate];
        final int[] x = p.getPosition(), v = p.getVelocity();
        final List<Direction> result = new ArrayList<>();
        if (p.isFinished() || game.raceTurnLimitReached()) return result;
        for (final Direction d : Direction.values()) {
            final int vx = v[0] + d.dx, vy = v[1] + d.dy;
            if (!RaceGame.aiVelocityOutOfRange(vx, vy)
                    && game.evaluateMove(p, x, new int[]{x[0] + vx, x[1] + vy}).legal()) result.add(d);
        }
        return result;
    }

    static int distance(final RaceGame game, final int slot) {
        final Player p = game.players[slot];
        if (p.isFinished()) return 0;
        final int[] x = p.getPosition(), v = p.getVelocity();
        final OptimalPotential potential = game.optimalPotential();
        if (potential != null) return potential.movesToFinish(OptimalPotential.remainingEvents(
                p.getNextGate(), p.getLap(), game.totalLaps), x[0], x[1], v[0], v[1]);
        return game.lapGates == null ? game.reach.turnsToFinish(x[0], x[1], v[0], v[1])
                : game.reach.turnsToGate(p.getNextGate(), x[0], x[1], v[0], v[1]);
    }

    static boolean classify(final RaceGame game, final String[] outcomes) {
        int live = 0, survivor = -1;
        for (int i = 0; i < game.players.length; i++) if (!game.players[i].isFinished()) { live++; survivor = i; }
        if (live > (game.players.length == 1 ? 0 : 1)) return false;
        if (survivor >= 0) {
            retire(game.players[survivor], game.researchFinishedFirst() + 1);
            outcomes[survivor] = "SURVIVOR";
        }
        return true;
    }

    private static void retire(final Player p, final int place) {
        p.setFinishedPlace(place); p.setPosition(new int[]{Player.INIT_POS, Player.INIT_POS});
        p.setVelocity(new int[]{0, 0});
    }

    static void expire(final RaceGame game, final String[] outcomes, final int[] moves, final List<String> trace) {
        final List<RaceGame.Standing> order = new ArrayList<>();
        for (int k = 0; k < game.players.length; k++) {
            final Player p = game.players[(game.subgamestate + k) % game.players.length];
            if (!p.isFinished()) {
                final int[] x = p.getPosition(), v = p.getVelocity();
                final int t = game.reach.turnsToGate(p.getNextGate(), x[0], x[1], v[0], v[1]);
                order.add(new RaceGame.Standing(p, OptimalPotential.remainingEvents(p.getNextGate(),
                        p.getLap(), game.totalLaps), t, k));
            }
        }
        order.sort(RaceGame.BY_PROGRESS);
        int last = game.researchFinishedLast();
        for (int k = order.size() - 1; k >= (game.players.length == 1 ? 0 : 1); k--) {
            final Player p = order.get(k).player();
            outcomes[p.getNumber() - 1] = "TIMEOUT"; moves[p.getNumber() - 1]++;
            final int place = game.players.length - last++;
            final int[] x = p.getPosition(), v = p.getVelocity();
            trace.add((p.getNumber() - 1) + ":" + Direction.NONE.ordinal() + ":" + x[0] + "," + x[1]
                    + "," + v[0] + "," + v[1] + ":" + x[0] + "," + x[1] + "," + v[0] + "," + v[1]
                    + ":TIMEOUT:" + p.getLap() + "," + p.getNextGate() + "," + place);
            retire(p, place); game.setQueryTurnCounter(game.turnCount() + 1);
        }
        game.researchLedger(game.researchFinishedFirst(), last); classify(game, outcomes);
    }

    /** One exact live-referee transition; no GUI, logging, process exit or search. */
    static String advance(final RaceGame game, final Direction action, final String[] outcomes, final int[] moves) {
        final int slot = game.subgamestate; final Player p = game.players[slot];
        final int[] x = p.getPosition(), v = p.getVelocity();
        final int vx = v[0] + action.dx, vy = v[1] + action.dy;
        final int[] to = {x[0] + vx, x[1] + vy};
        final RaceGame.MoveResult result = game.evaluateMove(p, x, to);
        moves[slot]++; game.setQueryTurnCounter(game.turnCount() + 1);
        if (result.passCp1()) { p.setNextGate(2); p.passGate(1); }
        if (result.passCp2()) { p.setNextGate(0); p.passGate(2); }
        final String status;
        if (result.finishes()) {
            status = "FINISH"; game.researchLedger(game.researchFinishedFirst() + 1, game.researchFinishedLast());
            retire(p, game.researchFinishedFirst()); outcomes[slot] = status;
        } else if (!result.legal()) {
            status = "CRASH"; retire(p, game.players.length - game.researchFinishedLast());
            game.researchLedger(game.researchFinishedFirst(), game.researchFinishedLast() + 1); outcomes[slot] = status;
        } else {
            status = result.lapCross() ? "LAP" : "OK";
            if (result.lapCross()) { p.incrementLap(); p.setNextGate(1); }
            p.setPosition(to); p.setVelocity(new int[]{vx, vy}); p.logPosition(to);
            if (result.lapCross()) p.passGate(0);
            if (game.startZoneA != null && !game.startZoneA.contains(to[0], to[1])) p.leaveGrid();
        }
        return slot + ":" + action.ordinal() + ":" + x[0] + "," + x[1] + "," + v[0] + "," + v[1]
                + ":" + to[0] + "," + to[1] + "," + vx + "," + vy + ":" + status
                + ":" + p.getLap() + "," + p.getNextGate() + "," + p.getFinishedPlace();
    }

    static void next(final RaceGame game) {
        for (int k = 1; k <= game.players.length; k++) {
            final int i = (game.subgamestate + k) % game.players.length;
            if (!game.players[i].isFinished()) { game.subgamestate = i; return; }
        }
    }
}
