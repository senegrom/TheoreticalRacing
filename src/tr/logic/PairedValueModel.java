package tr.logic;

import java.io.IOException;
import java.io.Reader;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;

/** Small pairwise ridge model. Only a chooser's exact ties are eligible.
 * Strict model/build/profile and feature-domain checks fall back to the chooser;
 * a model never asserts physical legality, classification or a tactical proof. */
final class PairedValueModel {
    final double[] mean, scale, low, high, place, time;
    final String identity;
    private PairedValueModel(final Properties p) {
        final java.util.TreeMap<String, String> values = new java.util.TreeMap<>();
        for (final String key : p.stringPropertyNames()) values.put(key, p.getProperty(key));
        identity = ResearchBoard.sha256(values.toString());
        mean = vector(p, "mean"); scale = vector(p, "scale");
        low = vector(p, "low"); high = vector(p, "high");
        place = vector(p, "place"); time = vector(p, "time");
        for (int i = 0; i < mean.length; i++)
            if (scale[i] <= 0 || low[i] > high[i]) throw new IllegalArgumentException("invalid model scale/domain");
    }
    static PairedValueModel load(final Path path, final String policyId) {
        final Properties p = new Properties();
        try {
            if (Files.size(path) > 65536) throw new IllegalArgumentException("oversized racecraft model");
            try (Reader input = Files.newBufferedReader(path, StandardCharsets.UTF_8)) { p.load(input); }
        } catch (final IOException error) { throw new UncheckedIOException("cannot load racecraft model", error); }
        return fromProperties(p, policyId);
    }
    static PairedValueModel fromProperties(final Properties p, final String policyId) {
        if (!"paired-ridge-1".equals(p.getProperty("schema"))) throw new IllegalArgumentException("unknown racecraft model schema");
        final PairedValueModel model = new PairedValueModel(p);
        // A well-formed model from another executable/profile is inapplicable,
        // not permission to quietly change a different champion.
        return DecisionResearch.engineId().equals(p.getProperty("engine")) && policyId.equals(p.getProperty("policy"))
                ? model : null;
    }
    private static double[] vector(final Properties p, final String key) {
        final String[] fields = p.getProperty(key, "").split(",", -1);
        if (fields.length != DecisionResearch.FEATURES) throw new IllegalArgumentException("invalid model vector: " + key);
        final double[] values = new double[fields.length];
        for (int i = 0; i < values.length; i++) {
            values[i] = Double.parseDouble(fields[i]);
            if (!Double.isFinite(values[i]) || Math.abs(values[i]) > 1e12)
                throw new IllegalArgumentException("nonfinite/unbounded model value: " + key);
        }
        return values;
    }
    double[] predict(final double[] features) {
        if (features.length != mean.length) return null;
        double p = 0, t = 0;
        for (int i = 0; i < features.length; i++) {
            final double f = features[i];
            if (!Double.isFinite(f) || f < low[i] - 1e-10 || f > high[i] + 1e-10) return null;
            final double x = (f - mean[i]) / scale[i];
            p += place[i] * x; t += time[i] * x;
        }
        return Double.isFinite(p) && Double.isFinite(t) ? new double[]{p, t + 1000.0 * features[4]} : null;
    }
}
