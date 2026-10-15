package tr.logic;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Best-first AND/OR proof-number search. A disproof is only of the bounded
 * win-by-deadline goal, never of winning the whole race. Every physical rival
 * acceleration is represented. Only completed proofs become executable plans. */
final class ProofNumberSearch {
    private ProofNumberSearch() {}
    private static final long INF = 1_000_000_000L;
    private static final Direction[] ACTIONS = Direction.values();
    record Answer(Direction action, int left) {}
    record Plan(int place, int expires, Map<String, Answer> answers) {
        Plan {
            answers = java.util.Collections.unmodifiableMap(new TreeMap<>(answers));
            if (place < 1 || place > 9 || expires < 0 || answers.isEmpty() || answers.size() > 512)
                throw new IllegalArgumentException("invalid proof plan");
            for (final Map.Entry<String, Answer> e : answers.entrySet())
                if (!e.getKey().matches("[0-9a-f]{64}") || e.getValue().action() == null
                        || e.getValue().left() < 1 || e.getValue().left() > 12)
                    throw new IllegalArgumentException("invalid proof response");
        }
        Answer at(final StrategyState s) { return s.board.turn <= expires ? answers.get(s.key()) : null; }
        String encode() {
            final StringBuilder text = new StringBuilder().append(place).append('_').append(expires);
            for (final Map.Entry<String, Answer> e : answers.entrySet())
                text.append('!').append(e.getKey()).append('_').append(e.getValue().action()).append('_').append(e.getValue().left());
            return text.toString();
        }
        static Plan parse(final String text) {
            final String[] rows = text.split("!", -1), header = rows[0].split("_", -1);
            if (header.length != 2 || rows.length < 2 || rows.length > 513)
                throw new IllegalArgumentException("invalid proof encoding");
            final Map<String, Answer> map = new TreeMap<>();
            for (int i = 1; i < rows.length; i++) {
                final String[] f = rows[i].split("_", -1);
                if (f.length != 3 || map.put(f[0], new Answer(Direction.valueOf(f[1]), Integer.parseInt(f[2]))) != null)
                    throw new IllegalArgumentException("duplicate proof state");
            }
            final Plan plan = new Plan(Integer.parseInt(header[0]), Integer.parseInt(header[1]), map);
            if (!plan.encode().equals(text)) throw new IllegalArgumentException("noncanonical proof encoding");
            return plan;
        }
    }
    record Result(Plan plan, Direction action, int transitions, boolean refuted, int deadline) {}
    private static final class Node {
        final StrategyState state;
        final int left;
        final Node parent;
        final Direction action;
        final boolean or;
        final List<Node> children = new ArrayList<>();
        long proof = 1, disproof = 1;
        boolean expanded, blocked;
        Node(final RaceGame game, final StrategyState s, final int self, final int goal,
                final int remaining, final Node parent, final Direction action) {
            state = s != null && s.timedOut(game) ? s.expire(game) : s;
            left = remaining; this.parent = parent; this.action = action;
            or = state != null && state.slot() == self;
            if (state == null) { blocked = true; proof = disproof = INF; }
            else if (state.place(self) != 0) terminal(state.place(self) == goal);
            else if (or && remaining == 0 || remaining < 0) terminal(false);
        }
        void terminal(final boolean win) { proof = win ? 0 : INF; disproof = win ? INF : 0; expanded = true; }
    }
    static Result search(final RaceGame game, final StrategyState state, final int deadline, final int limit) {
        if (deadline < 1 || deadline > 12 || limit < 0) throw new IllegalArgumentException("invalid proof budget");
        final int self = state.slot(), goal = state.board.first + 1;
        if (state.live() != 2 || state.place(self) != 0 || state.timedOut(game))
            return new Result(null, null, 0, false, deadline);
        final Node root = new Node(game, state, self, goal, deadline, null, null);
        int used = 0;
        while (root.proof != 0 && root.disproof != 0 && used < limit) {
            Node leaf = root;
            while (leaf.expanded && !leaf.children.isEmpty()) {
                Node chosen = null;
                for (final Node child : leaf.children)
                    if (chosen == null || (leaf.or ? child.proof < chosen.proof : child.disproof < chosen.disproof)) chosen = child;
                leaf = chosen;
            }
            if (leaf.blocked || leaf.expanded || limit - used < ACTIONS.length) break;
            // Reserve the complete expansion. A missing reply never looks like a win.
            for (final Direction action : ACTIONS) {
                used++;
                if (leaf.or && !leaf.state.ownDomain(action)) continue;
                final StrategyState next = leaf.state.after(game, action);
                leaf.children.add(new Node(game, next, self, goal, leaf.left - (leaf.or ? 1 : 0), leaf, action));
            }
            leaf.expanded = true;
            if (leaf.children.isEmpty()) leaf.terminal(false);
            for (Node n = leaf; n != null; n = n.parent) update(n);
        }
        if (root.proof != 0) return new Result(null, null, used, root.disproof == 0, deadline);
        final Map<String, Answer> answers = new LinkedHashMap<>();
        if (!extract(root, answers) || answers.size() > 512) return new Result(null, null, used, false, deadline);
        final long expiration = (long) state.board.turn + 2L * deadline;
        if (expiration > Integer.MAX_VALUE) return new Result(null, null, used, false, deadline);
        final Plan plan = new Plan(goal, (int) expiration, answers);
        final Answer first = plan.at(state);
        return new Result(plan, first == null ? null : first.action(), used, false, deadline);
    }
    /** Search shorter deadlines first with one shared transition allowance. */
    static Result iterative(final RaceGame game, final StrategyState state, final int minimum,
            final int maximum, final int limit) {
        int used = 0;
        for (int deadline = minimum; deadline <= maximum; deadline++) {
            final Result result = search(game, state, deadline, Math.max(0, limit - used));
            used += result.transitions();
            if (result.plan() != null || !result.refuted())
                return new Result(result.plan(), result.action(), used, result.refuted(), deadline);
        }
        return new Result(null, null, used, true, maximum);
    }
    private static void update(final Node n) {
        if (n.children.isEmpty()) return;
        long minimum = INF, sum = 0;
        for (final Node child : n.children) {
            minimum = Math.min(minimum, n.or ? child.proof : child.disproof);
            sum = Math.min(INF, sum + (n.or ? child.disproof : child.proof));
        }
        n.proof = n.or ? minimum : sum;
        n.disproof = n.or ? sum : minimum;
    }
    private static boolean extract(final Node n, final Map<String, Answer> answers) {
        if (n.proof != 0) return false;
        if (n.children.isEmpty()) return true;
        if (n.or) {
            Node chosen = null;
            for (final Node child : n.children) if (child.proof == 0) { chosen = child; break; }
            if (chosen == null) return false;
            final Answer answer = new Answer(chosen.action, n.left);
            final Answer old = answers.putIfAbsent(n.state.key(), answer);
            return (old == null || old.equals(answer)) && answers.size() <= 512 && extract(chosen, answers);
        }
        for (final Node child : n.children) if (!extract(child, answers)) return false;
        return true;
    }
    /** Independent verifier used by tests/replay: follows only stored own
     * responses and enumerates ALL rival accelerations, with a hard work bound. */
    static boolean verify(final RaceGame game, final StrategyState state, final int self,
            final Plan plan, final int remaining, final StrategyState.Budget budget) {
        if (!budget.take()) return false;
        final StrategyState s = state.timedOut(game) ? state.expire(game) : state;
        if (s.place(self) != 0) return s.place(self) == plan.place();
        if (s.slot() == self) {
            final Answer answer = plan.at(s);
            if (remaining <= 0 || answer == null || answer.left() > remaining || !s.ownDomain(answer.action())) return false;
            final StrategyState next = s.after(game, answer.action());
            return next != null && verify(game, next, self, plan, remaining - 1, budget);
        }
        for (final Direction action : ACTIONS) {
            final StrategyState next = s.after(game, action);
            if (next == null || !verify(game, next, self, plan, remaining, budget)) return false;
        }
        return true;
    }
}
