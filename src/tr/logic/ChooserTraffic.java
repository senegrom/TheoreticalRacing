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
