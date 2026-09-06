package tr.browser;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/** Test-only observer: blocks at distance entry, never substitutes any game logic. */
public final class Progress {
    public static final CountDownLatch ENTERED = new CountDownLatch(1);
    public static final CountDownLatch RELEASE = new CountDownLatch(1);
    public static final AtomicInteger BUILDS = new AtomicInteger(), DISTANCES = new AtomicInteger(), FINISHES = new AtomicInteger();
    private Progress() {}
    public static void geometry() { BUILDS.incrementAndGet(); }
    public static void plan(final boolean multiLap) {}
    public static void begin(final String phase, final int stage) {
        if (stage == 4) FINISHES.incrementAndGet();
        if (stage != 2) return;
        DISTANCES.incrementAndGet();
        ENTERED.countDown();
        try {
            if (!RELEASE.await(20, TimeUnit.SECONDS)) throw new AssertionError("Distance job not released");
        } catch (final InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new AssertionError(ex);
        }
    }
    public static void begin(final String phase) {}
    public static void reused() {}
    public static void complete() {}
    public static void scan(final int done, final int total) {}
    public static void explored(final int count) {}
    public static void searching() {}
}
