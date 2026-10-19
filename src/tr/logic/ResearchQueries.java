package tr.logic;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** rp3 snapshots plus bounded complete referee continuations. Responses carry
 * every terminal fate, actual per-car moves, trace and request digest. */
@SuppressWarnings("try")
final class ResearchQueries {
    private ResearchQueries() {}
    static String answer(final RaceGame game, final String line) {
        if (line.equals("snapshot3")) return ResearchBoard.capture(game).encode();
        final String[] request = line.split("\\|", 4);
        // Snapshot plan tables contain '|', so split only the tail3 prefix.
        if (request.length != 4 || !request[0].equals("tail3"))
            throw new IllegalArgumentException("expected tail3|budget|first-action (-1=control)|rp3 snapshot");
        final int budget = Integer.parseInt(request[1]), first = Integer.parseInt(request[2]);
        if (budget < 1 || budget > 100000 || first < -1 || first > 8)
            throw new IllegalArgumentException("research tail budget/action out of range");
        final ResearchBoard board = ResearchBoard.parse(game, request[3]);
        return tail(game, board, budget, first, ResearchBoard.sha256(line));
    }

    static String tail(final RaceGame game, final ResearchBoard root, final int budget,
            final int firstAction, final String requestId) {
        try (ResearchBoard.Scope scope = new ResearchBoard.Scope(game, root)) {
            for (final Player p : game.players) if (!p.isAi())
                throw new IllegalArgumentException("full research tails require AI-only profiles");
            final RaceAi ai = new RaceAi(game);
            final int n = game.players.length;
            final String[] outcomes = new String[n]; final int[] moves = new int[n];
            Arrays.fill(outcomes, "RUNNING");
            for (int i = 0; i < n; i++) if (game.players[i].isFinished()) outcomes[i] = "PRIOR";
            final List<String> trace = new ArrayList<>();
            boolean complete = ResearchBoard.classify(game, outcomes);
            for (int event = 0; event < budget && !complete; event++) {
                if (game.raceTurnLimitReached()) {
                    ResearchBoard.expire(game, outcomes, moves, trace); complete = true; break;
                }
                final Direction ordinary = ai.computeAiMove();
                final Direction action = event == 0 && firstAction >= 0 ? Direction.values()[firstAction] : ordinary;
                if (action == null) break; // incomplete and unusable as a label
                game.research.commit(game, ai, action);
                trace.add(ResearchBoard.advance(game, action, outcomes, moves));
                complete = ResearchBoard.classify(game, outcomes);
                if (!complete) ResearchBoard.next(game);
            }
            final int[] places = new int[n];
            for (int i = 0; i < n; i++) places[i] = game.players[i].getFinishedPlace();
            final StringBuilder b = new StringBuilder("{\"schema\":1,\"request_id\":")
                    .append(DecisionResearch.quote(requestId)).append(",\"complete\":").append(complete)
                    .append(",\"engine\":").append(DecisionResearch.quote(DecisionResearch.engineId()))
                    .append(",\"policy\":").append(DecisionResearch.quote(game.research.policyId))
                    .append(",\"places\":").append(Arrays.toString(places)).append(",\"moves\":")
                    .append(Arrays.toString(moves)).append(",\"outcomes\":[");
            for (int i = 0; i < n; i++) b.append(i == 0 ? "" : ",").append(DecisionResearch.quote(outcomes[i]));
            b.append("],\"trace\":[");
            for (int i = 0; i < trace.size(); i++) b.append(i == 0 ? "" : ",").append(DecisionResearch.quote(trace.get(i)));
            return b.append("],\"trace_hash\":").append(DecisionResearch.quote(ResearchBoard.sha256(String.join("\n", trace))))
                    .append('}').toString();
        }
    }
}
