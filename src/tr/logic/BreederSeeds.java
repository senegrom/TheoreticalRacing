package tr.logic;

import java.util.ArrayList;
import java.util.List;

/** Seeds the offline archive with pulse and target-first interception families.
 * These are only proposals; breed1 must still execute and validate each prefix. */
@SuppressWarnings("try")
final class BreederSeeds {
    private BreederSeeds() {}
    static String json(final RaceGame game, final RacecraftReplay.Board root, final List<Direction> original) {
        final List<List<Direction>> paths = new ArrayList<>();
        try (RacecraftReplay.Scope ignored = new RacecraftReplay.Scope(game, root)) {
            final StrategyState state = StrategyState.capture(game);
            paths.addAll(CreativePaths.feints(game, state, original, new StrategyState.Budget(128)));
            for (final List<Direction> path : AmbushPlans.propose(game, state, CreativeForecast.target(state), 512))
                if (!paths.contains(path)) paths.add(path);
        }
        final List<String> encoded = new ArrayList<>();
        for (final List<Direction> path : paths) {
            final List<String> actions = new ArrayList<>();
            for (final Direction action : path) actions.add("\"" + action.name() + "\"");
            encoded.add("[" + String.join(",", actions) + "]");
        }
        return "[" + String.join(",", encoded) + "]";
    }
}
