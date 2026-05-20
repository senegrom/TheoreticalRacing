package tr.gui;

import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import tr.logic.RaceGame;

/**
 * Forwards grid mouse-clicks to the game in grid-coord space.
 *
 * @author CGH
 */
public class GridListener extends MouseAdapter {

	private final RaceGame game;

	public GridListener(final RaceGame game) {
		this.game = game;
	}

	@Override
	public void mousePressed(final MouseEvent e) {
		final int x = (int) Math.round(e.getX() / (double) RaceUI.GRID_DIST);
		final int y = (int) Math.round(e.getY() / (double) RaceUI.GRID_DIST);
		game.clickedGrid(x, y);
	}
}
