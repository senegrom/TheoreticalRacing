package tr.browser;

import java.util.concurrent.atomic.AtomicInteger;

/** Output-only telemetry. Stage counts describe dependencies, never estimated time. */
public final class Progress {
    private static final AtomicInteger PASSES = new AtomicInteger();
    private static final AtomicInteger BUILDS = new AtomicInteger();
    private static final AtomicInteger DISTANCES = new AtomicInteger();
    private static final ThreadLocal<Pass> CURRENT = ThreadLocal.withInitial(Pass::new);
    private static volatile boolean nativeAvailable = true;
    private static volatile int stage = 1, stages = 6;
    private static volatile boolean cached, complete;
    private Progress() {}
    private static final class Pass {
        String phase = "Preparing track";
        int number, lastDone = -1;
        long lastReport;
    }
    private static native void report(String phase, int done, int total, int pass,
            int stage, int stages, boolean complete, boolean cached);
    /** One geometry build owns one plan, irrespective of the number of drivers. */
    public static void geometry() {
        BUILDS.incrementAndGet();
        stage = 1; stages = 6; cached = false; complete = false;
        begin("Building track geometry");
    }
    public static void plan(final boolean multiLap, final boolean informed) {
        stages = multiLap ? (informed ? 10 : 9) : 6;
        final Pass pass = CURRENT.get();
        pass.lastReport = 0;
        emit(pass, 0, 0);
    }
    public static void begin(final String phase, final int step) {
        // Safety sweeps run again over the different coherent multi-lap graph.
        stage = step == 5 && stage >= 6 ? 8 : step;
        if (step == 2) DISTANCES.incrementAndGet();
        begin(phase);
    }
    public static void reused() { cached = true; }
    public static void complete() {
        complete = true;
        stage = stages;
        begin("Track preparation complete");
    }
    /** Read-only diagnostics used by startup regressions (not game decisions). */
    public static int buildCount() { return BUILDS.get(); }
    public static int distanceCount() { return DISTANCES.get(); }
    public static int stageCount() { return stages; }
    public static void begin(final String phase) {
        final Pass pass = CURRENT.get();
        pass.phase = phase;
        pass.number = PASSES.incrementAndGet();
        pass.lastDone = -1;
        pass.lastReport = 0;
        emit(pass, 0, 0);
    }
    /** Actual scan index, NOT a prediction of total preparation time. */
    public static void scan(final int done, final int total) {
        final Pass pass = CURRENT.get();
        if (done < total && done - pass.lastDone < Math.max(1, total / 200)) return;
        emit(pass, done, total);
    }
    /** Searches do not know their final reachable-set size in advance. */
    public static void explored(final int count) { emit(CURRENT.get(), count, 0); }
    public static void searching() {
        final Pass pass = CURRENT.get();
        pass.phase += " — exploring paths";
        pass.lastReport = 0;
        emit(pass, 0, 0);
    }
    private static void emit(final Pass pass, final int done, final int total) {
        final long now = System.nanoTime();
        if (pass.lastReport != 0 && now - pass.lastReport < 100_000_000L && done != total) return;
        pass.lastReport = now;
        pass.lastDone = done;
        if (!nativeAvailable) return;
        try { report(pass.phase, done, total, pass.number, stage, stages, complete, cached); }
        catch (final UnsatisfiedLinkError unavailableOnDesktop) { nativeAvailable = false; }
    }
}
