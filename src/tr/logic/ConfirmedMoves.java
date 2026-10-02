package tr.logic;

import java.util.function.Function;

/** Select only completed model confirmations; iteration order does not override
 * finishing place or own time. An unavailable confirmation is never a success. */
final class ConfirmedMoves {
    private ConfirmedMoves() {}
    static Direction choose(final Direction[] candidates,
            final Function<Direction, RacecraftOutcome> confirmation) {
        Direction best = null;
        RacecraftOutcome value = null;
        for (final Direction d : candidates) {
            final RacecraftOutcome result = confirmation.apply(d);
            if (result == null || !result.known() || result.crashed()) continue;
            if (value == null || result.betterThan(value, false)) { best = d; value = result; }
        }
        return best;
    }
}
