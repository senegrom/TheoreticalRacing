package tr.logic;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Shape;
import java.awt.geom.Area;
import java.awt.geom.Path2D;
import java.io.File;
import java.io.FileOutputStream;
import java.util.Arrays;
import java.util.Hashtable;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.Properties;
import java.util.Scanner;
import javax.swing.JButton;
import javax.swing.JOptionPane;
import tr.gui.GameUI;
import tr.gui.RaceUI;
import tr.gui.StartDialog;
import tr.main.Main;

/**
 * Main game logic component of TheoreticRacing
 *
 * @version 0.2.0
 * @author CGH
 */
public class RaceGame {
	public final static String			AUTHOR				= "CGH";
	private final static int			checkIntervalSplit	= 100;
	private final static int			defCols				= 50;
	private final static Color[]		defPlayerColors		= new Color[]{Color.BLUE, Color.RED, Color.GREEN, Color.YELLOW, Color.CYAN,
			Color.ORANGE, Color.GRAY, Color.MAGENTA, Color.BLACK };
	public final static String			defProperties		= "default.properties";
	private final static int			defRows				= 50;
	private final static int			defWindowX			= 1600;
	private final static int			defWindowY			= 900;
	public final static String			NAME				= "Theoretical Racing";
	private final static float			startZoneWidth		= 2f;
	private final static BasicStroke	strkTolerance		= new BasicStroke(.01f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND);
	public final static String			userProperties		= "user.properties";
	public final static String			VERSION				= "0.2.0";

	/**
	 * Add element to track
	 *
	 * @param track
	 * @param x
	 * @param y
	 * @param isLeft
	 */
	private final static void addToTrack(final Track track, final int x, final int y, final boolean isLeft) {
		if (isLeft)
			track.addLeft(x, y);
		else
			track.addRight(x, y);
	}

	/**
	 * @param p11
	 * @param p12
	 * @param p21
	 * @param p22
	 * @param seq
	 *            0: all endpoints checked, 1: p11=p22 allowed, 2: p12=21
	 *            allowed, 3: == always allowed
	 * @return true iff the lines (p11,p12) and (p21,p22) intersect
	 */
	private final static boolean checkIntersect(final int[] p11, final int[] p12, final int[] p21, final int[] p22, final byte seq) {
		if (seq != 3 && (Arrays.equals(p11, p12) || Arrays.equals(p11, p21) || Arrays.equals(p12, p22) || Arrays.equals(p21, p22)))
			return true;
		if (seq != 1 && seq != 3 && Arrays.equals(p11, p22))
			return true;
		if (seq != 2 && seq != 3 && Arrays.equals(p12, p21))
			return true;

		final double x1 = p11[0];
		final double y1 = p11[1];
		final double x2 = p21[0];
		final double y2 = p21[1];
		final double dx1 = p12[0] - p11[0];
		final double dy1 = p12[1] - p11[1];
		final double dx2 = p22[0] - p21[0];
		final double dy2 = p22[1] - p21[1];
		final double d = dx2 * dy1 - dx1 * dy2;
		if (d == 0 && seq != 0 && seq != 3) {
			if (Math.signum(dx1) != Math.signum(dx2) || Math.signum(dy1) != Math.signum(dy2))
				return true;
		} else if (seq == 0 || seq == 3) {
			final double s = (dy1 * x1 - dy1 * x2 - dx1 * y1 + dx1 * y2) / d;
			final double t = (dy2 * x1 - dy2 * x2 - dx2 * y1 + dx2 * y2) / d;
			if (s > 0 && s < 1 && t > 0 && t < 1)
				return true;
			if (seq == 0 && (s == 0 || s == 1) && (t == 0 || t == 1))
				return true;
		}
		return false;
	}

	/**
	 * @param p1
	 * @param p2
	 * @return true iff the line paths p1, p2 intersect anywhere
	 */
	private final static boolean checkIntersect(final LinkedList<int[]> p1, final LinkedList<int[]> p2, final boolean allowEqual) {
		if (p1 == null || p2 == null || p1.size() < 2 || p2.size() < 2)
			return false;
		if (p1.size() == 2 && Arrays.equals(p1.getFirst(), p1.getLast()))
			return true;
		if (p2.size() == 2 && Arrays.equals(p2.getFirst(), p2.getLast()))
			return true;
		Iterator<int[]> it1, it2;
		it1 = p1.iterator();
		int[] p11, p12, p21, p22;
		p11 = null;
		p12 = null;
		while (it1.hasNext()) {
			p12 = it1.next();
			if (p11 != null) {
				it2 = p2.iterator();
				p21 = null;
				p22 = null;
				while (it2.hasNext()) {
					p22 = it2.next();
					if (p21 != null)
						// not using equals but == to check if its the same
						// point in the same path
						if (p11 != p21 || p12 != p22) {
							byte seq;
							if (allowEqual)
								seq = 3;
							else if (p11 == p22)
								seq = 1;
							else if (p12 == p21)
								seq = 2;
							else
								seq = 0;
							if (checkIntersect(p11, p12, p21, p22, seq))
								return true;
						}
					p21 = p22;
				}
			}
			p11 = p12;
		}
		return false;
	}

	/**
	 * @param s
	 * @return Expand Area s by strkTolerance
	 */
	private final static Area getToleranceExpandedShape(final Shape s) {
		final Area a = new Area(strkTolerance.createStrokedShape(s));
		a.add(new Area(s));
		return a;
	}

	private final static int[] makeFinishLine(final int[] pL, final int[] pR) {
		return new int[]{pL[0], pL[1], pR[0], pR[1] };
	}

	/**
	 * @param pL
	 * @param pR
	 * @return coordinates of the 4 vertices of the start zone
	 *         {{x1,x2,x3,x4},{y1,y2,y3,y4}}
	 */
	private final static float[][] makeStartZone(final int[] pL, final int[] pR) {
		final float len = (float) Math.sqrt((pR[0] - pL[0]) * (pR[0] - pL[0]) + (pR[1] - pL[1]) * (pR[1] - pL[1]));
		final float dirX = (pL[1] - pR[1]) * startZoneWidth / len;
		final float dirY = (pR[0] - pL[0]) * startZoneWidth / len;
		return new float[][]{{pL[0], pR[0], pR[0] + dirX, pL[0] + dirX }, {pL[1], pR[1], pR[1] + dirY, pL[1] + dirY } };
	}

	/**
	 * @param left
	 * @param right
	 * @return Polygon or path stored as Path2D.Float from input line paths
	 */
	private final static Path2D.Float newPrefilledPath(final LinkedList<int[]> left, final LinkedList<int[]> right) {
		if (left == null || left.size() == 0)
			return null;
		final Path2D.Float p = new Path2D.Float();
		int[] pos = left.getFirst();
		p.moveTo(pos[0], pos[1]);
		Iterator<int[]> it = left.iterator();
		while (it.hasNext()) {
			pos = it.next();
			p.lineTo(pos[0], pos[1]);
		}
		if (right == null || right.size() == 0)
			return p;
		it = right.descendingIterator();
		while (it.hasNext()) {
			pos = it.next();
			p.lineTo(pos[0], pos[1]);
		}
		p.closePath();
		return p;
	}

	/**
	 * Remove last element from track
	 *
	 * @param track
	 * @param isLeft
	 */
	private final static void undoFromTrack(final Track track, final boolean isLeft) {
		if (track == null)
			return;
		if (isLeft)
			track.removeLastLeft();
		else
			track.removeLastRight();
	}

	private int					finishedLast, finishedFirst;
	private int[]				finishLine;
	private final GameUI		gameFrame;
	private GameState			gamestate;
	private int					isShowingPrePath;
	private final int			maxPlayers;
	private int[]				oldVel;
	private Player[]			players;
	private final Properties	prop;
	private RaceUI				rui;
	private float[][]			startZone;
	private Area				startZoneA;
	private int					subgamestate;
	private Track				track;
	private Area				trackA;

	/**
	 * Create new RaceGame. (Start it afterwards)
	 */
	public RaceGame(final Properties prop) {
		int temp;
		this.prop = prop;
		gamestate = GameState.SETUP;

		try {
			temp = Integer.valueOf(prop.getProperty("maxPlayers"));
		} catch (final Exception e) {
			temp = 9;
		}
		maxPlayers = temp;
		prop.put("maxPlayers", String.valueOf(maxPlayers));
		track = null;
		finishLine = null;

		try {
			temp = Integer.valueOf(prop.getProperty("nPlayers"));
		} catch (final Exception e) {
			temp = 2;
		}
		prop.put("nPlayers", String.valueOf(temp));
		for (int i = 0; i < maxPlayers; i++) {
			String sTemp;
			try {
				sTemp = prop.getProperty("player" + (i + 1) + "Name");
			} catch (final Exception e) {
				sTemp = "Player " + (i + 1);
			}
			if (sTemp == null)
				sTemp = "Player " + (i + 1);
			prop.put("player" + (i + 1) + "Name", sTemp);
		}
		for (int i = 0; i < maxPlayers; i++) {
			final Scanner sc;
			Color cTemp;
			try {
				sc = new Scanner(prop.getProperty("player" + (i + 1) + "Color"));
				cTemp = new Color(sc.nextInt(), sc.nextInt(), sc.nextInt());
				sc.close();
			} catch (final Exception e) {
				cTemp = defPlayerColors[i];
			}
			if (cTemp == null)
				cTemp = defPlayerColors[i];
			prop.put("player" + (i + 1) + "Color", cTemp.getRed() + " " + cTemp.getGreen() + " " + cTemp.getBlue());
		}

		gameFrame = new GameUI(NAME + " " + VERSION, maxPlayers);
		gamestate = GameState.PRESTART;
		subgamestate = 0;
		finishedLast = 0;
		finishedFirst = 0;
		isShowingPrePath = -1;
	}

	private boolean checkFinished() {
		if (finishedLast + finishedFirst >= players.length - (players.length == 1 ? 0 : 1)) {
			gamestate = GameState.FINISHED;
			rui.setVelVector(null, -1);
			rui.setPrePath(null);

			final Hashtable<Integer, String> place = new Hashtable<Integer, String>();
			for (final Player p : players) {
				if (p.getFinishedPlace() == 0)
					p.setFinishedPlace(finishedFirst + 1);
				place.put(p.getFinishedPlace(), p.getName());
			}
			String s = "The game has finished.\n";
			for (int i = 1; i <= players.length; i++)
				s += "\n" + i + ".   " + place.get(i);
			gameFrame.setStatus("The game has finished");
			gameFrame.repaint();
			dispMessage(s);
			gameFrame.getBtnUndo().setEnabled(false);
			for (final JButton b : gameFrame.getBtnDirections())
				b.setEnabled(false);
			gameFrame.repaint();
			return true;
		}
		return false;
	}

	/**
	 * Gets activated when one of the direction buttons is clicked.
	 *
	 * @param direction
	 *            0..8 stands for NW N NE W 0 E SW S SE
	 */
	public void clickedDirection(final int direction) {
		if (gamestate == GameState.PLAY) {
			int[] vel = players[subgamestate].getVelocity();
			int[] newpos;
			oldVel = vel;
			{
				int dvx = 0;
				int dvy = 0;
				if (direction == 0 || direction == 3 || direction == 6)
					dvx = -1;
				else if (direction == 2 || direction == 5 || direction == 8)
					dvx = 1;
				if (direction == 0 || direction == 1 || direction == 2)
					dvy = -1;
				else if (direction == 6 || direction == 7 || direction == 8)
					dvy = 1;
				vel = new int[]{vel[0] + dvx, vel[1] + dvy };
			}
			int[] pos = players[subgamestate].getPosition();
			newpos = new int[]{pos[0] + vel[0], pos[1] + vel[1] };
			if (isShowingPrePath != direction) {
				isShowingPrePath = direction;
				int vx = vel[0];
				int vy = vel[1];
				int px = pos[0];
				int py = pos[1];
				if (vx == 0 && vy == 0)
					return;
				final LinkedList<int[]> prePath = new LinkedList<int[]>();
				while (vx != 0 || vy != 0) {
					px = px + vx;
					py = py + vy;
					prePath.add(new int[]{px, py });
					if (vx > 0)
						vx--;
					else if (vx < 0)
						vx++;
					if (vy > 0)
						vy--;
					else if (vy < 0)
						vy++;
				}
				rui.setPrePath(prePath);
				gameFrame.repaint();
			} else {
				final LinkedList<int[]> move = new LinkedList<int[]>();
				move.add(pos);
				move.add(newpos);
				final double dx = ((double) (newpos[0] - pos[0])) / (checkIntervalSplit);
				final double dy = ((double) (newpos[1] - pos[1])) / (checkIntervalSplit);
				final double[][] chkpoints = new double[checkIntervalSplit - 1][2];
				int j;
				for (j = 0; j < checkIntervalSplit - 1; j++) {
					chkpoints[j][0] = pos[0] + (j + 1) * dx;
					chkpoints[j][1] = pos[1] + (j + 1) * dy;
				}
				boolean leavesTrack = false;
				j = 0;
				while (!leavesTrack && j < checkIntervalSplit - 1) {
					leavesTrack = (!trackA.contains(chkpoints[j][0], chkpoints[j][1]))
							&& (!startZoneA.contains(chkpoints[j][0], chkpoints[j][1]));
					j++;
				}
				if (checkIntersect(new int[]{finishLine[0], finishLine[1] }, new int[]{finishLine[2], finishLine[3] }, pos, newpos,
						(byte) 0)) {
					finishedFirst++;
					dispMessage(players[subgamestate].getName() + " finishes on place " + finishedFirst + ".");
					players[subgamestate].logPosition(newpos);
					players[subgamestate].setVelocity(new int[]{0, 0 });
					players[subgamestate].setPosition(new int[]{Player.INIT_POS, Player.INIT_POS });
					players[subgamestate].setFinishedPlace(finishedFirst);
					redoPlayerLabels();
					if (checkFinished()) {
						redoPlayerLabels();
						gameFrame.repaint();
						return;
					}
				} else if (leavesTrack || isCrashingPlayer(newpos[0], newpos[1], players[subgamestate].getNumber())
						|| ((!trackA.contains(newpos[0], newpos[1])) && (!startZoneA.contains(newpos[0], newpos[1])))
						|| checkIntersect(move, track.getLeft(), true) || checkIntersect(move, track.getRight(), true)) {
					final int answ = JOptionPane.showConfirmDialog(gameFrame, "Going there will crash you. Do you really want to?", NAME,
							JOptionPane.YES_NO_OPTION);
					if (answ == JOptionPane.YES_OPTION) {
						dispMessage(players[subgamestate].getName() + " crashes.");
						players[subgamestate].logPosition(newpos);
						players[subgamestate].setVelocity(new int[]{0, 0 });
						players[subgamestate].setPosition(new int[]{Player.INIT_POS, Player.INIT_POS });
						players[subgamestate].setFinishedPlace(players.length - finishedLast);
						finishedLast++;
						redoPlayerLabels();
						if (checkFinished()) {
							redoPlayerLabels();
							gameFrame.repaint();
							return;
						}
					} else
						return;
				} else {
					players[subgamestate].setVelocity(vel);
					players[subgamestate].setPosition(newpos);
					players[subgamestate].logPosition(newpos);
					redoPlayerLabels();
				}

				do {
					subgamestate++;
					if (subgamestate == players.length)
						subgamestate = 0;
				} while (players[subgamestate].isFinished());

				gameFrame.setStatus(players[subgamestate].getName() + "'s turn...");
				vel = players[subgamestate].getVelocity();
				pos = players[subgamestate].getPosition();
				rui.setVelVector(new int[]{pos[0] + vel[0], pos[1] + vel[1] }, subgamestate);
				rui.setPrePath(null);
				isShowingPrePath = -1;
				gameFrame.getBtnUndo().setEnabled(true);
			}
		}

		gameFrame.repaint();
	}

	/**
	 * Gets activated when the game grid is clicked with x- and y-coordinates in
	 * the grid system.
	 *
	 * @param x
	 * @param y
	 */
	public void clickedGrid(final int x, final int y) {
		if (gamestate == GameState.DRAWTRACK) {
			if (track == null) {
				track = new Track();
				rui.setTrack(track);
			}
			addToTrack(track, x, y, subgamestate == 0);
			if (checkIntersect(track.getLeft(), track.getLeft(), false) || checkIntersect(track.getLeft(), track.getRight(), false)
					|| checkIntersect(track.getRight(), track.getRight(), false)) {
				dispMessage("Tracks intersect.");
				undoFromTrack(track, subgamestate == 0);
			}

		} else if (gamestate == GameState.PLACEPLAYERS) {
			if (subgamestate < 0 || subgamestate >= players.length) {
				dispMessage("No players left to place.");
				return;
			}
			if (!startZoneA.contains(x, y)) {
				dispMessage("Player is not in the start zone.");
				return;
			}
			if (isCrashingPlayer(x, y, players[subgamestate].getNumber())) {
				dispMessage("Player crashes with other player.");
				return;
			}

			players[subgamestate].setPosition(new int[]{x, y });
			subgamestate++;
			if (subgamestate < players.length)
				gameFrame.setStatus("Place player " + players[subgamestate].getName());
			else {
				gameFrame.getBtnOK().setEnabled(true);
				gameFrame.setStatus("Click OK to confirm.");
			}
		}
		gameFrame.repaint();
	}

	/**
	 * Gets activated when the btnOK is clicked.
	 */
	public void clickedOK() {
		if (gamestate == GameState.START) {
			gameFrame.getBtnUndo().setEnabled(true);
			gameFrame.setStatus("Draw left track border.");
			gamestate = GameState.DRAWTRACK;
			subgamestate = 0;

		} else if (gamestate == GameState.DRAWTRACK && subgamestate == 0) {
			if (track == null || track.getLeft().size() < 2) {
				dispMessage("Track too short.");
				return;
			}
			gameFrame.setStatus("Draw right track border.");
			subgamestate = 1;

		} else if (gamestate == GameState.DRAWTRACK && subgamestate == 1) {
			if (track == null || track.getRight().size() < 2) {
				dispMessage("Track too short.");
				return;
			}
			final LinkedList<int[]> tTrack = new LinkedList<int[]>();
			Iterator<int[]> it = track.getLeft().iterator();
			while (it.hasNext())
				tTrack.add(it.next());
			it = track.getRight().descendingIterator();
			while (it.hasNext())
				tTrack.add(it.next());
			tTrack.add(track.getLeft().getFirst());
			if (checkIntersect(tTrack, tTrack, false)) {
				dispMessage("Track/start line/finish line intersect.");
				return;
			}
			gamestate = GameState.PLACEPLAYERS;
			subgamestate = 0;
			gameFrame.getBtnOK().setEnabled(false);
			// make finishline
			finishLine = makeFinishLine(track.getLeft().getLast(), track.getRight().getLast());
			rui.setFinishLine(finishLine);
			// make startzone
			startZone = makeStartZone(track.getLeft().getFirst(), track.getRight().getFirst());
			rui.setStartZone(startZone);
			final Path2D.Float p = new Path2D.Float();
			p.moveTo(startZone[0][0], startZone[1][0]);
			for (int i = 1; i < 4; i++)
				p.lineTo(startZone[0][i], startZone[1][i]);
			p.closePath();
			startZoneA = getToleranceExpandedShape(p);
			// make track
			trackA = getToleranceExpandedShape(newPrefilledPath(track.getLeft(), track.getRight()));
			rui.finishTrack();
			gameFrame.setStatus("Place " + players[0].getName());

		} else if (gamestate == GameState.PLACEPLAYERS && subgamestate == players.length) {
			gameFrame.getBtnOK().setEnabled(false);
			gameFrame.getBtnUndo().setEnabled(false);
			for (final Player player : players)
				player.logPosition(player.getPosition());
			gamestate = GameState.PLAY;
			subgamestate = 0;
			gameFrame.setStatus(players[0].getName() + "'s turn...");
			rui.setVelVector(players[0].getPosition(), 0);
			rui.setPrePath(null);
			isShowingPrePath = -1;
			redoPlayerLabels();
		} else if (gamestate == GameState.IDLE)
			return;
		else if (gamestate == GameState.EXIT)
			System.exit(0);
		gameFrame.repaint();
	}

	/**
	 * Gets activated when the button btnUndo is clicked.
	 */
	public void clickedUndo() {
		if (gamestate == GameState.DRAWTRACK)
			undoFromTrack(track, subgamestate == 0);
		else if (gamestate == GameState.PLACEPLAYERS && subgamestate > 0) {
			subgamestate--;
			players[subgamestate].setPosition(new int[]{Player.INIT_POS, Player.INIT_POS });
			gameFrame.getBtnOK().setEnabled(false);
			gameFrame.setStatus("Place player " + players[subgamestate].getName());
		} else if (gamestate == GameState.PLAY) {
			do {
				subgamestate--;
				if (subgamestate == -1)
					subgamestate = players.length - 1;
				;
			} while (players[subgamestate].isFinished());
			final int[] vel = players[subgamestate].getVelocity();
			players[subgamestate].setVelocity(oldVel);
			final int[] pos = players[subgamestate].getPosition();
			players[subgamestate].setPosition(new int[]{pos[0] - vel[0], pos[1] - vel[1] });
			gameFrame.setStatus(players[subgamestate].getName() + "'s turn...");
			rui.setVelVector(new int[]{pos[0] - vel[0] + oldVel[0], pos[1] - vel[1] + oldVel[1] }, subgamestate);
			rui.setPrePath(null);
			isShowingPrePath = -1;
			players[subgamestate].getHistory().removeLast();
			gameFrame.getBtnUndo().setEnabled(false);
			redoPlayerLabels();
		}
		gameFrame.repaint();
	}

	/**
	 * Displays a standard message dialog
	 *
	 * @param s
	 *            Message to be displayed.
	 */
	public void dispMessage(final String s) {
		JOptionPane.showMessageDialog(gameFrame, s, NAME, JOptionPane.OK_OPTION);
	}

	/**
	 * Exit the game after a prompt.
	 */
	public void exitMe() {
		final GameState oldGamestate = gamestate;
		gamestate = GameState.EXIT;
		final int answer = JOptionPane.showConfirmDialog(gameFrame, "Do you really want to exit?", NAME, JOptionPane.YES_NO_OPTION);
		if (answer == JOptionPane.YES_OPTION) {
			final File uP = new File(userProperties);
			if (uP.exists())
				uP.delete();
			FileOutputStream out;
			try {
				out = new FileOutputStream(new File(userProperties));
				prop.store(out, null);
				out.close();
			} catch (final Exception e) {
				e.printStackTrace();
			}
			System.exit(0);
		}
		gamestate = oldGamestate;
	}

	/**
	 * @return the GameUI linked with this game
	 */
	public GameUI getGameFrame() {
		return gameFrame;
	}

	/**
	 * @return Array of all players for the game
	 */
	private Player[] getPlayers() {
		String s;
		int i, temp;
		Scanner sc;
		try {
			temp = Integer.valueOf(prop.getProperty("nPlayers"));
		} catch (final Exception e) {
			temp = 2;
		}
		final Player[] players = new Player[temp];
		for (i = 0; i < players.length; i++) {
			s = prop.getProperty("player" + (i + 1) + "Name");
			sc = new Scanner(prop.getProperty("player" + (i + 1) + "Color"));
			players[i] = new Player(s, i + 1, new Color(sc.nextInt(), sc.nextInt(), sc.nextInt()));
			sc.close();
		}
		return players;
	}

	/**
	 * @param x
	 * @param y
	 * @param i
	 * @return true iff player i crashes any other player
	 */
	private boolean isCrashingPlayer(final int x, final int y, final int i) {
		for (final Player player : players) {
			if (player.getNumber() == i)
				continue;
			if ((player.getPosition()[0] == x) && (player.getPosition()[1] == y))
				return true;
		}
		return false;
	}

	private void redoPlayerLabels() {
		String s;
		for (int i = 0; i < players.length; i++) {
			if (players[i].isFinished())
				s = players[i].getFinishedPlace() + ".";
			else
				s = players[i].getVelocity()[0] + " " + (-players[i].getVelocity()[1]);
			gameFrame.setPlayerInfo(s, i);
		}
	}

	/**
	 * Restart the game after a prompt.
	 */
	public void restartMe() {
		final GameState oldGamestate = gamestate;
		gamestate = GameState.RESTART;
		final int answer = JOptionPane.showConfirmDialog(gameFrame, "Do you really want to restart?", NAME, JOptionPane.YES_NO_OPTION);
		if (answer == JOptionPane.YES_OPTION) {
			final File uP = new File(userProperties);
			if (uP.exists())
				uP.delete();
			FileOutputStream out;
			try {
				out = new FileOutputStream(new File(userProperties));
				prop.store(out, null);
				out.close();
			} catch (final Exception e) {
				e.printStackTrace();
			}
			gameFrame.dispose();
			Main.main(null);
		}
		gamestate = oldGamestate;
	}

	/**
	 * Start a new RaceGame
	 */
	public void start() {
		final RaceGame me = this;

		final StartDialog startDial = new StartDialog(NAME + " " + VERSION, prop);
		new Thread(() -> startDial.setupUI()).start();

		new Thread(() -> {
			while (startDial.isActive())
				try {
					Thread.sleep(50L);
				} catch (final InterruptedException e1) {
					e1.printStackTrace();
				}
			int temp;
			final int wx, wy, rows, cols;
			try {
				temp = Integer.valueOf(prop.getProperty("gameX"));
			} catch (final Exception e2) {
				temp = defCols;
			}
			cols = temp;
			prop.put("gameX", String.valueOf(cols));
			try {
				temp = Integer.valueOf(prop.getProperty("gameY"));
			} catch (final Exception e3) {
				temp = defRows;
			}
			rows = temp;
			prop.put("gameY", String.valueOf(rows));
			try {
				temp = Integer.valueOf(prop.getProperty("windowX"));
			} catch (final Exception e4) {
				temp = defWindowX;
			}
			wx = temp;
			prop.put("windowX", String.valueOf(wx));
			try {
				temp = Integer.valueOf(prop.getProperty("windowY"));
			} catch (final Exception e5) {
				temp = defWindowY;
			}
			wy = temp;
			prop.put("windowY", String.valueOf(wy));

			rui = new RaceUI(rows, cols);
			gameFrame.setStatus("Game setup...");
			players = getPlayers();
			rui.setPlayers(players);
			gameFrame.setupUI(rui.getGrid(), me, wx, wy, players);
			gameFrame.setStatus("Click OK to start.");
			gamestate = GameState.START;
		}).start();
	}
}
