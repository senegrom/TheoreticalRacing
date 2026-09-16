package tr.logic;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Properties;
import java.util.Set;

/** Research controls, snapshotted per game. No flag and no selected slot means
 * exactly the champion; a model is data embedded in the manifest-bound profile. */
final class RacecraftConfig {
    static final String FEATURES = "speed_inf,speed_squared,acceleration,legal_exits,map_alive,"
            + "remaining_events,solo_turns,direct_rivals,indirect_rivals,contested_exits,nearest_distance,terminal";
    static final int FEATURE_COUNT = 12;
    final boolean interaction, refresh, opportunity, encounter, learned, audit;
    final int rounds, extraRounds, policyBudget, extensionBudget, alternatives;
    final double[] weights;
    final double margin;
    final String specification;

    RacecraftConfig(final Properties p) {
        specification = p.getProperty("racecraft.experiments", "").trim();
        final Set<String> flags = new HashSet<>();
        if (!specification.isEmpty()) {
            for (final String part : specification.split(",", -1)) {
                final String flag = part.trim();
                if (!Set.of("interaction", "refresh", "opportunity", "encounter", "learned").contains(flag)
                        || !flags.add(flag))
                    throw new IllegalArgumentException("Unknown/duplicate racecraft experiment: " + flag);
            }
        }
        interaction = flags.contains("interaction") || flags.contains("refresh");
        refresh = flags.contains("refresh");
        opportunity = flags.contains("opportunity");
        encounter = flags.contains("encounter");
        learned = flags.contains("learned");
        final String auditValue = p.getProperty("racecraft.audit", "false");
        if (!auditValue.equals("true") && !auditValue.equals("false"))
            throw new IllegalArgumentException("racecraft.audit must be true or false");
        audit = Boolean.parseBoolean(auditValue);
        rounds = integer(p, "racecraft.rounds", 2, 1, 4);
        extraRounds = integer(p, "racecraft.extraRounds", 1, 0, 3);
        policyBudget = integer(p, "racecraft.policyBudget", 96, 0, 512);
        extensionBudget = integer(p, "racecraft.extensionBudget", 64, 0, 512);
        alternatives = integer(p, "racecraft.alternatives", 2, 1, 8);
        margin = finite(p.getProperty("racecraft.model.margin", "0.05"));
        if (margin < 0 || margin > 100) throw new IllegalArgumentException("Invalid model margin");
        if (learned) {
            if (!"1".equals(p.getProperty("racecraft.model.version"))
                    || !FEATURES.equals(p.getProperty("racecraft.model.features"))
                    || !p.getProperty("racecraft.model.trainingSha256", "").matches("[0-9a-f]{64}"))
                throw new IllegalArgumentException("Learned experiment requires a versioned, provenance-bound model");
            weights = Arrays.stream(p.getProperty("racecraft.model.weights", "").split(",", -1))
                    .mapToDouble(RacecraftConfig::finite).toArray();
            if (weights.length != FEATURE_COUNT)
                throw new IllegalArgumentException("Wrong racecraft model dimension");
            for (final double w : weights)
                if (Math.abs(w) > 1e6) throw new IllegalArgumentException("Model weight too large");
        } else weights = null;
    }

    boolean enabled() { return interaction || opportunity || encounter || learned; }

    double score(final double[] f) {
        if (weights == null || f.length != FEATURE_COUNT)
            throw new IllegalArgumentException("Model or features unavailable");
        double value = 0;
        for (int i = 0; i < f.length; i++) {
            if (!Double.isFinite(f[i])) throw new IllegalArgumentException("Non-finite feature");
            value += f[i] * weights[i];
        }
        return value;
    }

    private static int integer(final Properties p, final String key, final int def, final int lo, final int hi) {
        final int v;
        try { v = Integer.parseInt(p.getProperty(key, Integer.toString(def))); }
        catch (final NumberFormatException e) { throw new IllegalArgumentException("Invalid " + key, e); }
        if (v < lo || v > hi) throw new IllegalArgumentException(key + " outside " + lo + ".." + hi);
        return v;
    }

    private static double finite(final String s) {
        final double value;
        try { value = Double.parseDouble(s.trim()); }
        catch (final NumberFormatException e) { throw new IllegalArgumentException("Invalid model number", e); }
        if (!Double.isFinite(value)) throw new IllegalArgumentException("Non-finite model number");
        return value;
    }
}
