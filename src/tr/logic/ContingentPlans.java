package tr.logic;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Bounded conditional-second-action research. Both worlds use the SAME rival:
 * its nominal scorer reply or its stronger first reply. Each trial reruns the
 * whole prefix, and the second action is installed through the exact same
 * response mechanism used by a real committed move. No trace splicing. */
@SuppressWarnings("try")
final class ContingentPlans {
    private ContingentPlans() {}
    record Forecast(boolean known, int ahead, long time, ResearchBoard next, Direction second) {}
    record Result(DecisionResearch.Proposal proposal, int trials) {}
    interface Policy { Direction select(RaceGame game, RaceAi ai, boolean strong); }
    private static final Policy POLICY = (g, ai, strong) -> strong ? ai.computeAiMove() : ai.researchScorer();
    private static Forecast unknown() { return new Forecast(false, 0, 0, null, null); }
    static boolean better(final Forecast a, final Forecast b) {
        return a.known && b.known && (a.ahead < b.ahead || a.ahead == b.ahead && a.time < b.time);
    }
    static boolean noWorse(final Forecast a, final Forecast b) {
        return a.known && b.known && (a.ahead < b.ahead || a.ahead == b.ahead && a.time <= b.time);
    }
    static boolean improvesBothWorlds(final Forecast[] a, final Forecast[] b) {
        return noWorse(a[0], b[0]) && noWorse(a[1], b[1]) && (better(a[0], b[0]) || better(a[1], b[1]));
    }
    static Result choose(final RaceGame game, final ResearchBoard root, final Direction incumbent,
            final List<Direction> candidates, final int budget) {
        return choose(game, root, incumbent, candidates, budget, POLICY);
    }
    static Result choose(final RaceGame game, final ResearchBoard root, final Direction incumbent,
            final List<Direction> candidates, final int budget, final Policy policy) {
        if (budget < 4) return new Result(null, 0);
        final int target = target(root, incumbent);
        if (target < 0) return new Result(null, 0);
        final Forecast[] base = new Forecast[2]; int used = 0;
        for (int world = 0; world < 2; world++) { base[world] = run(game, root, incumbent, null, target, world, policy); used++; }
        if (!base[0].known || !base[1].known) return new Result(null, used);
        Forecast[] best = base; DecisionResearch.Proposal proposal = null;
        final List<Direction> ordered = new ArrayList<>(); ordered.add(incumbent);
        for (final Direction d : candidates) if (d != incumbent) ordered.add(d);
        for (final Direction first : ordered) {
            if (used + 2 > budget) break;
            final Forecast[] forecasts = new Forecast[2];
            for (int world = 0; world < 2; world++) {
                Forecast f = run(game, root, first, null, target, world, policy); used++;
                if (f.known && f.next != null && used + (1 - world) < budget) {
                    final List<Direction> alternatives = secondCandidates(game, f.next);
                    int extra = 0;
                    for (final Direction second : alternatives) {
                        if (second == f.second) continue;
                        // Always reserve the OTHER world's baseline comparison.
                        if (extra == 2 || used + (1 - world) >= budget) break;
                        final Forecast alternative = run(game, root, first, second, target, world, policy); used++; extra++;
                        if (better(alternative, f)) f = alternative;
                    }
                }
                forecasts[world] = f;
            }
            if (!improvesBothWorlds(forecasts, best)) continue;
            final Map<String, Direction> responses = new TreeMap<>(); boolean consistent = true;
            for (final Forecast f : forecasts) {
                if (f.next == null || f.second == null) { consistent = false; break; }
                final Direction prior = responses.put(f.next.physicalKey(), f.second);
                if (prior != null && prior != f.second) consistent = false;
            }
            if (consistent) {
                proposal = new DecisionResearch.Proposal(root.physicalKey(), first, responses);
                best = forecasts;
            }
        }
        return new Result(proposal, used);
    }

    private static List<Direction> secondCandidates(final RaceGame game, final ResearchBoard board) {
        try (ResearchBoard.Scope scope = new ResearchBoard.Scope(game, board)) {
            final List<Direction> actions = ResearchBoard.legal(game);
            final int[] distances = new int[9];
            for (final Direction d : actions) {
                try (ResearchBoard.Scope child = new ResearchBoard.Scope(game, board)) {
                    ResearchBoard.advance(game, d, new String[game.players.length], new int[game.players.length]);
                    distances[d.ordinal()] = ResearchBoard.distance(game, board.slot);
                }
            }
            // Spend the two alternative trials on promising continuations,
            // rather than always NW/N merely because they are first in the enum.
            actions.sort(java.util.Comparator.comparingInt((Direction d) -> distances[d.ordinal()])
                    .thenComparingInt(Direction::ordinal));
            return actions;
        }
    }

    private static int target(final ResearchBoard b, final Direction action) {
        final int[] own = b.cars[b.slot];
        final int x = own[0] + own[2] + action.dx, y = own[1] + own[3] + action.dy;
        int target = -1, best = Integer.MAX_VALUE;
        for (int i = 0; i < b.cars.length; i++) if (i != b.slot && b.cars[i][4] == 0) {
            final int[] r = b.cars[i];
            final int d = Math.max(Math.abs(x - r[0] - r[2]), Math.abs(y - r[1] - r[3]));
            if (d < best) { target = i; best = d; }
        }
        return target;
    }

    static Forecast run(final RaceGame game, final ResearchBoard root, final Direction first,
            final Direction second, final int target, final int world, final Policy policy) {
        if (world < 0 || world > 1 || target < 0 || target >= root.cars.length || target == root.slot)
            throw new IllegalArgumentException("invalid contingent forecast profile");
        try (ResearchBoard.Scope scope = new ResearchBoard.Scope(game, root)) {
            game.research.suppressed++; game.research.allowResponse = true;
            final RaceAi ai = new RaceAi(game);
            final int own = root.slot, n = root.cars.length;
            final int[] moves = new int[n]; final String[] outcomes = new String[n];
            ResearchBoard next = null; Direction response = null; boolean targetUsed = false;
            for (int event = 0; event < 13 * n; event++) {
                if (game.raceTurnLimitReached()) return unknown();
                if (game.players[own].isFinished()) {
                    if ("CRASH".equals(outcomes[own]))
                        return new Forecast(true, game.players[own].getFinishedPlace() - 1, moves[own], next, response);
                    return new Forecast(true, game.players[own].getFinishedPlace() - 1, moves[own], next, response);
                }
                final int slot = game.subgamestate;
                if (slot == own && moves[own] == 12) {
                    final int distance = ResearchBoard.distance(game, own);
                    return distance == Integer.MAX_VALUE ? unknown()
                            : new Forecast(true, game.researchFinishedFirst(), (long)moves[own] + distance, next, response);
                }
                if (slot == own && moves[own] == 1) {
                    next = ResearchBoard.capture(game);
                    if (second != null) game.research.plans = game.research.plans.with(own, Map.of(next.physicalKey(), second));
                }
                final boolean forced = event == 0;
                final boolean strong = !forced && (slot == own && moves[own] <= 5 || slot == target && world == 1 && !targetUsed);
                final Direction action = forced ? first : policy.select(game, ai, strong);
                if (slot == target) targetUsed = true;
                if (action == null || forced && !ResearchBoard.legal(game).contains(action)) return unknown();
                if (slot == own && moves[own] == 1) {
                    // A proof, finish or solo-rule override makes the explicit plan
                    // inadmissible. It cannot quietly pretend the action was followed.
                    if (second != null && action != second) return unknown();
                    response = action;
                }
                game.research.commit(game, ai, action);
                ResearchBoard.advance(game, action, outcomes, moves);
                // A cheap rival's predicted retirement never earns a winning plan.
                if (slot != own && "CRASH".equals(outcomes[slot])) return unknown();
                if (ResearchBoard.classify(game, outcomes)) {
                    if ("CRASH".equals(outcomes[own])) return new Forecast(true, game.players[own].getFinishedPlace() - 1, moves[own], next, response);
                    return new Forecast(true, game.players[own].getFinishedPlace() - 1, moves[own], next, response);
                }
                ResearchBoard.next(game);
            }
            return unknown();
        }
    }
}
