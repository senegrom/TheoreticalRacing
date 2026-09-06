package tr.browser;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/** Test-only observer: pause distance AND exact-potential work independently. */
public final class Progress {
    public static final CountDownLatch ENTERED = new CountDownLatch(1), RELEASE = new CountDownLatch(1);
    public static final CountDownLatch OPTIMAL_ENTERED = new CountDownLatch(1), OPTIMAL_RELEASE = new CountDownLatch(1);
    public static final AtomicInteger BUILDS = new AtomicInteger(), DISTANCES = new AtomicInteger(), FINISHES = new AtomicInteger(), OPTIMAL = new AtomicInteger();
    private Progress() {}
    public static void geometry() { BUILDS.incrementAndGet(); }
    public static void plan(final boolean multiLap, final boolean informed) {}
    public static void begin(final String phase, final int stage) {
        if (stage == 4) FINISHES.incrementAndGet();
        if (stage == 2) { DISTANCES.incrementAndGet(); block(ENTERED, RELEASE); }
        if (stage == 9) { OPTIMAL.incrementAndGet(); block(OPTIMAL_ENTERED, OPTIMAL_RELEASE); }
    }
    private static void block(final CountDownLatch entered, final CountDownLatch release) {
        entered.countDown();
        try {
            if (!release.await(30, TimeUnit.SECONDS)) throw new AssertionError("Preparation observer not released");
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
