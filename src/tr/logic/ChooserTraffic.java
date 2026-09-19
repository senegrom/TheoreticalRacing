package tr.logic;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/** Recovered from archived research f03922e. Used only for feature compatibility
 * and bounded policy allocation, not a new proximity veto.
 * A two-own-move, slot-aware interaction graph. Reachable sets ignore other
 * bodies: they allocate prediction effort, NEVER certify danger or veto a move.
 * Finishes vanish; ordinary laps keep their progress. Physical speeds are not
 * clipped to the AI map index. Deterministic bounded work, no wall-clock branch. */
final class ChooserTraffic {
    private static final Direction[] DIRECTIONS = Direction.values();
    private static final int TRANSITION_BUDGET = 2048;
    record Car(int x, int y, int vx, int vy, int lap, int gate) {}

    private ChooserTraffic() {}

    static final class Graph {
        final int[][] edge;
        final int[] x, y;
        final boolean[] alive;
        final boolean complete;
        final int transitions;

        Graph(final int[][] edge, final int[] x, final int[] y, final boolean[] alive,
                final boolean complete, final int transitions) {
            this.edge = edge; this.x = x; this.y = y; this.alive = alive;
            this.complete = complete; this.transitions = transitions;
        }

        int direct(final int i) {
            int n = 0;
            for (int j = 0; j < alive.length; j++) if (alive[j] && j != i && edge[i][j] > 0) n++;
            return n;
        }

        int indirect(final int i, final int j) {
            int value = 0;
            for (int k = 0; k < alive.length; k++)
                if (k != i && k != j && alive[k] && edge[i][k] > 0 && edge[k][j] > 0)
                    value += Math.min(edge[i][k], edge[k][j]);
            return value;
        }

        int indirectCount(final int i) {
            int n = 0;
            for (int j = 0; j < alive.length; j++)
                if (j != i && alive[j] && edge[i][j] == 0 && indirect(i, j) > 0) n++;
            return n;
        }

        /** Same cap as the caller. Non-interacting slots only fill unused places
         * inside the original radius. Slot number is the final stable tie-break. */
        void select(final int focal, final int cap, final int radius, final boolean[] selected) {
            Arrays.fill(selected, false);
            final List<Integer> order = new ArrayList<>();
            for (int j = 0; j < alive.length; j++) {
                if (!alive[j] || j == focal) continue;
                if (edge[focal][j] > 0 || indirect(focal, j) > 0 || distance(focal, j) <= radius)
                    order.add(j);
            }
            order.sort((a, b) -> {
                int c = Integer.compare(edge[focal][b], edge[focal][a]);
                if (c == 0) c = Integer.compare(indirect(focal, b), indirect(focal, a));
                if (c == 0) c = Long.compare(distance(focal, a), distance(focal, b));
                return c != 0 ? c : Integer.compare(a, b);
            });
            for (int k = 0; k < Math.min(cap, order.size()); k++) selected[order.get(k)] = true;
        }

        long distance(final int a, final int b) {
            return Math.max(Math.abs((long) x[a] - x[b]), Math.abs((long) y[a] - y[b]));
        }
    }

    static Graph graph(final RaceGame g, final int[] x, final int[] y, final int[] vx, final int[] vy,
            final int[] lap, final int[] gate, final boolean[] alive, final int first, final int cycles) {
        if (cycles < 1 || cycles > 2 || first < 0 || first >= alive.length)
            throw new IllegalArgumentException("Bad interaction horizon or first slot");
        final int n = alive.length;
        final int[][] edges = new int[n][n];
        final List<Set<Car>> front = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            final Set<Car> s = new LinkedHashSet<>();
            if (alive[i]) s.add(new Car(x[i], y[i], vx[i], vy[i], lap[i], gate[i]));
            front.add(s);
        }
        int work = 0;
        for (int slot = 0; slot < n * cycles; slot++) {
            final int i = (first + slot) % n;
            final Set<Car> next = new LinkedHashSet<>();
            for (final Car p : front.get(i)) for (final Direction d : DIRECTIONS) {
                if (++work > TRANSITION_BUDGET) {
                    // Unknown cannot be used as evidence of independence. Allocate
                    // attention conservatively; the graph never removes a body.
                    for (int a = 0; a < n; a++) for (int b = 0; b < n; b++)
                        if (a != b && alive[a] && alive[b]) edges[a][b] = Math.max(1, edges[a][b]);
                    return new Graph(edges, x.clone(), y.clone(), alive.clone(), false, work - 1);
                }
                final long nvx = (long) p.vx() + d.dx, nvy = (long) p.vy() + d.dy;
                final long nx = p.x() + nvx, ny = p.y() + nvy;
                if (!integer(nvx) || !integer(nvy) || !integer(nx) || !integer(ny)) continue;
                final RaceGame.MoveResult r = g.evaluateMove(p.lap(), p.gate(), p.x(), p.y(),
                        (int) nx, (int) ny, false);
                if (r.legal() && !r.finishes()) next.add(new Car((int) nx, (int) ny,
                        (int) nvx, (int) nvy, r.lapAfter(), g.lapGates == null ? 0 : r.gateAfter()));
            }
            // Compare arriving cells with the other cars' cells AT this slot,
            // not with a simultaneous-move board or only current positions.
            final Set<Long> arrivals = cells(next);
            for (int j = 0; j < n; j++) if (i != j && alive[j]) {
                int hits = 0;
                for (final long cell : cells(front.get(j))) if (arrivals.contains(cell)) hits++;
                edges[i][j] += hits; edges[j][i] += hits;
            }
            front.set(i, next);
        }
        return new Graph(edges, x.clone(), y.clone(), alive.clone(), true, work);
    }

    static Graph graph(final RaceGame g, final ChooserResearch.Board b, final int first) {
        return graph(g, b.x, b.y, b.vx, b.vy, b.lap, b.gate, b.alive, first, 2);
    }

    private static Set<Long> cells(final Set<Car> cars) {
        final Set<Long> result = new LinkedHashSet<>();
        for (final Car p : cars) result.add(((long) p.x() << 32) ^ (p.y() & 0xffffffffL));
        return result;
    }
    private static boolean integer(final long v) { return v >= Integer.MIN_VALUE && v <= Integer.MAX_VALUE; }
}
