package tr.logic;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.TreeMap;

/** Independently opt-in research, never a promotion. Every arm acts only at a
 * candidate's own top-level chooser. Nested champion models remain unchanged.
 * Real committed moves alone install plans and write training captures. */
@SuppressWarnings("try")
final class DecisionResearch {
    static final int FEATURES = 18;
    private static final Set<String> FLAGS = Set.of("response-cycle", "duel-ties", "paired-value",
            "paired-shadow", "contingent");
    final Set<String> flags;
    final int trials, captureLimit;
    final String policyId, replayId;
    final Path capturePath;
    final PairedValueModel model;
    Plans plans = Plans.empty();
    int suppressed, detached, captures;
    boolean allowResponse;
    final boolean audit;
    long tieComparisons, tieChanges, modelComparisons, modelChanges, planTrials, planChanges;

    DecisionResearch(final Properties props) {
        final Set<String> enabled = new LinkedHashSet<>();
        for (final String s : props.getProperty("racecraftFeatures", "").split(",")) {
            if (s.isBlank()) continue;
            if (!FLAGS.contains(s.trim())) throw new IllegalArgumentException("unknown racecraft feature: " + s);
            enabled.add(s.trim());
        }
        flags = Set.copyOf(enabled);
        trials = bounded(props, "racecraftTrials", 24, 0, 128);
        captureLimit = bounded(props, "racecraftCaptureLimit", 64, 0, 100000);
        final String output = props.getProperty("racecraftCapture", "").trim();
        capturePath = output.isEmpty() ? null : Path.of(output);
        audit = Boolean.parseBoolean(props.getProperty("racecraftAudit", "false"));
        // Bind all non-presentation policy settings. Candidate seats are bound
        // separately in each snapshot; output paths must not change decisions.
        final TreeMap<String, String> policy = new TreeMap<>();
        for (final String key : props.stringPropertyNames())
            if (!key.equals("candidateSlots") && !key.startsWith("racecraftModel")
                    && !key.startsWith("racecraftCapture") && !key.equals("racecraftAudit")
                    && !key.matches("player[0-9]+(Name|Color)") && !key.startsWith("window")
                    && !Set.of("lastTrackLeft", "lastTrackRight", "lastTrackDrawn", "useLastTrack",
                            "gameX", "gameY", "lapClosable").contains(key)) {
                final String value = props.getProperty(key);
                policy.put(key, key.matches("player[0-9]+Kind") && (value.equals("AI1") || value.equals("AI2")) ? "AI" : value);
            }
        final Set<String> contextFlags = new java.util.TreeSet<>(flags);
        contextFlags.remove("paired-value"); contextFlags.remove("paired-shadow");
        policy.put("racecraftFeatures", String.join(",", contextFlags));
        policy.put("racecraftTrials", Integer.toString(trials));
        policyId = ResearchBoard.sha256(policy.toString());
        final String modelPath = props.getProperty("racecraftModel", "").trim();
        final Properties inline = new Properties();
        for (final String key : props.stringPropertyNames())
            if (key.startsWith("racecraftModel.")) inline.setProperty(key.substring(15), props.getProperty(key));
        model = !(has("paired-value") || has("paired-shadow")) ? null
                : !modelPath.isEmpty() ? PairedValueModel.load(Path.of(modelPath), policyId)
                : inline.isEmpty() ? null : PairedValueModel.fromProperties(inline, policyId);
        // Snapshot requests bind the exact execution mode and actual model,
        // while the training policy ID deliberately permits shadow/application.
        replayId = ResearchBoard.sha256(policyId + new java.util.TreeSet<>(flags)
                + (model == null ? "-" : model.identity));
    }

    private static int bounded(final Properties p, final String key, final int def, final int low, final int high) {
        final int v = Integer.parseInt(p.getProperty(key, Integer.toString(def)).trim());
        if (v < low || v > high) throw new IllegalArgumentException(key + " out of range");
        return v;
    }
    boolean has(final String flag) { return flags.contains(flag); }
    boolean enabled(final RaceGame game, final int player) {
        return suppressed == 0 && trials > 0 && game.candidatePolicy(player)
                && (!flags.isEmpty() || capturePath != null);
    }

    /** Immutable, bounded per-seat response maps; snapshots and Undo can share them. */
    record Plans(List<Map<String, Direction>> seats) {
        Plans {
            final List<Map<String, Direction>> copy = new ArrayList<>();
            for (final Map<String, Direction> seat : seats) {
                if (seat.size() > 2) throw new IllegalArgumentException("at most two contingent worlds per seat");
                copy.add(Map.copyOf(seat));
            }
            seats = List.copyOf(copy);
        }
        static Plans empty() { return new Plans(java.util.Collections.nCopies(9, Map.of())); }
        Plans with(final int seat, final Map<String, Direction> responses) {
            final List<Map<String, Direction>> copy = new ArrayList<>(seats);
            copy.set(seat, responses); return new Plans(copy);
        }
        String encode() {
            final StringBuilder b = new StringBuilder();
            for (int i = 0; i < seats.size(); i++)
                for (final Map.Entry<String, Direction> r : new TreeMap<>(seats.get(i)).entrySet())
                    b.append(b.length() == 0 ? "" : "|").append(i).append(':').append(r.getKey())
                            .append(':').append(r.getValue().ordinal());
            return b.length() == 0 ? "-" : b.toString();
        }
        static Plans parse(final String value, final int players) {
            Plans result = empty();
            if (value.equals("-")) return result;
            if (value.length() > 1400) throw new IllegalArgumentException("oversized contingent memory");
            for (final String token : value.split("\\|", -1)) {
                final String[] r = token.split(":", -1);
                if (r.length != 3 || !r[1].matches("[0-9a-f]{64}"))
                    throw new IllegalArgumentException("invalid contingent memory");
                final int seat = Integer.parseInt(r[0]), action = Integer.parseInt(r[2]);
                if (seat < 0 || seat >= players || action < 0 || action >= 9)
                    throw new IllegalArgumentException("invalid contingent seat/action");
                final Map<String, Direction> map = new TreeMap<>(result.seats.get(seat));
                if (map.put(r[1], Direction.values()[action]) != null)
                    throw new IllegalArgumentException("duplicate contingent world");
                result = result.with(seat, map);
            }
            if (!result.encode().equals(value)) throw new IllegalArgumentException("noncanonical contingent memory");
            return result;
        }
    }
    record Proposal(String rootKey, Direction action, Map<String, Direction> responses) {
        Proposal { responses = Map.copyOf(responses); }
    }
    record Sample(ResearchBoard board, String policy, Direction baseline, Direction selected,
            Direction[] actions, long[] verdicts, double[][] features) {
        Sample {
            actions = actions.clone(); verdicts = verdicts.clone();
            features = Arrays.stream(features).map(double[]::clone).toArray(double[][]::new);
        }
    }

    Direction response(final RaceGame game) {
        final int slot = game.subgamestate;
        if (!has("contingent") || trials == 0 || !game.candidatePolicy(game.players[slot].getNumber())
                || suppressed != 0 && !allowResponse || plans.seats.get(slot).isEmpty()) return null;
        final Direction d = plans.seats.get(slot).get(ResearchBoard.capture(game).physicalKey());
        return d != null && ResearchBoard.legal(game).contains(d) ? d : null;
    }

    void commit(final RaceGame game, final RaceAi ai, final Direction actual) {
        final int slot = game.subgamestate;
        if (ai.researchProposal == null && ai.researchSample == null && plans.seats.get(slot).isEmpty()) return;
        // Never consume a plan at a hint or a mere query. This is called after
        // the live Undo snapshot, or by an explicitly detached full referee tail.
        final Proposal proposal = ai.researchProposal;
        final ResearchBoard root = proposal != null || ai.researchSample != null ? ResearchBoard.capture(game) : null;
        plans = plans.with(slot, Map.of());
        if (proposal != null && proposal.action() == actual && proposal.rootKey().equals(root.physicalKey()))
            plans = plans.with(slot, proposal.responses());
        if (detached == 0 && capturePath != null && captures < captureLimit && ai.researchSample != null
                && ai.researchSample.board().physicalKey().equals(root.physicalKey())) {
            final Path parent = capturePath.toAbsolutePath().getParent();
            try {
                Files.createDirectories(parent);
                Files.writeString(capturePath, sampleJson(ai.researchSample, actual) + "\n", StandardCharsets.UTF_8,
                        StandardOpenOption.CREATE, StandardOpenOption.APPEND);
                captures++;
            } catch (final IOException error) { throw new UncheckedIOException("cannot write requested racecraft capture", error); }
        }
    }

    record Choice(Direction action, boolean rejectPace) {}
    Choice choose(final RaceGame game, final RaceAi ai, final Direction incumbent,
            final Direction[] candidates, final long[] verdicts, final Direction pace) {
        final ResearchBoard root = ResearchBoard.capture(game);
        final List<Direction> tied = new ArrayList<>();
        final long best = verdicts[incumbent.ordinal()];
        for (final Direction d : candidates) if (verdicts[d.ordinal()] == best) tied.add(d);
        Direction pick = incumbent;
        boolean rejectPace = false;
        if (has("duel-ties") && live(game) == 2 && tied.size() > 1) {
            final long[] secondaryValues = new long[9];
            Arrays.fill(secondaryValues, Long.MIN_VALUE);
            long secondary = ai.researchForecast(pick, 1);
            secondaryValues[pick.ordinal()] = secondary;
            for (final Direction d : tied) if (d != incumbent) {
                final long alternative = ai.researchForecast(d, 1); tieComparisons++;
                secondaryValues[d.ordinal()] = alternative;
                if (alternative >= 0 && (secondary < 0 || alternative < secondary)) {
                    pick = d; secondary = alternative;
                }
            }
            if (pick != incumbent) tieChanges++;
            if (pace != null && tied.contains(pace) && secondary >= 0) {
                final long pv = secondaryValues[pace.ordinal()];
                rejectPace = pv < 0 || pv > secondary;
            }
        }
        final double[][] feature = new double[candidates.length][];
        final boolean capture = tied.size() > 1 && capturePath != null;
        if (capture) for (int i = 0; i < candidates.length; i++) feature[i] = features(game, root, candidates[i]);
        if (model != null && tied.size() > 1) {
            Direction learned = pick;
            double[] predicted = model.predict(features(game, root, pick));
            if (predicted != null) for (final Direction d : tied) if (d != pick) {
                final double[] other = model.predict(features(game, root, d)); modelComparisons++;
                if (other != null && lexBetter(other, predicted)) { learned = d; predicted = other; }
            }
            if (learned != pick) {
                modelChanges++;
                if (audit && detached == 0) System.err.println("RACECRAFT model " + pick + " -> " + learned
                        + (has("paired-value") ? " applied" : " shadow"));
                if (has("paired-value")) pick = learned;
            }
            if (has("paired-value") && pace != null && tied.contains(pace)) {
                final double[] pp = model.predict(features(game, root, pick));
                final double[] pv = model.predict(features(game, root, pace));
                rejectPace |= pp != null && pv != null && lexBetter(pp, pv);
            }
        }
        if (has("contingent") && tied.size() > 1) {
            final ContingentPlans.Result result = ContingentPlans.choose(game, root, pick, tied, trials);
            planTrials += result.trials();
            if (result.proposal() != null) {
                ai.researchProposal = result.proposal(); pick = result.proposal().action(); planChanges++;
            }
        }
        // Captures are committed later, so post-chooser overrides and rejected
        // human moves cannot be mistaken for an executed choice.
        if (capture)
            ai.researchSample = new Sample(root, policyId, incumbent, pick, candidates, verdicts, feature);
        if (audit && detached == 0) System.err.println("RACECRAFT p=" + (root.slot + 1) + " ties=" + tied.size()
                + " chosen=" + pick + " tieComparisons=" + tieComparisons + " tieChanges=" + tieChanges
                + " modelComparisons=" + modelComparisons + " modelChanges=" + modelChanges
                + " planTrials=" + planTrials + " planChanges=" + planChanges);
        return new Choice(pick, rejectPace || pick != incumbent
                || ai.researchProposal != null && pick != pace);
    }

    static boolean lexBetter(final double[] a, final double[] b) {
        return a[0] < b[0] || a[0] == b[0] && a[1] < b[1];
    }
    static int live(final RaceGame game) {
        int count = 0; for (final Player p : game.players) if (!p.isFinished()) count++; return count;
    }

    /** Candidate-conditioned physical features; labels come from COMPLETE
     * reacting referee tails, not from the feature heuristic. */
    static double[] features(final RaceGame game, final ResearchBoard root, final Direction action) {
        try (ResearchBoard.Scope scope = new ResearchBoard.Scope(game, root)) {
            final int own = root.slot;
            ResearchBoard.advance(game, action, new String[game.players.length], new int[game.players.length]);
            final Player p = game.players[own]; final int[] x = p.getPosition(), v = p.getVelocity();
            final double[] f = new double[FEATURES];
            f[0] = v[0] / 10.0; f[1] = v[1] / 10.0;
            f[2] = x[0] / (double) (game.gameCols + 1); f[3] = x[1] / (double) (game.gameRows + 1);
            final int distance = ResearchBoard.distance(game, own);
            f[4] = distance == Integer.MAX_VALUE ? 100.0 : distance / 1000.0;
            f[5] = p.isFinished() ? 0.0 : ResearchBoard.legal(game).size() / 9.0;
            final int owed = OptimalPotential.remainingEvents(p.getNextGate(), p.getLap(), game.totalLaps);
            f[6] = owed / (3.0 * game.totalLaps); f[7] = live(game) / 9.0;
            int nearest = -1, gap = Integer.MAX_VALUE, overlaps = 0;
            for (int i = 0; i < game.players.length; i++) if (i != own && !game.players[i].isFinished()) {
                final int[] r = game.players[i].getPosition(), w = game.players[i].getVelocity();
                final int d = Math.max(Math.abs(r[0] - x[0]), Math.abs(r[1] - x[1]));
                if (d < gap) { nearest = i; gap = d; }
                if (Math.abs(x[0] + v[0] - r[0] - w[0]) <= 2
                        && Math.abs(x[1] + v[1] - r[1] - w[1]) <= 2) overlaps++;
            }
            f[8] = Math.min(gap, 100) / 20.0;
            if (nearest >= 0) {
                final Player r = game.players[nearest]; final int[] y = r.getPosition(), w = r.getVelocity();
                f[9] = clip((y[0] - x[0]) / 40.0); f[10] = clip((y[1] - x[1]) / 40.0);
                f[11] = (w[0] - v[0]) / 10.0; f[12] = (w[1] - v[1]) / 10.0;
                f[13] = (OptimalPotential.remainingEvents(r.getNextGate(), r.getLap(), game.totalLaps) - owed)
                        / (3.0 * game.totalLaps);
                f[14] = nearest < own ? -1.0 : 1.0;
            }
            f[15] = overlaps / 8.0; f[16] = action.dx; f[17] = action.dy;
            return f;
        }
    }
    private static double clip(final double d) { return Math.max(-5, Math.min(5, d)); }

    static String sampleJson(final Sample sample, final Direction actual) {
        final StringBuilder b = new StringBuilder("{\"schema\":1,\"engine\":").append(quote(engineId()))
                .append(",\"policy\":").append(quote(sample.policy())).append(",\"state\":").append(quote(sample.board().encode())).append(",\"state_id\":")
                .append(quote(ResearchBoard.sha256(sample.board().encode())))
                .append(",\"baseline\":").append(sample.baseline().ordinal()).append(",\"selected\":")
                .append(sample.selected().ordinal()).append(",\"executed\":").append(actual.ordinal())
                .append(",\"candidates\":[");
        for (int i = 0; i < sample.actions().length; i++) {
            final Direction d = sample.actions()[i];
            b.append(i == 0 ? "" : ",").append("{\"action\":").append(d.ordinal()).append(",\"verdict\":")
                    .append(sample.verdicts()[d.ordinal()]).append(",\"features\":")
                    .append(Arrays.toString(sample.features()[i])).append('}');
        }
        return b.append("]}").toString();
    }
    static String quote(final String s) {
        final StringBuilder b = new StringBuilder("\"");
        for (int i = 0; i < s.length(); i++) {
            final char c = s.charAt(i);
            if (c == '"' || c == '\\') b.append('\\').append(c);
            else if (c < 32) b.append(String.format(java.util.Locale.ROOT, "\\u%04x", (int)c));
            else b.append(c);
        }
        return b.append('"').toString();
    }
    private static void addClasses(final Map<String, Class<?>> classes, final Class<?> type) {
        if (classes.putIfAbsent(type.getName(), type) != null) return;
        for (final Class<?> nested : type.getDeclaredClasses()) addClasses(classes, nested);
    }
    private static String engineIdentity;
    static synchronized String engineId() {
        if (engineIdentity != null) return engineIdentity;
        try {
            final MessageDigest hash = MessageDigest.getInstance("SHA-256");
            // A packaged executable includes synthetic/anonymous helper classes
            // that reflection does not enumerate. Bind the entire JAR when present.
            final java.security.CodeSource source = RaceAi.class.getProtectionDomain().getCodeSource();
            if (source != null && "file".equals(source.getLocation().getProtocol())) {
                final Path binary;
                try { binary = Path.of(source.getLocation().toURI()); }
                catch (final java.net.URISyntaxException invalid) { throw new IOException(invalid); }
                if (Files.isRegularFile(binary)) {
                    try (InputStream input = Files.newInputStream(binary)) {
                        final byte[] bytes = new byte[65536]; int count;
                        while ((count = input.read(bytes)) >= 0) hash.update(bytes, 0, count);
                    }
                    engineIdentity = java.util.HexFormat.of().formatHex(hash.digest());
                    return engineIdentity;
                }
            }
            // Include nested records/helpers too: changing only a nested class
            // must invalidate an old trained model. Sort for canonical ordering.
            final Map<String, Class<?>> classes = new TreeMap<>();
            for (final Class<?> type : new Class<?>[]{RaceAi.class, RaceGame.class, ResearchBoard.class,
                    DecisionResearch.class, PairedValueModel.class, ContingentPlans.class, ResearchQueries.class,
                    Reachability.class, OptimalPotential.class, OptimalLap.class, RaceAiTactics.class,
                    RaceAiDuelSearch.class, RaceAiPrivateLane.class, RaceAiMoveMemo.class, ChooserTraffic.class,
                    GateFixedPoint.class, PocketCells.class, StartPlacement.class, Player.class, Direction.class,
                    Track.class, TrackGeometry.class, TrackIO.class, MoveQueries.class}) addClasses(classes, type);
            for (final Map.Entry<String, Class<?>> entry : classes.entrySet()) {
                hash.update(entry.getKey().getBytes(StandardCharsets.UTF_8));
                try (InputStream input = entry.getValue().getResourceAsStream("/" + entry.getKey().replace('.', '/') + ".class")) {
                    if (input == null) throw new IOException("research needs JVM class resources");
                    hash.update(input.readAllBytes());
                }
            }
            engineIdentity = java.util.HexFormat.of().formatHex(hash.digest());
            return engineIdentity;
        } catch (final IOException error) { throw new UncheckedIOException(error); }
        catch (final NoSuchAlgorithmException impossible) { throw new AssertionError(impossible); }
    }
}
