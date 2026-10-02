package tr.logic;

import java.util.ArrayList;
import java.util.List;

/** Bounded opening scheduler. The model supplies legal follow-ups in continuation
 * order from the actual projected second-move board, not a compass prefix. */
final class OpeningPlans {
    private OpeningPlans() {}
    record Trial(RacecraftOutcome outcome, List<Direction> followups) {
        Trial { followups = List.copyOf(followups); }
    }
    @FunctionalInterface interface Forecast { Trial run(Direction first, Direction second); }
    record Selection(Direction move, int trials) {}

    static Selection choose(final Direction nominal, final Direction[] roots, final int budget,
            final boolean compareCrashes, final Forecast forecast) {
        if (budget <= 0) return new Selection(nominal, 0);
        final List<Direction> order = new ArrayList<>();
        order.add(nominal);
        for (final Direction d : roots) if (!order.contains(d)) order.add(d);
        final List<Trial> baseline = new ArrayList<>();
        Direction best = nominal;
        RacecraftOutcome value = null;
        int used = 0;
        for (final Direction first : order) {
            if (used == budget) break;
            final Trial result = forecast.run(first, null); used++;
            baseline.add(result);
            if (value == null) {
                value = result.outcome();
                if (!value.known()) return new Selection(nominal, used);
            } else if (result.outcome().betterThan(value, compareCrashes)) {
                value = result.outcome(); best = first;
            }
        }
        for (int next = 0; used < budget; next++) {
            boolean any = false;
            for (int k = 0; k < baseline.size() && used < budget; k++) {
                final List<Direction> followups = baseline.get(k).followups();
                if (next >= followups.size()) continue;
                any = true;
                final Trial result = forecast.run(order.get(k), followups.get(next)); used++;
                if (result.outcome().betterThan(value, compareCrashes)) {
                    value = result.outcome(); best = order.get(k);
                }
            }
            if (!any) break;
        }
        return new Selection(best, used);
    }

    /** Distances are evaluated AFTER the legal second action. Ties use momentum,
     * then enum order only as a final deterministic tie, never to truncate unsorted actions. */
    static List<Direction> ordered(final int[] turns, final int vx, final int vy) {
        final List<Direction> sorted = new ArrayList<>();
        for (final Direction d : Direction.values()) if (turns[d.ordinal()] >= 0) sorted.add(d);
        sorted.sort((a, b) -> {
            int c = Integer.compare(turns[a.ordinal()], turns[b.ordinal()]);
            if (c == 0) c = Long.compare((long) b.dx * vx + (long) b.dy * vy,
                    (long) a.dx * vx + (long) a.dy * vy);
            return c == 0 ? Integer.compare(a.ordinal(), b.ordinal()) : c;
        });
        // Admit a different acceleration early only among equally well-valued moves.
        if (sorted.size() > 2) {
            final Direction first = sorted.getFirst();
            int diverse = 1, separation = -1;
            for (int k = 1; k < sorted.size(); k++) {
                final Direction d = sorted.get(k);
                if (turns[d.ordinal()] != turns[sorted.get(1).ordinal()]) break;
                final int distance = Math.abs(d.dx - first.dx) + Math.abs(d.dy - first.dy);
                if (distance > separation) { separation = distance; diverse = k; }
            }
            final Direction d = sorted.remove(diverse); sorted.add(1, d);
        }
        return List.copyOf(sorted);
    }

}
