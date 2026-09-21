package tr.logic;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Research around the promoted round-260 chooser. Forecasts remain predictions,
 * not proofs. All actual alternatives re-enter the ordinary downstream guards.
 * Only legacy-unchecked deliberately bypasses them, as an isolated diagnostic. */
final class ChooserResearch {
    private static final Direction[] DIRECTIONS = Direction.values();
    private ChooserResearch() {}

    static final class Limit extends RuntimeException {
        private static final long serialVersionUID = 1L;
        Limit() { super("Chooser research work budget exhausted", null, false, false); }
    }
    static final class Budget {
        final int policyLimit, moveLimit;
        int policies, moves, reusedPolicies, reusedMoves;
        private final List<Boolean> events = new ArrayList<>();
        Budget(final int policyLimit, final int moveLimit) { this.policyLimit = policyLimit; this.moveLimit = moveLimit; }
        void policy() { spend(true, false); }
        void move() { spend(false, false); }
        int mark() { return events.size(); }
        List<Boolean> since(final int mark) { return List.copyOf(events.subList(mark, events.size())); }
        void replay(final List<Boolean> charges) { for (final boolean policy : charges) spend(policy, true); }
        private void spend(final boolean policy, final boolean reused) {
            if (policy) {
                if (policies >= policyLimit) throw new Limit();
                policies++; if (reused) reusedPolicies++;
            } else {
                if (moves >= moveLimit) throw new Limit();
                moves++; if (reused) reusedMoves++;
            }
            events.add(policy);
        }
    }

    /** Detached progress AND classification ledger. No snapshot points into live players. */
    static final class Board {
        final int[] x, y, vx, vy, lap, gate, place, ownMoves;
        final boolean[] alive;
        final String[] fate;
        int first, last;
        long turns;
        final boolean classificationKnown;
        Board(final RaceGame g) {
            final int n = g.players.length;
            x = new int[n]; y = new int[n]; vx = new int[n]; vy = new int[n];
            lap = new int[n]; gate = new int[n]; place = new int[n]; ownMoves = new int[n];
            alive = new boolean[n]; fate = new String[n]; Arrays.fill(fate, "RUNNING");
            first = g.chooserFinishedFirst(); last = g.chooserFinishedLast(); turns = g.turnCount();
            final boolean[] seen = new boolean[n + 1]; boolean known = first >= 0 && last >= 0 && first + last <= n;
            for (int i = 0; i < n; i++) {
                final Player p = g.players[i];
                x[i] = p.getPosition()[0]; y[i] = p.getPosition()[1]; vx[i] = p.getVelocity()[0]; vy[i] = p.getVelocity()[1];
                lap[i] = p.getLap(); gate[i] = g.lapGates == null ? 0 : p.getNextGate();
                place[i] = p.getFinishedPlace(); alive[i] = !p.isFinished();
                if (!alive[i]) {
                    if (place[i] < 1 || place[i] > n || seen[place[i]] || !(place[i] <= first || place[i] > n - last)) known = false;
                    else seen[place[i]] = true;
                    fate[i] = "PREVIOUS";
                }
            }
            classificationKnown = known && first + last == n - live();
        }
        Board(final Board b) {
            x = b.x.clone(); y = b.y.clone(); vx = b.vx.clone(); vy = b.vy.clone(); lap = b.lap.clone(); gate = b.gate.clone();
            place = b.place.clone(); ownMoves = b.ownMoves.clone(); alive = b.alive.clone(); fate = b.fate.clone();
            first = b.first; last = b.last; turns = b.turns; classificationKnown = b.classificationKnown;
        }
        int live() { int n = 0; for (final boolean a : alive) if (a) n++; return n; }
        boolean over() { return live() <= (alive.length == 1 ? 0 : 1); }
        boolean timedOut(final RaceGame g) { return g.lapGates != null && turns > (long) g.totalLaps * 750 * alive.length; }
        boolean occupied(final int i, final int nx, final int ny) {
            for (int j = 0; j < alive.length; j++) if (j != i && alive[j] && x[j] == nx && y[j] == ny) return true;
            return false;
        }
        RaceGame.MoveResult transition(final RaceGame g, final int i, final Direction d) {
            final int nx = Math.addExact(x[i], Math.addExact(vx[i], d.dx));
            final int ny = Math.addExact(y[i], Math.addExact(vy[i], d.dy));
            return g.evaluateMove(lap[i], gate[i], x[i], y[i], nx, ny, occupied(i, nx, ny));
        }
        String step(final RaceGame g, final int i, final Direction d) {
            if (!alive[i] || over()) throw new IllegalArgumentException("No move after classification");
            String status;
            if (timedOut(g)) { status = "TIMEOUT"; retire(i, alive.length - last++, status); }
            else {
                final RaceGame.MoveResult r = transition(g, i, d);
                if (r.finishes()) { status = "FINISH"; retire(i, ++first, status); }
                else if (!r.legal()) { status = "CRASH"; retire(i, alive.length - last++, status); }
                else {
                    status = r.lapCross() ? "LAP" : "OK";
                    vx[i] += d.dx; vy[i] += d.dy; x[i] += vx[i]; y[i] += vy[i];
                    lap[i] = r.lapAfter(); gate[i] = g.lapGates == null ? 0 : r.gateAfter();
                }
            }
            turns++; ownMoves[i]++;
            if (over()) for (int j = 0; j < alive.length; j++) if (alive[j]) retire(j, first + 1, "SURVIVOR");
            return status;
        }
        private void retire(final int i, final int rank, final String status) {
            alive[i] = false; place[i] = rank; fate[i] = status;
            x[i] = -100000; y[i] = -100000; vx[i] = 0; vy[i] = 0;
        }
        List<Object> cars() {
            final List<Object> out = new ArrayList<>();
            for (int i = 0; i < x.length; i++) out.add(List.of(x[i], y[i], vx[i], vy[i], place[i], lap[i], gate[i]));
            return out;
        }
    }

    record Outcome(int verdict, boolean resolved, int place, int ownMoves, String status) {
        Map<String, Object> data() {
            return Map.of("verdict", verdict, "resolved", resolved, "place", place,
                    "ownMoves", ownMoves, "status", status);
        }
    }

    /** One forecast's parallel referee ledger. The production simulator supplies
     * every action; this ledger does not choose an action or replace its verdict. */
    static final class Run {
        final Board root, state;
        final int focal, depth;
        final Direction action, forcedSecond;
        final boolean aware, student, trace;
        final boolean[] upgraded;
        final int relevant;
        final List<Object> steps = new ArrayList<>();
        final List<Direction> secondOptions = new ArrayList<>();
        Board secondBoard;
        Direction actualSecond;
        int upgrades, eventStart, rounds, replyIndex = -1;
        boolean compareReply, replyDone;
        Direction forcedReply, normalReply, alternateReply;
        RaceAi.ChooserPrefix secondPrefix, resume;
        Outcome outcome;
        Run(final RaceGame g, final int focal, final Direction action, final int depth,
                final boolean aware, final boolean student, final Direction forcedSecond, final boolean trace) {
            root = new Board(g); state = new Board(root); this.focal = focal; this.action = action; this.depth = depth;
            this.aware = aware; this.student = student; this.forcedSecond = forcedSecond; this.trace = trace;
            upgraded = new boolean[root.x.length];
            record(g, focal, action, "candidate");
            relevant = relevant(g, state, focal);
        }
        /** Copy only immutable observations and deep state, never live players or
         * another branch's mutable working arrays. Prefix handles are not copied. */
        Run(final Run r, final int depth, final Direction second) {
            root = new Board(r.root); state = new Board(r.state);
            focal = r.focal; action = r.action; this.depth = depth;
            aware = r.aware; student = r.student; trace = r.trace; forcedSecond = second;
            upgraded = r.upgraded.clone(); relevant = r.relevant; upgrades = r.upgrades;
            steps.addAll(r.steps); rounds = r.rounds; replyIndex = r.replyIndex;
            compareReply = r.compareReply; replyDone = r.replyDone;
            forcedReply = r.forcedReply; normalReply = r.normalReply; alternateReply = r.alternateReply;
        }
        boolean firstReply(final int i) { return i == replyIndex && !replyDone; }
        boolean higher(final int i) {
            if (!(aware || student) || upgraded[i] || i != focal && i != relevant) return false;
            upgraded[i] = true; upgrades++; return true;
        }
        boolean second(final int i) { return i == focal && actualSecond == null && state.alive[i]; }
        void secondOptions(final RaceGame g, final Direction selected, final int width) {
            if (actualSecond != null) return;
            secondBoard = new Board(state); actualSecond = selected;
            // Always include the actual continuation. Additional legal continuations
            // are ordered by complete route potential where available, then ordinal.
            secondOptions.add(selected);
            final List<Direction> legal = new ArrayList<>();
            if (!state.timedOut(g)) for (final Direction d : DIRECTIONS) {
                if (d != selected && !RaceGame.aiVelocityOutOfRange(state.vx[focal] + d.dx, state.vy[focal] + d.dy)
                        && state.transition(g, focal, d).legal()) legal.add(d);
            }
            legal.sort((a, b) -> {
                final int c = Integer.compare(secondCost(g, state, focal, a), secondCost(g, state, focal, b));
                return c != 0 ? c : Integer.compare(a.ordinal(), b.ordinal());
            });
            for (int j = 0; j < legal.size() && secondOptions.size() < width; j++) secondOptions.add(legal.get(j));
        }
        void record(final RaceGame g, final int i, final Direction d, final String model) {
            final long turn = state.turns;
            final List<Integer> before = List.of(state.x[i], state.y[i], state.vx[i], state.vy[i], state.lap[i], state.gate[i]);
            final RaceGame.MoveResult result = state.timedOut(g) ? null : state.transition(g, i, d);
            final int cp = result == null ? 0 : (result.passCp1() ? 1 : 0) | (result.passCp2() ? 2 : 0);
            final String status = state.step(g, i, d);
            if (trace) steps.add(Map.of("turn", turn, "mover", i, "action", d.name(), "before", before,
                    "status", status, "model", model, "checkpoints", cp));
        }
        Outcome finish(final int verdict) {
            outcome = new Outcome(verdict, state.classificationKnown && state.place[focal] > 0,
                    state.classificationKnown ? state.place[focal] : -1, state.ownMoves[focal], state.fate[focal]);
            return outcome;
        }
        Map<String, Object> data() {
            final Map<String, Object> m = new LinkedHashMap<>();
            m.put("action", action.name()); m.put("forcedSecond", name(forcedSecond)); m.put("actualSecond", name(actualSecond));
            m.put("secondOptions", secondOptions.stream().map(Direction::name).toList());
            m.put("outcome", outcome == null ? null : outcome.data()); m.put("upgrades", upgrades);
            m.put("replyIndex", replyIndex); m.put("normalReply", name(normalReply));
            m.put("alternateReply", name(alternateReply)); m.put("forcedReply", name(forcedReply));
            m.put("relevant", relevant); m.put("steps", steps); return m;
        }
    }

    static int secondCost(final RaceGame g, final Board b, final int focal, final Direction d) {
        final Board after = new Board(b); after.step(g, focal, d);
        return after.alive[focal] ? ChooserFeatures.remaining(g, after, focal) : 0;
    }
    static int relevant(final RaceGame g, final Board b, final int focal) {
        if (!b.alive[focal] || b.over()) return -1;
        final ChooserTraffic.Graph graph = ChooserTraffic.graph(g, b, (focal + 1) % b.alive.length);
        int best = -1;
        for (int i = 0; i < b.alive.length; i++) if (i != focal && b.alive[i] && graph.edge[focal][i] > 0
                && (best < 0 || graph.edge[focal][i] > graph.edge[focal][best]
                    || graph.edge[focal][i] == graph.edge[focal][best] && graph.distance(focal, i) < graph.distance(focal, best))) best = i;
        return best;
    }

    static final class Context {
        final Board root;
        final int focal, laps;
        final ChooserConfig config;
        final boolean active, trace;
        final List<Object> stages = new ArrayList<>();
        final List<Run> teacher = new ArrayList<>(), experiments = new ArrayList<>();
        final Map<String, Object> features = new LinkedHashMap<>();
        Direction scoreChoice, baseline, proposal, finalChoice, unchecked;
        Run selectedPlan;
        final Map<String, Object> geometry;
        double[] scores;
        String path = "before-chooser";
        boolean chooserReached, exhausted;
        int policies, moves, reusedPolicies, reusedMoves;
        Map<String, Object> contingentReport = Map.of();
        Context(final RaceGame g, final boolean active, final boolean trace) {
            root = new Board(g); focal = g.subgamestate; laps = g.totalLaps; config = g.chooserConfig;
            this.active = active && root.classificationKnown; this.trace = trace;
            final List<Object> gates = new ArrayList<>();
            if (g.lapGates != null) for (final java.awt.geom.Line2D line : g.lapGates)
                gates.add(List.of(line.getX1(), line.getY1(), line.getX2(), line.getY2()));
            final String key = g.reach.geometryCacheKey();
            geometry = new LinkedHashMap<>();
            geometry.put("grid", List.of(g.gameCols, g.gameRows)); geometry.put("crossing", g.crossingIdentity());
            geometry.put("gates", gates); geometry.put("cacheKey", key == null ? "" : java.nio.file.Path.of(key).getFileName().toString());
        }
        void stage(final String at, final Direction d) { stages.add(Map.of("stage", at, "action", name(d))); }
        String json() {
            final Map<String, Object> data = new LinkedHashMap<>();
            data.put("schema", 1); data.put("laps", laps); data.put("turn", root.turns); data.put("mover", focal);
            data.put("geometry", geometry); data.put("selectedPlan", selectedPlan == null ? null : selectedPlan.data());
            data.put("first", root.first); data.put("last", root.last); data.put("cars", root.cars());
            data.put("classificationKnown", root.classificationKnown); data.put("active", active);
            data.put("flags", config.specification); data.put("path", path); data.put("chooserReached", chooserReached);
            data.put("scoreChoice", name(scoreChoice)); data.put("baseline", name(baseline)); data.put("proposal", name(proposal));
            data.put("uncheckedProposal", name(unchecked)); data.put("final", name(finalChoice)); data.put("finalCompared", teacher.stream().anyMatch(r -> r.action == finalChoice)
                    || experiments.stream().anyMatch(r -> r.action == finalChoice));
            data.put("stages", stages); data.put("teacher", teacher.stream().map(Run::data).toList());
            data.put("experiments", experiments.stream().map(Run::data).toList());
            data.put("features", features); data.put("featureSchema", ChooserConfig.FEATURES);
            data.put("reusedPolicies", reusedPolicies); data.put("reusedMoves", reusedMoves);
            data.put("physicalPolicies", policies - reusedPolicies); data.put("physicalMoves", moves - reusedMoves);
            data.put("contingent", contingentReport);
            data.put("policies", policies); data.put("moves", moves); data.put("exhausted", exhausted);
            return encode(data);
        }
    }

    /** Exact resolved outcomes get their own comparison. Nonterminal estimates
     * never masquerade as classifications, and no time can buy a worse place. */
    static boolean better(final Outcome a, final Outcome b, final boolean terminal) {
        if (terminal && a.resolved && b.resolved) return a.place < b.place || a.place == b.place && a.ownMoves < b.ownMoves;
        return a.verdict >= 0 && (b.verdict < 0 || a.verdict < b.verdict);
    }

    static Direction choose(final RaceGame g, final RaceAi ai, final Context context, final List<Direction> initial) {
        final ChooserConfig c = context.config;
        final Direction champion = context.baseline;
        if (!context.active || c.policyBudget == 0 || c.moveBudget == 0) return champion;
        if (c.contingent) return contingent(g, ai, context, initial);
        if (c.legacyGuarded || c.legacyUnchecked) {
            final Direction proposed = modelPick(g, context.root, context.focal, initial, champion, c.legacy, false);
            if (c.legacyUnchecked) { context.unchecked = proposed; return champion; }
            return proposed;
        }
        // An assistant may suggest ONE additional candidate, but the actual
        // forecasts must still compare it before it can change the real move.
        final List<Direction> actions = new ArrayList<>(initial);
        if (c.assist) {
            final List<Direction> extras = new ArrayList<>();
            for (final Direction d : DIRECTIONS) if (!actions.contains(d) && context.scores[d.ordinal()] != Double.MAX_VALUE
                    && context.root.transition(g, context.focal, d).legal()) extras.add(d);
            Direction extra = null; double value = Double.POSITIVE_INFINITY;
            for (final Direction d : extras) {
                final double[] f = ChooserFeatures.relative(g, context.root, context.focal, d);
                final double score = c.model.score(f);
                if (score < value) { extra = d; value = score; }
            }
            if (extra != null) actions.add(extra);
        }
        final Budget budget = new Budget(c.policyBudget, c.moveBudget);
        final List<Run> results = new ArrayList<>();
        try {
            for (final Direction d : actions) {
                final Run base = ai.chooserForecast(d, c.rounds, c.aware, c.student, null, context.trace, budget);
                results.add(base); context.experiments.add(base);
                if (c.setup && base.secondBoard != null) for (final Direction second : base.secondOptions) {
                    if (second == base.actualSecond) continue;
                    final Run setup = ai.chooserForecast(d, c.rounds, c.aware, c.student, second, context.trace, budget,
                            -1, null, false, c.prefix ? base.secondPrefix : null);
                    results.add(setup); context.experiments.add(setup);
                }
            }
        } catch (final Limit limit) {
            context.exhausted = true;
            return champion; // No partial comparison, and no budget-derived death.
        } finally { recordBudget(context, budget); }
        // Keep the old score order on ties. Terminal comparisons are restricted to
        // a resolved legacy/estimate winner, avoiding a non-transitive mixture.
        Run best = null;
        for (final Run r : results) if (best == null || better(r.outcome, best.outcome, false)) best = r;
        if (c.terminal && best != null && best.outcome.resolved) {
            for (final Run r : results) if (r.outcome.resolved && better(r.outcome, best.outcome, true)) best = r;
        }
        context.selectedPlan = best;
        return best == null ? champion : best.action;
    }

    private static void recordBudget(final Context c, final Budget b) {
        c.policies = b.policies; c.moves = b.moves;
        c.reusedPolicies = b.reusedPolicies; c.reusedMoves = b.reusedMoves;
    }

    /** Partial comparison: resolved classifications are comparable to each other;
     * finite unresolved forecasts are comparable at the same horizon. A mixed
     * resolved/estimated pair is UNKNOWN, not an equality or a safety proof. */
    static Integer compareScenario(final Outcome a, final Outcome b) {
        if (a.resolved && b.resolved) {
            final int rank = Integer.compare(a.place, b.place);
            return rank != 0 ? rank : Integer.compare(a.ownMoves, b.ownMoves);
        }
        if (a.resolved != b.resolved || a.verdict < 0 || b.verdict < 0
                || a.verdict == Integer.MAX_VALUE || b.verdict == Integer.MAX_VALUE) return null;
        return Integer.compare(a.verdict, b.verdict);
    }
    static boolean dominates(final List<Outcome> a, final List<Outcome> b) {
        if (a.size() != b.size() || a.isEmpty()) return false;
        boolean strict = false;
        for (int i = 0; i < a.size(); i++) {
            final Integer cmp = compareScenario(a.get(i), b.get(i));
            if (cmp == null || cmp > 0) return false;
            strict |= cmp < 0;
        }
        return strict;
    }

    private static Run scenario(final RaceGame g, final RaceAi ai, final Context c, final Budget budget,
            final Direction first, final int rival, final Direction reply, final boolean inspect) {
        final Run base = ai.chooserForecast(first, c.config.rounds, false, false, null, c.trace,
                budget, rival, reply, inspect, null);
        c.experiments.add(base);
        final List<Run> plans = new ArrayList<>(); plans.add(base);
        // Each world gets its OWN legal second-action choices, after its reply.
        if (base.secondBoard != null) for (final Direction second : base.secondOptions) {
            if (second == base.actualSecond) continue;
            final Run run = ai.chooserForecast(first, c.config.rounds, false, false, second, c.trace,
                    budget, rival, reply, inspect, c.config.prefix ? base.secondPrefix : null);
            plans.add(run); c.experiments.add(run);
        }
        Run best = base;
        for (final Run r : plans) if (better(r.outcome, best.outcome, false)) best = r;
        if (c.config.terminal && best.outcome.resolved)
            for (final Run r : plans) if (r.outcome.resolved && better(r.outcome, best.outcome, true)) best = r;
        return best;
    }

    /** Two declared models of ONE rival's first response: the normal forecast and
     * its own stronger chooser. No coalition, invented response probabilities, or
     * worst-legal-reply oracle. A switch must improve at least one model and not
     * worsen the other, compared against the same baseline first action. */
    private static Direction contingent(final RaceGame g, final RaceAi ai, final Context c,
            final List<Direction> actions) {
        final ChooserTraffic.Graph graph = ChooserTraffic.graph(g, c.root, c.focal);
        int rival = -1;
        for (int i = 0; i < c.root.alive.length; i++) if (i != c.focal && c.root.alive[i]
                && graph.edge[c.focal][i] > 0 && (rival < 0 || graph.edge[c.focal][i] > graph.edge[c.focal][rival])) rival = i;
        if (rival < 0) {
            c.contingentReport = Map.of("reason", "no-direct-rival"); return c.baseline;
        }
        final Budget budget = new Budget(c.config.policyBudget, c.config.moveBudget);
        final Map<Direction, List<Run>> worlds = new LinkedHashMap<>();
        final List<Object> audit = new ArrayList<>();
        boolean disagreement = false, unavailable = false;
        try {
            for (final Direction d : actions) {
                final Run normal = scenario(g, ai, c, budget, d, rival, null, true);
                final boolean different = normal.replyDone && normal.alternateReply != null
                        && normal.normalReply != normal.alternateReply;
                disagreement |= different;
                unavailable |= normal.replyDone ? normal.alternateReply == null : !normal.outcome.resolved;
                final Run alternate = different
                        ? scenario(g, ai, c, budget, d, rival, normal.alternateReply, false) : normal;
                worlds.put(d, List.of(normal, alternate));
                audit.add(Map.of("first", d.name(), "normal", normal.data(), "chooser", alternate.data(),
                        "differentReply", different));
            }
        } catch (final Limit exhausted) {
            c.exhausted = true;
            c.contingentReport = Map.of("reason", "budget", "rival", rival, "plans", audit);
            return c.baseline;
        } finally { recordBudget(c, budget); }
        Direction pick = c.baseline;
        final List<Run> baseline = worlds.get(pick);
        if (disagreement && !unavailable && baseline != null) for (final Direction d : actions) {
            final List<Outcome> candidate = worlds.get(d).stream().map(r -> r.outcome).toList();
            if (dominates(candidate, baseline.stream().map(r -> r.outcome).toList())
                    && (pick == c.baseline || dominates(candidate, worlds.get(pick).stream().map(r -> r.outcome).toList()))) pick = d;
        }
        c.contingentReport = Map.of("reason", unavailable ? "unavailable-response" : !disagreement ? "models-agree" : pick == c.baseline ? "no-dominating-plan" : "dominates",
                "rival", rival, "responseModels", List.of("forecast-policy", "bounded-chooser"), "plans", audit);
        if (worlds.containsKey(pick)) c.selectedPlan = worlds.get(pick).get(0);
        return pick;
    }

    static Direction modelPick(final RaceGame g, final Board b, final int focal, final List<Direction> actions,
            final Direction baseline, final ChooserConfig.Model model, final boolean relative) {
        final double[] initial = relative ? ChooserFeatures.relative(g, b, focal, baseline) : ChooserFeatures.features(g, b, focal, baseline);
        if (initial == null) return baseline;
        final double original = model.score(initial); double best = original; Direction pick = baseline;
        for (final Direction d : actions) {
            final double[] f = relative ? ChooserFeatures.relative(g, b, focal, d) : ChooserFeatures.features(g, b, focal, d);
            if (f == null) continue;
            final double score = model.score(f);
            if (score < best) { best = score; pick = d; }
        }
        return original - best > model.margin ? pick : baseline;
    }

    static String name(final Direction d) { return d == null ? "" : d.name(); }
    /** Small strict JSON writer: no dependencies in the browser JAR. */
    static String encode(final Object value) {
        if (value == null) return "null";
        if (value instanceof Boolean || value instanceof Integer || value instanceof Long) return value.toString();
        if (value instanceof Number n) {
            if (!Double.isFinite(n.doubleValue())) throw new IllegalArgumentException("Non-finite audit number");
            return n.toString();
        }
        if (value instanceof String s) {
            final StringBuilder out = new StringBuilder("\"");
            for (int i = 0; i < s.length(); i++) {
                final char ch = s.charAt(i);
                if (ch == '"' || ch == '\\') out.append('\\').append(ch);
                else if (ch < 32) out.append(String.format(java.util.Locale.ROOT, "\\u%04x", (int) ch));
                else out.append(ch);
            }
            return out.append('"').toString();
        }
        if (value instanceof Map<?, ?> map) {
            final List<String> parts = new ArrayList<>();
            for (final Map.Entry<?, ?> e : map.entrySet()) parts.add(encode(e.getKey().toString()) + ":" + encode(e.getValue()));
            return "{" + String.join(",", parts) + "}";
        }
        if (value instanceof Iterable<?> list) {
            final List<String> parts = new ArrayList<>(); for (final Object v : list) parts.add(encode(v));
            return "[" + String.join(",", parts) + "]";
        }
        if (value instanceof double[] row) { final List<Double> list = new ArrayList<>(); for (final double v : row) list.add(v); return encode(list); }
        throw new IllegalArgumentException("Unsupported audit value: " + value.getClass());
    }
}
