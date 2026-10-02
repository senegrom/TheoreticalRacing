package tr.logic;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** The referee's turn-limit classification, usable on live or projected boards.
 * No player, clock, map or classification ledger is modified here. */
final class RaceTimeout {
    private RaceTimeout() {}

    record Progress(int owed, int toGate, int order) implements Comparable<Progress> {
        @Override public int compareTo(final Progress other) {
            int c = Integer.compare(owed, other.owed);
            if (c == 0) c = Integer.compare(toGate, other.toGate);
            return c == 0 ? Integer.compare(order, other.order) : c;
        }
    }

    static boolean reached(final RaceGame game, final long turn) {
        return game.lapGates != null && turn > (long) game.totalLaps * 750 * game.players.length;
    }

    static Progress progress(final RaceGame game, final int lap, final int gate,
            final int x, final int y, final int vx, final int vy, final int order) {
        int distance = Integer.MAX_VALUE;
        if (game.reach.isReady()) {
            try { distance = game.reach.turnsToGate(gate, x, y, vx, vy); }
            catch (final RuntimeException unavailable) { distance = Integer.MAX_VALUE; }
        }
        return new Progress(OptimalPotential.remainingEvents(gate, lap, game.totalLaps), distance, order);
    }

    static Progress progress(final RaceGame game, final Player p, final int order) {
        final int[] x = p.getPosition(), v = p.getVelocity();
        return progress(game, p.getLap(), p.getNextGate(), x[0], x[1], v[0], v[1], order);
    }

    static int[] order(final RaceGame game) {
        final int n = game.players.length;
        final List<Integer> live = new ArrayList<>();
        final Progress[] values = new Progress[n];
        for (int i = 0; i < n; i++) if (!game.players[i].isFinished()) {
            live.add(i);
            values[i] = progress(game, game.players[i], Math.floorMod(i - game.subgamestate, n));
        }
        live.sort(Comparator.comparing(i -> values[i]));
        return live.stream().mapToInt(Integer::intValue).toArray();
    }

    static int[] order(final RaceGame game, final int slot, final int[] laps, final int[] gates,
            final int[] px, final int[] py, final int[] vx, final int[] vy, final boolean[] alive) {
        final int n = alive.length;
        final List<Integer> live = new ArrayList<>();
        final Progress[] values = new Progress[n];
        for (int i = 0; i < n; i++) if (alive[i]) {
            live.add(i);
            values[i] = progress(game, laps[i], gates[i], px[i], py[i], vx[i], vy[i], Math.floorMod(i - slot, n));
        }
        live.sort(Comparator.comparing(i -> values[i]));
        return live.stream().mapToInt(Integer::intValue).toArray();
    }
}
