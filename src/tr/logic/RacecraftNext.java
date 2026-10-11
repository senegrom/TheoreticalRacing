package tr.logic;

import java.util.EnumSet;
import java.util.Properties;

/** Independent candidate arms; settings and shipped defaults stay unchanged. */
final class RacecraftNext {
    enum Feature {
        CRASH_RANK("crash-rank"), RANK_TIME("rank-time"), OPENING("opening"), ADAPTIVE_ESCAPE("adaptive-escape"),
        FOLLOWUP("followup"), RECOVERY("recovery"), TACTICAL_EXTENSION("tactical-extension"), DENIAL("denial"), MANOEUVRE("manoeuvre"),
        CHECKPOINT_TRAFFIC("checkpoint-traffic"), DECISION_ENDPOINT("decision-endpoint"),
        STAGED_ORDER("staged-order"), SHORT_TRANSITIONS("short-transitions"), SUFFIX_MANOEUVRES("suffix-manoeuvres"),
        RESPONSE_STRATEGY("response-strategy"), PLACE_CERTIFICATES("place-certificates"),
        FORCED_SEQUENCE("forced-sequence"), CONTINUATION_POLICIES("continuation-policies"),
        ORDERED_BLOCKADE("ordered-blockade"), PACE_FEINTS("pace-feints"), AMBUSH("ambush"),
        TRAFFIC_JUDO("traffic-judo"), SELFISH_SEARCH("selfish-search"), TWO_JUDGE("two-judge");
        final String flag;
        Feature(final String flag) { this.flag = flag; }
    }

    private final EnumSet<Feature> features;
    final boolean capture;
    final int openingRounds;
    final int openingTrials;
    final int captureEvery;
    final int captureLimit;
    final int adaptiveNodes, adaptiveCycles, recoveryTrials, tacticalExtraRounds;
    final int manoeuvreNodes, manoeuvreDepth;
    final int strategyNodes, forcedMoveCap;
    final int creativeNodes, creativeTrials, selfishPlies;

    RacecraftNext(final Properties props) {
        features = EnumSet.noneOf(Feature.class);
        final String spec = props.getProperty("racecraftNext", "").trim();
        if (!spec.isEmpty()) for (final String token : spec.split(",", -1)) {
            Feature found = null;
            for (final Feature f : Feature.values()) if (f.flag.equals(token.trim())) found = f;
            if (found == null || !features.add(found))
                throw new IllegalArgumentException("unknown or repeated racecraftNext flag: " + token);
        }
        final String audit = props.getProperty("racecraftCapture", "false").trim();
        if (!audit.equals("true") && !audit.equals("false"))
            throw new IllegalArgumentException("racecraftCapture must be true or false");
        capture = Boolean.parseBoolean(audit);
        creativeNodes = bounded(props, "racecraftCreativeNodes", 2048, 0, 20000);
        creativeTrials = bounded(props, "racecraftCreativeTrials", 6, 0, 12);
        selfishPlies = bounded(props, "racecraftSelfishPlies", 6, 2, 9);
        strategyNodes = bounded(props, "racecraftStrategyNodes", 12000, 0, 40000);
        forcedMoveCap = bounded(props, "racecraftForcedMoveCap", 16, 4, 24);
        manoeuvreNodes = bounded(props, "racecraftManoeuvreNodes", 192, 0, 2048);
        manoeuvreDepth = bounded(props, "racecraftManoeuvreDepth", 4, 2, 4);
        adaptiveNodes = bounded(props, "racecraftAdaptiveNodes", 2048, 0, 20000);
        adaptiveCycles = bounded(props, "racecraftAdaptiveCycles", 2, 1, 3);
        recoveryTrials = bounded(props, "racecraftRecoveryTrials", 9, 0, 9);
        tacticalExtraRounds = bounded(props, "racecraftTacticalExtraRounds", 2, 0, 2);
        openingRounds = bounded(props, "racecraftOpeningRounds", 6, 2, 12);
        openingTrials = bounded(props, "racecraftOpeningTrials", 18, 0, 36);
        captureEvery = bounded(props, "racecraftCaptureEvery", 1, 1, 1000000);
        captureLimit = bounded(props, "racecraftCaptureLimit", 100, 0, 100000);
    }

    boolean enabled(final RaceGame game, final int player, final Feature feature) {
        return game.candidatePolicy(player) && configured(feature)
                && (feature.ordinal() < Feature.SUFFIX_MANOEUVRES.ordinal()
                        || feature.ordinal() > Feature.ORDERED_BLOCKADE.ordinal() || strategyNodes > 0)
                && (!creative(feature) || creativeNodes > 0 && creativeTrials > 0)
                && (feature != Feature.SUFFIX_MANOEUVRES || manoeuvreNodes > 0)
                && (feature != Feature.OPENING || openingTrials > 0 && opening(game, player))
                && (feature != Feature.FOLLOWUP || features.contains(Feature.OPENING)
                        && openingTrials > 0 && opening(game, player))
                && (feature != Feature.MANOEUVRE || manoeuvreNodes > 0)
                && (feature != Feature.ADAPTIVE_ESCAPE || adaptiveNodes > 0)
                && (feature != Feature.RECOVERY || recoveryTrials > 0)
                && (feature != Feature.TACTICAL_EXTENSION || tacticalExtraRounds > 0);
    }
    boolean driving(final RaceGame game, final int player) {
        return enabled(game, player, Feature.CRASH_RANK) || enabled(game, player, Feature.RANK_TIME)
                || enabled(game, player, Feature.OPENING);
    }

    boolean configured(final Feature feature) { return features.contains(feature)
            || feature == Feature.MANOEUVRE && features.contains(Feature.SUFFIX_MANOEUVRES)
                    && strategyNodes > 0; }
    String signature() { return features.toString() + ":" + openingRounds + ":" + openingTrials
            + ":" + adaptiveNodes + ":" + adaptiveCycles + ":" + recoveryTrials + ":" + tacticalExtraRounds
            + ":" + manoeuvreNodes + ":" + manoeuvreDepth + ":" + strategyNodes + ":" + forcedMoveCap
            + ":" + creativeNodes + ":" + creativeTrials + ":" + selfishPlies; }

    static boolean creative(final Feature feature) { return feature.ordinal() >= Feature.PACE_FEINTS.ordinal(); }
    boolean creativeConfigured() {
        for (final Feature feature : features) if (creative(feature)) return true;
        return false;
    }
    boolean creativeEnabled(final RaceGame game, final int player) {
        return game.candidatePolicy(player) && creativeConfigured() && creativeNodes > 0 && creativeTrials > 0;
    }

    boolean any(final RaceGame game, final int player) {
        for (final Feature feature : features) if (enabled(game, player, feature)) return true;
        return false;
    }

    private static int bounded(final Properties props, final String key, final int fallback,
            final int minimum, final int maximum) {
        final int value = Integer.parseInt(props.getProperty(key, Integer.toString(fallback)).trim());
        if (value < minimum || value > maximum) throw new IllegalArgumentException(key + " out of range");
        return value;
    }

    /** Initial four roster rounds, before the mover passes CP1. */
    static boolean opening(final RaceGame game, final int player) {
        if (game.turnCount() >= 4 * game.players.length) return false;
        for (final Player p : game.players) {
            if (p.getNumber() == player && (p.getLap() != 0
                    || game.lapGates != null && p.getNextGate() != 1)) return false;
            if (!p.isFinished() && p.getPosition()[0] == Player.INIT_POS) return false;
        }
        return true;
    }
}
