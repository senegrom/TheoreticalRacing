package tr.logic;

import java.util.Arrays;

/** Feature functions recovered from f03922e, unchanged for legacy-model controls.
 * New students use the 19-value relative schema. No model chooses legality. */
final class ChooserFeatures {
    private static final Direction[] DIRECTIONS = Direction.values();
    private ChooserFeatures() {}
    static int remaining(final RaceGame g, final ChooserResearch.Board b, final int i) {
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

    /** v1: bounded, identity-free numeric features; the collector obtains these
     * exact Java values rather than reimplementing them in Python. */
    static double[] features(final RaceGame g, final ChooserResearch.Board root, final int i, final Direction action) {
        if (root.timedOut(g) || !root.alive[i] || root.over()) return null;
        final RaceGame.MoveResult t = root.transition(g, i, action);
        if (!t.legal()) return null;
        final ChooserResearch.Board b = new ChooserResearch.Board(root);
        final int nvx = b.vx[i] + action.dx, nvy = b.vy[i] + action.dy;
        b.vx[i] = nvx; b.vy[i] = nvy; b.x[i] += nvx; b.y[i] += nvy;
        b.lap[i] = t.lapAfter(); b.gate[i] = g.lapGates == null ? 0 : t.gateAfter();
        final double[] f = new double[12];
        f[0] = Math.min(1, Math.max(Math.abs(nvx), Math.abs(nvy)) / 12.0);
        f[1] = Math.min(1, ((double) nvx * nvx + (double) nvy * nvy) / 288.0);
        f[2] = (action.dx * (double) root.vx[i] + action.dy * (double) root.vy[i])
                / Math.max(1.0, Math.abs((double) root.vx[i]) + Math.abs((double) root.vy[i]));
        f[4] = g.reach.isAlive(b.x[i], b.y[i], nvx, nvy) ? 1 : 0;
        f[5] = Math.max(0, Math.min(1, OptimalPotential.remainingEvents(b.gate[i], b.lap[i], g.totalLaps) / 297.0));
        f[11] = t.finishes() ? 1 : 0;
        final int remaining = t.finishes() ? 0 : remaining(g, b, i);
        f[6] = Math.min(1, remaining / 256.0);
        final ChooserTraffic.Graph graph = ChooserTraffic.graph(g, b, (i + 1) % b.alive.length);
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

    /** Schema 2 adds relative context; route_known distinguishes missing potential.
     * No track/seed/player identifiers or absolute coordinates enter the model. */
    static double[] relative(final RaceGame g, final ChooserResearch.Board root, final int focal,
            final Direction action) {
        final double[] old = features(g, root, focal, action);
        if (old == null) return null;
        final double[] f = Arrays.copyOf(old, 19);
        f[18] = Math.min(1, (root.alive.length - 1) / 7.0);
        final ChooserResearch.Board b = new ChooserResearch.Board(root);
        b.step(g, focal, action);
        if (!b.alive[focal] || b.over()) return f;
        final ChooserTraffic.Graph graph = ChooserTraffic.graph(g, b, (focal + 1) % b.alive.length);
        final boolean[] selected = new boolean[b.alive.length];
        graph.select(focal, 1, Integer.MAX_VALUE, selected);
        int rival = -1;
        for (int j = 0; j < selected.length; j++) if (selected[j]) rival = j;
        if (rival < 0) return f;
        final double dx = (double) b.x[rival] - b.x[focal], dy = (double) b.y[rival] - b.y[focal];
        f[12] = clamp(((b.vx[focal] - (double) b.vx[rival]) * dx
                + (b.vy[focal] - (double) b.vy[rival]) * dy) / (24 * Math.max(1, Math.abs(dx) + Math.abs(dy))));
        final int mine = remaining(g, b, focal), other = remaining(g, b, rival);
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

    private static int legalMask(final RaceGame g, final ChooserResearch.Board b, final int i) {
        if (!b.alive[i] || b.over() || b.timedOut(g)) return 0;
        int mask = 0;
        for (final Direction d : DIRECTIONS) if (b.transition(g, i, d).legal()) mask |= 1 << d.ordinal();
        return mask;
    }
}
