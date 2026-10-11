package tr.logic;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;

/** Bounded creative nominations, followed by a separate acceptance stage.
 * All values concern the mover's own place and time. No opponent-delay bonus,
 * no cooperative action, no widening of the outer twenty-cell rule. */
final class CreativeTactics {
    private CreativeTactics() {}
    record Proposal(String source, List<Direction> actions) {
        Proposal { actions = List.copyOf(actions); }
    }
    record Choice(Direction action, FollowupPlans.Entry tail, int proposals, int forecasts,
            boolean accepted, boolean checked) {}
    record Judgement(boolean accepted, CreativeForecast.Result challenger) {}
    static boolean better(final RacecraftOutcome candidate, final RacecraftOutcome incumbent) {
        return candidate != null && incumbent != null && candidate.known() && incumbent.known()
                && (candidate.ahead() < incumbent.ahead() || candidate.ahead() == incumbent.ahead()
                        && candidate.time() < incumbent.time());
    }
    static Judgement check(final List<Direction> incumbent, final List<Direction> challenger,
            final Function<List<Direction>, CreativeForecast.Result> judge) {
        // Fresh, matched evaluations. Do not fall back to a second convenient
        // proposal after a rejection; that would search the checking model too.
        final CreativeForecast.Result base = judge.apply(incumbent);
        final CreativeForecast.Result candidate = judge.apply(challenger);
        return new Judgement(better(candidate.outcome(), base.outcome()), candidate);
    }
    static Choice choose(final RaceGame game, final List<Direction> incumbent,
            final FollowupPlans.Entry inherited) {
        final Direction first = incumbent.get(0);
        final int self = game.subgamestate, player = game.players[self].getNumber();
        if (!game.racecraftNext.creativeEnabled(game, player)) return new Choice(first, null, 0, 0, false, false);
        for (final Player p : game.players) if (!p.isAi()) return new Choice(first, null, 0, 0, false, false);
        if (game.lapGates != null && game.optimalPotential() == null) return new Choice(first, null, 0, 0, false, false);
        final StrategyState root = StrategyState.capture(game);
        final int target = CreativeForecast.target(root);
        if (target < 0 || root.timedOut(game)) return new Choice(first, null, 0, 0, false, false);
        final CreativeForecast.Result base = CreativeForecast.run(game, root.board, incumbent, 12, CreativeForecast.Model.SCORER, target);
        if (!base.outcome().known()) return new Choice(first, null, 0, 1, false, false);
        final List<List<Proposal>> groups = new ArrayList<>();
        final boolean feints = game.racecraftNext.enabled(game, player, RacecraftNext.Feature.PACE_FEINTS);
        final boolean ambush = game.racecraftNext.enabled(game, player, RacecraftNext.Feature.AMBUSH);
        final boolean judo = game.racecraftNext.enabled(game, player, RacecraftNext.Feature.TRAFFIC_JUDO);
        final boolean selfish = game.racecraftNext.enabled(game, player, RacecraftNext.Feature.SELFISH_SEARCH);
        final boolean checker = game.racecraftNext.enabled(game, player, RacecraftNext.Feature.TWO_JUDGE);
        final int generators = (feints ? 1 : 0) + (ambush ? 1 : 0) + (judo ? 1 : 0) + (selfish ? 1 : 0);
        final int share = game.racecraftNext.creativeNodes / Math.max(1, generators);
        if (inherited != null && inherited.traffic()) groups.add(List.of(new Proposal("retained", inherited.actions())));
        if (feints) groups.add(label("feint", CreativePaths.feints(game, root, base.ownPrefix(), new StrategyState.Budget(share))));
        if (ambush) groups.add(label("ambush", AmbushPlans.propose(game, root, target, share)));
        if (judo) {
            final List<Proposal> proposals = new ArrayList<>();
            for (final TrafficJudo.Effect effect : TrafficJudo.propose(game, root, first,
                    Math.min(3, Math.min(share, game.racecraftNext.creativeTrials))))
                proposals.add(new Proposal(effect.interference() ? "judo" : "gap", List.of(effect.own())));
            groups.add(proposals);
        }
        if (selfish && root.live() == 3 && root.distance(game, self) <= 10) {
            final Direction move = SelfishSearch.search(game, root, game.racecraftNext.selfishPlies, share).best(self);
            groups.add(move == null ? List.of() : List.of(new Proposal("selfish", List.of(move))));
        }
        if (checker && generators == 0) {
            // Standalone checker experiment: use the existing manoeuvre generator,
            // rather than silently enabling all four new generators.
            final TrafficManoeuvres.Forecast ordinary = TrafficManoeuvres.forecast(game, root.board, incumbent, 12);
            groups.add(label("manoeuvre", TrafficManoeuvres.propose(game, ordinary.schedule(), first, 4,
                    Math.min(game.racecraftNext.manoeuvreNodes, share)).proposals()));
        }
        final List<Proposal> offered = roundRobin(groups, game.racecraftNext.creativeTrials, incumbent);
        CreativeForecast.Result value = base;
        List<Direction> best = incumbent;
        int forecasts = 1, examined = 0;
        for (final Proposal proposal : offered) {
            if (!root.legal(game, true).contains(proposal.actions().get(0))) continue;
            final CreativeForecast.Result trial = CreativeForecast.run(game, root.board, proposal.actions(), 12,
                    CreativeForecast.Model.SCORER, target);
            examined++; forecasts++;
            if (better(trial.outcome(), value.outcome())) { best = proposal.actions(); value = trial; }
        }
        if (best.equals(incumbent)) return new Choice(first, null, examined, forecasts, false, false);
        if (checker) {
            final Judgement result = check(incumbent, best, plan -> CreativeForecast.run(game, root.board, plan, 12,
                    CreativeForecast.Model.FULL_FIRST, target));
            forecasts += 2;
            if (!result.accepted()) return new Choice(first, null, examined, forecasts, false, true);
            value = result.challenger();
        }
        final FollowupPlans.Entry tail = best.size() < 2 || value.nextKey() == null ? null
                : FollowupPlans.Entry.traffic(best.subList(1, best.size()), value.nextKey());
        return new Choice(best.get(0), tail, examined, forecasts, true, checker);
    }
    static List<Proposal> roundRobin(final List<List<Proposal>> groups, final int cap, final List<Direction> incumbent) {
        final List<Proposal> result = new ArrayList<>();
        final List<List<Direction>> seen = new ArrayList<>(); seen.add(incumbent);
        int round = 0;
        boolean more = true;
        while (more && result.size() < cap) {
            more = false;
            for (final List<Proposal> group : groups) if (round < group.size()) {
                more = true;
                final Proposal candidate = group.get(round);
                if (!candidate.actions().isEmpty() && candidate.actions().size() <= 4 && !seen.contains(candidate.actions())) {
                    seen.add(candidate.actions()); result.add(candidate);
                    if (result.size() == cap) break;
                }
            }
            round++;
        }
        return List.copyOf(result);
    }
    private static List<Proposal> label(final String label, final List<List<Direction>> paths) {
        final List<Proposal> result = new ArrayList<>();
        for (final List<Direction> path : paths) result.add(new Proposal(label, path));
        return List.copyOf(result);
    }
}
