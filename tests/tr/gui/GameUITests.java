package tr.gui;

import java.awt.Dimension;
import java.awt.Point;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JViewport;
import javax.swing.SwingUtilities;

/** Headless layout regressions for the main game window. */
public final class GameUITests {
    private GameUITests() {}

    public static void run() {
        final JPanel grid = new JPanel();
        grid.setPreferredSize(new Dimension(240, 160));
        final JScrollPane scroller = GameUI.createGridScroller(grid);
        scroller.setSize(640, 480);
        scroller.doLayout();
        final JViewport viewport = scroller.getViewport();
        viewport.doLayout();
        final JPanel centered = (JPanel) viewport.getView();
        centered.doLayout();

        check(scroller.getWidth() == 640 && scroller.getHeight() == 480,
                "race scroller lost its assigned extent");
        check(centered.getWidth() >= viewport.getExtentSize().width
                        && centered.getHeight() >= viewport.getExtentSize().height,
                "center wrapper did not fill the viewport");
        check(grid.getWidth() == 240 && grid.getHeight() == 160,
                "small race grid was resized unexpectedly");
        check(grid.getX() > 0 && grid.getY() > 0,
                "small race grid should be centered in the viewport");

        final JPanel largeGrid = new JPanel();
        largeGrid.setPreferredSize(new Dimension(2400, 2600));
        final JScrollPane largeScroller = GameUI.createGridScroller(largeGrid);
        largeScroller.setSize(640, 480);
        largeScroller.doLayout();
        largeScroller.getViewport().doLayout();
        final JPanel largeCentered = (JPanel) largeScroller.getViewport().getView();
        largeCentered.doLayout();
        check(largeGrid.getWidth() == 2400 && largeGrid.getHeight() == 2600,
                "large race grid lost its scrollable preferred size");
        check(largeScroller.getHorizontalScrollBar().isVisible()
                        && largeScroller.getVerticalScrollBar().isVisible(),
                "large race grid should expose both scroll bars");

        // Hungaroring's start is around grid cell (87,142): it used to open on
        // an entirely blank top-left viewport in a normal-sized game window.
        final int startX = 87 * RaceUI.GRID_DIST;
        final int startY = 142 * RaceUI.GRID_DIST;
        final Point target = SwingUtilities.convertPoint(largeGrid, startX, startY, largeCentered);
        GameUI.centerGridAt(largeScroller, largeGrid, startX, startY);
        final Point view = largeScroller.getViewport().getViewPosition();
        final Dimension extent = largeScroller.getViewport().getExtentSize();
        check(Math.abs(target.x - view.x - extent.width / 2) <= 1
                        && Math.abs(target.y - view.y - extent.height / 2) <= 1,
                "race viewport did not center the selected track start");
    }

    private static void check(final boolean condition, final String message) {
        if (!condition)
            throw new AssertionError(message);
    }
}
