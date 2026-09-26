package tr.logic;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.EnumSet;
import java.util.List;
import java.util.Locale;
import java.util.Properties;

/** Independently gated review experiments; no system properties or default promotion. */
final class RacecraftReview {
    private static final Direction[] DIRECTIONS = Direction.values();
    private RacecraftReview() {}

    enum Feature {
        CROSSING("crossing"), DUEL_ANYTIME("duel-anytime"), DUEL_CACHE("duel-cache"),
        PROJECTED_PLACE("projected-place"), DIVERSE("diverse"), SELECTIVE("selective");
        final String flag;
        Feature(final String flag) { this.flag = flag; }
    }

    static final class Config {
        private final EnumSet<Feature> features;
        final boolean audit;
        private Config(final EnumSet<Feature> features, final boolean audit) {
            this.features = features;
            this.audit = audit;
        }
        static Config from(final Properties props) {
            final EnumSet<Feature> features = EnumSet.noneOf(Feature.class);
            final String spec = props.getProperty("racecraftReview", "").trim();
            if (!spec.isEmpty()) {
                for (final String item : spec.split(",", -1)) {
                    final String flag = item.trim().toLowerCase(Locale.ROOT);
                    if (flag.equals("all")) {
                        features.addAll(EnumSet.allOf(Feature.class));
                        continue;
                    }
                    Feature match = null;
                    for (final Feature feature : Feature.values())
                        if (feature.flag.equals(flag)) match = feature;
                    if (match == null) throw new IllegalArgumentException("Unknown racecraftReview flag: " + item);
                    features.add(match);
                }
            }
            final String audit = props.getProperty("racecraftReviewAudit", "false").trim();
            if (!audit.equalsIgnoreCase("true") && !audit.equalsIgnoreCase("false"))
                throw new IllegalArgumentException("racecraftReviewAudit must be true or false");
            return new Config(features, Boolean.parseBoolean(audit));
        }
        boolean has(final Feature feature) { return features.contains(feature); }
    }

    static boolean enabled(final RaceGame game, final int player, final Feature feature) {
        return game.candidatePolicy(player) && game.racecraftReview.has(feature);
    }

    /** Original stable score shortlist, optionally plus ONE kinematically distinct action.
     * Distinct means largest minimum Manhattan separation in acceleration space;
     * this is a proposal heuristic, not a proof of tactical superiority. */
    static Direction[] shortlist(final double[] scores, final double bestScore,
            final int width, final double window, final boolean diverse) {
        if (width < 1 || width > DIRECTIONS.length || !Double.isFinite(window) || window < 0)
            throw new IllegalArgumentException("invalid shortlist limits");
        if (scores.length != DIRECTIONS.length) throw new IllegalArgumentException("wrong score row length");
        final List<Direction> sorted = new ArrayList<>();
        for (final Direction d : DIRECTIONS) {
            final double score = scores[d.ordinal()];
            if (!Double.isFinite(score) || score == Double.MAX_VALUE || score > bestScore + window) continue;
            int index = sorted.size();
            while (index > 0 && scores[sorted.get(index - 1).ordinal()] > score) index--;
            sorted.add(index, d);
        }
        final List<Direction> selected = new ArrayList<>(sorted.subList(0, Math.min(width, sorted.size())));
        if (diverse && !selected.isEmpty()) {
            Direction extra = null;
            int bestSeparation = -1;
            for (final Direction d : DIRECTIONS) {
                final double score = scores[d.ordinal()];
                if (selected.contains(d) || !Double.isFinite(score) || score == Double.MAX_VALUE
                        || score > bestScore + window + 1.0) continue;
                int separation = Integer.MAX_VALUE;
                for (final Direction existing : selected)
                    separation = Math.min(separation, Math.abs(d.dx - existing.dx) + Math.abs(d.dy - existing.dy));
                if (separation > bestSeparation || separation == bestSeparation
                        && (extra == null || score < scores[extra.ordinal()])) {
                    extra = d;
                    bestSeparation = separation;
                }
            }
            if (extra != null) selected.add(extra);
        }
        return selected.toArray(Direction[]::new);
    }

    /** At a full-round endpoint, equal remaining move counts favor the earlier slot.
     * Return -1 rather than guessing when any live car lacks a finite route value. */
    static int projectedAhead(final int self, final int finishedAhead, final int[] remaining,
            final boolean[] alive) {
        if (remaining.length != alive.length || self < 0 || self >= alive.length)
            throw new IllegalArgumentException("invalid endpoint roster");
        if (!alive[self] || remaining[self] < 0 || remaining[self] == Integer.MAX_VALUE) return -1;
        int ahead = finishedAhead;
        for (int i = 0; i < alive.length; i++) {
            if (i == self || !alive[i]) continue;
            if (remaining[i] < 0 || remaining[i] == Integer.MAX_VALUE) return -1;
            if (remaining[i] < remaining[self] || remaining[i] == remaining[self] && i < self) ahead++;
        }
        return ahead;
    }

    /** A selective response-model change is admitted only for a nominal tie and
     * a strictly better, completed nonnegative stronger-world forecast. */
    static boolean improvesTiedForecast(final long nominal, final long alternativeNominal,
            final long stronger, final long alternativeStronger) {
        return nominal >= 0 && nominal == alternativeNominal && stronger >= 0
                && alternativeStronger >= 0 && alternativeStronger < stronger;
    }

    /** Root-only diagnostics. No policy calls, workspace reset, or mutable array aliasing.
     * Endpoint rows are forecast observations, NOT labeled/replay-ready referee states. */
    static final class Trace {
        private final String root;
        private final List<String> stages = new ArrayList<>();
        private final List<String> candidates = new ArrayList<>();
        private String endpoint = "null";
        int evaluations;

        Trace(final RaceGame game, final int player) {
            final StringBuilder out = new StringBuilder("{\"schema\":1,\"turn\":")
                    .append(game.turnCount()).append(",\"player\":").append(player)
                    .append(",\"totalLaps\":").append(game.totalLaps).append(",\"roster\":[");
            for (int i = 0; i < game.players.length; i++) {
                if (i > 0) out.append(',');
                final Player p = game.players[i];
                out.append("{\"slot\":").append(i).append(",\"number\":").append(p.getNumber())
                        .append(",\"position\":").append(Arrays.toString(p.getPosition()))
                        .append(",\"velocity\":").append(Arrays.toString(p.getVelocity()))
                        .append(",\"lapState\":").append(Arrays.toString(p.lapState()))
                        .append(",\"finishedPlace\":").append(p.getFinishedPlace()).append('}');
            }
            root = out.append(']').toString();
        }
        void stage(final String name, final Direction action) {
            stages.add("{\"stage\":\"" + name + "\",\"action\":" + direction(action) + "}");
        }
        void endpoint(final int turn, final boolean gridLegal, final int[] px, final int[] py,
                final int[] vx, final int[] vy, final int[] laps, final int[] gates, final boolean[] alive) {
            final StringBuilder out = new StringBuilder("{\"replayReady\":false,\"turn\":")
                    .append(turn).append(",\"aiGridLegal\":").append(gridLegal).append(",\"cars\":[");
            for (int i = 0; i < px.length; i++) {
                if (i > 0) out.append(',');
                out.append('[').append(px[i]).append(',').append(py[i]).append(',')
                        .append(vx[i]).append(',').append(vy[i]).append(',').append(laps[i]).append(',')
                        .append(gates[i]).append(',').append(alive[i] ? 1 : 0).append(']');
            }
            endpoint = out.append("]}").toString();
        }
        void candidate(final Direction action, final String model, final long verdict) {
            evaluations++;
            candidates.add("{\"action\":" + direction(action) + ",\"model\":\"" + model
                    + "\",\"verdict\":" + verdict + ",\"endpoint\":" + endpoint + "}");
            endpoint = "null";
        }
        String json(final Direction selected) {
            return root + ",\"stages\":[" + String.join(",", stages) + "],\"candidates\":["
                    + String.join(",", candidates) + "],\"selected\":" + direction(selected) + "}";
        }
        void emit(final Direction selected) { System.err.println("RACECRAFT_REVIEW " + json(selected)); }
        private static String direction(final Direction d) { return d == null ? "null" : "\"" + d.name() + "\""; }
    }
}
