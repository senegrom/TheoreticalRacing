package tr.gui;

import java.awt.Graphics;
import java.awt.Graphics2D;
import javax.swing.JPanel;

/**
 * The grid JPanel itself, invokes RaceUI's drawMe
 *
 * @author CGH
 */
public class Grid extends JPanel {
	private static final long	serialVersionUID	= 8231688287006820437L;

	public final int			rows, cols;
	private final RaceUI		rui;

	public Grid(final RaceUI rui, final int rows, final int cols) {
		this.rows = rows;
		this.cols = cols;
		this.rui = rui;
		setSize(cols * RaceUI.GRID_DIST, rows * RaceUI.GRID_DIST);
	}

	@Override
	protected void paintComponent(final Graphics g) {
		super.paintComponent(g);
		final Graphics2D g2 = (Graphics2D) g;
		rui.drawMe(g2);
	}
}
