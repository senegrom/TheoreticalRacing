package tr.logic;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Extra chooser work only at a named trigger. Every compared value comes from
 * the same model and horizon; an extension re-evaluates the complete candidate set. */
final class TacticalComparison {
    private TacticalComparison() {}
    record Evaluation(RacecraftOutcome outcome, boolean imminentFinish) {
        Evaluation { if (outcome == null) throw new IllegalArgumentException("missing forecast"); }
    }
    @FunctionalInterface interface Forecast { Evaluation run(Direction action, int rounds); }
    record Selection(Direction move, int trials, int extensionRounds, boolean inheritedOffered,
            boolean recoveryExpanded) {}

    static Selection choose(final Direction nominal, final Map<Direction, Evaluation> initial,
            final List<Direction> legal, final Direction inherited, final int baseRounds,
            final int recoveryBudget, final int extraRounds, final Forecast forecast) {
        if (nominal == null || !initial.containsKey(nominal) || baseRounds < 1
                || recoveryBudget < 0 || recoveryBudget > 9 || extraRounds < 0 || extraRounds > 2)
            throw new IllegalArgumentException("invalid tactical comparison");
        Map<Direction, Evaluation> values = new LinkedHashMap<>(initial);
        int trials = 0;
        boolean inheritedOffered = false, expanded = false;
        if (inherited != null && legal.contains(inherited) && !values.containsKey(inherited)) {
            values.put(inherited, forecast.run(inherited, baseRounds));
            trials++; inheritedOffered = true;
        }
        if (recoveryBudget > 0 && allCrashes(values)) {
            int used = 0;
            for (final Direction d : legal) {
                if (values.containsKey(d)) continue;
                if (used == recoveryBudget) break;
                values.put(d, forecast.run(d, baseRounds));
                used++; trials++; expanded = true;
            }
        }
        Direction pick = inheritedOffered || expanded ? select(nominal, values) : nominal;
        int extension = 0;
        boolean unsettled = false;
        for (final Evaluation e : values.values()) if (e.outcome.known()
                && e.outcome.status() == RacecraftOutcome.Status.RUNNING && e.imminentFinish) unsettled = true;
        if (extraRounds > 0 && unsettled) {
            final Map<Direction, Evaluation> extended = new LinkedHashMap<>();
            for (final Direction d : values.keySet()) {
                extended.put(d, forecast.run(d, baseRounds + extraRounds)); trials++;
            }
            // Unknown at the longer horizon is never compared with an old short-horizon value.
            if (extended.get(pick).outcome.known()) pick = select(pick, extended);
            extension = extraRounds;
        }
        return new Selection(pick, trials, extension, inheritedOffered, expanded);
    }

    private static boolean allCrashes(final Map<Direction, Evaluation> values) {
        if (values.isEmpty()) return false;
        for (final Evaluation value : values.values()) if (!value.outcome.known() || !value.outcome.crashed()) return false;
        return true;
    }
    private static Direction select(final Direction nominal, final Map<Direction, Evaluation> values) {
        Direction best = nominal;
        RacecraftOutcome value = values.get(nominal).outcome;
        final boolean compareCrashes = allCrashes(values);
        for (final Map.Entry<Direction, Evaluation> entry : values.entrySet()) {
            if (entry.getValue().outcome.betterThan(value, compareCrashes)) {
                best = entry.getKey(); value = entry.getValue().outcome;
            }
        }
        return best;
    }
}
