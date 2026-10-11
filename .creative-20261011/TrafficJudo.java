package tr.logic;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** Poisoned gaps and three-car interference are nominations, not bonuses.
 * Only a changed real first-response decision can nominate a pace-neutral root.
 * No opponent is asked to cooperate or to replay an action from another board. */
final class TrafficJudo {
    private TrafficJudo() {}
    record Effect(Direction own, boolean released, boolean interference, CreativeForecast.Reply response) {}
    static boolean newlyAvailable(final RaceGame game, final StrategyState before,
            final StrategyState after, final Direction response) {
        if (before.slot() != after.slot()) return false;
        final RaceGame.MoveResult old = before.evaluate(game, response), now = after.evaluate(game, response);
        return old != null && now != null && !old.legal() && now.legal();
    }
    static int bestDistance(final RaceGame game, final StrategyState state) {
        if (state == null || state.live() < 2 || state.timedOut(game)) return Integer.MAX_VALUE;
        final int self = state.slot();
        int best = Integer.MAX_VALUE;
        for (final Direction d : state.legal(game, true)) {
            final StrategyState next = state.after(game, d);
            if (next != null) best = Math.min(best, next.distance(game, self));
        }
        return best;
    }
    static List<Effect> propose(final RaceGame game, final StrategyState root,
            final Direction incumbent, final int trialCap) {
        if (trialCap <= 0) return List.of();
        final StrategyState base = root.after(game, incumbent);
        if (base == null || base.live() < 2 || base.slot() == root.slot() || base.timedOut(game)) return List.of();
        final CreativeForecast.Reply reference = CreativeForecast.firstReply(game, base);
        if (reference == null) return List.of();
        final StrategyState baseReply = base.after(game, reference.action());
        final int pace = base.distance(game, root.slot());
        if (pace == Integer.MAX_VALUE) return List.of();
        final List<Direction> choices = new ArrayList<>(root.legal(game, true));
        choices.sort(Comparator.comparingInt(d -> {
            final StrategyState after = root.after(game, d);
            return after == null ? Integer.MAX_VALUE : after.distance(game, root.slot());
        }));
        final List<Effect> result = new ArrayList<>();
        int examined = 0;
        for (final Direction d : choices) {
            if (d == incumbent) continue;
            final StrategyState after = root.after(game, d);
            if (after == null || after.live() < 2 || after.slot() != base.slot()
                    || after.distance(game, root.slot()) > pace) continue;
            if (examined++ == trialCap) break;
            final CreativeForecast.Reply response = CreativeForecast.firstReply(game, after);
            if (response == null || response.action() == reference.action()) continue;
            final RaceGame.MoveResult physical = after.evaluate(game, response.action());
            if (physical == null || !physical.legal()) continue;
            final boolean released = newlyAvailable(game, base, after, response.action());
            final StrategyState reply = after.after(game, response.action());
            final boolean comparableThird = reply != null && baseReply != null && reply.live() >= 2
                    && baseReply.live() >= 2 && reply.slot() == baseReply.slot()
                    && reply.slot() != root.slot() && reply.slot() != base.slot();
            final boolean interference = comparableThird && bestDistance(game, reply) > bestDistance(game, baseReply);
            // A plain direction change without an unlocked option or actual next
            // third-car disadvantage is not labelled a poisoned-gap/judo tactic.
            if (released || interference) result.add(new Effect(d, released, interference, response));
        }
        return List.copyOf(result);
    }
}
