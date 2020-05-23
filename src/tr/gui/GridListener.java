package tr.gui;

import java.awt.event.MouseEvent;
import java.awt.event.MouseListener;
import tr.logic.RaceGame;

/**
 * Listener for the game grid (to place start positions)
 *
 * @author CGH
 */
public class GridListener implements MouseListener {

	private final RaceGame	game;

	public GridListener(final RaceGame game) {
		super();
		this.game = game;
	}

	@Override
	public void mouseClicked(final MouseEvent arg0) {}

	@Override
	public void mouseEntered(final MouseEvent arg0) {}

	@Override
	public void mouseExited(final MouseEvent arg0) {}

	@Override
	public void mousePressed(final MouseEvent arg0) {
		double x = arg0.getX();
		double y = arg0.getY();
		x = x / RaceUI.GRID_DIST;
		y = y / RaceUI.GRID_DIST;

		game.clickedGrid((int) Math.round(x), (int) Math.round(y));
	}

	@Override
	public void mouseReleased(final MouseEvent arg0) {}

}
