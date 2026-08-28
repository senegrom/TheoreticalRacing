package tr.gui;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.GraphicsEnvironment;
import java.awt.Polygon;
import java.awt.RenderingHints;
import java.awt.Stroke;
import java.awt.Toolkit;
import java.util.Arrays;
import java.util.Iterator;
import java.util.List;
import javax.swing.JPanel;
import tr.logic.Player;
import tr.logic.Track;

/**
 * The race field: draws grid, track, start zone, finish line, players, and the
 * preview path.
 *
 * @author CGH
 */
public final class RaceUI {
	public final static int		CAR_SIZE			= 5;
	private final static Color	colBackgrd			= Color.WHITE;
	private final static Color	colBackgrdForb		= new Color(255, 245, 245);
	private final static Color	colCheckpoint		= new Color(205, 205, 205);
	private final static Color	colFinish			= Color.BLACK;
	private final static Color	colGrid				= Color.GRAY;
	private final static Color	colStartZFill		= new Color(220, 255, 220);
	private final static Color	colStartZOutline	= Color.BLACK;
	private final static Color	colTrack			= Color.BLACK;
	private final static Color	colTrackFill		= new Color(245, 255, 245);
	public final static int		GRID_DIST			= computeGridDistance();
	private final static Stroke	strkFinish			= new BasicStroke(3f, BasicStroke.CAP_BUTT, BasicStroke.JOIN_BEVEL, 1f,
			new float[]{3f, 3f }, 0f);
	private final static Stroke	strkPlayer			= new BasicStroke(2f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND, 1f, null, 0f);
	private final static Stroke	strkSglTrack		= new BasicStroke(4f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND, 1f, null, 0f);
	private final static Stroke	strkSimple			= new BasicStroke(1f);
	private final static Stroke	strkStartZ			= new BasicStroke(1f);
	private final static Stroke	strkTrack			= new BasicStroke(2f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND, 1f, null, 0f);
	private final static int	VELVEC_SIZE			= 3;

	private static int computeGridDistance() {
		return GraphicsEnvironment.isHeadless() ? 15
				: Math.max(15, 15 * Toolkit.getDefaultToolkit().getScreenResolution() / 96);
	}

	private int[]				finishLine;	// 4-element pixel coords [x1,y1,x2,y2]
	private int[][]				checkpoints;	// light-grey gate lines, same coords
	private final JPanel		grid;
	private final int			rows, cols;
	private Player[]			players;
	private List<int[]>		prePath;
	private Polygon				startZone;
	private Track				track;
	private Polygon				trackPol;
	private int[]				velVector;
	private int					velVectorPlayer	= -1;

	public RaceUI(final int rows, final int cols) {
		this.rows = rows;
		this.cols = cols;
		if (GraphicsEnvironment.isHeadless()) {
			grid = null;
		} else {
			grid = new JPanel() {
				private static final long serialVersionUID = 1L;

				@Override
				protected void paintComponent(final Graphics graphics) {
					super.paintComponent(graphics);
					drawMe((Graphics2D) graphics);
				}
			};
			grid.setBackground(colBackgrd);
			grid.setPreferredSize(new java.awt.Dimension(cols * GRID_DIST + 1, rows * GRID_DIST + 1));
		}
	}

	protected void drawMe(final Graphics2D g) {
		g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

		if (startZone != null) {
			g.setColor(colStartZFill);
			g.setStroke(strkSimple);
			g.fill(startZone);
		}
		if (trackPol != null) {
			g.setColor(colTrackFill);
			g.setStroke(strkSimple);
			g.fill(trackPol);
		}

		// grid
		g.setColor(colGrid);
		g.setStroke(strkSimple);
		for (int i = 0; i <= cols * GRID_DIST; i += GRID_DIST)
			g.drawLine(i, 0, i, rows * GRID_DIST);
		for (int i = 0; i <= rows * GRID_DIST; i += GRID_DIST)
			g.drawLine(0, i, cols * GRID_DIST, i);

		if (startZone != null) {
			g.setColor(colStartZOutline);
			g.setStroke(strkStartZ);
			g.draw(startZone);
		}
		if (checkpoints != null) {
			g.setColor(colCheckpoint);
			g.setStroke(strkFinish);
			for (final int[] cp : checkpoints)
				g.drawLine(cp[0], cp[1], cp[2], cp[3]);
		}
		if (finishLine != null) {
			g.setColor(colFinish);
			g.setStroke(strkFinish);
			g.drawLine(finishLine[0], finishLine[1], finishLine[2], finishLine[3]);
		}

		if (track != null) {
			g.setColor(colTrack);
			drawTrackSide(g, track.getLeft());
			drawTrackSide(g, track.getRight());
		}

		drawPlayers(g);
	}

	private void drawTrackSide(final Graphics2D g, final List<int[]> side) {
		if (side.size() > 1) {
			g.setStroke(strkTrack);
			final Iterator<int[]> iterator = side.iterator();
			int[] previous = iterator.next();
			while (iterator.hasNext()) {
				final int[] point = iterator.next();
				g.drawLine(previous[0] * GRID_DIST, previous[1] * GRID_DIST, point[0] * GRID_DIST, point[1] * GRID_DIST);
				previous = point;
			}
		} else if (side.size() == 1) {
			g.setStroke(strkSglTrack);
			final int[] p = side.getFirst();
			g.drawLine(p[0] * GRID_DIST, p[1] * GRID_DIST, p[0] * GRID_DIST, p[1] * GRID_DIST);
		}
	}

	private void drawPlayers(final Graphics2D g) {
		if (players == null)
			return;
		g.setStroke(strkPlayer);
		for (int i = 0; i < players.length; i++) {
			final Player pl = players[i];
			g.setColor(pl.getColor());
			for (int j = Math.max(1, pl.getTraceStart() + 1); j < pl.getHistory().size(); j++) {
				final int[] oldP = pl.getHistory().get(j - 1);
				final int[] pos = pl.getHistory().get(j);
				g.drawLine(oldP[0] * GRID_DIST, oldP[1] * GRID_DIST, pos[0] * GRID_DIST, pos[1] * GRID_DIST);
			}
			final int[] pos = pl.getPosition();
			if (velVector != null && velVectorPlayer == i) {
				g.setColor(pl.getBrightColor());
				if (!Arrays.equals(pos, velVector))
					g.fillRect(velVector[0] * GRID_DIST - VELVEC_SIZE, velVector[1] * GRID_DIST - VELVEC_SIZE, VELVEC_SIZE * 2,
							VELVEC_SIZE * 2);
				g.drawRect((velVector[0] - 1) * GRID_DIST, (velVector[1] - 1) * GRID_DIST, GRID_DIST * 2, GRID_DIST * 2);
			}
			if (prePath != null && velVectorPlayer == i && !prePath.isEmpty()) {
				g.setColor(pl.getBrightColor());
				int[] oldP = pos;
				for (final int[] newP : prePath) {
					g.drawLine(oldP[0] * GRID_DIST, oldP[1] * GRID_DIST, newP[0] * GRID_DIST, newP[1] * GRID_DIST);
					oldP = newP;
				}
			}
			g.setColor(pl.getColor());
			g.fillOval(pos[0] * GRID_DIST - CAR_SIZE, pos[1] * GRID_DIST - CAR_SIZE, 2 * CAR_SIZE, 2 * CAR_SIZE);
		}
	}

	public void finishTrack() {
		if (grid == null || track == null)
			return;
		final int[][] tTrack = new int[2][track.getLeft().size() + track.getRight().size()];
		int i = 0;
		for (final int[] pos : track.getLeft()) {
			tTrack[0][i] = pos[0] * GRID_DIST;
			tTrack[1][i] = pos[1] * GRID_DIST;
			i++;
		}
		for (final int[] pos : track.getRight().reversed()) {
			tTrack[0][i] = pos[0] * GRID_DIST;
			tTrack[1][i] = pos[1] * GRID_DIST;
			i++;
		}
		trackPol = new Polygon(tTrack[0], tTrack[1], tTrack[0].length);
		grid.setBackground(colBackgrdForb);
	}

	public JPanel getGrid() {
		if (grid == null)
			throw new IllegalStateException("grid is unavailable in headless mode");
		return grid;
	}

	/** Multi-lap checkpoint lines in grid coords (x1,y1,x2,y2), or null. */
	public void setCheckpoints(final int[][] cps) {
		if (cps == null) {
			checkpoints = null;
			return;
		}
		checkpoints = new int[cps.length][];
		for (int i = 0; i < cps.length; i++)
			checkpoints[i] = new int[]{cps[i][0] * GRID_DIST, cps[i][1] * GRID_DIST,
					cps[i][2] * GRID_DIST, cps[i][3] * GRID_DIST };
	}

	public void setFinishLine(final int[] pL, final int[] pR) {
		if (grid == null || pL == null || pR == null)
			return;
		finishLine = new int[]{pL[0] * GRID_DIST, pL[1] * GRID_DIST, pR[0] * GRID_DIST, pR[1] * GRID_DIST };
	}

	public void setPlayers(final Player[] players) {
		if (grid != null)
			this.players = players;
	}

	public void setPrePath(final List<int[]> prePath) {
		if (grid != null)
			this.prePath = prePath;
	}

	public void setStartZone(final float[][] startZone) {
		if (grid == null || startZone == null || startZone.length != 2 || startZone[0] == null)
			return;
		final int[][] tStartZone = new int[2][startZone[0].length];
		for (int j = 0; j < startZone[0].length; j++) {
			tStartZone[0][j] = Math.round(startZone[0][j] * GRID_DIST);
			tStartZone[1][j] = Math.round(startZone[1][j] * GRID_DIST);
		}
		this.startZone = new Polygon(tStartZone[0], tStartZone[1], 4);
	}

	public void setTrack(final Track track) {
		if (grid != null)
			this.track = track;
	}

	public void setVelVector(final int[] velVector, final int player) {
		if (grid == null)
			return;
		this.velVector = velVector;
		this.velVectorPlayer = player;
	}
}
