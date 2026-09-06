package tr.browser;

import java.util.function.Consumer;

/** The sole core timer is a one-shot readiness poll; browser ticks supply pacing. */
public final class Timer {
    private final Consumer<Object> action;
    public Timer(final int delay, final Consumer<Object> action) { this.action = action; }
    public void setRepeats(final boolean repeats) {
        if (repeats) throw new IllegalArgumentException("Only one-shot core polls are supported");
    }
    public void start() { SwingUtilities.invokeLater(() -> action.accept(null)); }
}
