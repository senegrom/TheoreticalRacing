package tr.logic;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;
import java.util.Set;

/** A bounded time/velocity graph supplies proposals; reactive scorer forecasts
 * independently re-evaluate every proposal against a freshly forecast incumbent.
 * Scheduled occupancy is not a promise that opponents will keep their old moves. */
@SuppressWarnings("try")
final class TrafficManoeuvres {
    private TrafficManoeuvres() {}
    record Occupancy(int[] x, int[] y, boolean[] live, int self) {
        Occupancy { x = x.clone(); y = y.clone(); live = live.clone(); }
        boolean contains(final int nx, final int ny) {
            for (int i = 0; i < x.length; i++)
                if (i != self && live[i] && x[i] == nx && y[i] == ny) return true;
            return false;
        }
        static Occupancy capture(final RaceGame game, final int self) {
            final int n = game.players.length;
            final int[] x = new int[n], y = new int[n]; final boolean[] live = new boolean[n];
            for (int i = 0; i < n; i++) {
                x[i] = game.players[i].getPosition()[0]; y[i] = game.players[i].getPosition()[1];
                live[i] = !game.players[i].isFinished();
            }
            return new Occupancy(x, y, live, self);
        }
    }
    record Forecast(RacecraftOutcome outcome, List<Occupancy> schedule, String nextKey) {
        Forecast { schedule = List.copyOf(schedule); }
    }
    record State(int x, int y, int vx, int vy, int lap, int gate, boolean leftGrid, int depth, Direction first) {}
    private record Node(State state, List<Direction> actions, int estimate, boolean finishes, int serial) {}
    record Search(List<List<Direction>> proposals, int expanded) {
        Search { proposals = List.copyOf(proposals); }
    }
    record Choice(Direction action, FollowupPlans.Entry continuation, int expanded, int forecasts) {}

    /** Exact detached referee transitions, with all cars using the same suppressed
     * scorer continuation. A common number of OWN moves and the final reply cycle
     * is used for every comparison. Humans are not assigned fictitious policies. */
    static Forecast forecast(final RaceGame game, final RacecraftReplay.Board root,
            final List<Direction> prefix, final int horizon) {
        if (prefix.isEmpty() || prefix.size() > 4 || horizon < prefix.size())
            throw new IllegalArgumentException("invalid manoeuvre forecast");
        final int self = root.slot;
        final List<Occupancy> schedule = new ArrayList<>();
        try (RacecraftReplay.Scope ignored = new RacecraftReplay.Scope(game, root)) {
            for (final Player p : game.players) if (!p.isAi())
                return new Forecast(RacecraftOutcome.unknown(), schedule, null);
            final RaceAi policy = new RaceAi(game);
            int own = 0;
            String nextKey = null;
            RacecraftOutcome.Status status = RacecraftOutcome.Status.RUNNING;
            boolean complete = RacecraftReplay.classifyLast(game);
            final int maxEvents = (horizon + 1) * game.players.length;
            for (int event = 0; event < maxEvents && !complete; event++) {
                final int slot = game.subgamestate;
                if (game.raceTurnLimitReached()) {
                    RacecraftReplay.expire(game);
                    status = game.players[self].getFinishedPlace() == game.researchFinishedFirst() + 1
                            ? RacecraftOutcome.Status.CLASSIFIED : RacecraftOutcome.Status.TIMED_OUT;
                    complete = true; break;
                }
                if (slot == self) {
                    if (own == 1) nextKey = FollowupPlans.key(game);
                    if (own < 4) schedule.add(Occupancy.capture(game, self));
                    if (own == horizon) break;
                }
                final Direction action = slot == self && own < prefix.size()
                        ? prefix.get(own) : policy.researchScorer();
                if (action == null) return new Forecast(RacecraftOutcome.unknown(), schedule, nextKey);
                if (slot == self && own < prefix.size() && !RacecraftReplay.legalActions(game).contains(action))
                    return new Forecast(RacecraftOutcome.unknown(), schedule, nextKey);
                if (slot == self) own++;
                final String transition = RacecraftReplay.advance(game, action);
                if (slot == self && game.players[self].isFinished()) status = transition.contains(":FINISH:")
                        ? RacecraftOutcome.Status.FINISHED : RacecraftOutcome.Status.CRASHED;
                complete = RacecraftReplay.classifyLast(game);
                if (game.players[self].isFinished()) {
                    if (status == RacecraftOutcome.Status.RUNNING) status = RacecraftOutcome.Status.CLASSIFIED;
                    break;
                }
                if (!complete) {
                    int next = slot;
                    do { next = (next + 1) % game.players.length; } while (game.players[next].isFinished());
                    game.subgamestate = next;
                }
            }
            final Player me = game.players[self];
            final int place = me.getFinishedPlace();
            final int[] x = me.getPosition(), v = me.getVelocity();
            final OptimalPotential pot = game.optimalPotential();
            final int remaining = place != 0 ? 0 : game.lapGates == null
                    ? game.reach.turnsToFinish(x[0], x[1], v[0], v[1]) : pot == null ? Integer.MAX_VALUE
                    : pot.movesToFinish(OptimalPotential.remainingEvents(me.getNextGate(), me.getLap(),
                            game.totalLaps), x[0], x[1], v[0], v[1]);
            return new Forecast(new RacecraftOutcome(status, place == 0 ? game.researchFinishedFirst() : place - 1,
                    own, remaining), schedule, nextKey);
        }
    }

    static Search propose(final RaceGame game, final List<Occupancy> schedule,
            final Direction nominal, final int depth, final int budget) {
        if (game.racecraftNext.enabled(game, game.players[game.subgamestate].getNumber(), RacecraftNext.Feature.SUFFIX_MANOEUVRES))
            return SuffixManoeuvres.propose(game, schedule, nominal, depth, budget);
        if (budget <= 0 || schedule.size() < depth) return new Search(List.of(), 0);
        final Player me = game.players[game.subgamestate];
        final int[] x = me.getPosition(), v = me.getVelocity();
        final Comparator<Node> ordering = Comparator.comparingInt(Node::estimate)
                .thenComparingInt(node -> -node.state().depth()).thenComparingInt(Node::serial);
        final PriorityQueue<Node> queue = new PriorityQueue<>(ordering);
        final State initial = new State(x[0], x[1], v[0], v[1], me.getLap(), me.getNextGate(), me.hasLeftGrid(), 0, null);
        queue.add(new Node(initial, List.of(), 0, false, 0));
        final Set<State> seen = new HashSet<>();
        final Map<Direction, Node> best = new LinkedHashMap<>();
        int expanded = 0, serial = 0;
        while (!queue.isEmpty() && expanded < budget) {
            final Node node = queue.remove();
            final State s = node.state();
            if (!seen.add(s)) continue;
            if (s.depth() == depth || node.finishes()) {
                if (s.first() != nominal && !best.containsKey(s.first())) best.put(s.first(), node);
                continue;
            }
            expanded++;
            for (final Direction d : Direction.values()) {
                final int vx = s.vx() + d.dx, vy = s.vy() + d.dy;
                if (RaceGame.aiVelocityOutOfRange(vx, vy)) continue;
                final int nx = s.x() + vx, ny = s.y() + vy;
                final RaceGame.MoveResult move = game.evaluateMove(s.lap(), s.gate(), !s.leftGrid(),
                        s.x(), s.y(), nx, ny, schedule.get(s.depth()).contains(nx, ny));
                if (!move.legal()) continue;
                final int remaining = TrafficOpportunities.distance(game, move, nx, ny, vx, vy);
                if (remaining == Integer.MAX_VALUE) continue;
                final boolean left = s.leftGrid() || game.startZoneA != null && !game.startZoneA.contains(nx, ny);
                final State next = new State(nx, ny, vx, vy, move.lapAfter(), move.gateAfter(), left,
                        s.depth() + 1, s.first() == null ? d : s.first());
                final List<Direction> actions = new ArrayList<>(node.actions()); actions.add(d);
                queue.add(new Node(next, List.copyOf(actions), next.depth() + remaining, move.finishes(), ++serial));
            }
        }
        // Complete discovered leaves are proposals even if optimality was not established.
        for (final Node node : queue) if ((node.finishes() || node.state().depth() == depth)
                && node.state().first() != nominal) {
            final Node old = best.get(node.state().first());
            if (old == null || ordering.compare(node, old) < 0) best.put(node.state().first(), node);
        }
        final List<Node> leaves = new ArrayList<>(best.values()); leaves.sort(ordering);
        final List<List<Direction>> result = new ArrayList<>();
        for (int i = 0; i < Math.min(2, leaves.size()); i++) result.add(leaves.get(i).actions());
        return new Search(result, expanded);
    }

    static Choice choose(final RaceGame game, final Direction nominal, final FollowupPlans.Entry inherited,
            final int depth, final int budget) {
        if (budget <= 0) return new Choice(nominal, null, 0, 0);
        for (final Player p : game.players) if (!p.isAi()) return new Choice(nominal, null, 0, 0);
        if (game.lapGates != null && game.optimalPotential() == null) return new Choice(nominal, null, 0, 0);
        final RacecraftReplay.Board root = RacecraftReplay.capture(game);
        final Forecast baseline = forecast(game, root, List.of(nominal), 12);
        if (!baseline.outcome().known()) return new Choice(nominal, null, 0, 1);
        final Search search = propose(game, baseline.schedule(), nominal, depth, budget);
        final List<List<Direction>> proposals = new ArrayList<>(search.proposals());
        if (inherited != null && inherited.traffic() && !proposals.contains(inherited.actions()))
            proposals.add(0, inherited.actions());
        List<Direction> best = List.of(nominal);
        Forecast value = baseline;
        int forecasts = 1;
        for (final List<Direction> proposal : proposals) {
            final Forecast alternative = forecast(game, root, proposal, 12); forecasts++;
            if (alternative.outcome().betterThan(value.outcome(), false)) { value = alternative; best = proposal; }
        }
        final FollowupPlans.Entry tail = best.size() < 2 || value.nextKey() == null ? null
                : FollowupPlans.Entry.traffic(best.subList(1, best.size()), value.nextKey());
        return new Choice(best.get(0), tail, search.expanded(), forecasts);
    }
}
