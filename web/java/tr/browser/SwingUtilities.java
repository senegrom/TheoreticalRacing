package tr.browser;

import java.util.ArrayDeque;

/** Browser-controlled EDT: one queued callback per tick, never recursive AI play. */
public final class SwingUtilities {
    private static final ArrayDeque<Runnable> QUEUE = new ArrayDeque<>();
    private SwingUtilities() {}
    public static synchronized void invokeLater(final Runnable task) { QUEUE.addLast(task); }
    public static synchronized void clear() { QUEUE.clear(); }
    public static synchronized int pendingCount() { return QUEUE.size(); }
    public static boolean tick() {
        final Runnable task;
        synchronized (SwingUtilities.class) { task = QUEUE.pollFirst(); }
        if (task == null) return false;
        task.run();
        return true;
    }
}
