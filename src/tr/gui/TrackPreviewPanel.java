package tr.gui;

import java.awt.Color;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.geom.Path2D;
import java.util.Iterator;
import java.util.LinkedList;
import javax.swing.JPanel;

/**
 * Small panel that renders a track outline for the StartDialog chooser.
 *
 * @author CGH
 */
public class TrackPreviewPanel extends JPanel {
	private static final long	serialVersionUID	= 1L;

	private int					gameX, gameY;
	private LinkedList<int[]>	trackLeft, trackRight;
	private String				caption;

	public TrackPreviewPanel() {
		setBackground(Color.WHITE);
	}

	public void setTrack(final int gx, final int gy, final LinkedList<int[]> left, final LinkedList<int[]> right, final String caption) {
		this.gameX = gx;
		this.gameY = gy;
		this.trackLeft = left;
		this.trackRight = right;
		this.caption = caption;
		repaint();
	}

	public void clearTrack(final String caption) {
		this.trackLeft = null;
		this.trackRight = null;
		this.caption = caption;
		repaint();
	}

	@Override
	protected void paintComponent(final Graphics g) {
		super.paintComponent(g);
		final Graphics2D g2 = (Graphics2D) g.create();
		try {
			g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
			final int w = getWidth();
			final int h = getHeight();

			if (trackLeft == null || trackRight == null || trackLeft.isEmpty() || trackRight.isEmpty()) {
				g2.setColor(Color.GRAY);
				final String msg = caption == null ? "" : caption;
				final int sw = g2.getFontMetrics().stringWidth(msg);
				g2.drawString(msg, (w - sw) / 2, h / 2);
				return;
			}

			final double margin = 6;
			final double scale = Math.min((w - 2 * margin) / Math.max(1.0, gameX), (h - 2 * margin) / Math.max(1.0, gameY));
			final double ox = (w - gameX * scale) / 2.0;
			final double oy = (h - gameY * scale) / 2.0;

			final Path2D.Double corridor = new Path2D.Double();
			int[] first = trackLeft.getFirst();
			corridor.moveTo(ox + first[0] * scale, oy + first[1] * scale);
			for (final int[] p : trackLeft)
				corridor.lineTo(ox + p[0] * scale, oy + p[1] * scale);
			final Iterator<int[]> it = trackRight.descendingIterator();
			while (it.hasNext()) {
				final int[] p = it.next();
				corridor.lineTo(ox + p[0] * scale, oy + p[1] * scale);
			}
			corridor.closePath();
			g2.setColor(new Color(232, 232, 232));
			g2.fill(corridor);

			g2.setColor(new Color(80, 80, 80));
			drawPolyline(g2, trackLeft, scale, ox, oy);
			drawPolyline(g2, trackRight, scale, ox, oy);

			final int[] sL = trackLeft.getFirst(), sR = trackRight.getFirst();
			g2.setColor(new Color(0, 160, 0));
			g2.drawLine((int) (ox + sL[0] * scale), (int) (oy + sL[1] * scale), (int) (ox + sR[0] * scale), (int) (oy + sR[1] * scale));

			final int[] fL = trackLeft.getLast(), fR = trackRight.getLast();
			g2.setColor(new Color(200, 0, 0));
			g2.drawLine((int) (ox + fL[0] * scale), (int) (oy + fL[1] * scale), (int) (ox + fR[0] * scale), (int) (oy + fR[1] * scale));

			if (caption != null && !caption.isEmpty()) {
				g2.setColor(new Color(60, 60, 60));
				g2.drawString(caption, 6, h - 6);
			}
		} finally {
			g2.dispose();
		}
	}

	private static void drawPolyline(final Graphics2D g, final LinkedList<int[]> path, final double scale, final double ox, final double oy) {
		int[] prev = null;
		for (final int[] p : path) {
			if (prev != null)
				g.drawLine((int) (ox + prev[0] * scale), (int) (oy + prev[1] * scale), (int) (ox + p[0] * scale), (int) (oy + p[1] * scale));
			prev = p;
		}
	}
}
