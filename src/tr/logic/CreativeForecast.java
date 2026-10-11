package tr.logic;

import java.util.ArrayList;
import java.util.List;

/** Discovery and checking are distinct fixed models. FULL_FIRST upgrades only
 * the fixed target rival's first action and our first unforced future action;
 * calls beneath those decisions use the suppressed scorer. Never a proof. */
@SuppressWarnings("try")
final class CreativeForecast {
    private CreativeForecast() {}
    enum Model { SCORER, FULL_FIRST }
    record Reply(int slot, Direction action, int x, int y) {}
    record Result(RacecraftOutcome outcome, List<Direction> ownPrefix, List<Reply> replies,
            String nextKey, StrategyState end, int fullCalls) {
        Result { ownPrefix = List.copyOf(ownPrefix); replies = List.copyOf(replies); }
    }
    /** Fixed across alternatives, not selected by whichever response looks best. */
    static int target(final StrategyState root) {
        for (int offset = 1; offset < root.board.cars.length; offset++) {
            final int slot = (root.slot() + offset) % root.board.cars.length;
            if (root.place(slot) == 0) return slot;
        }
        return -1;
    }
    static Result run(final RaceGame game, final RacecraftReplay.Board root, final List<Direction> prefix,
            final int horizon, final Model model, final int target) {
        if (prefix.isEmpty() || prefix.size() > 4 || horizon < prefix.size() || horizon > 24
                || target < -1 || target >= root.cars.length || target == root.slot)
            throw new IllegalArgumentException("invalid creative forecast");
        final List<Direction> ownPrefix = new ArrayList<>();
        final List<Reply> replies = new ArrayList<>();
        try (RacecraftReplay.Scope ignored = new RacecraftReplay.Scope(game, root)) {
            for (final Player p : game.players) if (!p.isAi()) return unknown(game, ownPrefix, replies, null, 0);
            final RaceAi policy = new RaceAi(game);
            final boolean[] firstReply = new boolean[root.cars.length];
            boolean selfUsed = false, targetUsed = false, stopped = false;
            int own = 0, fullCalls = 0;
            String nextKey = null;
            RacecraftOutcome.Status status = RacecraftOutcome.Status.RUNNING;
            boolean complete = RacecraftReplay.classifyLast(game);
            final int eventCap = (horizon + 1) * root.cars.length;
            for (int event = 0; event < eventCap && !complete; event++) {
                final int slot = game.subgamestate;
                if (game.raceTurnLimitReached()) {
                    final List<String> expired = RacecraftReplay.expire(game);
                    boolean retired = false;
                    for (final String line : expired) if (line.startsWith(root.slot + ":")) { own++; retired = true; }
                    status = retired ? RacecraftOutcome.Status.TIMED_OUT : RacecraftOutcome.Status.CLASSIFIED;
                    complete = true; break;
                }
                if (slot == root.slot) {
                    if (own == 1) nextKey = FollowupPlans.key(game);
                    if (own == horizon) { stopped = true; break; }
                }
                final boolean forced = slot == root.slot && own < prefix.size();
                final boolean strong = !forced && model == Model.FULL_FIRST
                        && (slot == target && !targetUsed || slot == root.slot && !selfUsed);
                final Direction action = forced ? prefix.get(own)
                        : strong ? policy.researchFullFirst() : policy.researchScorer();
                if (strong) { fullCalls++; if (slot == target) targetUsed = true; else selfUsed = true; }
                if (action == null || forced && !RacecraftReplay.legalActions(game).contains(action))
                    return unknown(game, ownPrefix, replies, nextKey, fullCalls);
                if (slot == root.slot) { if (ownPrefix.size() < 4) ownPrefix.add(action); own++; }
                else if (!firstReply[slot]) {
                    final int[] x = game.players[slot].getPosition(), v = game.players[slot].getVelocity();
                    replies.add(new Reply(slot, action, x[0] + v[0] + action.dx, x[1] + v[1] + action.dy));
                    firstReply[slot] = true;
                }
                final String transition = RacecraftReplay.advance(game, action);
                if (slot == root.slot && game.players[root.slot].isFinished())
                    status = transition.contains(":FINISH:") ? RacecraftOutcome.Status.FINISHED : RacecraftOutcome.Status.CRASHED;
                complete = RacecraftReplay.classifyLast(game);
                if (game.players[root.slot].isFinished()) {
                    if (status == RacecraftOutcome.Status.RUNNING) status = RacecraftOutcome.Status.CLASSIFIED;
                    stopped = true; break;
                }
                if (!complete) advanceSlot(game, slot);
            }
            final StrategyState end = StrategyState.capture(game);
            if (!complete && !stopped) return unknown(game, ownPrefix, replies, nextKey, fullCalls);
            final int place = end.place(root.slot);
            return new Result(new RacecraftOutcome(status, place == 0 ? game.researchFinishedFirst() : place - 1,
                    own, end.distance(game, root.slot)), ownPrefix, replies, nextKey, end, fullCalls);
        }
    }
    static void advanceSlot(final RaceGame game, final int old) {
        int next = old;
        do { next = (next + 1) % game.players.length; } while (game.players[next].isFinished());
        game.subgamestate = next;
    }
    private static Result unknown(final RaceGame game, final List<Direction> own, final List<Reply> replies,
            final String nextKey, final int fullCalls) {
        return new Result(RacecraftOutcome.unknown(), own, replies, nextKey, StrategyState.capture(game), fullCalls);
    }
    /** Full first rival response at its actual next turn, with all intermediates
     * already supplied by the root transition. Used only for nominations. */
    static Reply firstReply(final RaceGame game, final StrategyState state) {
        if (state.live() < 2 || state.timedOut(game)) return null;
        try (RacecraftReplay.Scope ignored = new RacecraftReplay.Scope(game, state.board)) {
            if (!game.players[state.slot()].isAi()) return null;
            final Direction action = new RaceAi(game).researchFullFirst();
            if (action == null) return null;
            final int[] row = state.board.cars[state.slot()];
            return new Reply(state.slot(), action, row[2] + row[4] + action.dx, row[3] + row[5] + action.dy);
        }
    }
}
