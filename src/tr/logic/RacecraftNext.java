package tr.logic;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Research-only candidate allocation and matched-horizon comparisons.
 * Tactical signatures allocate trials; they never award points for obstruction.
 * All estimates, including empirical model intervals, are predictions, not proofs. */
final class RacecraftNext {
    private static final Direction[] DIRS = Direction.values();
    private RacecraftNext() {}

    static List<Direction> shortlist(final RaceGame g, final RacecraftSearch.Board root, final int focal,
            final Direction champion, final double[] scores, final RacecraftConfig c) {
        final List<Direction> pool = new ArrayList<>();
        for (final Direction d : DIRS)
            if (d != champion && !RaceGame.aiVelocityOutOfRange(root.vx[focal] + d.dx, root.vy[focal] + d.dy)
                    && root.transition(g, focal, d).legal()) pool.add(d);
        pool.sort((a, b) -> {
            final int cmp = Double.compare(scores[a.ordinal()], scores[b.ordinal()]);
            return cmp == 0 ? Integer.compare(a.ordinal(), b.ordinal()) : cmp;
        });
        final int count = Math.min(c.alternatives, pool.size());
        final List<Direction> chosen = new ArrayList<>();
        chosen.add(champion);
        for (int i = 0; i < count; i++) chosen.add(pool.get(i));
        if (!c.diverse || count == 0 || count == pool.size()) return chosen;
        // Reserve just the last slot: fixed shortlist size and fixed call budget.
        chosen.remove(chosen.size() - 1);
        final List<int[]> signatures = new ArrayList<>();
        for (final Direction d : chosen) signatures.add(signature(g, root, focal, d));
        Direction representative = null;
        int bestDistance = -1;
        for (final Direction d : pool) if (!chosen.contains(d)) {
            final int[] candidate = signature(g, root, focal, d);
            int distance = Integer.MAX_VALUE;
            for (final int[] existing : signatures) distance = Math.min(distance, distance(candidate, existing));
            // Equal diversity keeps the original score/ordinal ordering.
            if (distance > bestDistance) { bestDistance = distance; representative = d; }
        }
        chosen.add(representative);
        return chosen;
    }

    /** Legal replies on the candidate board are a tactical descriptor, not a
     * simultaneous-move forecast. Intervening responses are replayed by search. */
    static int[] signature(final RaceGame g, final RacecraftSearch.Board root, final int focal,
            final Direction action) {
        final RacecraftSearch.Board b = new RacecraftSearch.Board(root);
        b.step(g, focal, action);
        final int[] s = new int[b.alive.length + 2];
        for (int j = 0; j < b.alive.length; j++) s[j] = legalMask(g, b, j);
        s[s.length - 2] = root.vx[focal] + action.dx;
        s[s.length - 1] = root.vy[focal] + action.dy;
        return s;
    }

    private static int distance(final int[] a, final int[] b) {
        int difference = 0;
        for (int i = 0; i < a.length - 2; i++) difference += 4 * Integer.bitCount(a[i] ^ b[i]);
        return difference + Math.abs(a[a.length - 2] - b[b.length - 2])
                + Math.abs(a[a.length - 1] - b[b.length - 1]);
    }

    private static int legalMask(final RaceGame g, final RacecraftSearch.Board b, final int i) {
        if (!b.alive[i] || b.over() || b.timedOut(g)) return 0;
        int mask = 0;
        for (final Direction d : DIRS) if (b.transition(g, i, d).legal()) mask |= 1 << d.ordinal();
        return mask;
    }

    private static final class Cursor {
        final RacecraftSearch.Board board;
        int slot;
        Cursor(final RaceGame g, final RacecraftSearch.Board root, final int focal, final Direction action) {
            board = new RacecraftSearch.Board(root); board.step(g, focal, action);
            slot = (focal + 1) % board.alive.length;
        }
        boolean cycle(final RaceGame g, final int focal, final RacecraftSearch.Policy policy,
                final RacecraftSearch.Budget budget) {
            for (int k = 0; k < board.alive.length && !board.over() && board.place[focal] == 0; k++) {
                final int mover = slot; slot = (slot + 1) % board.alive.length;
                if (!board.alive[mover]) continue;
                if (board.turns > Integer.MAX_VALUE) return false;
                Direction d = Direction.NONE;
                if (!board.timedOut(g)) {
                    if (!budget.take()) return false;
                    d = policy.choose(board, mover);
                    if (d == null) return false;
                }
                board.step(g, mover, d);
            }
            return true;
        }
    }

    record Comparison(RacecraftSearch.Value[] values, int rounds, String reason) {}

    static Comparison progressive(final RaceGame g, final RacecraftSearch.Board root, final int focal,
            final List<Direction> actions, final RacecraftConfig c, final RacecraftSearch.Policy policy,
            final RacecraftSearch.Budget budget) {
        final List<Cursor> cursors = new ArrayList<>();
        for (final Direction d : actions) cursors.add(new Cursor(g, root, focal, d));
        RacecraftSearch.Value[] completed = null;
        int completedRounds = 0, previousWinner = -1;
        for (int depth = 1; depth <= c.rounds + (c.encounter ? c.extraRounds : 0); depth++) {
            if (depth > c.rounds) {
                boolean encounter = false;
                for (final Cursor x : cursors)
                    if (!x.board.over() && x.board.place[focal] == 0
                            && RacecraftTraffic.graph(g, x.board, x.slot).direct(focal) > 0) encounter = true;
                if (!encounter) break;
            }
            final RacecraftSearch.Value[] stage = new RacecraftSearch.Value[actions.size()];
            boolean comparable = true, allTerminal = true;
            for (int i = 0; i < cursors.size(); i++) {
                final Cursor x = cursors.get(i);
                if (!x.cycle(g, focal, policy, budget))
                    return new Comparison(completed, completedRounds, budget.exhausted ? "budget" : "unknown-policy");
                stage[i] = RacecraftSearch.value(g, x.board, focal, x.slot);
                comparable &= stage[i] != null;
                allTerminal &= x.board.place[focal] > 0;
            }
            // A partially known stage NEVER replaces the last comparable stage.
            if (comparable) {
                int winner = 0;
                for (int i = 1; i < stage.length; i++)
                    if (stage[i].compareTo(stage[winner]) < 0) winner = i;
                if (previousWinner >= 0 && winner != previousWinner) budget.rankingChanges++;
                previousWinner = winner;
                completed = stage; completedRounds = depth;
            }
            if (allTerminal) break;
        }
        return new Comparison(completed, completedRounds, completed == null ? "unknown-leaf" : "complete");
    }

    static Direction improve(final RaceGame g, final RacecraftSearch.Board root, final int focal,
            final Direction champion, final List<Direction> actions, final RacecraftConfig c,
            final RacecraftSearch.Policy policy, final RacecraftSearch.Budget budget) {
        RacecraftSearch.Value[] values = null;
        int rounds = 0;
        String reason = "model";
        if (c.opportunity) {
            if (c.progressive) {
                final Comparison result = progressive(g, root, focal, actions, c, policy, budget);
                values = result.values(); rounds = result.rounds(); reason = result.reason();
            } else {
                values = new RacecraftSearch.Value[actions.size()]; rounds = c.rounds;
                for (int i = 0; i < actions.size(); i++) {
                    final RacecraftSearch.Forecast result = RacecraftSearch.forecast(g, root, focal, actions.get(i), c, policy, budget);
                    if (result.exhausted() || result.value() == null) { values = null; reason = "unknown"; break; }
                    values[i] = result.value();
                }
            }
            if (values == null) {
                budget.diagnostic = diagnostic(champion, champion, actions, null, rounds, budget, reason);
                return champion;
            }
        }
        int best = 0;
        final double[][] f = new double[actions.size()][];
        if (c.learned) for (int i = 0; i < actions.size(); i++)
            f[i] = c.lexicographic ? features(g, root, focal, actions.get(i))
                    : RacecraftSearch.features(g, root, focal, actions.get(i));
        for (int i = 1; i < actions.size(); i++) {
            final int compare = values == null ? 0 : values[i].compareTo(values[best]);
            if (compare < 0 || compare == 0 && c.learned
                    && (c.lexicographic ? modelBetter(c, f[i], f[best], root.alive.length)
                        : c.score(f[i]) < c.score(f[best]))) best = i;
        }
        // Margin and unknown-place abstention are always relative to champion,
        // never a chain of near-ties through arbitrary alternative enumeration.
        if (best != 0 && c.learned && (values == null || values[best].compareTo(values[0]) == 0)) {
            if (c.lexicographic ? !modelBetter(c, f[best], f[0], root.alive.length)
                    : c.score(f[0]) - c.score(f[best]) <= c.margin) best = 0;
        }
        budget.completedRounds = rounds;
        budget.diagnostic = diagnostic(champion, actions.get(best), actions, values, rounds, budget, reason);
        return actions.get(best);
    }

    static double linear(final double[] weights, final double[] f) {
        if (weights == null || weights.length != f.length + 1) throw new IllegalArgumentException("Bad model dimension");
        double result = weights[f.length];
        for (int i = 0; i < f.length; i++) result += weights[i] * f[i];
        if (!Double.isFinite(result)) throw new IllegalArgumentException("Non-finite model result");
        return result;
    }

    static int predictedPlace(final RacecraftConfig c, final double[] f, final int n) {
        final double v = linear(c.weights, f);
        if (v < 0 || v > 1) return -1;
        final int lower = rank(v - c.placeRadius, n), upper = rank(v + c.placeRadius, n);
        return lower == upper ? lower : -1;
    }
    private static int rank(final double v, final int n) {
        return (int) Math.floor(Math.max(0, Math.min(1, v)) * (n - 1) + 1.5);
    }
    static boolean modelBetter(final RacecraftConfig c, final double[] a, final double[] b, final int n) {
        final int pa = predictedPlace(c, a, n), pb = predictedPlace(c, b, n);
        if (pa < 0 || pb < 0) return false; // unresolved evidence is not a place tie
        return pa < pb || pa == pb && linear(c.timeWeights, b) - linear(c.timeWeights, a) > c.margin;
    }

    /** Schema 2 adds relative context; route_known distinguishes missing potential.
     * No track/seed/player identifiers or absolute coordinates enter the model. */
    static double[] features(final RaceGame g, final RacecraftSearch.Board root, final int focal,
            final Direction action) {
        final double[] old = RacecraftSearch.features(g, root, focal, action);
        if (old == null) return null;
        final double[] f = Arrays.copyOf(old, RacecraftConfig.FEATURE_COUNT_V2);
        f[18] = Math.min(1, (root.alive.length - 1) / 7.0);
        final RacecraftSearch.Board b = new RacecraftSearch.Board(root);
        b.step(g, focal, action);
        if (!b.alive[focal] || b.over()) return f;
        final RacecraftTraffic.Graph graph = RacecraftTraffic.graph(g, b, (focal + 1) % b.alive.length);
        final boolean[] selected = new boolean[b.alive.length];
        graph.select(focal, 1, Integer.MAX_VALUE, selected);
        int rival = -1;
        for (int j = 0; j < selected.length; j++) if (selected[j]) rival = j;
        if (rival < 0) return f;
        final double dx = (double) b.x[rival] - b.x[focal], dy = (double) b.y[rival] - b.y[focal];
        f[12] = clamp(((b.vx[focal] - (double) b.vx[rival]) * dx
                + (b.vy[focal] - (double) b.vy[rival]) * dy) / (24 * Math.max(1, Math.abs(dx) + Math.abs(dy))));
        final int mine = RacecraftSearch.remaining(g, b, focal), other = RacecraftSearch.remaining(g, b, rival);
        if (mine != Integer.MAX_VALUE && other != Integer.MAX_VALUE) {
            f[13] = clamp(((double) other - mine) / 256); f[14] = 1;
        }
        // Every other still-active racer has a slot before our next turn.
        f[15] = 1.0 - (Math.floorMod(rival - focal, b.alive.length) - 1.0) / Math.max(1, b.alive.length - 1);
        final int before = Integer.bitCount(legalMask(g, root, rival));
        final int after = Integer.bitCount(legalMask(g, b, rival));
        f[16] = (after - before) / 9.0; f[17] = after / 9.0;
        return f;
    }
    private static double clamp(final double v) { return Math.max(-1, Math.min(1, v)); }

    static String diagnostic(final Direction champion, final Direction selected, final List<Direction> actions,
            final RacecraftSearch.Value[] values, final int rounds, final RacecraftSearch.Budget budget,
            final String reason) {
        final StringBuilder s = new StringBuilder("{\"baseline\":\"").append(champion)
                .append("\",\"selected\":\"").append(selected).append("\",\"shortlist\":[");
        for (int i = 0; i < actions.size(); i++) {
            if (i != 0) s.append(','); s.append('"').append(actions.get(i)).append('"');
        }
        s.append("],\"completedRounds\":").append(rounds).append(",\"policyCalls\":").append(budget.spent)
                .append(",\"rankingChanges\":").append(budget.rankingChanges)
                .append(",\"exhausted\":").append(budget.exhausted).append(",\"reason\":\"")
                .append(reason).append("\",\"values\":[");
        if (values != null) for (int i = 0; i < values.length; i++) {
            if (i != 0) s.append(',');
            s.append('[').append(values[i].place()).append(',').append(values[i].ownTime()).append(']');
        }
        return s.append("]}").toString();
    }
}
