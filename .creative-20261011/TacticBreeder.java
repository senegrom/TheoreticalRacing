package tr.logic;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Offline multi-action counterfactual oracle. Mutated prefixes execute through
 * the real referee with all other cars making fresh production decisions.
 * Complete traces, prefix endpoints and policy memory make legal ancestry
 * reproducible. This endpoint never installs a learned policy or alters a race. */
@SuppressWarnings("try")
final class TacticBreeder {
    private TacticBreeder() {}
    record Trial(RacecraftReplay.Tail tail, boolean validPrefix, int forcedExecuted,
            String endpoint, List<Direction> legalNext, List<Direction> ownActions) {
        Trial { legalNext = List.copyOf(legalNext); ownActions = List.copyOf(ownActions); }
    }
    static Trial run(final RaceGame game, final RacecraftReplay.Board root,
            final List<Direction> prefix, final int maxMoves) {
        if (prefix.size() > 4 || maxMoves < 1 || maxMoves > 100000)
            throw new IllegalArgumentException("invalid breeder limits");
        final List<String> trace = new ArrayList<>();
        final List<Direction> ownActions = new ArrayList<>();
        final int self = root.slot;
        try (RacecraftReplay.Scope ignored = new RacecraftReplay.Scope(game, root)) {
            for (final Player p : game.players) if (!p.isAi()) throw new IllegalArgumentException("breeder needs AI-only rosters");
            final RaceAi policy = new RaceAi(game);
            int own = 0, forcedExecuted = 0;
            String endpoint = null;
            List<Direction> legalNext = List.of();
            boolean complete = RacecraftReplay.classifyLast(game), valid = true;
            RacecraftOutcome.Status status = complete ? RacecraftOutcome.Status.CLASSIFIED : RacecraftOutcome.Status.RUNNING;
            for (int step = 0; step < maxMoves && !complete; step++) {
                final int slot = game.subgamestate;
                if (game.raceTurnLimitReached()) {
                    int live = 0; for (final Player p : game.players) if (!p.isFinished()) live++;
                    if (live - (game.players.length == 1 ? 0 : 1) > maxMoves - step) break;
                    final List<String> expired = RacecraftReplay.expire(game);
                    for (final String row : expired) if (row.startsWith(self + ":")) { own++; status = RacecraftOutcome.Status.TIMED_OUT; }
                    if (status == RacecraftOutcome.Status.RUNNING) status = RacecraftOutcome.Status.CLASSIFIED;
                    trace.addAll(expired); complete = true; break;
                }
                if (slot == self && own == prefix.size() && endpoint == null) {
                    endpoint = RacecraftReplay.snapshot(game); legalNext = RacecraftReplay.legalActions(game);
                }
                final Direction proposed = policy.computeAiMove();
                final boolean forced = slot == self && own < prefix.size();
                final Direction action = forced ? prefix.get(own) : proposed;
                if (action == null || forced && !RacecraftReplay.legalActions(game).contains(action)) { valid = false; break; }
                if (slot == self) {
                    if (ownActions.size() < 4) ownActions.add(action);
                    own++; if (forced) forcedExecuted++;
                }
                policy.commitResearchPlan(action);
                final String transition = RacecraftReplay.advance(game, action); trace.add(transition);
                if (slot == self && game.players[self].isFinished()) status = transition.contains(":FINISH:")
                        ? RacecraftOutcome.Status.FINISHED : RacecraftOutcome.Status.CRASHED;
                complete = RacecraftReplay.classifyLast(game);
                if (complete && status == RacecraftOutcome.Status.RUNNING && game.players[self].isFinished())
                    status = RacecraftOutcome.Status.CLASSIFIED;
                if (!complete) CreativeForecast.advanceSlot(game, slot);
            }
            final StrategyState end = StrategyState.capture(game);
            final int place = end.place(self);
            final RacecraftOutcome outcome = !valid ? RacecraftOutcome.unknown()
                    : new RacecraftOutcome(status, place == 0 ? game.researchFinishedFirst() : place - 1,
                            own, end.distance(game, self));
            return new Trial(new RacecraftReplay.Tail(complete && valid, place, own, outcome,
                    RacecraftReplay.snapshot(game), trace), valid, forcedExecuted, endpoint, legalNext, ownActions);
        }
    }
    static String answer(final RaceGame game, final String request) {
        final int divider = request.indexOf('|');
        if (divider < 0 || request.length() > 280000) throw new IllegalArgumentException("invalid breed1 request");
        final String[] header = request.substring(0, divider).split(",", -1);
        if (header.length != 3 || !header[0].equals("breed1")) throw new IllegalArgumentException("invalid breed1 header");
        final int bound = Integer.parseInt(header[1]);
        final List<Direction> prefix = header[2].equals("-") ? List.of()
                : Arrays.stream(header[2].split("\\+", -1)).map(Direction::valueOf).toList();
        if (prefix.size() > 4 || bound < 1 || bound > 100000) throw new IllegalArgumentException("invalid breed1 budget/prefix");
        final RacecraftReplay.Board root = RacecraftReplay.parse(game, request.substring(divider + 1));
        final Direction actual;
        final List<Direction> legal;
        try (RacecraftReplay.Scope ignored = new RacecraftReplay.Scope(game, root)) {
            actual = new RaceAi(game).computeAiMove(); legal = RacecraftReplay.legalActions(game);
        }
        if (actual == null) throw new IllegalArgumentException("no control action");
        final Trial trial = run(game, root, prefix, bound);
        final Direction first = prefix.isEmpty() ? actual : prefix.get(0);
        final RacecraftReplay.Tail tail = trial.tail();
        return "{\"schema\":1,\"requestSha256\":" + quote(RacecraftReplay.sha(request))
                + ",\"rootIdentity\":" + quote(root.identity) + ",\"baseline\":" + quote(actual.name())
                + ",\"maxMoves\":" + bound + ",\"prefix\":" + directions(prefix)
                + ",\"validPrefix\":" + trial.validPrefix() + ",\"forcedExecuted\":" + trial.forcedExecuted()
                + ",\"endpoint\":" + quote(trial.endpoint()) + ",\"legalNext\":" + directions(trial.legalNext())
                + ",\"ownActions\":" + directions(trial.ownActions()) + ",\"trial\":{\"action\":" + quote(first.name())
                + ",\"legal\":" + legal.contains(first) + ",\"complete\":" + tail.complete()
                + ",\"place\":" + tail.place() + ",\"ownMoves\":" + tail.ownMoves()
                + ",\"status\":" + quote(tail.outcome().status().name())
                + ",\"traceSha256\":" + quote(RacecraftReplay.sha(String.join("\n", tail.trace())))
                + ",\"trace\":" + strings(tail.trace()) + ",\"finalState\":" + quote(tail.finalState()) + "}}";
    }
    private static String directions(final List<Direction> values) {
        return strings(values.stream().map(Enum::name).toList());
    }
    private static String strings(final List<String> values) {
        return "[" + String.join(",", values.stream().map(TacticBreeder::quote).toList()) + "]";
    }
    private static String quote(final String text) {
        return text == null ? "null" : "\"" + text.replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", "\\n").replace("\r", "\\r") + "\"";
    }
}
