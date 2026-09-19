package tr.logic;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Properties;
import java.util.Set;

/** Per-game, opt-in research controls. Nothing is enabled by candidateSlots alone. */
final class ChooserConfig {
    static final String LEGACY_FEATURES = "speed_inf,speed_squared,acceleration,legal_exits,map_alive,"
            + "remaining_events,solo_turns,direct_rivals,indirect_rivals,contested_exits,nearest_distance,terminal";
    static final String FEATURES = LEGACY_FEATURES + ",closing_motion,relative_route,route_known,"
            + "rival_moves_first,response_delta,rival_exits,field_size";
    final boolean aware, setup, terminal, student, assist, legacyGuarded, legacyUnchecked, audit;
    final int rounds, policyBudget, moveBudget, setupWidth, auditEvery;
    final Model model, legacy;
    final String specification;

    ChooserConfig(final Properties p) {
        specification = p.getProperty("chooser.experiments", "").trim();
        final Set<String> flags = new HashSet<>();
        if (!specification.isEmpty()) for (final String value : specification.split(",", -1)) {
            final String flag = value.trim();
            if (!Set.of("aware", "setup", "terminal", "student", "assist", "legacy-guarded", "legacy-unchecked").contains(flag)
                    || !flags.add(flag)) throw new IllegalArgumentException("Unknown/duplicate chooser experiment: " + flag);
        }
        aware = flags.contains("aware"); setup = flags.contains("setup"); terminal = flags.contains("terminal");
        student = flags.contains("student"); assist = flags.contains("assist");
        legacyGuarded = flags.contains("legacy-guarded"); legacyUnchecked = flags.contains("legacy-unchecked");
        if (aware && student) throw new IllegalArgumentException("Compare aware and student separately");
        if ((legacyGuarded || legacyUnchecked) && flags.size() != 1)
            throw new IllegalArgumentException("Legacy insertion-point controls must be isolated arms");
        final String a = p.getProperty("chooser.audit", "false");
        if (!a.equals("true") && !a.equals("false")) throw new IllegalArgumentException("chooser.audit must be boolean");
        audit = Boolean.parseBoolean(a);
        rounds = integer(p, "chooser.rounds", 12, 1, 24);
        policyBudget = integer(p, "chooser.policyBudget", 4096, 0, 65536);
        moveBudget = integer(p, "chooser.moveBudget", 8192, 0, 131072);
        setupWidth = integer(p, "chooser.setupWidth", 2, 1, 3);
        auditEvery = integer(p, "chooser.auditEvery", 1, 1, 1000000);
        model = student || assist ? new Model(p, "chooser.student.", FEATURES, "chooser-distill-v1", 19) : null;
        legacy = legacyGuarded || legacyUnchecked
                ? new Model(p, "racecraft.model.", LEGACY_FEATURES, "1", 12) : null;
    }

    boolean enabled() { return !specification.isEmpty(); }

    static final class Model {
        final double[] weights;
        final double margin;
        final String digest;
        Model(final Properties p, final String prefix, final String features, final String version, final int count) {
            digest = p.getProperty(prefix + "trainingSha256", "");
            if (!version.equals(p.getProperty(prefix + "version")) || !features.equals(p.getProperty(prefix + "features"))
                    || !digest.matches("[0-9a-f]{64}"))
                throw new IllegalArgumentException("A versioned, provenance-bound model is required: " + prefix);
            weights = Arrays.stream(p.getProperty(prefix + "weights", "").split(",", -1))
                    .mapToDouble(ChooserConfig::finite).toArray();
            if (weights.length != count) throw new IllegalArgumentException("Wrong model dimension");
            for (final double w : weights) if (Math.abs(w) > 1e6) throw new IllegalArgumentException("Model weight too large");
            margin = finite(p.getProperty(prefix + "margin", "0.05"));
            if (margin < 0 || margin > 100) throw new IllegalArgumentException("Invalid model margin");
        }
        double score(final double[] f) {
            if (f == null || f.length != weights.length) throw new IllegalArgumentException("Incompatible features");
            double result = 0;
            for (int i = 0; i < f.length; i++) {
                if (!Double.isFinite(f[i])) throw new IllegalArgumentException("Invalid feature");
                result += weights[i] * f[i];
            }
            return result;
        }
    }

    private static int integer(final Properties p, final String key, final int fallback, final int min, final int max) {
        final int n;
        try { n = Integer.parseInt(p.getProperty(key, Integer.toString(fallback))); }
        catch (final NumberFormatException e) { throw new IllegalArgumentException("Invalid " + key, e); }
        if (n < min || n > max) throw new IllegalArgumentException(key + " outside " + min + ".." + max);
        return n;
    }
    private static double finite(final String s) {
        final double n;
        try { n = Double.parseDouble(s.trim()); }
        catch (final NumberFormatException e) { throw new IllegalArgumentException("Invalid model number", e); }
        if (!Double.isFinite(n)) throw new IllegalArgumentException("Non-finite model number");
        return n;
    }
}
