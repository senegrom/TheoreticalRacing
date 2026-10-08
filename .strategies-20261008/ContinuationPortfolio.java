package tr.logic;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/** Two controllable own continuations, never optimistic opponent-model selection.
 * Only a chooser/pace disagreement activates the portfolio. Both first actions
 * receive both profiles and the same reactive twelve-own-move evaluation. */
@SuppressWarnings("try")
final class ContinuationPortfolio {
    private ContinuationPortfolio() {}
    enum Profile { SCORER, SOLO_PACE }
    record Choice(Direction action, FollowupPlans.Entry tail, int forecasts) {}

    static List<Direction> prefix(final RaceGame game, final RacecraftReplay.Board root,
            final Direction first, final Profile profile) {
        final List<Direction> actions = new ArrayList<>();
        try (RacecraftReplay.Scope ignored = new RacecraftReplay.Scope(game, root)) {
            for (final Player p : game.players) if (!p.isAi()) return List.of();
            final RaceAi policy = new RaceAi(game);
            for (int event = 0; event < 5 * game.players.length; event++) {
                if (game.raceTurnLimitReached() || RacecraftReplay.classifyLast(game)) break;
                final int slot = game.subgamestate;
                if (game.players[root.slot].isFinished() || slot == root.slot && actions.size() == 4) break;
                Direction action;
                if (slot == root.slot && actions.isEmpty()) action = first;
                else if (slot == root.slot && profile == Profile.SOLO_PACE) action = solo(game);
                else action = policy.researchScorer();
                if (action == null) return List.of();
                if (slot == root.slot) {
                    if (!RacecraftReplay.legalActions(game).contains(action)) return List.of();
                    actions.add(action);
                }
                RacecraftReplay.advance(game, action);
                if (RacecraftReplay.classifyLast(game)) break;
                int next = slot;
                do { next = (next + 1) % game.players.length; } while (game.players[next].isFinished());
                game.subgamestate = next;
            }
        }
        return List.copyOf(actions);
    }
    private static Direction solo(final RaceGame game) {
        Direction best = null; int cost = Integer.MAX_VALUE;
        for (final Direction d : RacecraftReplay.legalActions(game)) {
            final int value = TrafficOpportunities.ownDistance(game, game.subgamestate, d);
            if (value < cost) { best = d; cost = value; }
        }
        return best;
    }
    static Choice choose(final RaceGame game, final Direction incumbent, final Direction chooser,
            final FollowupPlans.Entry inherited) {
        if (incumbent == null || chooser == null || incumbent == chooser && inherited == null)
            return new Choice(incumbent, null, 0);
        for (final Player p : game.players) if (!p.isAi()) return new Choice(incumbent, null, 0);
        if (game.lapGates != null && game.optimalPotential() == null) return new Choice(incumbent, null, 0);
        final RacecraftReplay.Board root = RacecraftReplay.capture(game);
        final TrafficManoeuvres.Forecast baseline = TrafficManoeuvres.forecast(game, root, List.of(incumbent), 12);
        if (!baseline.outcome().known()) return new Choice(incumbent, null, 1);
        final Set<List<Direction>> proposals = new LinkedHashSet<>();
        for (final Direction first : incumbent == chooser ? List.of(incumbent) : List.of(incumbent, chooser))
            for (final Profile profile : Profile.values()) {
                final List<Direction> path = prefix(game, root, first, profile);
                if (!path.isEmpty()) proposals.add(path);
            }
        if (inherited != null && inherited.traffic()) proposals.add(inherited.actions());
        List<Direction> best = List.of(incumbent);
        TrafficManoeuvres.Forecast value = baseline;
        int forecasts = 1;
        for (final List<Direction> path : proposals) {
            final TrafficManoeuvres.Forecast outcome = TrafficManoeuvres.forecast(game, root, path, 12); forecasts++;
            if (outcome.outcome().betterThan(value.outcome(), false)) { best = path; value = outcome; }
        }
        final FollowupPlans.Entry tail = best.size() < 2 || value.nextKey() == null ? null
                : FollowupPlans.Entry.traffic(best.subList(1, best.size()), value.nextKey());
        return new Choice(best.get(0), tail, forecasts);
    }
}
