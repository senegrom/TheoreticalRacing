package tr.gui;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.Polygon;
import java.awt.RenderingHints;
import java.awt.Stroke;
import java.util.Arrays;
import java.util.Iterator;
import java.util.LinkedList;
import tr.logic.Player;
import tr.logic.Track;

/**
 * The race field responsible for drawing grid, tracks, players, and player
 * tracks
 *
 * @author CGH
 */
public class RaceUI {
	public final static int		CAR_SIZE			= 5;
	private final static Color	colBackgrd			= Color.WHITE;
	private final static Color	colBackgrdForb		= new Color(255, 245, 245);
	private final static Color	colFinish			= Color.BLACK;
	private final static Color	colGrid				= Color.GRAY;
	private final static Color	colStartZFill		= new Color(220, 255, 220);
	private final static Color	colStartZOutline	= Color.BLACK;
	private final static Color	colTrack			= Color.BLACK;
	private final static Color	colTrackFill		= new Color(245, 255, 245);
	public final static int		GRID_DIST			= 15;
	private final static Stroke	strkFinish			= new BasicStroke(3f, BasicStroke.CAP_BUTT, BasicStroke.JOIN_BEVEL, 1f,
			new float[]{3f, 3f }, 0f);
	private final static Stroke	strkPlayer			= new BasicStroke(2f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND, 1f, null, 0f);
	private final static Stroke	strkSglTrack		= new BasicStroke(4f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND, 1f, null, 0f);
	private final static Stroke	strkSimple			= new BasicStroke(1f);
	private final static Stroke	strkStartZ			= new BasicStroke(1f);
	private final static Stroke	strkTrack			= new BasicStroke(2f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND, 1f, null, 0f);
	private final static int	VELVEC_SIZE			= 3;

	private int[]				finishLine;
	private final Grid			grid;
	private Iterator<int[]>		it;
	private Player[]			players;
	private LinkedList<int[]>	prePath;
	private Polygon				startZone;
	private Track				track;
	private Polygon				trackPol;
	private int[]				velVector;
	private int					velVectorPlayer;

	public RaceUI(final int rows, final int cols) {
		grid = new Grid(this, rows, cols);
		track = null;
		grid.setBackground(colBackgrd);
		startZone = null;
		trackPol = null;
		finishLine = null;
		players = null;
		velVectorPlayer = -1;
		velVector = null;
		prePath = null;
	}

	protected void drawMe(final Graphics2D g) {
		int i;
		int[] pos;

		// init
		g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

		// startzone fill
		if (startZone != null) {
			g.setColor(colStartZFill);
			g.setStroke(strkSimple);
			g.fill(startZone);
		}

		// track fill
		if (trackPol != null) {
			g.setColor(colTrackFill);
			g.setStroke(strkSimple);
			g.fill(trackPol);
		}

		// grid
		g.setColor(colGrid);
		g.setStroke(strkSimple);
		for (i = 0; i <= grid.cols * GRID_DIST; i += GRID_DIST)
			g.drawLine(i, 0, i, grid.rows * GRID_DIST);
		for (i = 0; i <= grid.rows * GRID_DIST; i += GRID_DIST)
			g.drawLine(0, i, grid.cols * GRID_DIST, i);

		// startzone line
		if (startZone != null) {
			g.setColor(colStartZOutline);
			g.setStroke(strkStartZ);
			g.draw(startZone);
		}

		// finish line
		if (finishLine != null) {
			g.setColor(colFinish);
			g.setStroke(strkFinish);
			g.drawLine(finishLine[0], finishLine[1], finishLine[2], finishLine[3]);
		}

		// track
		if (track != null) {
			g.setColor(colTrack);
			if (track.getLeft().size() > 1) {
				g.setStroke(strkTrack);
				it = track.getLeft().iterator();
				int[] oldC = it.next();
				while (it.hasNext()) {
					final int newC[] = it.next();
					g.drawLine(oldC[0] * GRID_DIST, oldC[1] * GRID_DIST, newC[0] * GRID_DIST, newC[1] * GRID_DIST);
					oldC = newC;
				}
			} else if (track.getLeft().size() == 1) {
				g.setStroke(strkSglTrack);
				final int[] p = track.getLeft().getFirst();
				g.drawLine(p[0] * GRID_DIST, p[1] * GRID_DIST, p[0] * GRID_DIST, p[1] * GRID_DIST);
			}
			if (track.getRight().size() > 1) {
				g.setStroke(strkTrack);
				it = track.getRight().iterator();
				int[] oldC = it.next();
				while (it.hasNext()) {
					final int newC[] = it.next();
					g.drawLine(oldC[0] * GRID_DIST, oldC[1] * GRID_DIST, newC[0] * GRID_DIST, newC[1] * GRID_DIST);
					oldC = newC;
				}
			} else if (track.getRight().size() == 1) {
				final int[] p = track.getRight().getFirst();
				g.setStroke(strkSglTrack);
				g.drawLine(p[0] * GRID_DIST, p[1] * GRID_DIST, p[0] * GRID_DIST, p[1] * GRID_DIST);
			}
		}

		// cars
		g.setStroke(strkPlayer);
		if (players != null) {
			int[] oldP, newP;
			Iterator<int[]> it;
			for (i = 0; i < players.length; i++) {
				g.setColor(players[i].getColor());
				if (players[i].getHistory() != null && players[i].getHistory().size() > 1) {
					it = players[i].getHistory().iterator();
					oldP = it.next();
					while (it.hasNext()) {
						pos = it.next();
						g.drawLine(oldP[0] * GRID_DIST, oldP[1] * GRID_DIST, pos[0] * GRID_DIST, pos[1] * GRID_DIST);
						oldP = pos;
					}
				}
				pos = players[i].getPosition();
				if (velVector != null && velVectorPlayer == i) {
					g.setColor(players[i].getBrightColor());
					if (!Arrays.equals(pos, velVector))
						g.fillRect(velVector[0] * GRID_DIST - VELVEC_SIZE, velVector[1] * GRID_DIST - VELVEC_SIZE, VELVEC_SIZE * 2,
								VELVEC_SIZE * 2);
					g.drawRect((velVector[0] - 1) * GRID_DIST, (velVector[1] - 1) * GRID_DIST, GRID_DIST * 2, GRID_DIST * 2);
				}
				if (prePath != null && velVectorPlayer == i && prePath.size() > 0) {
					g.setColor(players[i].getBrightColor());
					oldP = pos;
					it = prePath.iterator();
					while (it.hasNext()) {
						newP = it.next();
						g.drawLine(oldP[0] * GRID_DIST, oldP[1] * GRID_DIST, newP[0] * GRID_DIST, newP[1] * GRID_DIST);
						oldP = newP;
					}
				}
				g.setColor(players[i].getColor());
				g.fillOval(pos[0] * GRID_DIST - CAR_SIZE, pos[1] * GRID_DIST - CAR_SIZE, 2 * CAR_SIZE, 2 * CAR_SIZE);
			}
		}
	}

	public void finishTrack() {
		if (track == null || track.getLeft() == null || track.getRight() == null)
			return;
		final int[][] tTrack = new int[2][track.getLeft().size() + track.getRight().size()];
		int i = 0;
		int[] pos;
		it = track.getLeft().iterator();
		while (it.hasNext()) {
			pos = it.next();
			tTrack[0][i] = pos[0] * GRID_DIST;
			tTrack[1][i] = pos[1] * GRID_DIST;
			i++;
		}
		it = track.getRight().descendingIterator();
		while (it.hasNext()) {
			pos = it.next();
			tTrack[0][i] = pos[0] * GRID_DIST;
			tTrack[1][i] = pos[1] * GRID_DIST;
			i++;
		}
		trackPol = new Polygon(tTrack[0], tTrack[1], tTrack[0].length);
		grid.setBackground(colBackgrdForb);
	}

	public Grid getGrid() {
		return grid;
	}

	public void setFinishLine(final int[] finishLine) {
		if (finishLine == null)
			return;
		this.finishLine = new int[finishLine.length];
		for (int i = 0; i < finishLine.length; i++)
			this.finishLine[i] = finishLine[i] * GRID_DIST;
	}

	public void setPlayers(final Player[] players) {
		this.players = players;
	}

	public void setPrePath(final LinkedList<int[]> prePath) {
		this.prePath = prePath;
	}

	public void setStartZone(final float[][] startZone) {
		if (startZone == null || startZone.length != 2 || startZone[0] == null)
			return;
		final int[][] tStartZone = new int[startZone.length][startZone[0].length];
		for (int j = 0; j < startZone[0].length; j++) {
			tStartZone[0][j] = Math.round(startZone[0][j] * GRID_DIST);
			tStartZone[1][j] = Math.round(startZone[1][j] * GRID_DIST);
		}
		this.startZone = new Polygon(tStartZone[0], tStartZone[1], 4);
	}

	public void setTrack(final Track track) {
		if (track == null || track.getLeft() == null || track.getRight() == null)
			return;
		this.track = track;
	}

	public void setVelVector(final int[] velVector, final int player) {
		this.velVector = velVector;
		velVectorPlayer = player;
	}
}
