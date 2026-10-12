package tr.logic;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/** Round 285 (the round-263 lab's ChooserTraffic, graph part only): a two-cycle,
 *  slot-aware interaction graph. Each car's reachable landings are expanded in
 *  turn order, ignoring other bodies, and an edge counts the cells where one
 *  car's arrivals meet another car's cells at that slot. It allocates forecast
 *  fidelity; it never certifies danger or vetoes a move. Bounded work: past
 *  the transition budget every live pair is treated as interacting. */
final class ChooserTraffic {
    private static final Direction[] DIRECTIONS = Direction.values();
    private static final int TRANSITION_BUDGET = 2048;
    private record Car(int x, int y, int vx, int vy, int lap, int gate) {}

    private ChooserTraffic() {}

    /** perf_aware (exact): {@link #relevant} from per-car fronts. Only the focal row of
     *  the graph decides. The focal car is expanded last in each cycle, so its edge to
     *  rival j is |C1j & C1f| + |C2j & C2f| (its own arrivals against j's fronts) plus
     *  |{focal cell} & C1j| + |C1f & C2j| (j's arrivals against the focal's fronts), Cc
     *  being a car's cells after c cycles. A car expands from its own state ignoring
     *  every body, so its fronts are shared by all the landings of one chooser call.
     *  Past the transition budget (more than 22 live cars) the original graph runs, so
     *  its partial reading there is unchanged too. */
    static int relevant(final RaceGame g, final FrontCache cache, final int[] x, final int[] y,
            final int[] vx, final int[] vy, final int[] lap, final int[] gate, final boolean[] alive,
            final int focal) {
        final int n = alive.length;
        if (focal < 0 || focal >= n || !alive[focal])
            return -1;
        final boolean grid = g.aiGridLegal;
        final Fronts[] fronts = new Fronts[n];
        long work = 0;
        for (int i = 0; i < n; i++)
            if (alive[i]) {
                fronts[i] = cache.get(g, grid, x[i], y[i], vx[i], vy[i], lap[i], gate[i]);
                work += (long) DIRECTIONS.length * (1 + fronts[i].size1);
            }
        if (work > TRANSITION_BUDGET)
            return relevant(g, x, y, vx, vy, lap, gate, alive, focal);
        final Fronts mine = fronts[focal];
        final long here = cell(x[focal], y[focal]);
        int best = -1, bestEdge = 0;
        for (int i = 0; i < n; i++) {
            if (i == focal || !alive[i])
                continue;
            final Fronts other = fronts[i];
            final int edge = common(other.cells1, mine.cells1) + common(other.cells2, mine.cells2)
                    + (java.util.Arrays.binarySearch(other.cells1, here) >= 0 ? 1 : 0)
                    + common(mine.cells1, other.cells2);
            if (edge <= 0)
                continue;
            if (best < 0 || edge > bestEdge
                    || edge == bestEdge && distance(x, y, focal, i) < distance(x, y, focal, best)) {
                best = i;
                bestEdge = edge;
            }
        }
        return best;
    }

    /** perf_aware: one car's two-cycle fronts as ascending distinct cell sets, and the
     *  number of distinct first-cycle states (each costs the graph nine transitions). */
    static final class Fronts {
        final int size1;
        final long[] cells1;
        final long[] cells2;

        Fronts(final int size1, final long[] cells1, final long[] cells2) {
            this.size1 = size1;
            this.cells1 = cells1;
            this.cells2 = cells2;
        }
    }

    /** perf_aware: fronts by car state and grid world -- evaluateMove's only inputs here
     *  besides the course. Its owner clears it before every top-level chooser call, so no
     *  entry outlives the board, course or grid world it was computed for. */
    static final class FrontCache {
        private record Key(int x, int y, int vx, int vy, int lap, int gate, boolean grid) {}

        private final java.util.HashMap<Key, Fronts> fronts = new java.util.HashMap<>();

        void clear() {
            fronts.clear();
        }

        Fronts get(final RaceGame g, final boolean grid, final int x, final int y, final int vx,
                final int vy, final int lap, final int gate) {
            final Key key = new Key(x, y, vx, vy, lap, gate, grid);
            Fronts known = fronts.get(key);
            if (known == null) {
                known = expand(g, grid, x, y, vx, vy, lap, gate);
                fronts.put(key, known);
            }
            return known;
        }
    }

    /** The graph's two cycles from one state, as {@link #graph} expands them. */
    private static Fronts expand(final RaceGame g, final boolean grid, final int x, final int y,
            final int vx, final int vy, final int lap, final int gate) {
        final int[] first = new int[DIRECTIONS.length * 6];
        final int size1 = successors(g, grid, x, y, vx, vy, lap, gate, first);
        final long[] cells1 = new long[size1];
        final long[] cells2 = new long[size1 * DIRECTIONS.length];
        final int[] second = new int[DIRECTIONS.length * 6];
        int size2 = 0;
        for (int k = 0; k < size1; k++) {
            final int b = 6 * k;
            cells1[k] = cell(first[b], first[b + 1]);
            final int count = successors(g, grid, first[b], first[b + 1], first[b + 2], first[b + 3],
                    first[b + 4], first[b + 5], second);
            for (int q = 0; q < count; q++)
                cells2[size2++] = cell(second[6 * q], second[6 * q + 1]);
        }
        return new Fronts(size1, distinct(cells1, size1), distinct(cells2, size2));
    }

    /** One state's legal, non-finishing landings in direction order as
     *  (x, y, vx, vy, lap, gate) rows, each state once -- the graph's Car set. */
    private static int successors(final RaceGame g, final boolean grid, final int x, final int y,
            final int vx, final int vy, final int lap, final int gate, final int[] out) {
        int count = 0;
        for (final Direction d : DIRECTIONS) {
            final int nvx = vx + d.dx, nvy = vy + d.dy;
            final int nx = x + nvx, ny = y + nvy;
            final RaceGame.MoveResult r = g.evaluateMove(lap, gate, grid, x, y, nx, ny, false);
            if (!r.legal() || r.finishes())
                continue;
            final int nlap = r.lapAfter(), ngate = g.lapGates == null ? 0 : r.gateAfter();
            boolean seen = false;
            for (int k = 0; k < count && !seen; k++) {
                final int b = 6 * k;
                seen = out[b] == nx && out[b + 1] == ny && out[b + 2] == nvx && out[b + 3] == nvy
                        && out[b + 4] == nlap && out[b + 5] == ngate;
            }
            if (seen)
                continue;
            final int b = 6 * count++;
            out[b] = nx;
            out[b + 1] = ny;
            out[b + 2] = nvx;
            out[b + 3] = nvy;
            out[b + 4] = nlap;
            out[b + 5] = ngate;
        }
        return count;
    }

    /** {@link #cells}' key for one cell. */
    private static long cell(final int x, final int y) {
        return ((long) x << 32) ^ (y & 0xffffffffL);
    }

    private static long[] distinct(final long[] values, final int size) {
        final long[] sorted = java.util.Arrays.copyOf(values, size);
        java.util.Arrays.sort(sorted);
        int kept = 0;
        for (int k = 0; k < size; k++)
            if (kept == 0 || sorted[k] != sorted[kept - 1])
                sorted[kept++] = sorted[k];
        return java.util.Arrays.copyOf(sorted, kept);
    }

    /** The size of the intersection of two ascending distinct sets. */
    private static int common(final long[] a, final long[] b) {
        int hits = 0;
        for (int i = 0, j = 0; i < a.length && j < b.length;) {
            if (a[i] < b[j])
                i++;
            else if (a[i] > b[j])
                j++;
            else {
                hits++;
                i++;
                j++;
            }
        }
        return hits;
    }

    /** The live rival with the heaviest edge to {@code focal} (then the nearer,
     *  then the lower index), or -1 when none interacts. */
    static int relevant(final RaceGame g, final int[] x, final int[] y, final int[] vx, final int[] vy,
            final int[] lap, final int[] gate, final boolean[] alive, final int focal) {
        final int n = alive.length;
        if (focal < 0 || focal >= n || !alive[focal])
            return -1;
        final int[][] edge = graph(g, x, y, vx, vy, lap, gate, alive, (focal + 1) % n);
        int best = -1;
        for (int i = 0; i < n; i++) {
            if (i == focal || !alive[i] || edge[focal][i] <= 0)
                continue;
            if (best < 0 || edge[focal][i] > edge[focal][best]
                    || edge[focal][i] == edge[focal][best] && distance(x, y, focal, i) < distance(x, y, focal, best))
                best = i;
        }
        return best;
    }

    private static long distance(final int[] x, final int[] y, final int a, final int b) {
        return Math.max(Math.abs((long) x[a] - x[b]), Math.abs((long) y[a] - y[b]));
    }

    private static int[][] graph(final RaceGame g, final int[] x, final int[] y, final int[] vx, final int[] vy,
            final int[] lap, final int[] gate, final boolean[] alive, final int first) {
        final int n = alive.length;
        final int[][] edges = new int[n][n];
        final List<Set<Car>> front = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            final Set<Car> s = new LinkedHashSet<>();
            if (alive[i])
                s.add(new Car(x[i], y[i], vx[i], vy[i], lap[i], gate[i]));
            front.add(s);
        }
        int work = 0;
        for (int slot = 0; slot < n * 2; slot++) {
            final int i = (first + slot) % n;
            final Set<Car> next = new LinkedHashSet<>();
            for (final Car p : front.get(i))
                for (final Direction d : DIRECTIONS) {
                    if (++work > TRANSITION_BUDGET) {
                        for (int a = 0; a < n; a++)
                            for (int b = 0; b < n; b++)
                                if (a != b && alive[a] && alive[b])
                                    edges[a][b] = Math.max(1, edges[a][b]);
                        return edges;
                    }
                    final int nvx = p.vx() + d.dx, nvy = p.vy() + d.dy;
                    final int nx = p.x() + nvx, ny = p.y() + nvy;
                    final RaceGame.MoveResult r = g.evaluateMove(p.lap(), p.gate(), p.x(), p.y(), nx, ny, false);
                    if (r.legal() && !r.finishes())
                        next.add(new Car(nx, ny, nvx, nvy, r.lapAfter(), g.lapGates == null ? 0 : r.gateAfter()));
                }
            final Set<Long> arrivals = cells(next);
            for (int j = 0; j < n; j++)
                if (i != j && alive[j]) {
                    int hits = 0;
                    for (final long cell : cells(front.get(j)))
                        if (arrivals.contains(cell))
                            hits++;
                    edges[i][j] += hits;
                    edges[j][i] += hits;
                }
            front.set(i, next);
        }
        return edges;
    }

    private static Set<Long> cells(final Set<Car> cars) {
        final Set<Long> result = new LinkedHashSet<>();
        for (final Car p : cars)
            result.add(((long) p.x() << 32) ^ (p.y() & 0xffffffffL));
        return result;
    }
}
