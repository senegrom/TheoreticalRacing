package tr.gui;

import tr.logic.Player;
import tr.logic.RaceGame;

/** Browser presentation sink. No game decisions belong in this class. */
public final class GameUI {
    public String status = "";
    public boolean okEnabled = true, undoEnabled, directionsEnabled;
    public GameUI(final String title, final int maxPlayers) {}
    public void dispose() {}
    public Object getDialogParent() { return null; }
    public void repaint() {}
    public void centerGridAt(final int x, final int y) {}
    public void setDirectionsEnabled(final boolean enabled) { directionsEnabled = enabled; }
    public void setOkEnabled(final boolean enabled) { okEnabled = enabled; }
    public void setUndoEnabled(final boolean enabled) { undoEnabled = enabled; }
    public void setPlayerInfo(final String text, final int i) {}
    public void setStatus(final String text) { status = text; }
    public void setupUI(final Object grid, final RaceGame game, final int x, final int y, final Player[] players) {}
}
