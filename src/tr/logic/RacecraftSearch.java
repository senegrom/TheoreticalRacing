package tr.logic;

import java.util.List;

/** Opt-in opportunity search, bounded encounter extension and feature contract.
 * Predictions are not certificates. Every continuation is recomputed AFTER the
 * candidate; all players pursue their own policy. No reward for field slowdown. */
final class RacecraftSearch {
    private static final Direction[] DIRECTIONS = Direction.values();
    private RacecraftSearch() {}

    @FunctionalInterface interface Policy { Direction choose(Board board, int mover); }
    static final class Budget {
        int remaining, spent;
        int completedRounds, rankingChanges;
        boolean exhausted;
        String diagnostic = "{\"reason\":\"precedence-or-no-hook\"}";
        Budget(final int remaining) {
            if (remaining < 0) throw new IllegalArgumentException("Negative policy budget");
            this.remaining = remaining;
        }
        boolean take() {
            if (remaining == 0) { exhausted = true; return false; }
            remaining--; spent++; return true;
        }
    }

    /** Detached full transition state; ownMoves counts future COMMITTED moves,
     * never phantom slots for finished cars. */
    static final class Board {
        final int[] x, y, vx, vy, lap, gate, place, ownMoves;
        final boolean[] alive;
        int first, last;
        boolean classificationKnown;
        long turns;
        Board(final RaceGame g) {
            final int n = g.players.length;
            x = new int[n]; y = new int[n]; vx = new int[n]; vy = new int[n];
            lap = new int[n]; gate = new int[n]; place = new int[n]; ownMoves = new int[n];
            alive = new boolean[n]; turns = g.turnCount();
            first = g.racecraftFinishedFirst(); last = g.racecraftFinishedLast();
            for (int i = 0; i < n; i++) {
                final Player p = g.players[i];
                x[i] = p.getPosition()[0]; y[i] = p.getPosition()[1];
                vx[i] = p.getVelocity()[0]; vy[i] = p.getVelocity()[1];
                lap[i] = p.getLap(); gate[i] = g.lapGates == null ? 0 : p.getNextGate();
                place[i] = p.getFinishedPlace(); alive[i] = !p.isFinished();
            }
            classificationKnown = first + last == n - live();
            final boolean[] seen = new boolean[n + 1];
            for (int i = 0; i < n; i++) if (!alive[i]) {
                if (place[i] < 1 || place[i] > n || seen[place[i]]) classificationKnown = false;
                else seen[place[i]] = true;
            }
        }
        Board(final Board b) {
            x = b.x.clone(); y = b.y.clone(); vx = b.vx.clone(); vy = b.vy.clone();
            lap = b.lap.clone(); gate = b.gate.clone(); place = b.place.clone();
            ownMoves = b.ownMoves.clone(); alive = b.alive.clone();
            first = b.first; last = b.last; turns = b.turns; classificationKnown = b.classificationKnown;
        }
        int live() { int n = 0; for (final boolean v : alive) if (v) n++; return n; }
        boolean over() { return live() <= (alive.length == 1 ? 0 : 1); }
        boolean occupied(final int i, final int nx, final int ny) {
            for (int j = 0; j < alive.length; j++)
                if (j != i && alive[j] && x[j] == nx && y[j] == ny) return true;
            return false;
        }
        boolean timedOut(final RaceGame g) {
            return g.lapGates != null && turns > (long) g.totalLaps * 750 * alive.length;
        }
        RaceGame.MoveResult transition(final RaceGame g, final int i, final Direction d) {
            final int nx = Math.addExact(x[i], Math.addExact(vx[i], d.dx));
            final int ny = Math.addExact(y[i], Math.addExact(vy[i], d.dy));
            return g.evaluateMove(lap[i], gate[i], x[i], y[i], nx, ny, occupied(i, nx, ny));
        }
        void step(final RaceGame g, final int i, final Direction d) {
            if (!alive[i] || over()) throw new IllegalArgumentException("Cannot move a classified car");
            if (timedOut(g)) retire(i, alive.length - last++);
            else {
                final RaceGame.MoveResult t = transition(g, i, d);
                if (t.finishes()) retire(i, ++first);
                else if (!t.legal()) retire(i, alive.length - last++);
                else {
                    vx[i] += d.dx; vy[i] += d.dy; x[i] += vx[i]; y[i] += vy[i];
                    lap[i] = t.lapAfter(); gate[i] = g.lapGates == null ? 0 : t.gateAfter();
                }
            }
            turns++; ownMoves[i]++;
            if (over()) for (int j = 0; j < alive.length; j++)
                if (alive[j]) retire(j, first + 1);
        }
        private void retire(final int i, final int classification) {
            alive[i] = false; place[i] = classification;
            x[i] = -100000; y[i] = -100000; vx[i] = 0; vy[i] = 0;
        }
    }

    record Value(int place, long ownTime, boolean terminal) implements Comparable<Value> {
        @Override public int compareTo(final Value v) {
            final int c = Integer.compare(place, v.place);
            return c != 0 ? c : Long.compare(ownTime, v.ownTime);
        }
    }
    record Forecast(Value value, Board board, boolean exhausted, int extensions) {}

    static Forecast forecast(final RaceGame g, final Board root, final int focal, final Direction action,
            final RacecraftConfig config, final Policy policy, final Budget budget) {
        final Board b = new Board(root);
        b.step(g, focal, action);
        int slot = (focal + 1) % b.alive.length, cycles = 0, extensions = 0;
        while (!b.over() && b.place[focal] == 0) {
            if (cycles >= config.rounds + extensions) {
                if (!config.encounter || extensions >= config.extraRounds
                        || RacecraftTraffic.graph(g, b, slot).direct(focal) == 0) break;
                extensions++;
            }
            for (int count = 0; count < b.alive.length && !b.over() && b.place[focal] == 0; count++) {
                final int i = slot;
                slot = (slot + 1) % b.alive.length;
                if (!b.alive[i]) continue;
                if (b.turns > Integer.MAX_VALUE) return new Forecast(null, b, true, extensions);
                Direction d = Direction.NONE;
                if (!b.timedOut(g)) {
                    if (!budget.take()) return new Forecast(null, b, true, extensions);
                    d = policy.choose(b, i);
                    if (d == null) return new Forecast(null, b, true, extensions);
                }
                b.step(g, i, d);
            }
            cycles++;
        }
        return new Forecast(value(g, b, focal, slot), b, false, extensions);
    }

    /** A leaf estimate uses each driver's own remaining route, NOT the sum of
     * field costs. Unreachable solo maps are uncertainty, not a predicted crash. */
    static Value value(final RaceGame g, final Board b, final int focal, final int next) {
        if (b.place[focal] > 0) return new Value(b.place[focal], b.ownMoves[focal], true);
        final int mine = remaining(g, b, focal);
        if (mine == Integer.MAX_VALUE) return null;
        int place = b.first + 1;
        final int n = b.alive.length;
        final long eta = (long) mine * n + Math.floorMod(focal - next, n);
        for (int j = 0; j < n; j++) if (j != focal && b.alive[j]) {
            final int t = remaining(g, b, j);
            if (t == Integer.MAX_VALUE) return null;
            if ((long) t * n + Math.floorMod(j - next, n) < eta) place++;
        }
        return new Value(place, (long) b.ownMoves[focal] + mine, false);
    }

    static int remaining(final RaceGame g, final Board b, final int i) {
        if (!b.alive[i]) return 0;
        final OptimalPotential p = g.optimalPotential();
        if (p != null) return p.movesToFinish(OptimalPotential.remainingEvents(b.gate[i], b.lap[i],
                g.totalLaps), b.x[i], b.y[i], b.vx[i], b.vy[i]);
        // Next-gate distance is NOT a comparable final race time when progress
        // differs. Without the complete potential, abstain on multi-lap leaves.
        if (g.lapGates != null && (b.lap[i] + 1 < g.totalLaps || b.gate[i] != 0))
            return Integer.MAX_VALUE;
        return g.reach.turnsToFinish(b.x[i], b.y[i], b.vx[i], b.vy[i]);
    }

    static Direction improve(final RaceGame g, final Direction champion, final double[] scores,
            final RacecraftConfig config, final Policy policy, final Budget budget) {
        final int focal = g.subgamestate;
        final Board root = new Board(g);
        if (!root.classificationKnown || root.over() || root.timedOut(g) || champion == null
                || !root.transition(g, focal, champion).legal()
                || root.transition(g, focal, champion).finishes()) return champion;
        if (RacecraftTraffic.graph(g, root, focal).direct(focal) == 0) return champion;
        final List<Direction> actions = RacecraftNext.shortlist(g, root, focal, champion, scores, config);
        if (config.progressive || config.lexicographic)
            return RacecraftNext.improve(g, root, focal, champion, actions, config, policy, budget);
        Direction best = champion;
        Value bestValue = null;
        final double originalModel = config.learned ? config.score(features(g, root, focal, champion)) : 0;
        double bestModel = originalModel;
        Value originalValue = null;
        final Value[] observed = config.opportunity ? new Value[actions.size()] : null;
        // Freeze the shortlist BEFORE asking any nested scorer: its scratch rows
        // cannot overwrite the parent's comparison. Exhaustion keeps champion.
        for (final Direction d : actions) {
            Value v = null;
            if (config.opportunity) {
                final Forecast f = forecast(g, root, focal, d, config, policy, budget);
                if (f.exhausted() || f.value() == null) {
                    budget.diagnostic = RacecraftNext.diagnostic(champion, champion, actions, null, 0,
                            budget, f.exhausted() ? "budget" : "unknown-leaf");
                    return champion;
                }
                v = f.value();
                observed[actions.indexOf(d)] = v;
            }
            final double model = config.learned ? config.score(features(g, root, focal, d)) : 0;
            if (d == champion) { bestValue = v; originalValue = v; continue; }
            if (config.opportunity && v.compareTo(bestValue) < 0
                    || (!config.opportunity || v.compareTo(bestValue) == 0)
                        && config.learned && model < bestModel) {
                best = d; bestValue = v; bestModel = model;
            }
        }
        if (config.learned && (!config.opportunity || bestValue.compareTo(originalValue) == 0)
                && originalModel - bestModel <= config.margin) best = champion;
        budget.diagnostic = RacecraftNext.diagnostic(champion, best, actions, observed, config.rounds,
                budget, "sequential");
        return best;
    }

    /** v1: bounded, identity-free numeric features; the collector obtains these
     * exact Java values rather than reimplementing them in Python. */
    static double[] features(final RaceGame g, final Board root, final int i, final Direction action) {
        if (root.timedOut(g) || !root.alive[i] || root.over()) return null;
        final RaceGame.MoveResult t = root.transition(g, i, action);
        if (!t.legal()) return null;
        final Board b = new Board(root);
        final int nvx = b.vx[i] + action.dx, nvy = b.vy[i] + action.dy;
        b.vx[i] = nvx; b.vy[i] = nvy; b.x[i] += nvx; b.y[i] += nvy;
        b.lap[i] = t.lapAfter(); b.gate[i] = g.lapGates == null ? 0 : t.gateAfter();
        final double[] f = new double[RacecraftConfig.FEATURE_COUNT];
        f[0] = Math.min(1, Math.max(Math.abs(nvx), Math.abs(nvy)) / 12.0);
        f[1] = Math.min(1, ((double) nvx * nvx + (double) nvy * nvy) / 288.0);
        f[2] = (action.dx * (double) root.vx[i] + action.dy * (double) root.vy[i])
                / Math.max(1.0, Math.abs((double) root.vx[i]) + Math.abs((double) root.vy[i]));
        f[4] = g.reach.isAlive(b.x[i], b.y[i], nvx, nvy) ? 1 : 0;
        f[5] = Math.max(0, Math.min(1, OptimalPotential.remainingEvents(b.gate[i], b.lap[i], g.totalLaps) / 297.0));
        f[11] = t.finishes() ? 1 : 0;
        final int remaining = t.finishes() ? 0 : remaining(g, b, i);
        f[6] = Math.min(1, remaining / 256.0);
        final RacecraftTraffic.Graph graph = RacecraftTraffic.graph(g, b, (i + 1) % b.alive.length);
        f[7] = Math.min(1, graph.direct(i) / 7.0); f[8] = Math.min(1, graph.indirectCount(i) / 7.0);
        long nearest = 64;
        for (int j = 0; j < b.alive.length; j++) if (j != i && b.alive[j])
            nearest = Math.min(nearest, graph.distance(i, j));
        f[10] = nearest / 64.0;
        int legal = 0, contested = 0;
        for (final Direction d : DIRECTIONS) {
            final RaceGame.MoveResult r = b.transition(g, i, d);
            if (!r.legal()) continue;
            legal++;
            final int nx = b.x[i] + b.vx[i] + d.dx, ny = b.y[i] + b.vy[i] + d.dy;
            boolean hit = false;
            for (int j = 0; j < b.alive.length && !hit; j++) if (j != i && b.alive[j])
                for (final Direction reply : DIRECTIONS)
                    if (b.x[j] + b.vx[j] + reply.dx == nx && b.y[j] + b.vy[j] + reply.dy == ny) {
                        final RaceGame.MoveResult rr = g.evaluateMove(b.lap[j], b.gate[j], b.x[j], b.y[j], nx, ny, false);
                        if (rr.legal() && !rr.finishes()) { hit = true; break; }
                    }
            if (hit && !r.finishes()) contested++;
        }
        f[3] = legal / 9.0; f[9] = contested / 9.0;
        for (final double v : f) if (!Double.isFinite(v)) throw new IllegalStateException("Invalid feature");
        return f;
    }

    static String featureProtocol(final RaceGame g) { return featureProtocol(g, false); }

    static String featureProtocol(final RaceGame g, final boolean v2) {
        g.reach.ensureReachabilityReady();
        final Board b = new Board(g);
        final StringBuilder out = new StringBuilder(v2 ? "lab3;2;" : "lab2;1;");
        for (final Direction d : DIRECTIONS) {
            if (d.ordinal() > 0) out.append('|');
            if (RaceGame.aiVelocityOutOfRange(b.vx[g.subgamestate] + d.dx, b.vy[g.subgamestate] + d.dy)) {
                out.append('-'); continue;
            }
            final double[] f = v2 ? RacecraftNext.features(g, b, g.subgamestate, d) : features(g, b, g.subgamestate, d);
            if (f == null) out.append('-');
            else for (int k = 0; k < f.length; k++) {
                if (k > 0) out.append(',');
                out.append(Double.toString(f[k]));
            }
        }
        return out.toString();
    }
}
