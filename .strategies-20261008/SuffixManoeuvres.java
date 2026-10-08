package tr.logic;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.List;
import java.util.PriorityQueue;

/** Proposal-only search preserving nominal-first suffixes and multiple histories.
 * Different paths to the same own endpoint are NOT declared equivalent: rivals
 * can respond to intermediate positions. Every path is reforecast reactively. */
final class SuffixManoeuvres {
    private SuffixManoeuvres() {}
    private record Node(TrafficManoeuvres.State state, List<Direction> path, int value, boolean finish, int serial) {}
    static TrafficManoeuvres.Search propose(final RaceGame game,
            final List<TrafficManoeuvres.Occupancy> schedule, final Direction nominal,
            final int depth, final int budget) {
        if (budget <= 0 || depth < 2 || depth > 4 || schedule.size() < depth)
            return new TrafficManoeuvres.Search(List.of(), 0);
        final Player me = game.players[game.subgamestate];
        final int[] p = me.getPosition(), v = me.getVelocity();
        final TrafficManoeuvres.State start = new TrafficManoeuvres.State(p[0], p[1], v[0], v[1],
                me.getLap(), me.getNextGate(), me.hasLeftGrid(), 0, null);
        final Comparator<Node> order = Comparator.comparingInt(Node::value)
                .thenComparingInt(n -> -n.state().depth()).thenComparingInt(Node::serial);
        final EnumMap<Direction, PriorityQueue<Node>> queues = new EnumMap<>(Direction.class);
        final List<Node> leaves = new ArrayList<>();
        int serial = 0, expanded = 1;
        for (final Direction first : Direction.values()) {
            final PriorityQueue<Node> queue = new PriorityQueue<>(order);
            final Node node = child(game, start, List.of(), first, schedule, ++serial);
            if (node != null) { queue.add(node); queues.put(first, queue); }
        }
        final List<Direction> rootOrder = new ArrayList<>();
        rootOrder.add(nominal);
        for (final Direction d : Direction.values()) if (d != nominal) rootOrder.add(d);
        boolean work = true;
        // No root receives all expansions just because enum order happened to favor it.
        while (work && expanded < budget) {
            work = false;
            for (final Direction first : rootOrder) {
                final PriorityQueue<Node> queue = queues.get(first);
                if (queue == null || queue.isEmpty() || expanded >= budget) continue;
                work = true;
                Node node = queue.remove();
                while (node.finish() || node.state().depth() == depth) {
                    leaves.add(node);
                    if (queue.isEmpty()) { node = null; break; }
                    node = queue.remove();
                }
                if (node == null) continue;
                expanded++;
                for (final Direction d : Direction.values()) {
                    final Node next = child(game, node.state(), node.path(), d, schedule, ++serial);
                    if (next != null) queue.add(next);
                }
            }
        }
        for (final PriorityQueue<Node> queue : queues.values()) for (final Node n : queue)
            if (n.finish() || n.state().depth() == depth) leaves.add(n);
        leaves.sort(order);
        final List<List<Direction>> result = new ArrayList<>();
        // Reserve two proposals for alternative suffixes of the nominal first move.
        for (final Node n : leaves) if (n.state().first() == nominal && result.size() < 2
                && !result.contains(n.path())) result.add(n.path());
        for (final Node n : leaves) if (n.state().first() != nominal && result.size() < 3
                && !result.contains(n.path())) { result.add(n.path()); break; }
        for (final Node n : leaves) if (result.size() < 3 && !result.contains(n.path())) result.add(n.path());
        return new TrafficManoeuvres.Search(result, expanded);
    }
    private static Node child(final RaceGame game, final TrafficManoeuvres.State s,
            final List<Direction> path, final Direction action,
            final List<TrafficManoeuvres.Occupancy> schedule, final int serial) {
        final int vx = s.vx() + action.dx, vy = s.vy() + action.dy;
        if (RaceGame.aiVelocityOutOfRange(vx, vy)) return null;
        final int x = s.x() + vx, y = s.y() + vy;
        final RaceGame.MoveResult move = game.evaluateMove(s.lap(), s.gate(), !s.leftGrid(),
                s.x(), s.y(), x, y, schedule.get(s.depth()).contains(x, y));
        if (!move.legal()) return null;
        final int remaining = TrafficOpportunities.distance(game, move, x, y, vx, vy);
        if (remaining == Integer.MAX_VALUE) return null;
        final List<Direction> actions = new ArrayList<>(path); actions.add(action);
        final TrafficManoeuvres.State next = new TrafficManoeuvres.State(x, y, vx, vy, move.lapAfter(),
                move.gateAfter(), s.leftGrid() || game.startZoneA != null && !game.startZoneA.contains(x, y),
                s.depth() + 1, s.first() == null ? action : s.first());
        return new Node(next, List.copyOf(actions), next.depth() + remaining, move.finishes(), serial);
    }
}
