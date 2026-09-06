package tr.browser;

import java.util.ArrayList;
import java.util.List;

/** Dialog transport, not a rules replacement. Crash consent is explicit and one-shot. */
public final class JOptionPane {
    public static final int YES_NO_OPTION = 0, YES_OPTION = 0, NO_OPTION = 1, OK_OPTION = 0;
    private static final List<String> MESSAGES = new ArrayList<>();
    private static boolean confirmed;
    private JOptionPane() {}
    public static void confirmCrash(final boolean value) { confirmed = value; }
    public static int showConfirmDialog(final Object parent, final String message,
            final String title, final int kind) {
        final boolean answer = confirmed;
        confirmed = false;
        return answer ? YES_OPTION : NO_OPTION;
    }
    public static void showMessageDialog(final Object parent, final String message,
            final String title, final int kind) { MESSAGES.add(message); }
    public static List<String> drain() {
        final List<String> result = new ArrayList<>(MESSAGES);
        MESSAGES.clear();
        return result;
    }
}
