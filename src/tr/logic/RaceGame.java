package tr.logic;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Shape;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Path2D;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.BitSet;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.Properties;
import java.util.Scanner;
import javax.swing.JButton;
import javax.swing.JOptionPane;
import javax.swing.SwingUtilities;
import tr.gui.GameUI;
import tr.gui.RaceUI;
import tr.gui.StartDialog;

/**
 * Main game logic component of TheoreticRacing.
 *
 * @version 0.3.0
 * @author CGH
 */
public class RaceGame {
	private final static int			defCols				= 86;
	private final static Color[]		defPlayerColors		= new Color[]{Color.BLUE, Color.RED, Color.GREEN, Color.YELLOW, Color.CYAN,
			Color.ORANGE, Color.GRAY, Color.MAGENTA, Color.BLACK };
	private final static int			defRows				= 48;
	private final static int			defWindowX			= 1500;
	private final static int			defWindowY			= 800;
	public final static String			NAME				= "Theoretical Racing";
	public final static String			VERSION				= "0.3.0";
	public final static String			defProperties		= "default.properties";

	private final static float			startZoneWidth		= 2f;
	private final static BasicStroke	strkTolerance		= new BasicStroke(.01f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND);

	/** Directory containing the JAR (or the classes dir in dev runs). */
	private static Path installDir() {
		try {
			final Path codeSource = Path.of(RaceGame.class.getProtectionDomain().getCodeSource().getLocation().toURI());
			return Files.isDirectory(codeSource) ? codeSource : codeSource.getParent();
		} catch (final Exception e) {
			return Path.of(".");
		}
	}

	/** Path to the user's saved properties (next to the JAR). */
	public static Path userPropertiesPath() {
		return installDir().resolve("user.properties");
	}

	/** Path to the per-session game log (next to the JAR). */
	public static Path gameLogPath() {
		return installDir().resolve("last_game.log");
	}

	/** Directory containing .track files. */
	public static Path tracksDir() {
		return installDir().resolve("tracks");
	}

	/** List names of available tracks (file stem, without .track suffix). */
	public static java.util.List<String> listTracks() {
		final Path dir = tracksDir();
		if (!Files.isDirectory(dir))
			return java.util.List.of();
		try (java.util.stream.Stream<Path> s = Files.list(dir)) {
			return s.filter(p -> p.toString().endsWith(".track"))
					.map(p -> p.getFileName().toString().replaceFirst("\\.track$", ""))
					.sorted()
					.toList();
		} catch (final IOException e) {
			return java.util.List.of();
		}
	}

	/** Parsed track data — used by the chooser for previews and by loadTrack to update props. */
	public static record TrackData(String name, int gameX, int gameY, LinkedList<int[]> left, LinkedList<int[]> right) {}

	/** Parse a named .track file. Returns null on miss / parse failure. */
	public static TrackData loadTrackData(final String name) {
		final Path file = tracksDir().resolve(name + ".track");
		if (!Files.isRegularFile(file))
			return null;
		final Properties tp = new Properties();
		try (java.io.InputStream in = Files.newInputStream(file)) {
			tp.load(in);
		} catch (final IOException e) {
			return null;
		}
		final LinkedList<int[]> left = parsePointList(tp.getProperty("trackLeft"));
		final LinkedList<int[]> right = parsePointList(tp.getProperty("trackRight"));
		if (left.size() < 2 || right.size() < 2)
			return null;
		int gx;
		int gy;
		try {
			gx = Integer.parseInt(tp.getProperty("gameX", String.valueOf(defCols)));
			gy = Integer.parseInt(tp.getProperty("gameY", String.valueOf(defRows)));
		} catch (final NumberFormatException e) {
			gx = defCols;
			gy = defRows;
		}
		return new TrackData(tp.getProperty("name", name), gx, gy, left, right);
	}

	/** Parse the "last track" data straight out of a Properties bundle. Null if missing/invalid. */
	public static TrackData loadLastTrackData(final Properties prop) {
		final String left = prop.getProperty("lastTrackLeft");
		final String right = prop.getProperty("lastTrackRight");
		if (left == null || right == null || left.isEmpty() || right.isEmpty())
			return null;
		final LinkedList<int[]> l = parsePointList(left);
		final LinkedList<int[]> r = parsePointList(right);
		if (l.size() < 2 || r.size() < 2)
			return null;
		int gx;
		int gy;
		try {
			gx = Integer.parseInt(prop.getProperty("gameX", String.valueOf(defCols)));
			gy = Integer.parseInt(prop.getProperty("gameY", String.valueOf(defRows)));
		} catch (final NumberFormatException e) {
			gx = defCols;
			gy = defRows;
		}
		return new TrackData("Last", gx, gy, l, r);
	}

	/** Load a named track into {@code prop}, replacing lastTrack* + gameX/gameY. */
	public static boolean loadTrack(final Properties prop, final String name) {
		final TrackData td = loadTrackData(name);
		if (td == null)
			return false;
		prop.put("lastTrackLeft", pointListToString(td.left()));
		prop.put("lastTrackRight", pointListToString(td.right()));
		prop.put("gameX", String.valueOf(td.gameX()));
		prop.put("gameY", String.valueOf(td.gameY()));
		prop.put("useLastTrack", "true");
		return true;
	}

	/**
	 * @param seq 0: all endpoints checked; 1: p11==p22 allowed; 2: p12==p21
	 *            allowed; 3: equal endpoints always allowed.
	 * @return true iff the segments (p11,p12) and (p21,p22) intersect.
	 */
	private final static boolean checkIntersect(final int[] p11, final int[] p12, final int[] p21, final int[] p22, final byte seq) {
		if (seq != 3 && (Arrays.equals(p11, p12) || Arrays.equals(p11, p21) || Arrays.equals(p12, p22) || Arrays.equals(p21, p22)))
			return true;
		if (seq != 1 && seq != 3 && Arrays.equals(p11, p22))
			return true;
		if (seq != 2 && seq != 3 && Arrays.equals(p12, p21))
			return true;

		final double x1 = p11[0], y1 = p11[1], x2 = p21[0], y2 = p21[1];
		final double dx1 = p12[0] - p11[0], dy1 = p12[1] - p11[1];
		final double dx2 = p22[0] - p21[0], dy2 = p22[1] - p21[1];
		final double d = dx2 * dy1 - dx1 * dy2;
		if (d == 0) {
			if (seq != 0 && seq != 3) {
				if (Math.signum(dx1) != Math.signum(dx2) || Math.signum(dy1) != Math.signum(dy2))
					return true;
				return false;
			}
			if ((x2 - x1) * dy1 - (y2 - y1) * dx1 != 0)
				return false;
			final double len1Sq = dx1 * dx1 + dy1 * dy1;
			if (len1Sq == 0)
				return false;
			final double s1 = ((x2 - x1) * dx1 + (y2 - y1) * dy1) / len1Sq;
			final double s2 = ((p22[0] - x1) * dx1 + (p22[1] - y1) * dy1) / len1Sq;
			return Math.max(0, Math.min(s1, s2)) < Math.min(1, Math.max(s1, s2));
		} else if (seq == 0 || seq == 3) {
			final double s = (dy1 * x1 - dy1 * x2 - dx1 * y1 + dx1 * y2) / d;
			final double t = (dy2 * x1 - dy2 * x2 - dx2 * y1 + dx2 * y2) / d;
			if (s > 0 && s < 1 && t > 0 && t < 1)
				return true;
			if (seq == 0 && (s == 0 || s == 1) && (t == 0 || t == 1))
				return true;
			// Corner-clip: AI line interior crosses through a border vertex
			// (s in code = AI line parameter, t in code = border parameter)
			if (seq == 3 && s > 0 && s < 1 && (t == 0 || t == 1))
				return true;
		}
		return false;
	}

	/**
	 * @return true iff the line paths p1, p2 intersect anywhere.
	 */
	private final static boolean checkIntersect(final LinkedList<int[]> p1, final LinkedList<int[]> p2, final boolean allowEqual) {
		if (p1 == null || p2 == null || p1.size() < 2 || p2.size() < 2)
			return false;
		if (p1.size() == 2 && Arrays.equals(p1.getFirst(), p1.getLast()))
			return true;
		if (p2.size() == 2 && Arrays.equals(p2.getFirst(), p2.getLast()))
			return true;
		final Iterator<int[]> it1 = p1.iterator();
		int[] p11 = null, p12 = null;
		while (it1.hasNext()) {
			p12 = it1.next();
			if (p11 != null) {
				final Iterator<int[]> it2 = p2.iterator();
				int[] p21 = null, p22 = null;
				while (it2.hasNext()) {
					p22 = it2.next();
					if (p21 != null && (p11 != p21 || p12 != p22)) {
						final byte seq;
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
	 * Cheap incremental self-intersection check: tests segment (prevLast,last)
	 * of `active` against all earlier segments of `active` and all segments of
	 * `other`. O(n) per call instead of O(n²).
	 */
	private final static boolean lastSegmentIntersects(final LinkedList<int[]> active, final LinkedList<int[]> other) {
		if (active.size() < 2)
			return false;
		final int[] a2 = active.getLast();
		final int[] a1 = active.get(active.size() - 2);
		// Against earlier segments of active itself (skip the adjacent one)
		int[] prev = null;
		final Iterator<int[]> it = active.iterator();
		int idx = 0;
		final int limit = active.size() - 2;
		while (it.hasNext() && idx <= limit) {
			final int[] cur = it.next();
			if (prev != null) {
				// segments (prev,cur) and (a1,a2); they're non-adjacent if idx < limit
				final boolean adjacent = idx == limit; // last segment before our new one
				if (!adjacent) {
					if (checkIntersect(prev, cur, a1, a2, (byte) 0))
						return true;
				} else {
					// adjacent: shared endpoint (cur == a1). Allowed.
					if (checkIntersect(prev, cur, a1, a2, (byte) 2))
						return true;
				}
			}
			prev = cur;
			idx++;
		}
		// Against all segments of the other side
		prev = null;
		final Iterator<int[]> it2 = other.iterator();
		while (it2.hasNext()) {
			final int[] cur = it2.next();
			if (prev != null && checkIntersect(prev, cur, a1, a2, (byte) 0))
				return true;
			prev = cur;
		}
		return false;
	}

	private final static Area getToleranceExpandedShape(final Shape s) {
		final Area a = new Area(strkTolerance.createStrokedShape(s));
		a.add(new Area(s));
		return a;
	}

	private final static float[][] makeStartZone(final int[] pL, final int[] pR) {
		final float len = (float) Math.sqrt((pR[0] - pL[0]) * (pR[0] - pL[0]) + (pR[1] - pL[1]) * (pR[1] - pL[1]));
		final float dirX = (pL[1] - pR[1]) * startZoneWidth / len;
		final float dirY = (pR[0] - pL[0]) * startZoneWidth / len;
		return new float[][]{{pL[0], pR[0], pR[0] + dirX, pL[0] + dirX }, {pL[1], pR[1], pR[1] + dirY, pL[1] + dirY } };
	}

	private final static Path2D.Float newPrefilledPath(final LinkedList<int[]> left, final LinkedList<int[]> right) {
		if (left == null || left.isEmpty())
			return null;
		final Path2D.Float p = new Path2D.Float();
		int[] pos = left.getFirst();
		p.moveTo(pos[0], pos[1]);
		Iterator<int[]> it = left.iterator();
		while (it.hasNext()) {
			pos = it.next();
			p.lineTo(pos[0], pos[1]);
		}
		if (right == null || right.isEmpty())
			return p;
		it = right.descendingIterator();
		while (it.hasNext()) {
			pos = it.next();
			p.lineTo(pos[0], pos[1]);
		}
		p.closePath();
		return p;
	}

	private int					finishedLast	= 0, finishedFirst = 0;
	private Line2D				finishLine;
	/** Unit vector of the racing direction at the finish line. A move only
	 *  counts as crossing the finish if it travels with this heading (positive
	 *  dot) — blocks the "cross the adjacent finish backward from the start"
	 *  exploit on closed-loop tracks with a small S/F gap. */
	private double				finishFwdX, finishFwdY;
	private final GameUI		gameFrame;
	private volatile GameState	gamestate		= GameState.PRESTART;
	private int					isShowingPrePath	= -1;
	private final int			maxPlayers;
	private int[]				oldVel;
	private Player[]			players;
	private final Properties	prop;
	private RaceUI				rui;
	private float[][]			startZone;
	private Area				startZoneA;
	private int					subgamestate	= 0;
	private Track				track;
	private Area				trackA;
	private int[][]				distToFinish;
	private int					gameCols, gameRows;
	private final StringBuilder	gameLog		= new StringBuilder();
	private int					turnCounter	= 0;
	private boolean				autoMode	= false;
	private volatile boolean	reachabilityReady;
	private Thread				reachabilityThread;

	/** Create new RaceGame. Call {@link #start()} afterwards. */
	public RaceGame(final Properties prop) {
		this.prop = prop;
		maxPlayers = sanitizeIntProp("maxPlayers", defPlayerColors.length, 1, defPlayerColors.length);
		sanitizeIntProp("nPlayers", 2, 1, maxPlayers);

		for (int i = 0; i < maxPlayers; i++) {
			final String prefix = "player" + (i + 1);
			final String name = prop.getProperty(prefix + "Name");
			prop.put(prefix + "Name", name == null ? "Player " + (i + 1) : name);
			final Color c = parseColor(prefix + "Color", i);
			prop.put(prefix + "Color", c.getRed() + " " + c.getGreen() + " " + c.getBlue());
			// Migrate legacy "Ai" → "Kind"
			if (prop.getProperty(prefix + "Kind") == null) {
				final String legacyAi = prop.getProperty(prefix + "Ai");
				prop.put(prefix + "Kind", "true".equalsIgnoreCase(legacyAi) ? "AI1" : "HUMAN");
			}
		}

		gameFrame = new GameUI(NAME + " " + VERSION, maxPlayers);
	}

	private int sanitizeIntProp(final String key, final int def, final int min, final int max) {
		int v;
		try {
			v = Integer.parseInt(prop.getProperty(key));
		} catch (final Exception e) {
			v = def;
		}
		v = Math.max(min, Math.min(v, max));
		prop.put(key, String.valueOf(v));
		return v;
	}

	private Color parseColor(final String key, final int defIdx) {
		try (Scanner sc = new Scanner(prop.getProperty(key))) {
			return new Color(sc.nextInt(), sc.nextInt(), sc.nextInt());
		} catch (final Exception e) {
			return defPlayerColors[defIdx];
		}
	}

	/** Enable headless auto-play (skip dialogs, exit on finish). */
	public void setAutoMode(final boolean b) {
		this.autoMode = b;
	}

	/** Show the start dialog and, on confirmation, build the play window. */
	public void start() {
		if (autoMode) {
			setupGameUI();
			return;
		}
		final StartDialog startDial = new StartDialog(NAME + " " + VERSION, prop);
		startDial.setOnSave(this::saveProperties);
		startDial.setOnConfirm(() -> setupGameUI());
		startDial.setOnCancel(() -> {
			saveProperties();
			System.exit(0);
		});
		startDial.setupUI();
	}

	private void setupGameUI() {
		gameCols = sanitizeIntProp("gameX", defCols, 2, 500);
		gameRows = sanitizeIntProp("gameY", defRows, 2, 500);
		final int wx = sanitizeIntProp("windowX", defWindowX, 200, 10000);
		final int wy = sanitizeIntProp("windowY", defWindowY, 200, 10000);

		rui = new RaceUI(gameRows, gameCols);
		gameFrame.setStatus("Game setup...");
		players = getPlayers();
		rui.setPlayers(players);
		if (!autoMode)
			gameFrame.setupUI(rui.getGrid(), this, wx, wy, players);

		final boolean useLast = Boolean.parseBoolean(prop.getProperty("useLastTrack", "false")) || autoMode;
		if (useLast && hasLastTrack(prop) && loadLastTrack()) {
			gamestate = GameState.PLACEPLAYERS;
			subgamestate = 0;
			gameFrame.getBtnOK().setEnabled(false);
			autoPlaceAiPlayers();
			updatePlaceStatus();
			gameFrame.repaint();
			if (autoMode && subgamestate == players.length)
				SwingUtilities.invokeLater(this::clickedOK);
			return;
		}
		if (autoMode) {
			System.err.println("--auto requires a saved track and all-AI players. Aborting.");
			System.exit(2);
		}
		gameFrame.setStatus("Click OK to start.");
		gamestate = GameState.START;
	}

	private boolean checkFinished() {
		if (finishedLast + finishedFirst >= players.length - (players.length == 1 ? 0 : 1)) {
			gamestate = GameState.FINISHED;
			rui.setVelVector(null, -1);
			rui.setPrePath(null);

			final HashMap<Integer, String> place = new HashMap<>();
			for (final Player p : players) {
				if (p.getFinishedPlace() == 0)
					p.setFinishedPlace(finishedFirst + 1);
				place.put(p.getFinishedPlace(), p.getName());
			}
			final StringBuilder sb = new StringBuilder("The game has finished.\n");
			for (int i = 1; i <= players.length; i++)
				sb.append("\n").append(i).append(".   ").append(place.get(i));
			gameFrame.setStatus("The game has finished");
			gameFrame.repaint();
			gameLog.append("# results\n");
			for (int i = 1; i <= players.length; i++)
				gameLog.append(i).append(". ").append(place.get(i)).append("\n");
			writeGameLog();
			dispMessage(sb.toString() + "\n\nLog written to " + gameLogPath());
			gameFrame.getBtnUndo().setEnabled(false);
			for (final JButton b : gameFrame.getBtnDirections())
				b.setEnabled(false);
			gameFrame.repaint();
			if (autoMode) {
				SwingUtilities.invokeLater(() -> System.exit(0));
			}
			return true;
		}
		return false;
	}

	/** Returns true if the move from `pos` to `newpos` is allowed for player i. */
	private boolean isMoveLegal(final int[] pos, final int[] newpos, final int playerNumber) {
		return isMoveLegalGeometry(pos[0], pos[1], newpos[0], newpos[1])
				&& !isCrashingPlayer(newpos[0], newpos[1], playerNumber);
	}

	/**
	 * Geometry-only legality (no player crash check). The interval scan is
	 * scaled by move length: ~2 samples per unit of euclidean distance. This
	 * keeps cost low for short moves while still catching cases where the line
	 * dips outside the polygon between two border vertices (e.g. tangent moves
	 * across an inside corner of the corridor).
	 */
	private boolean isMoveLegalGeometry(final int x1, final int y1, final int x2, final int y2) {
		if (!trackA.contains(x2, y2) && !startZoneA.contains(x2, y2))
			return false;
		final int dxi = x2 - x1, dyi = y2 - y1;
		final int n = Math.max(2, (int) Math.ceil(Math.sqrt(dxi * dxi + dyi * dyi) * 2));
		final double dx = (double) dxi / n;
		final double dy = (double) dyi / n;
		for (int j = 1; j < n; j++) {
			final double cx = x1 + j * dx;
			final double cy = y1 + j * dy;
			if (!trackA.contains(cx, cy) && !startZoneA.contains(cx, cy))
				return false;
		}
		final int[] from = {x1, y1 };
		final int[] to = {x2, y2 };
		return !segmentCrossesPath(from, to, track.getLeft()) && !segmentCrossesPath(from, to, track.getRight());
	}

	private final HashMap<Long, Boolean>	edgeLegalCache		= new HashMap<>();
	private final HashMap<Long, Boolean>	stateContCache		= new HashMap<>();
	private final HashMap<Long, Boolean>	stateLiveCache		= new HashMap<>();

	private boolean isMoveLegalGeometryCached(final int x1, final int y1, final int x2, final int y2) {
		final long key = ((long) x1 & 0xFFFF) << 48 | ((long) y1 & 0xFFFF) << 32 | ((long) x2 & 0xFFFF) << 16 | (long) y2 & 0xFFFF;
		Boolean cached = edgeLegalCache.get(key);
		if (cached != null)
			return cached;
		final boolean legal = isMoveLegalGeometry(x1, y1, x2, y2);
		edgeLegalCache.put(key, legal);
		return legal;
	}


	private BitSet	aliveStates;
	private int[]	turnsArr;
	private int		aliveW, aliveH, aliveVMAX;

	private int aliveIdx(final int x, final int y, final int vx, final int vy) {
		final int span = 2 * aliveVMAX + 1;
		return ((x * aliveH + y) * span + (vx + aliveVMAX)) * span + (vy + aliveVMAX);
	}

	/** True iff (x,y,vx,vy) can reach the finish via some legal sequence of moves. */
	private boolean isAlive(final int x, final int y, final int vx, final int vy) {
		if (aliveStates == null)
			return true; // not yet computed — be permissive
		if (Math.abs(vx) > aliveVMAX || Math.abs(vy) > aliveVMAX)
			return false;
		if (x < 0 || y < 0 || x >= aliveW || y >= aliveH)
			return false;
		return aliveStates.get(aliveIdx(x, y, vx, vy));
	}

	/** Minimum number of turns from (x,y,vx,vy) to crossing the finish, or MAX_VALUE if unreachable. */
	private int turnsToFinish(final int x, final int y, final int vx, final int vy) {
		if (turnsArr == null)
			return Integer.MAX_VALUE;
		if (Math.abs(vx) > aliveVMAX || Math.abs(vy) > aliveVMAX)
			return Integer.MAX_VALUE;
		if (x < 0 || y < 0 || x >= aliveW || y >= aliveH)
			return Integer.MAX_VALUE;
		return turnsArr[aliveIdx(x, y, vx, vy)];
	}

	/**
	 * Reverse-BFS from finish-line-crossing states: computes both the alive set
	 * AND the exact minimum number of turns from each state to crossing the finish.
	 * Run once per track build.
	 */
	private void computeReachability() {
		final long t0 = System.nanoTime();
		aliveW = gameCols + 1;
		aliveH = gameRows + 1;
		aliveVMAX = AI_MAX_SPEED;
		final int span = 2 * aliveVMAX + 1;
		final int total = aliveW * aliveH * span * span;
		aliveStates = new BitSet(total);
		turnsArr = new int[total];
		Arrays.fill(turnsArr, Integer.MAX_VALUE);
		final ArrayDeque<int[]> queue = new ArrayDeque<>();

		for (int x = 0; x < aliveW; x++) {
			for (int y = 0; y < aliveH; y++) {
				if (distAt(x, y) == Integer.MAX_VALUE)
					continue;
				if (distAt(x, y) > 2 * aliveVMAX + 5)
					continue; // optimization: too far for direct finish-cross
				for (int vx = -aliveVMAX; vx <= aliveVMAX; vx++) {
					for (int vy = -aliveVMAX; vy <= aliveVMAX; vy++) {
						for (final Direction d : Direction.values()) {
							final int nvx = vx + d.dx;
							final int nvy = vy + d.dy;
							if (Math.abs(nvx) > aliveVMAX || Math.abs(nvy) > aliveVMAX)
								continue;
							if (crossesFinish(x, y, x + nvx, y + nvy)) {
								final int idx = aliveIdx(x, y, vx, vy);
								if (!aliveStates.get(idx)) {
									aliveStates.set(idx);
									turnsArr[idx] = 1;
									queue.offer(new int[]{x, y, vx, vy });
								}
								break;
							}
						}
					}
				}
			}
		}

		final long tInit = System.nanoTime();

		while (!queue.isEmpty()) {
			final int[] cur = queue.poll();
			final int xp = cur[0], yp = cur[1], vxp = cur[2], vyp = cur[3];
			final int turns = turnsArr[aliveIdx(xp, yp, vxp, vyp)];
			final int x = xp - vxp;
			final int y = yp - vyp;
			if (x < 0 || y < 0 || x >= aliveW || y >= aliveH)
				continue;
			if (distAt(x, y) == Integer.MAX_VALUE)
				continue;
			if (!isMoveLegalGeometryCached(x, y, xp, yp))
				continue;
			for (final Direction d : Direction.values()) {
				final int vx = vxp - d.dx;
				final int vy = vyp - d.dy;
				if (Math.abs(vx) > aliveVMAX || Math.abs(vy) > aliveVMAX)
					continue;
				final int idx = aliveIdx(x, y, vx, vy);
				if (!aliveStates.get(idx)) {
					aliveStates.set(idx);
					turnsArr[idx] = turns + 1;
					queue.offer(new int[]{x, y, vx, vy });
				}
			}
		}
		final long tBfs = System.nanoTime();
		if (autoMode)
			System.out.printf("[reachability] init=%.0fms bfs=%.0fms total=%.0fms alive=%d%n",
					(tInit - t0) / 1e6, (tBfs - tInit) / 1e6, (tBfs - t0) / 1e6, aliveStates.cardinality());
	}

	/** True iff state (x,y,vx,vy) has at least one geometry-legal successor or reaches the finish. */
	private boolean stateHasContinuation(final int x, final int y, final int vx, final int vy) {
		final long key = stateKey(x, y, vx, vy);
		Boolean cached = stateContCache.get(key);
		if (cached != null)
			return cached;
		boolean result = false;
		for (final Direction d : Direction.values()) {
			final int nvx = vx + d.dx;
			final int nvy = vy + d.dy;
			final int nx = x + nvx;
			final int ny = y + nvy;
			if (crossesFinish(x, y, nx, ny) || isMoveLegalGeometryCached(x, y, nx, ny)) {
				result = true;
				break;
			}
		}
		stateContCache.put(key, result);
		return result;
	}

	/**
	 * True iff state (x,y,vx,vy) has at least one legal successor whose
	 * successor state itself has a continuation (or crosses finish in 1–2 steps).
	 * 2-level dead-end detection — catches states whose only legal moves all
	 * walk into next-turn-only-illegal positions.
	 */
	private boolean stateHasLiveContinuation(final int x, final int y, final int vx, final int vy) {
		final long key = stateKey(x, y, vx, vy);
		Boolean cached = stateLiveCache.get(key);
		if (cached != null)
			return cached;
		boolean result = false;
		for (final Direction d : Direction.values()) {
			final int nvx = vx + d.dx;
			final int nvy = vy + d.dy;
			final int nx = x + nvx;
			final int ny = y + nvy;
			if (crossesFinish(x, y, nx, ny)) {
				result = true;
				break;
			}
			if (isMoveLegalGeometryCached(x, y, nx, ny) && stateHasContinuation(nx, ny, nvx, nvy)) {
				result = true;
				break;
			}
		}
		stateLiveCache.put(key, result);
		return result;
	}

	private static boolean segmentCrossesPath(final int[] from, final int[] to, final LinkedList<int[]> path) {
		int[] prev = null;
		for (final int[] cur : path) {
			if (prev != null && checkIntersect(prev, cur, from, to, (byte) 3))
				return true;
			prev = cur;
		}
		return false;
	}

	private boolean crossesFinish(final double x1, final double y1, final double x2, final double y2) {
		if (!Line2D.linesIntersect(finishLine.getX1(), finishLine.getY1(), finishLine.getX2(), finishLine.getY2(), x1, y1, x2, y2))
			return false;
		// Only a forward crossing counts (move heads in the racing direction).
		// A zero-length or backward move across the line is not a finish.
		return (x2 - x1) * finishFwdX + (y2 - y1) * finishFwdY > 0;
	}

	/**
	 * Compute the racing-direction unit vector at the finish, as the average of
	 * the last left and right border segments (which point from the track
	 * interior outward through the finish line, i.e. the way a lapping car
	 * travels). Falls back to the finish-line normal if those segments are
	 * degenerate.
	 */
	private void computeFinishForward() {
		final LinkedList<int[]> left = track.getLeft();
		final LinkedList<int[]> right = track.getRight();
		final int[] fL = left.getLast(), fR = right.getLast();
		double hx = 0, hy = 0;
		if (left.size() >= 2) {
			final int[] p = left.get(left.size() - 2);
			hx += fL[0] - p[0];
			hy += fL[1] - p[1];
		}
		if (right.size() >= 2) {
			final int[] p = right.get(right.size() - 2);
			hx += fR[0] - p[0];
			hy += fR[1] - p[1];
		}
		if (hx == 0 && hy == 0) {
			hx = -(fR[1] - fL[1]);
			hy = fR[0] - fL[0];
		}
		final double len = Math.hypot(hx, hy);
		finishFwdX = len == 0 ? 0 : hx / len;
		finishFwdY = len == 0 ? 0 : hy / len;
	}

	/** Activated when a direction button is clicked. */
	public void clickedDirection(final Direction direction) {
		if (gamestate != GameState.PLAY)
			return;
		if (isShowingPrePath != direction.ordinal()) {
			final int[] vel = players[subgamestate].getVelocity();
			isShowingPrePath = direction.ordinal();
			showPreview(players[subgamestate].getPosition(), new int[]{vel[0] + direction.dx, vel[1] + direction.dy });
			gameFrame.repaint();
			return;
		}
		executeMove(direction);
	}

	private void executeMove(final Direction d) {
		final int[] pos = players[subgamestate].getPosition();
		final int[] vel = players[subgamestate].getVelocity();
		final int[] newVel = {vel[0] + d.dx, vel[1] + d.dy };
		final int[] newPos = {pos[0] + newVel[0], pos[1] + newVel[1] };
		commitMove(pos, newVel, newPos);
		gameFrame.repaint();
		maybeAiTurn();
	}

	private void showPreview(final int[] pos, final int[] vel) {
		int vx = vel[0], vy = vel[1];
		int px = pos[0], py = pos[1];
		if (vx == 0 && vy == 0) {
			rui.setPrePath(null);
			return;
		}
		final LinkedList<int[]> prePath = new LinkedList<>();
		while (vx != 0 || vy != 0) {
			px += vx;
			py += vy;
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
	}

	private void commitMove(final int[] pos, final int[] vel, final int[] newpos) {
		final Player player = players[subgamestate];
		final int[] velBefore = player.getVelocity().clone();
		final Direction d = directionOf(velBefore, vel);

		if (crossesFinish(pos[0], pos[1], newpos[0], newpos[1])) {
			finishedFirst++;
			dispMessage(player.getName() + " finishes on place " + finishedFirst + ".");
			logMove(player, d, velBefore, pos, vel, newpos, "FINISH place=" + finishedFirst);
			finishPlayer(player, newpos, finishedFirst);
			if (checkFinished())
				return;
		} else if (!isMoveLegal(pos, newpos, player.getNumber())) {
			if (!player.isAi()) {
				final int answ = JOptionPane.showConfirmDialog(gameFrame, "Going there will crash you. Do you really want to?", NAME,
						JOptionPane.YES_NO_OPTION);
				if (answ != JOptionPane.YES_OPTION)
					return;
			}
			dispMessage(player.getName() + " crashes.");
			logMove(player, d, velBefore, pos, vel, newpos, "CRASH place=" + (players.length - finishedLast));
			finishPlayer(player, newpos, players.length - finishedLast);
			finishedLast++;
			if (checkFinished())
				return;
		} else {
			oldVel = player.getVelocity();
			logMove(player, d, velBefore, pos, vel, newpos, "ok");
			player.setVelocity(vel);
			player.setPosition(newpos);
			player.logPosition(newpos);
			redoPlayerLabels();
		}
		advanceToNextPlayer();
	}

	private static Direction directionOf(final int[] velBefore, final int[] velAfter) {
		final int dx = velAfter[0] - velBefore[0];
		final int dy = velAfter[1] - velBefore[1];
		for (final Direction d : Direction.values())
			if (d.dx == dx && d.dy == dy)
				return d;
		return Direction.NONE;
	}

	private void finishPlayer(final Player p, final int[] lastPos, final int place) {
		p.logPosition(lastPos);
		p.setVelocity(new int[]{0, 0 });
		p.setPosition(new int[]{Player.INIT_POS, Player.INIT_POS });
		p.setFinishedPlace(place);
		redoPlayerLabels();
	}

	private void advanceToNextPlayer() {
		do {
			subgamestate++;
			if (subgamestate == players.length)
				subgamestate = 0;
		} while (players[subgamestate].isFinished());

		final int[] vel = players[subgamestate].getVelocity();
		final int[] pos = players[subgamestate].getPosition();
		gameFrame.setStatus(players[subgamestate].getName() + "'s turn...");
		rui.setVelVector(new int[]{pos[0] + vel[0], pos[1] + vel[1] }, subgamestate);
		rui.setPrePath(null);
		isShowingPrePath = -1;
		gameFrame.getBtnUndo().setEnabled(!players[subgamestate].isAi());
	}

	private void maybeAiTurn() {
		if (gamestate != GameState.PLAY)
			return;
		if (!players[subgamestate].isAi())
			return;
		SwingUtilities.invokeLater(this::doAiTurn);
	}

	private void doAiTurn() {
		if (gamestate == GameState.PLAY && players[subgamestate].isAi())
			executeMove(computeAiMove());
	}

	private final static int		AI_MAX_SPEED	= 12;

	/** Dispatches to AI1 or AI2. AI1 is now the FROZEN reference (the AI1.6
	 *  depth-2 self-search champion); AI2 is forked from it and is the one we
	 *  improve from here. */
	private Direction computeAiMove() {
		ensureReachabilityReady();
		final Player p = players[subgamestate];
		final int[] vel = p.getVelocity();
		final int[] pos = p.getPosition();
		final int playerNum = p.getNumber();

		if (p.getKind() == Player.Kind.AI2)
			return optimalMoveAI2(pos, vel, playerNum);
		return optimalMoveAI1(pos, vel, playerNum);
	}

	/**
	 * Pure min-turns lookup, no opponent reasoning. Used internally to predict
	 * opponent moves; we DON'T want recursion through the smart AI variants.
	 */
	private Direction pureMinTurnsMove(final int[] pos, final int[] vel, final int playerNum) {
		Direction best = null;
		int bestTurns = Integer.MAX_VALUE;
		Direction bestLegal = null;
		double bestLegalScore = Double.MAX_VALUE;
		Direction fallback = Direction.NONE;
		double fallbackScore = Double.MAX_VALUE;
		for (final Direction d : Direction.values()) {
			final int newVx = vel[0] + d.dx;
			final int newVy = vel[1] + d.dy;
			if (Math.abs(newVx) > AI_MAX_SPEED || Math.abs(newVy) > AI_MAX_SPEED)
				continue;
			final int newX = pos[0] + newVx;
			final int newY = pos[1] + newVy;
			if (crossesFinish(pos[0], pos[1], newX, newY))
				return d;
			final double sc = scorePos(newX, newY, newVx, newVy);
			if (!isMoveLegalGeometryCached(pos[0], pos[1], newX, newY)) {
				if (sc < fallbackScore) {
					fallbackScore = sc;
					fallback = d;
				}
				continue;
			}
			if (isCrashingPlayer(newX, newY, playerNum))
				continue;
			if (sc < bestLegalScore) {
				bestLegalScore = sc;
				bestLegal = d;
			}
			final int turns = turnsToFinish(newX, newY, newVx, newVy);
			if (turns < bestTurns) {
				bestTurns = turns;
				best = d;
			}
		}
		if (best != null)
			return best;
		if (bestLegal != null)
			return bestLegal;
		return fallback;
	}

	/** Number of my own moves AI1 searches below the candidate move (d1). 1 =
	 *  depth-2 total (AI1.6), 2 = depth-3, 3 = depth-4. Opponents are predicted
	 *  this many steps forward (one prediction layer per search level). */
	private final static int		AI1_LOOKAHEAD	= 1;

	/**
	 * AI1: depth-(1+AI1_LOOKAHEAD) self-search with multi-step fixed-policy
	 * opponent prediction. For each candidate move d1, the cost is the
	 * opponent-aware minimum turns to finish, found by searching AI1_LOOKAHEAD
	 * of my own moves deep (filtering each level against the opponents'
	 * predicted positions at that step) and using the precomputed reachability
	 * map for the tail. On top of the cost we keep AI1.6's narrow-escape trap
	 * penalty, corridor-width over-speed cap, conflict and spread terms — all
	 * keyed off the immediate 1-step maneuverability of s1.
	 */
	private Direction optimalMoveAI1(final int[] pos, final int[] vel, final int playerNum) {
		// Only one prediction layer: opponents are filtered at the FIRST search
		// level (d2) only. 2+-step opponent forecasts are too noisy to prune on
		// (they cause over-commitment in traffic); deeper levels improve my own
		// trajectory planning without betting on where rivals will be.
		final int[][][] predictedSteps = predictedOpponentSteps(playerNum, 1);
		final int[][] predicted = predictedSteps[0];

		Direction best = null;
		double bestScore = Double.MAX_VALUE;
		Direction bestLegal = null;
		double bestLegalScore = Double.MAX_VALUE;
		Direction fallback = Direction.NONE;
		double fallbackScore = Double.MAX_VALUE;

		for (final Direction d : Direction.values()) {
			final int newVx = vel[0] + d.dx;
			final int newVy = vel[1] + d.dy;
			if (Math.abs(newVx) > AI_MAX_SPEED || Math.abs(newVy) > AI_MAX_SPEED)
				continue;
			final int newX = pos[0] + newVx;
			final int newY = pos[1] + newVy;
			if (crossesFinish(pos[0], pos[1], newX, newY))
				return d;
			final double sc = scorePos(newX, newY, newVx, newVy);
			if (!isMoveLegalGeometryCached(pos[0], pos[1], newX, newY)) {
				if (sc < fallbackScore) {
					fallbackScore = sc;
					fallback = d;
				}
				continue;
			}
			if (isCrashingPlayer(newX, newY, playerNum))
				continue;
			if (sc < bestLegalScore) {
				bestLegalScore = sc;
				bestLegal = d;
			}
			if (turnsToFinish(newX, newY, newVx, newVy) == Integer.MAX_VALUE)
				continue;

			// Opponent-aware min-turns from s1, searching AI1_LOOKAHEAD of my
			// own moves. Returns MAX if every continuation within the horizon is
			// blocked (a 2..N-step trap) -- skip those.
			final int deep = searchMinTurns(newX, newY, newVx, newVy, AI1_LOOKAHEAD, 0, predictedSteps, playerNum);
			if (deep == Integer.MAX_VALUE)
				continue;
			final double costToFinish = deep;

			// Immediate (1-step) maneuverability of s1, for the safety penalties.
			final int d2SafeCount = countFutureSafeSuccessors(newX, newY, newVx, newVy, playerNum, predicted);
			final double trapPenalty = d2SafeCount == 0 ? 50.0
					: d2SafeCount == 1 ? 2.0
							: d2SafeCount == 2 ? 0.5
									: 0.0;
			final double speed = Math.hypot(newVx, newVy);
			final int widthBudget = 4 + d2SafeCount;
			final double overSpeed = Math.max(0.0, speed - widthBudget);
			final double speedCap = overSpeed * overSpeed * 0.4;
			final double conflict = cellOccupiedByPrediction(newX, newY, predicted) ? 3.0 : 0.0;
			final double spread = opponentSpreadPenalty(newX, newY, playerNum);
			final double score = costToFinish + trapPenalty + speedCap + conflict + spread;
			if (score < bestScore) {
				bestScore = score;
				best = d;
			}
		}
		if (best != null)
			return best;
		if (bestLegal != null)
			return bestLegal;
		return fallback;
	}

	/**
	 * Opponent-aware minimum turns from (x,y,vx,vy) to crossing the finish.
	 * The first {@code levels} of my moves are searched explicitly, filtering
	 * each level's destination against the opponents' predicted positions at
	 * that step ({@code predictedSteps[stepIdx]}); beyond the horizon the
	 * opponent-blind precomputed map ({@link #turnsToFinish}) takes over.
	 * Returns {@link Integer#MAX_VALUE} if no continuation reaches the finish.
	 */
	private int searchMinTurns(final int x, final int y, final int vx, final int vy, final int levels, final int stepIdx,
			final int[][][] predictedSteps, final int playerNum) {
		if (levels == 0)
			return turnsToFinish(x, y, vx, vy);
		int best = Integer.MAX_VALUE;
		for (final Direction d : Direction.values()) {
			final int nvx = vx + d.dx;
			final int nvy = vy + d.dy;
			if (Math.abs(nvx) > AI_MAX_SPEED || Math.abs(nvy) > AI_MAX_SPEED)
				continue;
			final int nx = x + nvx;
			final int ny = y + nvy;
			if (crossesFinish(x, y, nx, ny))
				return 1; // finishing in one move is the global minimum
			if (!isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			if (isCrashingPlayer(nx, ny, playerNum))
				continue;
			if (stepIdx < predictedSteps.length && cellOccupiedByPrediction(nx, ny, predictedSteps[stepIdx]))
				continue;
			final int sub = searchMinTurns(nx, ny, nvx, nvy, levels - 1, stepIdx + 1, predictedSteps, playerNum);
			if (sub == Integer.MAX_VALUE)
				continue;
			if (1 + sub < best)
				best = 1 + sub;
		}
		return best;
	}

	/**
	 * Project each live opponent forward {@code steps} of their own moves using
	 * the pure min-turns policy. {@code result[k][opponentIdx]} is that
	 * opponent's position after {@code k+1} moves (null if it can't be
	 * projected that far).
	 */
	private int[][][] predictedOpponentSteps(final int myPlayerNum, final int steps) {
		final int[][][] result = new int[Math.max(1, steps)][][];
		for (int k = 0; k < result.length; k++)
			result[k] = new int[players.length][];
		for (final Player p : players) {
			if (p.getNumber() == myPlayerNum || p.isFinished())
				continue;
			int px = p.getPosition()[0], py = p.getPosition()[1];
			int pvx = p.getVelocity()[0], pvy = p.getVelocity()[1];
			for (int k = 0; k < steps; k++) {
				final Direction d = pureMinTurnsMove(new int[]{px, py }, new int[]{pvx, pvy }, p.getNumber());
				if (d == null)
					break;
				final int nvx = pvx + d.dx;
				final int nvy = pvy + d.dy;
				if (Math.abs(nvx) > AI_MAX_SPEED || Math.abs(nvy) > AI_MAX_SPEED)
					break;
				px += nvx;
				py += nvy;
				pvx = nvx;
				pvy = nvy;
				result[k][p.getNumber() - 1] = new int[]{px, py };
			}
		}
		return result;
	}

	/**
	 * AI2 (EXPERIMENTAL FRONTIER): forked from the AI1.6 depth-2 self-search
	 * champion. Identical to {@link #optimalMoveAI1} at fork time; improvements
	 * are applied here while AI1 stays frozen as the reference.
	 */
	private Direction optimalMoveAI2(final int[] pos, final int[] vel, final int playerNum) {
		final int[][][] predictedSteps = predictedOpponentSteps(playerNum, 1);
		final int[][] predicted = predictedSteps[0];

		Direction best = null;
		double bestScore = Double.MAX_VALUE;
		Direction bestLegal = null;
		double bestLegalScore = Double.MAX_VALUE;
		Direction fallback = Direction.NONE;
		double fallbackScore = Double.MAX_VALUE;

		for (final Direction d : Direction.values()) {
			final int newVx = vel[0] + d.dx;
			final int newVy = vel[1] + d.dy;
			if (Math.abs(newVx) > AI_MAX_SPEED || Math.abs(newVy) > AI_MAX_SPEED)
				continue;
			final int newX = pos[0] + newVx;
			final int newY = pos[1] + newVy;
			if (crossesFinish(pos[0], pos[1], newX, newY))
				return d;
			final double sc = scorePos(newX, newY, newVx, newVy);
			if (!isMoveLegalGeometryCached(pos[0], pos[1], newX, newY)) {
				if (sc < fallbackScore) {
					fallbackScore = sc;
					fallback = d;
				}
				continue;
			}
			if (isCrashingPlayer(newX, newY, playerNum))
				continue;
			if (sc < bestLegalScore) {
				bestLegalScore = sc;
				bestLegal = d;
			}
			if (turnsToFinish(newX, newY, newVx, newVy) == Integer.MAX_VALUE)
				continue;

			final int deep = searchMinTurns(newX, newY, newVx, newVy, AI1_LOOKAHEAD, 0, predictedSteps, playerNum);
			if (deep == Integer.MAX_VALUE)
				continue;
			final double costToFinish = deep;

			final int d2SafeCount = countFutureSafeSuccessors(newX, newY, newVx, newVy, playerNum, predicted);
			final double trapPenalty = d2SafeCount == 0 ? 50.0
					: d2SafeCount == 1 ? 2.0
							: d2SafeCount == 2 ? 0.5
									: 0.0;
			final double speed = Math.hypot(newVx, newVy);
			final int widthBudget = 4 + d2SafeCount;
			final double overSpeed = Math.max(0.0, speed - widthBudget);
			final double speedCap = overSpeed * overSpeed * 0.4;
			final double conflict = cellOccupiedByPrediction(newX, newY, predicted) ? 3.0 : 0.0;
			final double spread = opponentSpreadPenalty(newX, newY, playerNum);
			// Racing-line momentum tie-break: among moves of otherwise-equal cost,
			// prefer the one carrying more usable speed (covers more ground, keeps
			// the line flowing). Weight is tiny so it can never override a real
			// turn or penalty difference.
			final double momentum = AI2_MOMENTUM_TIEBREAK * speed;
			final double score = costToFinish + trapPenalty + speedCap + conflict + spread - momentum;
			if (score < bestScore) {
				bestScore = score;
				best = d;
			}
		}
		if (best != null)
			return best;
		if (bestLegal != null)
			return bestLegal;
		return fallback;
	}

	private final static double	AI2_MOMENTUM_TIEBREAK	= 0.02;

	private boolean cellOccupiedByPrediction(final int x, final int y, final int[][] predicted) {
		for (final int[] p : predicted) {
			if (p != null && p[0] == x && p[1] == y)
				return true;
		}
		return false;
	}

	/** True iff the predicted cell belongs to an opponent whose player number is
	 *  LOWER than mine (so they would have moved before me this round, but their
	 *  prediction reflects their NEXT round move -- not directly relevant) OR
	 *  for an opponent later in this round (idx > mine - 1) AT their predicted
	 *  target. For not-yet-moved opponents (player number greater than mine),
	 *  I move first so I'll claim the cell -- no conflict.
	 *  This function returns true ONLY when the cell is targeted by an already-
	 *  moved opponent's next-round prediction AND that opponent currently sits
	 *  in front of me (i.e., they'll likely be there when I arrive). */
	private boolean predictedConflictByEarlierPlayer(final int x, final int y, final int[][] predicted, final int playerNum) {
		for (int i = 0; i < predicted.length; i++) {
			final int[] p = predicted[i];
			if (p == null || p[0] != x || p[1] != y)
				continue;
			final int otherNum = i + 1;
			// Player with LOWER number already moved this round; their predicted
			// position is their NEXT round move. If their NEXT-round target is
			// where I want to be NOW, they're already nearby and likely to be
			// there by the time it matters.
			if (otherNum < playerNum)
				return true;
		}
		return false;
	}

	/** Count live opponents within squared distance r2 of (pos). */
	private int countNearbyOpponents(final int[] pos, final int playerNum, final int r2) {
		int count = 0;
		for (final Player p : players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			final int dx = pos[0] - pp[0];
			final int dy = pos[1] - pp[1];
			if (dx * dx + dy * dy <= r2)
				count++;
		}
		return count;
	}

	/** Tiny penalty for ending up close to other live players, breaks lateral ties. */
	private double opponentSpreadPenalty(final int x, final int y, final int playerNum) {
		double penalty = 0;
		for (final Player p : players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			final int dx = x - pp[0];
			final int dy = y - pp[1];
			final int d2 = dx * dx + dy * dy;
			if (d2 <= 4)
				penalty += 0.3;
			else if (d2 <= 9)
				penalty += 0.1;
		}
		return penalty;
	}

	/**
	 * Count alive 1-step successors of (x,y,vx,vy) that are NOT also predicted
	 * to be occupied by an opponent's next move. Approximates the number of
	 * still-viable continuations after one opponent reaction.
	 */
	private int countFutureSafeSuccessors(final int x, final int y, final int vx, final int vy, final int playerNum,
			final int[][] predicted) {
		int count = 0;
		for (final Direction d : Direction.values()) {
			final int nvx = vx + d.dx;
			final int nvy = vy + d.dy;
			if (Math.abs(nvx) > AI_MAX_SPEED || Math.abs(nvy) > AI_MAX_SPEED)
				continue;
			final int nx = x + nvx;
			final int ny = y + nvy;
			if (crossesFinish(x, y, nx, ny))
				return 9;
			if (!isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			if (isCrashingPlayer(nx, ny, playerNum))
				continue;
			if (cellOccupiedByPrediction(nx, ny, predicted))
				continue;
			if (isAlive(nx, ny, nvx, nvy))
				count++;
		}
		return count;
	}

	private static long stateKey(final int x, final int y, final int vx, final int vy) {
		return ((long) x & 0xFFFF) << 48 | ((long) y & 0xFFFF) << 32 | ((long) (vx + 32) & 0xFF) << 16 | (long) (vy + 32) & 0xFF;
	}

	private double scorePos(final int x, final int y, final int vx, final int vy) {
		final int dist = distAt(x, y);
		double score = dist == Integer.MAX_VALUE ? 1e6 : dist;
		final double speed = Math.sqrt(vx * vx + vy * vy);
		if (speed > 5)
			score += 2 * (speed - 5);
		return score;
	}

	private int distAt(final int x, final int y) {
		if (distToFinish == null)
			return Integer.MAX_VALUE;
		if (x < 0 || y < 0 || x >= distToFinish.length || y >= distToFinish[0].length)
			return Integer.MAX_VALUE;
		return distToFinish[x][y];
	}

	/**
	 * 8-connected BFS from the finish line through track cells. Used as the AI's
	 * "distance to finish along the track" heuristic.
	 */
	private void computeDistMap() {
		final int w = gameCols + 1;
		final int h = gameRows + 1;
		distToFinish = new int[w][h];
		for (final int[] col : distToFinish)
			Arrays.fill(col, Integer.MAX_VALUE);

		final ArrayDeque<int[]> queue = new ArrayDeque<>();
		final double fx1 = finishLine.getX1(), fy1 = finishLine.getY1();
		final double fx2 = finishLine.getX2(), fy2 = finishLine.getY2();
		final int samples = (int) Math.ceil(Math.hypot(fx2 - fx1, fy2 - fy1) * 2) + 1;
		for (int i = 0; i <= samples; i++) {
			final double t = (double) i / samples;
			final int x = (int) Math.round(fx1 + t * (fx2 - fx1));
			final int y = (int) Math.round(fy1 + t * (fy2 - fy1));
			if (x < 0 || x >= w || y < 0 || y >= h)
				continue;
			if (distToFinish[x][y] != Integer.MAX_VALUE)
				continue;
			distToFinish[x][y] = 0;
			queue.add(new int[]{x, y });
		}

		while (!queue.isEmpty()) {
			final int[] cell = queue.poll();
			final int d = distToFinish[cell[0]][cell[1]];
			for (int dx = -1; dx <= 1; dx++)
				for (int dy = -1; dy <= 1; dy++) {
					if (dx == 0 && dy == 0)
						continue;
					final int nx = cell[0] + dx, ny = cell[1] + dy;
					if (nx < 0 || nx >= w || ny < 0 || ny >= h)
						continue;
					if (distToFinish[nx][ny] != Integer.MAX_VALUE)
						continue;
					if (!trackA.contains(nx, ny) && !startZoneA.contains(nx, ny))
						continue;
					distToFinish[nx][ny] = d + 1;
					queue.add(new int[]{nx, ny });
				}
		}
	}

	private void autoPlaceAiPlayers() {
		while (subgamestate < players.length && players[subgamestate].isAi()) {
			final int[] pos = findStartPosition();
			if (pos == null) {
				dispMessage(players[subgamestate].getName() + " (AI) couldn't find a start position.");
				return;
			}
			players[subgamestate].setPosition(pos);
			subgamestate++;
		}
	}

	private int[] findStartPosition() {
		if (startZone == null)
			return null;
		float minX = Float.MAX_VALUE, maxX = -Float.MAX_VALUE;
		float minY = Float.MAX_VALUE, maxY = -Float.MAX_VALUE;
		for (int i = 0; i < 4; i++) {
			minX = Math.min(minX, startZone[0][i]);
			maxX = Math.max(maxX, startZone[0][i]);
			minY = Math.min(minY, startZone[1][i]);
			maxY = Math.max(maxY, startZone[1][i]);
		}
		final int xMin = (int) Math.floor(minX), xMax = (int) Math.ceil(maxX);
		final int yMin = (int) Math.floor(minY), yMax = (int) Math.ceil(maxY);
		final int playerNum = players[subgamestate].getNumber();
		for (int x = xMin; x <= xMax; x++)
			for (int y = yMin; y <= yMax; y++) {
				if (!startZoneA.contains(x, y))
					continue;
				if (isCrashingPlayer(x, y, playerNum))
					continue;
				return new int[]{x, y };
			}
		return null;
	}

	private void updatePlaceStatus() {
		final boolean allPlaced = subgamestate >= players.length;
		gameFrame.getBtnOK().setEnabled(allPlaced);
		gameFrame.setStatus(allPlaced ? "Click OK to confirm." : "Place player " + players[subgamestate].getName());
	}

	private boolean isTrackSelfIntersecting() {
		final LinkedList<int[]> closed = new LinkedList<>();
		for (final int[] p : track.getLeft())
			closed.add(p);
		final Iterator<int[]> it = track.getRight().descendingIterator();
		while (it.hasNext())
			closed.add(it.next());
		closed.add(track.getLeft().getFirst());
		return checkIntersect(closed, closed, false);
	}

	private void initGameLog() {
		gameLog.setLength(0);
		turnCounter = 0;
		gameLog.append("# Theoretical Racing ").append(VERSION).append(" — game log\n");
		gameLog.append("# Grid ").append(gameCols).append("x").append(gameRows).append("\n");
		gameLog.append("trackLeft=").append(pointListToString(track.getLeft())).append("\n");
		gameLog.append("trackRight=").append(pointListToString(track.getRight())).append("\n");
		for (final Player pl : players) {
			gameLog.append("player").append(pl.getNumber()).append(" name=").append(pl.getName()).append(" kind=")
					.append(pl.getKind().name()).append(" start=").append(pl.getPosition()[0]).append(",").append(pl.getPosition()[1])
					.append("\n");
		}
		gameLog.append("# turns: turn player kind dir vBefore→vAfter pos→newPos outcome\n");
	}

	private void logMove(final Player pl, final Direction d, final int[] velBefore, final int[] posBefore, final int[] velAfter,
			final int[] posAfter, final String outcome) {
		turnCounter++;
		gameLog.append(turnCounter).append(" p").append(pl.getNumber()).append(" ").append(pl.getKind().name()).append(" ").append(d.name())
				.append(" v(").append(velBefore[0]).append(",").append(velBefore[1]).append(")→(").append(velAfter[0]).append(",")
				.append(velAfter[1]).append(") (").append(posBefore[0]).append(",").append(posBefore[1]).append(")→(").append(posAfter[0])
				.append(",").append(posAfter[1]).append(") ").append(outcome).append("\n");
	}

	private void writeGameLog() {
		try {
			Files.createDirectories(gameLogPath().getParent());
			Files.writeString(gameLogPath(), gameLog.toString());
		} catch (final IOException e) {
			e.printStackTrace();
		}
	}

	private void buildTrackGeometry() {
		final int[] fL = track.getLeft().getLast();
		final int[] fR = track.getRight().getLast();
		finishLine = new Line2D.Double(fL[0], fL[1], fR[0], fR[1]);
		computeFinishForward();
		rui.setFinishLine(fL, fR);
		startZone = makeStartZone(track.getLeft().getFirst(), track.getRight().getFirst());
		rui.setStartZone(startZone);
		final Path2D.Float p = new Path2D.Float();
		p.moveTo(startZone[0][0], startZone[1][0]);
		for (int i = 1; i < 4; i++)
			p.lineTo(startZone[0][i], startZone[1][i]);
		p.closePath();
		startZoneA = getToleranceExpandedShape(p);
		trackA = getToleranceExpandedShape(newPrefilledPath(track.getLeft(), track.getRight()));
		rui.finishTrack();
		computeDistMap();
		startReachabilityCompute();
		saveTrackToProperties();
	}

	/** Kick off reverse-BFS reachability on a daemon thread so it doesn't block the UI. */
	private void startReachabilityCompute() {
		reachabilityReady = false;
		final Thread t = new Thread(() -> {
			computeReachability();
			reachabilityReady = true;
		}, "reachability-compute");
		t.setDaemon(true);
		reachabilityThread = t;
		t.start();
	}

	/** Wait for reachability if the background BFS hasn't finished yet. */
	private void ensureReachabilityReady() {
		if (reachabilityReady)
			return;
		final Thread t = reachabilityThread;
		if (t == null)
			return;
		try {
			t.join();
		} catch (final InterruptedException e) {
			Thread.currentThread().interrupt();
		}
	}

	private static String pointListToString(final LinkedList<int[]> list) {
		final StringBuilder sb = new StringBuilder();
		boolean first = true;
		for (final int[] p : list) {
			if (!first)
				sb.append(";");
			sb.append(p[0]).append(",").append(p[1]);
			first = false;
		}
		return sb.toString();
	}

	private static LinkedList<int[]> parsePointList(final String s) {
		final LinkedList<int[]> result = new LinkedList<>();
		if (s == null || s.isEmpty())
			return result;
		for (final String pair : s.split(";")) {
			final String[] xy = pair.split(",");
			if (xy.length != 2)
				continue;
			try {
				result.add(new int[]{Integer.parseInt(xy[0].trim()), Integer.parseInt(xy[1].trim()) });
			} catch (final NumberFormatException ignored) {
			}
		}
		return result;
	}

	private void saveTrackToProperties() {
		if (track == null)
			return;
		prop.put("lastTrackLeft", pointListToString(track.getLeft()));
		prop.put("lastTrackRight", pointListToString(track.getRight()));
	}

	public static boolean hasLastTrack(final Properties prop) {
		final String left = prop.getProperty("lastTrackLeft");
		final String right = prop.getProperty("lastTrackRight");
		return left != null && right != null && !left.isEmpty() && !right.isEmpty();
	}

	private boolean loadLastTrack() {
		final LinkedList<int[]> left = parsePointList(prop.getProperty("lastTrackLeft"));
		final LinkedList<int[]> right = parsePointList(prop.getProperty("lastTrackRight"));
		if (left.size() < 2 || right.size() < 2)
			return false;
		track = new Track();
		for (final int[] p : left)
			track.addLeft(p[0], p[1]);
		for (final int[] p : right)
			track.addRight(p[0], p[1]);
		rui.setTrack(track);
		if (isTrackSelfIntersecting()) {
			track = null;
			rui.setTrack(null);
			return false;
		}
		buildTrackGeometry();
		return true;
	}

	/** Activated when the game grid is clicked at grid coords (x,y). */
	public void clickedGrid(final int x, final int y) {
		if (gamestate == GameState.DRAWTRACK) {
			if (track == null) {
				track = new Track();
				rui.setTrack(track);
			}
			final boolean isLeft = subgamestate == 0;
			if (isLeft)
				track.addLeft(x, y);
			else
				track.addRight(x, y);

			final LinkedList<int[]> active = isLeft ? track.getLeft() : track.getRight();
			final LinkedList<int[]> other = isLeft ? track.getRight() : track.getLeft();
			if (lastSegmentIntersects(active, other)) {
				dispMessage("Tracks intersect.");
				if (isLeft)
					track.removeLastLeft();
				else
					track.removeLastRight();
			}

		} else if (gamestate == GameState.PLACEPLAYERS) {
			if (subgamestate >= players.length) {
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
			autoPlaceAiPlayers();
			updatePlaceStatus();
		}
		gameFrame.repaint();
	}

	/** Activated when the OK button is clicked. */
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
			if (isTrackSelfIntersecting()) {
				dispMessage("Track/start line/finish line intersect.");
				return;
			}
			gamestate = GameState.PLACEPLAYERS;
			subgamestate = 0;
			gameFrame.getBtnOK().setEnabled(false);
			buildTrackGeometry();
			autoPlaceAiPlayers();
			updatePlaceStatus();
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
			initGameLog();
			maybeAiTurn();
		} else if (gamestate == GameState.EXIT)
			System.exit(0);
		gameFrame.repaint();
	}

	/** Activated when the Undo button is clicked. */
	public void clickedUndo() {
		if (gamestate == GameState.DRAWTRACK) {
			if (subgamestate == 0)
				track.removeLastLeft();
			else
				track.removeLastRight();
		} else if (gamestate == GameState.PLACEPLAYERS && subgamestate > 0) {
			subgamestate--;
			players[subgamestate].setPosition(new int[]{Player.INIT_POS, Player.INIT_POS });
			updatePlaceStatus();
		} else if (gamestate == GameState.PLAY) {
			do {
				subgamestate--;
				if (subgamestate == -1)
					subgamestate = players.length - 1;
			} while (players[subgamestate].isFinished() || players[subgamestate].isAi());
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

	private void dispMessage(final String s) {
		if (autoMode) {
			System.out.println("[msg] " + s);
			return;
		}
		JOptionPane.showMessageDialog(gameFrame, s, NAME, JOptionPane.OK_OPTION);
	}

	/** Exit the game after a prompt. */
	public void exitMe() {
		if (confirmAndSave("Do you really want to exit?", GameState.EXIT))
			System.exit(0);
	}

	/** Restart the game after a prompt. */
	public void restartMe() {
		if (confirmAndSave("Do you really want to restart?", GameState.RESTART)) {
			gameFrame.dispose();
			SwingUtilities.invokeLater(() -> new RaceGame(prop).start());
		}
	}

	private boolean confirmAndSave(final String question, final GameState transientState) {
		final GameState old = gamestate;
		gamestate = transientState;
		final int answer = JOptionPane.showConfirmDialog(gameFrame, question, NAME, JOptionPane.YES_NO_OPTION);
		if (answer == JOptionPane.YES_OPTION) {
			saveProperties();
			return true;
		}
		gamestate = old;
		return false;
	}

	/** Atomic property save: write to .tmp then rename. */
	public void saveProperties() {
		final Path target = userPropertiesPath();
		try {
			Files.createDirectories(target.getParent());
		} catch (final IOException e) {
			e.printStackTrace();
			return;
		}
		final Path tmp = target.resolveSibling(target.getFileName().toString() + ".tmp");
		try (OutputStream out = Files.newOutputStream(tmp)) {
			prop.store(out, null);
		} catch (final IOException e) {
			e.printStackTrace();
			return;
		}
		try {
			Files.move(tmp, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
		} catch (final IOException e) {
			try {
				Files.move(tmp, target, StandardCopyOption.REPLACE_EXISTING);
			} catch (final IOException e2) {
				e2.printStackTrace();
			}
		}
	}

	private Player[] getPlayers() {
		final int n = sanitizeIntProp("nPlayers", 2, 1, maxPlayers);
		final Player[] result = new Player[n];
		for (int i = 0; i < n; i++) {
			final String prefix = "player" + (i + 1);
			final Player.Kind kind = Player.Kind.parse(prop.getProperty(prefix + "Kind"));
			result[i] = new Player(prop.getProperty(prefix + "Name"), i + 1, parseColor(prefix + "Color", i), kind);
		}
		return result;
	}

	/** True iff a player other than playerNumber is at (x,y). */
	private boolean isCrashingPlayer(final int x, final int y, final int playerNumber) {
		for (final Player player : players) {
			if (player.getNumber() == playerNumber || player.isFinished())
				continue;
			if (player.getPosition()[0] == x && player.getPosition()[1] == y)
				return true;
		}
		return false;
	}

	private void redoPlayerLabels() {
		for (int i = 0; i < players.length; i++)
			gameFrame.setPlayerInfo(players[i].statusLabel(), i);
	}

}
