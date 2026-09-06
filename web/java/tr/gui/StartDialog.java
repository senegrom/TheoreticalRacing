package tr.gui;

import java.util.Properties;

/** Configuration is collected by HTML before calling the original start path. */
public final class StartDialog {
    private Runnable confirm;
    public StartDialog(final String title, final Properties properties) {}
    public void setOnConfirm(final Runnable action) { confirm = action; }
    public void setOnCancel(final Runnable action) {}
    public void setOnSave(final Runnable action) {}
    public void setupUI() { confirm.run(); }
}
