package tr.browser;

import java.util.concurrent.atomic.AtomicInteger;

/** Optional, read-only browser telemetry. No value feeds back into the engine. */
public final class Progress {
    private static final AtomicInteger PASSES = new AtomicInteger();
    private static final ThreadLocal<Pass> CURRENT = ThreadLocal.withInitial(Pass::new);
    private static volatile boolean nativeAvailable = true;
    private Progress() {}
    private static final class Pass {
        String phase = "Preparing track";
        int number, explored, lastDone = -1;
        long lastReport;
    }
    private static native void report(String phase, int done, int total, int pass);
    public static void begin(final String phase) {
        final Pass pass = CURRENT.get();
        pass.phase = phase;
        pass.number = PASSES.incrementAndGet();
        pass.explored = 0;
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
    public static void explored(final int count) {
        final Pass pass = CURRENT.get();
        pass.explored = count;
        emit(pass, count, 0);
    }
    public static void searching() {
        final Pass pass = CURRENT.get();
        pass.phase += " — exploring paths";
        pass.explored = 0;
        pass.lastReport = 0;
        emit(pass, 0, 0);
    }
    private static void emit(final Pass pass, final int done, final int total) {
        final long now = System.nanoTime();
        if (pass.lastReport != 0 && now - pass.lastReport < 100_000_000L && done != total) return;
        pass.lastReport = now;
        pass.lastDone = done;
        if (!nativeAvailable) return;
        try { report(pass.phase, done, total, pass.number); }
        catch (final UnsatisfiedLinkError unavailableOnDesktop) { nativeAvailable = false; }
    }
}
