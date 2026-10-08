package tr.logic;

import java.util.Collections;
import java.util.Map;
import java.util.SortedMap;
import java.util.TreeMap;

/** Executable finite-horizon response certificates. Tables contain only answers
 * actually proved for every physical reply; incomplete branches never enter them.
 * The clock is part of every key, so carrying a table cannot restart its horizon. */
final class ResponseStrategies {
    private ResponseStrategies() {}
    static final int MAX_STATES = 128;
    record Node(int mask, int cycles, int escapes) {
        Node {
            if (mask < 1 || mask > 511 || cycles < 1 || cycles > 3 || escapes < 1 || escapes > 9)
                throw new IllegalArgumentException("invalid response node");
        }
        boolean permits(final Direction action) { return (mask & (1 << action.ordinal())) != 0; }
    }
    static final class Tree {
        private final SortedMap<String, Node> nodes;
        Tree(final Map<String, Node> input) {
            if (input.size() > MAX_STATES) throw new IllegalArgumentException("response table too large");
            for (final String key : input.keySet()) if (!key.matches("[0-9a-f]{64}"))
                throw new IllegalArgumentException("invalid response state key");
            nodes = Collections.unmodifiableSortedMap(new TreeMap<>(input));
        }
        Node at(final String key) { return nodes.get(key); }
        boolean empty() { return nodes.isEmpty(); }
        int size() { return nodes.size(); }
        String encode() {
            final StringBuilder out = new StringBuilder();
            for (final Map.Entry<String, Node> e : nodes.entrySet()) {
                if (out.length() > 0) out.append('!');
                out.append(e.getKey()).append('_').append(e.getValue().mask()).append('_')
                        .append(e.getValue().cycles()).append('_').append(e.getValue().escapes());
            }
            return out.toString();
        }
        static Tree parse(final String text) {
            if (text.isEmpty() || text.length() > MAX_STATES * 80)
                throw new IllegalArgumentException("invalid response table length");
            final Map<String, Node> nodes = new TreeMap<>();
            for (final String part : text.split("!", -1)) {
                final String[] f = part.split("_", -1);
                if (f.length != 4 || nodes.put(f[0], new Node(Integer.parseInt(f[1]),
                        Integer.parseInt(f[2]), Integer.parseInt(f[3]))) != null)
                    throw new IllegalArgumentException("duplicate or malformed response state");
            }
            final Tree tree = new Tree(nodes);
            if (!tree.encode().equals(text)) throw new IllegalArgumentException("noncanonical response table");
            return tree;
        }
    }
    /** Mutable construction only. Refused actions discard their partial tables. */
    private static boolean add(final Map<String, Node> target, final Map<String, Node> source) {
        for (final Map.Entry<String, Node> e : source.entrySet()) {
            final Node old = target.get(e.getKey()), value = e.getValue();
            if (old != null && (old.cycles() != value.cycles() || old.escapes() != value.escapes())) return false;
            target.put(e.getKey(), old == null ? value : new Node(old.mask() | value.mask(), old.cycles(), old.escapes()));
        }
        return target.size() <= MAX_STATES;
    }
    static Tree certify(final RaceGame game, final StrategyState root, final Direction first,
            final int cycles, final int escapes, final StrategyState.Budget budget) {
        if (root.live() != 2 || cycles < 1 || cycles > 3 || escapes < 1 || escapes > 9
                || root.timedOut(game) || !root.ownDomain(first) || !budget.take()) return null;
        final RaceGame.MoveResult move = root.evaluate(game, first);
        if (move == null || !move.legal()) return null;
        final StrategyState after = root.after(game, first);
        if (after == null) return null;
        if (after.place(root.slot()) != 0) return new Tree(Map.of());
        if (after.distance(game, root.slot()) == Integer.MAX_VALUE) return null;
        final Map<String, Node> proof = replies(game, after, root.slot(), cycles, escapes, budget);
        return proof == null ? null : new Tree(proof);
    }
    /** Check an unrecorded answer without extending the original certificate. */
    static Tree continuation(final RaceGame game, final StrategyState root, final Direction action,
            final Node obligation, final StrategyState.Budget budget) {
        if (!root.ownDomain(action) || root.timedOut(game) || !budget.take()) return null;
        final RaceGame.MoveResult move = root.evaluate(game, action);
        if (move == null || !move.legal()) return null;
        final StrategyState next = root.after(game, action);
        if (next == null) return null;
        if (next.place(root.slot()) != 0) return new Tree(Map.of());
        final int before = root.distance(game, root.slot()), after = next.distance(game, root.slot());
        if (before == Integer.MAX_VALUE || after == Integer.MAX_VALUE || after >= before) return null;
        if (obligation.cycles() == 1) return new Tree(Map.of());
        final Map<String, Node> proof = replies(game, next, root.slot(), obligation.cycles() - 1,
                obligation.escapes(), budget);
        return proof == null ? null : new Tree(proof);
    }
    private static Map<String, Node> replies(final RaceGame game, final StrategyState state, final int self,
            final int cycles, final int escapes, final StrategyState.Budget budget) {
        if (state.timedOut(game)) return null;
        if (state.place(self) != 0) return new TreeMap<>();
        final Map<String, Node> result = new TreeMap<>();
        for (final Direction reply : Direction.values()) {
            if (!budget.take()) return null;
            final RaceGame.MoveResult move = state.evaluate(game, reply);
            if (move == null) return null;
            if (move.finishes()) return null; // not a permission to hand the rival this duel
            final StrategyState next = state.after(game, reply);
            if (next == null) return null;
            if (next.place(self) != 0) continue; // rival retirement classifies the survivor
            final Map<String, Node> branch = answers(game, next, self, cycles, escapes, budget);
            if (branch == null || !add(result, branch)) return null;
        }
        return result;
    }
    private static Map<String, Node> answers(final RaceGame game, final StrategyState state, final int self,
            final int cycles, final int escapes, final StrategyState.Budget budget) {
        if (state.slot() != self || state.timedOut(game)) return null;
        final int before = state.distance(game, self);
        if (before == Integer.MAX_VALUE) return null;
        final Map<String, Node> result = new TreeMap<>();
        int mask = 0, count = 0;
        for (final Direction action : Direction.values()) {
            if (!state.ownDomain(action)) continue;
            if (!budget.take()) return null;
            final RaceGame.MoveResult move = state.evaluate(game, action);
            if (move == null || !move.legal()) continue;
            final StrategyState next = state.after(game, action);
            if (next == null) continue;
            if (move.finishes() || next.place(self) != 0) {
                result.clear(); result.put(state.key(), new Node(1 << action.ordinal(), cycles, escapes));
                return result;
            }
            final int after = next.distance(game, self);
            if (after == Integer.MAX_VALUE || after >= before) continue;
            final Map<String, Node> branch = cycles == 1 ? new TreeMap<>()
                    : replies(game, next, self, cycles - 1, escapes, budget);
            if (branch == null) continue;
            if (!add(result, branch)) return null;
            mask |= 1 << action.ordinal();
            if (++count >= escapes) {
                result.put(state.key(), new Node(mask, cycles, escapes));
                return result.size() <= MAX_STATES ? result : null;
            }
        }
        return null;
    }
}
