package tr.browser;

import java.util.concurrent.atomic.AtomicInteger;

/** Output-only telemetry. Stage counts describe dependencies, never estimated time. */
public final class Progress {
    private static final AtomicInteger PASSES = new AtomicInteger();
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
        stage = 1; stages = 6; cached = false; complete = false;
        begin("Building track geometry");
    }
    /** exact: the daemon builds the exact race map too (any lap race an AI
     *  drives); with informed starts it always does. */
    public static void plan(final boolean multiLap, final boolean informed, final boolean exact) {
        stages = multiLap ? (informed ? 11 : exact ? 10 : 9) : (informed ? 7 : 6);
        final Pass pass = CURRENT.get();
        pass.lastReport = 0;
        emit(pass, 0, 0);
    }
    public static void begin(final String phase, final int step) {
        // With computed starts the exact race map builds BESIDE the reachability
        // maps; its stage must not mark their unfinished stages complete. It
        // shows as activity until those reach lap driving (review, 2026-09-28).
        if (step == 9 && stage < 8) {
            begin(phase);
            return;
        }
        // Safety sweeps run again over the different coherent multi-lap graph.
        stage = step == 5 && stage >= 6 ? 8 : step;
        begin(phase);
    }
    /** The checklist position last reported. */
    public static int stage() { return stage; }
    public static void alternatives() {
        stage = stages - 1;
        begin("Analysing starting alternatives for all AIs");
    }
    public static void reused() { cached = true; }
    public static void complete() {
        complete = true;
        stage = stages;
        begin("Track preparation complete");
    }
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
