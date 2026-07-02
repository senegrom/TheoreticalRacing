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
	/** Precomputed {@link #isRoomy} (depth 0 / depth 1) over all alive states;
	 *  non-alive states stay unset (isRoomy is false there — they can have
	 *  neither legal alive successors nor finish crossings). */
	private BitSet	roomy0, roomy1;
	/** Precomputed minimum |v|^2 over all states reachable in <= 2 braking
	 *  moves (legal edges, alive landings; the Roomy variant additionally
	 *  requires roomy1 landings). Unsigned bytes, clamped to 255. Together
	 *  they answer {@link #canShedSpeed}(..., depth=2, ...) in O(1). */
	private byte[]	minShed2, minShed2Roomy;
	/** Per-state certified speed budget, squared (unsigned bytes; 255 =
	 *  uncertified / non-alive): the SECOND-smallest entry of the multiset
	 *  {state's own |v|^2} plus {minShed2 of every qualifying braking
	 *  successor} -- i.e. the minimal T^2 such that at least two independent
	 *  blind braking descents reach |v| <= T within the
	 *  {@link #countBrakeProofs} horizon. Built by {@link #sweepCertSq};
	 *  consumed via {@link #certBudget} by AI2 only. */
	private byte[]	certSq;

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

		// --- Precomputed AI maps ------------------------------------------
		// One-time sweeps over the alive states turn the runtime questions
		// isRoomy(depth <= 1) and canShedSpeed(depth == 2) into O(1) lookups
		// with exactly the original semantics (see those methods). Non-alive
		// states keep unset/255 entries: they can have neither legal alive
		// successors (alive-closure of the BFS above) nor finish crossings
		// (those are seeded with turns == 1), so isRoomy is false there, and
		// the shed maps are only ever consulted behind an isAlive check.
		final short[] legalAlive = buildLegalAliveMask(total);
		final long tMask = System.nanoTime();
		final BitSet r0 = new BitSet(total);
		sweepRoomy(legalAlive, null, r0);
		final long tRoomy0 = System.nanoTime();
		final BitSet r1 = new BitSet(total);
		sweepRoomy(legalAlive, r0, r1);
		final long tRoomy1 = System.nanoTime();
		final byte[] shed0 = initMinShed(total);
		final byte[] shed = relaxMinShed(relaxMinShed(shed0, legalAlive, null), legalAlive, null);
		final long tShed = System.nanoTime();
		final byte[] shedRoomy = relaxMinShed(relaxMinShed(shed0, legalAlive, r1), legalAlive, r1);
		final long tShedRoomy = System.nanoTime();
		final byte[] cert = sweepCertSq(legalAlive, shed);
		final long tCert = System.nanoTime();
		roomy0 = r0;
		roomy1 = r1;
		minShed2 = shed;
		minShed2Roomy = shedRoomy;
		certSq = cert;
		if (autoMode)
			System.out.printf(
					"[reachability] init=%.0fms bfs=%.0fms mask=%.0fms roomy0=%.0fms roomy1=%.0fms shed=%.0fms shedRoomy=%.0fms cert=%.0fms total=%.0fms alive=%d%n",
					(tInit - t0) / 1e6, (tBfs - tInit) / 1e6, (tMask - tBfs) / 1e6, (tRoomy0 - tMask) / 1e6,
					(tRoomy1 - tRoomy0) / 1e6, (tShed - tRoomy1) / 1e6, (tShedRoomy - tShed) / 1e6, (tCert - tShedRoomy) / 1e6,
					(tCert - t0) / 1e6, aliveStates.cardinality());
	}

	/** Sweep helper for {@link #computeReachability}: per-alive-state bitmask
	 *  over {@link Direction} ordinals — bit d set iff the successor under d
	 *  stays in the velocity range, its edge is geometry-legal and its landing
	 *  is alive (the shared non-crossing qualifying conditions of
	 *  {@link #isRoomy} and {@link #canShedSpeed}). Every legality query here
	 *  hits {@code edgeLegalCache}: when the BFS popped an alive landing it
	 *  already checked the edge from the landing's unique cell-predecessor,
	 *  which is exactly the source cell used here. */
	private short[] buildLegalAliveMask(final int total) {
		final Direction[] dirs = Direction.values();
		final int span = 2 * aliveVMAX + 1;
		final short[] mask = new short[total];
		for (int idx = aliveStates.nextSetBit(0); idx >= 0; idx = aliveStates.nextSetBit(idx + 1)) {
			int rest = idx;
			final int vy = rest % span - aliveVMAX;
			rest /= span;
			final int vx = rest % span - aliveVMAX;
			rest /= span;
			final int y = rest % aliveH;
			final int x = rest / aliveH;
			short m = 0;
			for (int di = 0; di < dirs.length; di++) {
				final int nvx = vx + dirs[di].dx;
				final int nvy = vy + dirs[di].dy;
				if (Math.abs(nvx) > aliveVMAX || Math.abs(nvy) > aliveVMAX)
					continue;
				final int nx = x + nvx;
				final int ny = y + nvy;
				// Alive-first equals legal-first in result (both pure
				// predicates); alive-first keeps the HashMap lookups to alive
				// landings only (all of which are cache hits, see above).
				if (isAlive(nx, ny, nvx, nvy) && isMoveLegalGeometryCached(x, y, nx, ny))
					m |= 1 << di;
			}
			mask[idx] = m;
		}
		return mask;
	}

	/** Sweep helper for {@link #computeReachability}: sets in {@code out} every
	 *  alive state with >= 2 qualifying continuations per the {@link #isRoomy}
	 *  rule. A successor qualifies if it crosses the finish, or its
	 *  {@code legalAlive} bit is set and (when {@code req != null}) its state
	 *  bit is set in {@code req}. {@code req == null} computes depth 0;
	 *  {@code req == roomy0} computes depth 1. */
	private void sweepRoomy(final short[] legalAlive, final BitSet req, final BitSet out) {
		final Direction[] dirs = Direction.values();
		final int span = 2 * aliveVMAX + 1;
		for (int idx = aliveStates.nextSetBit(0); idx >= 0; idx = aliveStates.nextSetBit(idx + 1)) {
			int rest = idx;
			final int vy = rest % span - aliveVMAX;
			rest /= span;
			final int vx = rest % span - aliveVMAX;
			rest /= span;
			final int y = rest % aliveH;
			final int x = rest / aliveH;
			final int mask = legalAlive[idx];
			int count = 0;
			for (int di = 0; di < dirs.length; di++) {
				final int nvx = vx + dirs[di].dx;
				final int nvy = vy + dirs[di].dy;
				if (Math.abs(nvx) > aliveVMAX || Math.abs(nvy) > aliveVMAX)
					continue;
				final int nx = x + nvx;
				final int ny = y + nvy;
				if (crossesFinish(x, y, nx, ny)) {
					count++;
				} else {
					if ((mask & 1 << di) == 0)
						continue;
					if (req != null && !req.get(aliveIdx(nx, ny, nvx, nvy)))
						continue;
					count++;
				}
				if (count >= 2) {
					out.set(idx);
					break;
				}
			}
		}
	}

	/** Sweep helper for {@link #computeReachability}: |v|^2 (clamped to 255)
	 *  for every alive state, 255 for non-alive states (never read — the
	 *  runtime consults the shed maps only behind an isAlive check). */
	private byte[] initMinShed(final int total) {
		final int span = 2 * aliveVMAX + 1;
		final byte[] arr = new byte[total];
		Arrays.fill(arr, (byte) 0xFF);
		for (int idx = aliveStates.nextSetBit(0); idx >= 0; idx = aliveStates.nextSetBit(idx + 1)) {
			final int vy = idx % span - aliveVMAX;
			final int vx = idx / span % span - aliveVMAX;
			arr[idx] = (byte) Math.min(vx * vx + vy * vy, 255);
		}
		return arr;
	}

	/** Sweep helper for {@link #computeReachability}: one Jacobi relaxation of
	 *  the min-|v|^2-reachable-by-braking map (unsigned bytes): out[s] =
	 *  min(in[s], min in[succ]) over successors in the braking cone (|v|
	 *  non-increasing — the integer-square compare is exactly the runtime's
	 *  hypot compare) whose {@code legalAlive} bit is set and (when
	 *  {@code roomyReq != null}) whose state bit is set in {@code roomyReq} —
	 *  exactly the per-step conditions of {@link #canShedSpeed}. */
	private byte[] relaxMinShed(final byte[] in, final short[] legalAlive, final BitSet roomyReq) {
		final Direction[] dirs = Direction.values();
		final int span = 2 * aliveVMAX + 1;
		final byte[] out = new byte[in.length];
		Arrays.fill(out, (byte) 0xFF);
		for (int idx = aliveStates.nextSetBit(0); idx >= 0; idx = aliveStates.nextSetBit(idx + 1)) {
			int rest = idx;
			final int vy = rest % span - aliveVMAX;
			rest /= span;
			final int vx = rest % span - aliveVMAX;
			rest /= span;
			final int y = rest % aliveH;
			final int x = rest / aliveH;
			final int mask = legalAlive[idx];
			final int v2 = vx * vx + vy * vy;
			int best = in[idx] & 0xFF;
			for (int di = 0; di < dirs.length; di++) {
				if ((mask & 1 << di) == 0)
					continue;
				final int nvx = vx + dirs[di].dx;
				final int nvy = vy + dirs[di].dy;
				if (nvx * nvx + nvy * nvy > v2)
					continue; // braking cone only
				final int succ = aliveIdx(x + nvx, y + nvy, nvx, nvy);
				if (roomyReq != null && !roomyReq.get(succ))
					continue;
				final int cand = in[succ] & 0xFF;
				if (cand < best)
					best = cand;
			}
			out[idx] = (byte) best;
		}
		return out;
	}

	/** Sweep helper for {@link #computeReachability}: per-state certified speed
	 *  budget, squared (unsigned bytes, 255 = uncertified). For every alive
	 *  state the sweep collects {@code shed[succ]} (= minShed2, the min |v|^2
	 *  shed-able in <= 2 further braking moves) of each qualifying braking
	 *  successor -- braking cone by |v|^2, legal edge, alive landing: exactly
	 *  the first-move semantics of {@link #countBrakeProofs} minus the runtime
	 *  opponent-prediction filter -- plus the state's own |v|^2 (the zero-move
	 *  descent: the state is already at that speed). The entry written is the
	 *  SECOND-smallest of that multiset: the minimal target T^2 such that at
	 *  least two independent blind braking descents reach |v| <= T within the
	 *  proof horizon; 255 if fewer than two entries qualify. Non-alive states
	 *  keep 255 (only ever consulted behind an alive candidate). */
	private byte[] sweepCertSq(final short[] legalAlive, final byte[] shed) {
		final Direction[] dirs = Direction.values();
		final int span = 2 * aliveVMAX + 1;
		final byte[] arr = new byte[shed.length];
		Arrays.fill(arr, (byte) 0xFF);
		for (int idx = aliveStates.nextSetBit(0); idx >= 0; idx = aliveStates.nextSetBit(idx + 1)) {
			int rest = idx;
			final int vy = rest % span - aliveVMAX;
			rest /= span;
			final int vx = rest % span - aliveVMAX;
			rest /= span;
			final int y = rest % aliveH;
			final int x = rest / aliveH;
			final int mask = legalAlive[idx];
			final int v2 = vx * vx + vy * vy;
			// Two smallest entries of the witness multiset, seeded with the
			// state's own |v|^2 (the zero-move descent).
			int min1 = Math.min(v2, 255);
			int min2 = 256; // sentinel: fewer than two entries so far
			for (int di = 0; di < dirs.length; di++) {
				if ((mask & 1 << di) == 0)
					continue;
				final int nvx = vx + dirs[di].dx;
				final int nvy = vy + dirs[di].dy;
				if (nvx * nvx + nvy * nvy > v2)
					continue; // braking cone only
				final int cand = shed[aliveIdx(x + nvx, y + nvy, nvx, nvy)] & 0xFF;
				if (cand < min1) {
					min2 = min1;
					min1 = cand;
				} else if (cand < min2)
					min2 = cand;
			}
			arr[idx] = (byte) Math.min(min2, 255);
		}
		return arr;
	}

	/** Certified per-state speed budget for AI2's pace discipline: the minimal
	 *  integer target T such that at least two independent blind braking
	 *  descents from (x,y,vx,vy) reach |v| <= T within the
	 *  {@link #countBrakeProofs} horizon -- {@code ceil(sqrt(certSq))} over
	 *  the precomputed map (the uncertified 255 maps to 16, an effectively
	 *  unbounded budget). Replaces the global constant base 5 of the
	 *  pre-certification widthBudget with local, heading- and speed-exact map
	 *  truth. Conservative 0 for states outside the precomputed space or
	 *  before the map exists (never the case after ensureReachabilityReady). */
	private int certBudget(final int x, final int y, final int vx, final int vy) {
		if (certSq == null)
			return 0;
		if (Math.abs(vx) > aliveVMAX || Math.abs(vy) > aliveVMAX)
			return 0;
		if (x < 0 || y < 0 || x >= aliveW || y >= aliveH)
			return 0;
		return (int) Math.ceil(Math.sqrt(certSq[aliveIdx(x, y, vx, vy)] & 0xFF));
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

	/** Dispatches to AI1 or AI2. AI2 is now the FROZEN STANDARD (the AI2.6
	 *  open-running depth-2 champion); AI1 is forked from it and is the one we
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

	/** AI1 frontier only: explicit search depth for the depth-2 soft search
	 *  ({@link #searchMinTurnsCountedSoft2}) -- my next TWO moves are searched
	 *  explicitly, each ply priced against its own simulated opponent round
	 *  (world1 at stepIdx 0, world2 at stepIdx 1) before the opponent-blind
	 *  map takes over. AI1_LOOKAHEAD stays shared with the frozen AI2. */
	private final static int		AI1_DEEP_LOOKAHEAD	= 2;

	/** AI1 frontier only: soft price for landing, at the second explicit search
	 *  ply (stepIdx 1), on a round-2-simulated body -- applied in OPEN RUNNING
	 *  only (v4): with any rival within squared distance 36 of my current cell
	 *  the price is disabled for the move (occupancy2 = null), because a
	 *  two-rounds-out detour ceded while a rival is close enough to take the
	 *  vacated line converts saved time into lost PLACES (h2h forensics:
	 *  price-all lost 4.540/4.460, ahead-only lost harder 4.597/4.403 -- a
	 *  coordination asymmetry, since in all-frontier fields the collective
	 *  spreading is what buys the pace). Probes proved the price LEVEL is a
	 *  dead knob (2.0 == 3.0 bench-identical; 0.0 reverts to the exact frozen
	 *  baseline -- the entire depth-2 gain flows through this pricing), so the
	 *  structure, not the level, carries the design. */
	private final static double	AI1_PLY2_PRICE	= 3.0;

	/**
	 * AI1 (EXPERIMENTAL FRONTIER): forked verbatim from the AI2.6 standard.
	 * Identical to {@link #optimalMoveAI2} at fork time; improvements are
	 * applied here while AI2 stays frozen as the reference.
	 */
	private Direction optimalMoveAI1(final int[] pos, final int[] vel, final int playerNum) {
		final int[][][] predictedSteps = predictedOpponentSteps(playerNum, 1);
		// Vacated-cell awareness: a fast-moving opponent (|v| >= 3) will have
		// moved through/off its predicted cell by the time I could occupy it --
		// blocking those cells causes phantom detours. Null out transiting
		// opponents' predictions; only slow/parked rivals stay blocked.
		for (final Player p : players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pv = p.getVelocity();
			if (Math.hypot(pv[0], pv[1]) >= 3)
				predictedSteps[0][p.getNumber() - 1] = null;
		}
		final int[][] predicted = predictedSteps[0];
		// v4 pack gate for the ply-2 price: any rival within squared distance
		// 36 of where I stand means a ceded line is a ceded PLACE -- the ply-2
		// price is disabled for this whole move (see AI1_PLY2_PRICE).
		final boolean packNearby = countNearbyOpponents(pos, playerNum, 36) >= 1;

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
			final int ownTurns = turnsToFinish(newX, newY, newVx, newVy);
			if (ownTurns == Integer.MAX_VALUE)
				continue;

			// TWO-ROUND SOFT WORLD-STEP (the experiment): simulate TWO whole
			// rounds in actual turn order, conditioned on THIS candidate
			// landing. worlds[0] answers the round-r+1 questions (safe
			// successors, ply-1 pricing) exactly as before; worlds[1] gives the
			// bodies' cells when I make my round-r+2 move, pricing the second
			// explicit search ply -- but only in OPEN RUNNING (v4, see
			// AI1_PLY2_PRICE): with any rival within squared distance 36 the
			// ply-2 price is disabled (null), which is proven bit-identical to
			// the frozen standard's behavior, so the frontier never cedes a
			// contested line in a pack.
			final int[][][] worlds = simulateTwoRounds(playerNum, newX, newY);
			final int[][] world = worlds[0];
			final double[] deepCounted = searchMinTurnsCountedSoft2(newX, newY, newVx, newVy, AI1_DEEP_LOOKAHEAD, 0,
					predictedSteps, playerNum, worlds[0], packNearby ? null : worlds[1]);
			final double deep = deepCounted[0];
			// Soft trap: if every depth-2 continuation is blocked but the state
			// itself can still reach the finish, keep the move alive with a
			// large finite surcharge instead of hard-skipping (which would drop
			// the AI to the foresight-free bestLegal/fallback pick).
			final double costToFinish = deep == Double.MAX_VALUE ? ownTurns + 20.0 : deep;

			// Optimism-floored safe-successor count: the sim removing phantom
			// stale bodies ADDS safe successors (pace), while its model-dependent
			// pessimism (a mispredicted fast leader) can only LOWER the timed
			// count -- so max() with the frozen count keeps the optimism and
			// discards the pessimism, never more cautious than the crash-free
			// frozen standard.
			final int d2SafeCount = Math.max(countFutureSafeSuccessors(newX, newY, newVx, newVy, playerNum, predicted),
					countFutureSafeSuccessorsTimed(newX, newY, newVx, newVy, playerNum, world));
			final double trapPenalty = d2SafeCount == 0 ? 50.0
					: d2SafeCount == 1 ? 2.0
							: d2SafeCount == 2 ? 0.5
									: 0.0;
			final double speed = Math.hypot(newVx, newVy);
			// Per-state certified budget with a legacy floor: the map-certified
			// minimal target T (>= 2 independent blind braking descents reach
			// |v| <= T from this candidate state) governs above the floor; the
			// floor preserves the zero-penalty regime at low speed.
			final int widthBudget = Math.max(5, certBudget(newX, newY, newVx, newVy)) + d2SafeCount;
			final double overSpeed = Math.max(0.0, speed - widthBudget);
			double speedCap = overSpeed * overSpeed * 0.4;
			double uncertified = 0.0;
			if (speed > 4.0) {
				// Pace waiver: >= 2 alive braking descents prove the over-budget speed
				// is sheddable on the empty track -- waive the penalty entirely.
				if (overSpeed > 0 && countBrakeProofs(newX, newY, newVx, newVy, widthBudget, predicted, null, false) >= 2)
					speedCap = 0.0;
				// Trap surcharge, graded by certified escape count: zero roomy
				// escapes is a genuine trap; a single knife-edge escape is
				// survivable and only worth a mild detour.
				if (hasConvergingOpponentAhead(newX, newY, playerNum, speed)) {
					final int proofs = countBrakeProofs(newX, newY, newVx, newVy, widthBudget, predicted, null, true);
					if (proofs < 2)
						uncertified = (speed - 4.0) * (proofs == 0 ? 2.5 : 1.0);
				}
			}
			// Pack-gated knife-edge corner-entry brake: price roomy-successor
			// scarcity when a pack is packed at a corner entry (>= 2 rivals
			// within squared distance 36 and <= 1 roomy escape) -- fires where
			// the converging-opponent surcharge reads false. The pack gate
			// spares the lone fast knife-edge that is the racing line on tight
			// circuits, so only genuine corner-entry traffic jams brake.
			double cornerEntry = 0.0;
			if (speed > 4.0) {
				final int roomySucc = countRoomySuccessors(newX, newY, newVx, newVy, playerNum);
				if (roomySucc <= 1 && countNearbyOpponents(new int[]{newX, newY }, playerNum, 36) >= 2)
					cornerEntry = (speed - 4.0) * (roomySucc == 0 ? 3.0 : 1.5);
			}
			final double conflict = cellOccupiedByPrediction(newX, newY, predicted) ? 3.0 : 0.0;
			final double spread = opponentSpreadPenalty(newX, newY, playerNum);
			// Racing-line momentum tie-break: among moves of otherwise-equal cost,
			// prefer the one carrying more usable speed.
			final double momentum = AI2_MOMENTUM_TIEBREAK * speed;
			// Plateau-width robustness tie-break: prefer candidates whose best
			// follow-up is achievable many ways over knife-edge lines.
			final double robustness = AI2_PLATEAU_TIEBREAK * Math.min((int) deepCounted[1], 5);
			final double score = costToFinish + trapPenalty + speedCap + uncertified + cornerEntry + conflict + spread - momentum - robustness;
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

	/** {@link #pureMinTurnsMove} against a simulated occupancy instead of the
	 *  live player positions: used by {@link #simulateRound}. occupied[i] is
	 *  the current simulated cell of player i+1 (null = ignore). */
	private Direction pureMinTurnsMoveSim(final int[] pos, final int[] vel, final int[][] occupied) {
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
			if (cellOccupiedByPrediction(newX, newY, occupied))
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

	/** Step every live opponent one move in ACTUAL turn order, conditioned on
	 *  my candidate landing: players numbered after me take their round-r move
	 *  (they see my landing and all earlier sim moves), then players numbered
	 *  before me take their round-r+1 move. Movers use the greedy policy
	 *  against the updating occupancy; a mover with no legal unoccupied move
	 *  stays put. Returns occupancy[i] = player (i+1)'s simulated cell when I
	 *  make my next move (null for me and finished players).
	 *  <p>
	 *  Velocity note: every mover steps once from its CURRENT velocity, and
	 *  that is timing-exact for BOTH classes -- later movers' current state is
	 *  pre-round-r (their round-r move is the one simulated), while earlier
	 *  movers already moved this round, so their current velocity is
	 *  post-round-r and one step from it IS their round-r+1 move. Only the
	 *  policy (greedy min-turns instead of each opponent's real scorer) is
	 *  approximate; the sequencing and mutual exclusion are exact. */
	private int[][] simulateRound(final int playerNum, final int candX, final int candY) {
		final int[][] occ = new int[players.length][];
		for (final Player p : players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			occ[p.getNumber() - 1] = p.getPosition();
		}
		final int[][] blocked = occ.clone();           // shallow: shares position refs
		blocked[playerNum - 1] = new int[]{candX, candY }; // my landing blocks
		// later movers (round r), then earlier movers (round r+1), each once
		for (int pass = 0; pass < 2; pass++) {
			for (final Player p : players) {
				final boolean later = p.getNumber() > playerNum;
				if (p.getNumber() == playerNum || p.isFinished() || (pass == 0 ? !later : later))
					continue;
				final int idx = p.getNumber() - 1;
				final int[] cur = occ[idx];
				blocked[idx] = null;                   // the mover vacates its own cell
				final Direction d = pureMinTurnsMoveSim(cur, p.getVelocity(), blocked);
				int nx = cur[0], ny = cur[1];
				if (d != null) {
					final int nvx = p.getVelocity()[0] + d.dx;
					final int nvy = p.getVelocity()[1] + d.dy;
					if (Math.abs(nvx) <= AI_MAX_SPEED && Math.abs(nvy) <= AI_MAX_SPEED
							&& isMoveLegalGeometryCached(cur[0], cur[1], cur[0] + nvx, cur[1] + nvy)
							&& !cellOccupiedByPrediction(cur[0] + nvx, cur[1] + nvy, blocked)) {
						nx = cur[0] + nvx;
						ny = cur[1] + nvy;
					}
				}
				occ[idx] = new int[]{nx, ny };
				blocked[idx] = occ[idx];
			}
		}
		occ[playerNum - 1] = null;
		return occ;
	}

	/** AI1 frontier only: {@link #simulateRound} extended one more round.
	 *  Round 1 replays simulateRound's algorithm EXACTLY (same two-pass turn
	 *  order, same mutual exclusion via {@code blocked}, a blocked mover stays
	 *  put) while additionally tracking each opponent's simulated velocity --
	 *  bookkeeping only, it cannot alter any round-1 decision, so
	 *  {@code result[0]} is cell-identical to {@code simulateRound(...)}. Round
	 *  2 then runs the same two-pass loop again from the round-1 cells and
	 *  velocities, yielding {@code result[1]} = the opponents' cells when I
	 *  make my round-r+2 move. For round 2 my candidate cell no longer blocks
	 *  ({@code blocked[playerNum-1] = null}): by then I have moved off it to a
	 *  cell this sim cannot know, and leaving the stale cell blocked would wall
	 *  off a lane I have actually vacated -- an honest approximation.
	 *  Returns {@code {world1, world2}}. */
	private int[][][] simulateTwoRounds(final int playerNum, final int candX, final int candY) {
		final int[][] occ = new int[players.length][];
		final int[][] simVel = new int[players.length][];
		for (final Player p : players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			occ[p.getNumber() - 1] = p.getPosition();
			simVel[p.getNumber() - 1] = p.getVelocity();
		}
		final int[][] blocked = occ.clone();           // shallow: shares position refs
		blocked[playerNum - 1] = new int[]{candX, candY }; // my landing blocks round 1
		simulateRoundPass(playerNum, occ, simVel, blocked);
		occ[playerNum - 1] = null;
		final int[][] world1 = occ.clone();            // round 2 reassigns cells, never mutates them
		blocked[playerNum - 1] = null;                 // round 2: I have vacated my candidate cell
		simulateRoundPass(playerNum, occ, simVel, blocked);
		occ[playerNum - 1] = null;
		return new int[][][]{world1, occ };
	}

	/** One full two-pass opponent round for {@link #simulateTwoRounds}: every
	 *  live opponent steps once from its simulated cell/velocity in actual
	 *  turn order (players numbered after me first, then players numbered
	 *  before me), updating {@code occ}/{@code simVel}/{@code blocked} in
	 *  place. Mirrors {@link #simulateRound}'s loop exactly; the only addition
	 *  is recording the step a legal mover already took into {@code simVel}
	 *  (a stay-put mover keeps its old velocity). */
	private void simulateRoundPass(final int playerNum, final int[][] occ, final int[][] simVel, final int[][] blocked) {
		for (int pass = 0; pass < 2; pass++) {
			for (final Player p : players) {
				final boolean later = p.getNumber() > playerNum;
				if (p.getNumber() == playerNum || p.isFinished() || (pass == 0 ? !later : later))
					continue;
				final int idx = p.getNumber() - 1;
				final int[] cur = occ[idx];
				blocked[idx] = null;                   // the mover vacates its own cell
				final int[] vel = simVel[idx];
				final Direction d = pureMinTurnsMoveSim(cur, vel, blocked);
				int nx = cur[0], ny = cur[1];
				if (d != null) {
					final int nvx = vel[0] + d.dx;
					final int nvy = vel[1] + d.dy;
					if (Math.abs(nvx) <= AI_MAX_SPEED && Math.abs(nvy) <= AI_MAX_SPEED
							&& isMoveLegalGeometryCached(cur[0], cur[1], cur[0] + nvx, cur[1] + nvy)
							&& !cellOccupiedByPrediction(cur[0] + nvx, cur[1] + nvy, blocked)) {
						nx = cur[0] + nvx;
						ny = cur[1] + nvy;
						simVel[idx] = new int[]{nvx, nvy };
					}
				}
				occ[idx] = new int[]{nx, ny };
				blocked[idx] = occ[idx];
			}
		}
	}

	/** Soft-priced timing-exact search (AI1 frontier): like the hard
	 *  {@code searchMinTurnsTimed} but a stepIdx-0 move onto a sim-occupied
	 *  cell is PRICED (+3.0, the conflict weight) instead of hard-skipped, so
	 *  a mispredicted body costs a detour rather than acting as a wall/vacancy
	 *  -- graceful degradation when the greedy sim disagrees with a real
	 *  opponent. Geometry stays hard; a finish crossing escapes pricing. */
	private double searchMinTurnsSoft(final int x, final int y, final int vx, final int vy, final int levels, final int stepIdx,
			final int[][][] predictedSteps, final int playerNum, final int[][] occupancy) {
		if (levels == 0) {
			final int t = turnsToFinish(x, y, vx, vy);
			return t == Integer.MAX_VALUE ? Double.MAX_VALUE : t;
		}
		double best = Double.MAX_VALUE;
		for (final Direction d : Direction.values()) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (Math.abs(nvx) > AI_MAX_SPEED || Math.abs(nvy) > AI_MAX_SPEED)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (crossesFinish(x, y, nx, ny))
				return 1;
			if (!isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			double price = 0.0;
			if (stepIdx == 0) {
				if (cellOccupiedByPrediction(nx, ny, occupancy))
					price = 3.0;
			} else {
				if (isCrashingPlayer(nx, ny, playerNum))
					continue;
				if (stepIdx < predictedSteps.length && cellOccupiedByPrediction(nx, ny, predictedSteps[stepIdx]))
					continue;
			}
			final double sub = searchMinTurnsSoft(nx, ny, nvx, nvy, levels - 1, stepIdx + 1, predictedSteps, playerNum, occupancy);
			if (sub == Double.MAX_VALUE)
				continue;
			if (1.0 + price + sub < best)
				best = 1.0 + price + sub;
		}
		return best;
	}

	/** Soft-priced plateau-counting twin of {@link #searchMinTurnsSoft} (AI1
	 *  frontier): the same soft stepIdx-0 pricing (+3.0 for a sim-occupied
	 *  landing instead of a hard skip) and the same finish short-circuit, but it
	 *  additionally reports the plateau width -- how many follow-up moves achieve
	 *  the minimum cost -- for the robustness tie-break. Returns
	 *  {@code {min, countAtMin}} as doubles; the prices are exact small
	 *  constants so the plateau compare stays an exact {@code ==}. A
	 *  finish-crossing follow-up short-circuits as {@code {1, 9}} (the global
	 *  minimum, maximally robust). Recurses into {@link #searchMinTurnsSoft}. */
	private double[] searchMinTurnsCountedSoft(final int x, final int y, final int vx, final int vy, final int levels,
			final int stepIdx, final int[][][] predictedSteps, final int playerNum, final int[][] occupancy) {
		double best = Double.MAX_VALUE;
		int countAtMin = 0;
		for (final Direction d : Direction.values()) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (Math.abs(nvx) > AI_MAX_SPEED || Math.abs(nvy) > AI_MAX_SPEED)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (crossesFinish(x, y, nx, ny))
				return new double[]{1, 9 };
			if (!isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			double price = 0.0;
			if (stepIdx == 0) {
				if (cellOccupiedByPrediction(nx, ny, occupancy))
					price = 3.0;
			} else {
				if (isCrashingPlayer(nx, ny, playerNum))
					continue;
				if (stepIdx < predictedSteps.length && cellOccupiedByPrediction(nx, ny, predictedSteps[stepIdx]))
					continue;
			}
			final double sub = searchMinTurnsSoft(nx, ny, nvx, nvy, levels - 1, stepIdx + 1, predictedSteps, playerNum, occupancy);
			if (sub == Double.MAX_VALUE)
				continue;
			final double total = 1.0 + price + sub;
			if (total < best) {
				best = total;
				countAtMin = 1;
			} else if (total == best)
				countAtMin++;
		}
		return new double[]{best, countAtMin };
	}

	/** Depth-2 twin of {@link #searchMinTurnsSoft} (AI1 frontier only): takes
	 *  the SECOND simulated round {@code occupancy2} (nullable -- the v4 pack
	 *  gate passes null to disable ply-2 pricing entirely, see
	 *  {@link #AI1_PLY2_PRICE}) and, at {@code stepIdx == 1}, prices a landing
	 *  on a round-2-simulated body {@link #AI1_PLY2_PRICE}, so the second
	 *  explicit ply is priced against the world as simulated when I make that
	 *  move. Variant B2: the stepIdx-1 {@code isCrashingPlayer}
	 *  hard-skip is REMOVED here (opponents' round-r-start cells are doubly
	 *  stale two plies out -- phantom walls that prune real escape lanes); the
	 *  only opponent term at stepIdx 1 is the occupancy2 price. The
	 *  (inert, length-1 predictedSteps) prediction check is kept. */
	private double searchMinTurnsSoft2(final int x, final int y, final int vx, final int vy, final int levels, final int stepIdx,
			final int[][][] predictedSteps, final int playerNum, final int[][] occupancy, final int[][] occupancy2) {
		if (levels == 0) {
			final int t = turnsToFinish(x, y, vx, vy);
			return t == Integer.MAX_VALUE ? Double.MAX_VALUE : t;
		}
		double best = Double.MAX_VALUE;
		for (final Direction d : Direction.values()) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (Math.abs(nvx) > AI_MAX_SPEED || Math.abs(nvy) > AI_MAX_SPEED)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (crossesFinish(x, y, nx, ny))
				return 1;
			if (!isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			double price = 0.0;
			if (stepIdx == 0) {
				if (cellOccupiedByPrediction(nx, ny, occupancy))
					price = 3.0;
			} else {
				if (stepIdx < predictedSteps.length && cellOccupiedByPrediction(nx, ny, predictedSteps[stepIdx]))
					continue;
				if (stepIdx == 1 && occupancy2 != null && cellOccupiedByPrediction(nx, ny, occupancy2))
					price = AI1_PLY2_PRICE;
			}
			final double sub = searchMinTurnsSoft2(nx, ny, nvx, nvy, levels - 1, stepIdx + 1, predictedSteps, playerNum,
					occupancy, occupancy2);
			if (sub == Double.MAX_VALUE)
				continue;
			if (1.0 + price + sub < best)
				best = 1.0 + price + sub;
		}
		return best;
	}

	/** Depth-2 twin of {@link #searchMinTurnsCountedSoft} (AI1 frontier only):
	 *  same behavioral change as {@link #searchMinTurnsSoft2} -- at
	 *  {@code stepIdx == 1} a landing on a round-2-simulated body
	 *  ({@code occupancy2}, nullable via the v4 pack gate) is PRICED
	 *  {@link #AI1_PLY2_PRICE}, and (variant B2) the doubly-stale
	 *  {@code isCrashingPlayer} phantom-wall hard-skip is removed -- and it
	 *  recurses into {@link #searchMinTurnsSoft2}. Prices stay exact small
	 *  constants, so the plateau compare remains an exact {@code ==}. */
	private double[] searchMinTurnsCountedSoft2(final int x, final int y, final int vx, final int vy, final int levels,
			final int stepIdx, final int[][][] predictedSteps, final int playerNum, final int[][] occupancy,
			final int[][] occupancy2) {
		double best = Double.MAX_VALUE;
		int countAtMin = 0;
		for (final Direction d : Direction.values()) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (Math.abs(nvx) > AI_MAX_SPEED || Math.abs(nvy) > AI_MAX_SPEED)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (crossesFinish(x, y, nx, ny))
				return new double[]{1, 9 };
			if (!isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			double price = 0.0;
			if (stepIdx == 0) {
				if (cellOccupiedByPrediction(nx, ny, occupancy))
					price = 3.0;
			} else {
				if (stepIdx < predictedSteps.length && cellOccupiedByPrediction(nx, ny, predictedSteps[stepIdx]))
					continue;
				if (stepIdx == 1 && occupancy2 != null && cellOccupiedByPrediction(nx, ny, occupancy2))
					price = AI1_PLY2_PRICE;
			}
			final double sub = searchMinTurnsSoft2(nx, ny, nvx, nvy, levels - 1, stepIdx + 1, predictedSteps, playerNum,
					occupancy, occupancy2);
			if (sub == Double.MAX_VALUE)
				continue;
			final double total = 1.0 + price + sub;
			if (total < best) {
				best = total;
				countAtMin = 1;
			} else if (total == best)
				countAtMin++;
		}
		return new double[]{best, countAtMin };
	}

	/**
	 * Timing-exact variant of {@link #countFutureSafeSuccessors} (AI1
	 * frontier), used to floor the safe-successor count with the sim's
	 * optimism. The successors counted here are ply-2 questions -- moves I
	 * would make in round r+1, by which time every live opponent has moved
	 * exactly once (see {@link #searchMinTurnsSoft} for the move-order
	 * derivation) -- so the stale-body check ({@link #isCrashingPlayer}) and
	 * the nulled prediction check are replaced by a single test against
	 * {@code occupancy}, the simulated round-step positions of all live
	 * opponents (current cells as conservative fallback where unmoved).
	 */
	private int countFutureSafeSuccessorsTimed(final int x, final int y, final int vx, final int vy, final int playerNum,
			final int[][] occupancy) {
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
			if (cellOccupiedByPrediction(nx, ny, occupancy))
				continue;
			if (isAlive(nx, ny, nvx, nvy))
				count++;
		}
		return count;
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
	 * Same search as {@link #searchMinTurns} but additionally counts how many
	 * follow-up moves achieve the minimum (the "plateau width"). A candidate
	 * whose best continuation is achievable many ways is a robust, wide line;
	 * one whose minimum hinges on a single follow-up is a knife-edge. Used by
	 * AI2's robustness tie-break. Returns {min, countAtMin}; a finish-crossing
	 * follow-up short-circuits as {1, 9} (the global minimum, maximally robust).
	 */
	private int[] searchMinTurnsCounted(final int x, final int y, final int vx, final int vy, final int levels, final int stepIdx,
			final int[][][] predictedSteps, final int playerNum) {
		int best = Integer.MAX_VALUE;
		int countAtMin = 0;
		for (final Direction d : Direction.values()) {
			final int nvx = vx + d.dx;
			final int nvy = vy + d.dy;
			if (Math.abs(nvx) > AI_MAX_SPEED || Math.abs(nvy) > AI_MAX_SPEED)
				continue;
			final int nx = x + nvx;
			final int ny = y + nvy;
			if (crossesFinish(x, y, nx, ny))
				return new int[]{1, 9 };
			if (!isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			if (isCrashingPlayer(nx, ny, playerNum))
				continue;
			if (stepIdx < predictedSteps.length && cellOccupiedByPrediction(nx, ny, predictedSteps[stepIdx]))
				continue;
			final int sub = searchMinTurns(nx, ny, nvx, nvy, levels - 1, stepIdx + 1, predictedSteps, playerNum);
			if (sub == Integer.MAX_VALUE)
				continue;
			if (1 + sub < best) {
				best = 1 + sub;
				countAtMin = 1;
			} else if (1 + sub == best)
				countAtMin++;
		}
		return new int[]{best, countAtMin };
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
	 * AI2 (FROZEN STANDARD): the AI2.6 open-running depth-2 champion — the
	 * AI2.5 corner-entry-brake base plus a second explicit search ply priced
	 * against a second simulated opponent round ({@link #simulateTwoRounds} /
	 * {@link #searchMinTurnsCountedSoft2}), active in open running only: with
	 * any rival within squared distance 36 the ply-2 price is disabled, which
	 * is bit-identical to AI2.5's behavior, so packs are never conceded (the
	 * pricing is cooperative-optimal but competitively dominated -- pricing
	 * packs LOST the mixed-field h2h despite faster solo pace). Gates: pace
	 * f=154 c=0 mv=64.19 vs 64.25; h2h 4.483 vs 4.517 c=0; --slow 80.33 vs
	 * 80.48. Don't change AI2 — it's the yardstick; AI1 is the experimental
	 * copy being improved.
	 */
	private Direction optimalMoveAI2(final int[] pos, final int[] vel, final int playerNum) {
		final int[][][] predictedSteps = predictedOpponentSteps(playerNum, 1);
		// Vacated-cell awareness: a fast-moving opponent (|v| >= 3) will have
		// moved through/off its predicted cell by the time I could occupy it --
		// blocking those cells causes phantom detours. Null out transiting
		// opponents' predictions; only slow/parked rivals stay blocked.
		for (final Player p : players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pv = p.getVelocity();
			if (Math.hypot(pv[0], pv[1]) >= 3)
				predictedSteps[0][p.getNumber() - 1] = null;
		}
		final int[][] predicted = predictedSteps[0];
		// v4 pack gate for the ply-2 price: any rival within squared distance
		// 36 of where I stand means a ceded line is a ceded PLACE -- the ply-2
		// price is disabled for this whole move (see AI1_PLY2_PRICE).
		final boolean packNearby = countNearbyOpponents(pos, playerNum, 36) >= 1;

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
			final int ownTurns = turnsToFinish(newX, newY, newVx, newVy);
			if (ownTurns == Integer.MAX_VALUE)
				continue;

			// TWO-ROUND SOFT WORLD-STEP (the experiment): simulate TWO whole
			// rounds in actual turn order, conditioned on THIS candidate
			// landing. worlds[0] answers the round-r+1 questions (safe
			// successors, ply-1 pricing) exactly as before; worlds[1] gives the
			// bodies' cells when I make my round-r+2 move, pricing the second
			// explicit search ply -- but only in OPEN RUNNING (v4, see
			// AI1_PLY2_PRICE): with any rival within squared distance 36 the
			// ply-2 price is disabled (null), which is proven bit-identical to
			// the frozen standard's behavior, so the frontier never cedes a
			// contested line in a pack.
			final int[][][] worlds = simulateTwoRounds(playerNum, newX, newY);
			final int[][] world = worlds[0];
			final double[] deepCounted = searchMinTurnsCountedSoft2(newX, newY, newVx, newVy, AI1_DEEP_LOOKAHEAD, 0,
					predictedSteps, playerNum, worlds[0], packNearby ? null : worlds[1]);
			final double deep = deepCounted[0];
			// Soft trap: if every depth-2 continuation is blocked but the state
			// itself can still reach the finish, keep the move alive with a
			// large finite surcharge instead of hard-skipping (which would drop
			// the AI to the foresight-free bestLegal/fallback pick).
			final double costToFinish = deep == Double.MAX_VALUE ? ownTurns + 20.0 : deep;

			// Optimism-floored safe-successor count: the sim removing phantom
			// stale bodies ADDS safe successors (pace), while its model-dependent
			// pessimism (a mispredicted fast leader) can only LOWER the timed
			// count -- so max() with the frozen count keeps the optimism and
			// discards the pessimism, never more cautious than the crash-free
			// frozen standard.
			final int d2SafeCount = Math.max(countFutureSafeSuccessors(newX, newY, newVx, newVy, playerNum, predicted),
					countFutureSafeSuccessorsTimed(newX, newY, newVx, newVy, playerNum, world));
			final double trapPenalty = d2SafeCount == 0 ? 50.0
					: d2SafeCount == 1 ? 2.0
							: d2SafeCount == 2 ? 0.5
									: 0.0;
			final double speed = Math.hypot(newVx, newVy);
			// Per-state certified budget with a legacy floor: the map-certified
			// minimal target T (>= 2 independent blind braking descents reach
			// |v| <= T from this candidate state) governs above the floor; the
			// floor preserves the zero-penalty regime at low speed.
			final int widthBudget = Math.max(5, certBudget(newX, newY, newVx, newVy)) + d2SafeCount;
			final double overSpeed = Math.max(0.0, speed - widthBudget);
			double speedCap = overSpeed * overSpeed * 0.4;
			double uncertified = 0.0;
			if (speed > 4.0) {
				// Pace waiver: >= 2 alive braking descents prove the over-budget speed
				// is sheddable on the empty track -- waive the penalty entirely.
				if (overSpeed > 0 && countBrakeProofs(newX, newY, newVx, newVy, widthBudget, predicted, null, false) >= 2)
					speedCap = 0.0;
				// Trap surcharge, graded by certified escape count: zero roomy
				// escapes is a genuine trap; a single knife-edge escape is
				// survivable and only worth a mild detour.
				if (hasConvergingOpponentAhead(newX, newY, playerNum, speed)) {
					final int proofs = countBrakeProofs(newX, newY, newVx, newVy, widthBudget, predicted, null, true);
					if (proofs < 2)
						uncertified = (speed - 4.0) * (proofs == 0 ? 2.5 : 1.0);
				}
			}
			// Pack-gated knife-edge corner-entry brake: price roomy-successor
			// scarcity when a pack is packed at a corner entry (>= 2 rivals
			// within squared distance 36 and <= 1 roomy escape) -- fires where
			// the converging-opponent surcharge reads false. The pack gate
			// spares the lone fast knife-edge that is the racing line on tight
			// circuits, so only genuine corner-entry traffic jams brake.
			double cornerEntry = 0.0;
			if (speed > 4.0) {
				final int roomySucc = countRoomySuccessors(newX, newY, newVx, newVy, playerNum);
				if (roomySucc <= 1 && countNearbyOpponents(new int[]{newX, newY }, playerNum, 36) >= 2)
					cornerEntry = (speed - 4.0) * (roomySucc == 0 ? 3.0 : 1.5);
			}
			final double conflict = cellOccupiedByPrediction(newX, newY, predicted) ? 3.0 : 0.0;
			final double spread = opponentSpreadPenalty(newX, newY, playerNum);
			// Racing-line momentum tie-break: among moves of otherwise-equal cost,
			// prefer the one carrying more usable speed.
			final double momentum = AI2_MOMENTUM_TIEBREAK * speed;
			// Plateau-width robustness tie-break: prefer candidates whose best
			// follow-up is achievable many ways over knife-edge lines.
			final double robustness = AI2_PLATEAU_TIEBREAK * Math.min((int) deepCounted[1], 5);
			final double score = costToFinish + trapPenalty + speedCap + uncertified + cornerEntry + conflict + spread - momentum - robustness;
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
	private final static double	AI2_PLATEAU_TIEBREAK	= 0.05;

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

	/** True iff a live opponent genuinely threatens my escape thread at cell
	 *  (x,y): spatially near (squared distance <= 144), at similar track
	 *  progress (|distAt difference| <= 15 -- not merely across a wall on
	 *  another part of the circuit), and at-or-ahead
	 *  in track progress (smaller-or-similar distAt): a chaser behind cannot
	 *  occupy my escape thread ahead of me, so it shouldn't trigger the trap
	 *  surcharge. The +3 slack keeps side-by-side cars counted. Blockers moving
	 *  at similar-or-higher speed than {@code mySpeed} on open road (roomy
	 *  state, {@link #isRoomy}) are receding -- the gap stays stable and they
	 *  vacate the thread before I arrive -- so they don't count either; a
	 *  same-speed blocker threading a knife-edge stretch still does, because
	 *  it is about to brake (corner-entry compression). */
	private boolean hasConvergingOpponentAhead(final int x, final int y, final int playerNum, final double mySpeed) {
		final int myDist = distAt(x, y);
		if (myDist == Integer.MAX_VALUE)
			return true; // off-map: be conservative
		for (final Player p : players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			final int dx = x - pp[0];
			final int dy = y - pp[1];
			if (dx * dx + dy * dy > 144)
				continue;
			final int oDist = distAt(pp[0], pp[1]);
			if (oDist == Integer.MAX_VALUE || Math.abs(oDist - myDist) > 15 || oDist > myDist + 3)
				continue;
			final int[] pv = p.getVelocity();
			final double oSpeed = Math.hypot(pv[0], pv[1]);
			// Receding blockers don't block: at similar-or-higher speed on
			// OPEN ROAD (roomy state) the gap stays stable and they vacate
			// the thread before I arrive. A blocker threading a knife-edge
			// stretch is about to brake -- compression -- and still counts,
			// whatever its current speed (round-6 lesson: lemans corner-entry
			// packs crash when equal-speed blockers are treated as receding).
			if (oSpeed >= 3.0 && oSpeed >= mySpeed - 1.0 && isRoomy(pp[0], pp[1], pv[0], pv[1], 1))
				continue;
			return true;
		}
		return false;
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

	/**
	 * AI2-only twin of {@link #countFutureSafeSuccessors} keyed on ROOMINESS
	 * rather than mere aliveness, and opponent-blind (geometry + reachability
	 * only). Counts the geometry-legal one-step successors of (x,y,vx,vy) that
	 * are alive AND {@link #isRoomy roomy} at depth 0 -- i.e. escape moves onto
	 * genuinely open road, not alive-but-single-file knife-edge threads. A
	 * finish crossing short-circuits to a large count (a candidate that can end
	 * the race is never a corner-entry trap). Used solely by the AI2 knife-edge
	 * corner-entry brake as the geometric half of that gate; the traffic half
	 * (a pack around the target) is applied separately at the call site, because
	 * the funnel geometry is a fixed property of the state while the danger only
	 * materialises when rivals are packed at the corner entry.
	 */
	private int countRoomySuccessors(final int x, final int y, final int vx, final int vy, final int playerNum) {
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
			if (isAlive(nx, ny, nvx, nvy) && isRoomy(nx, ny, nvx, nvy, 0))
				count++;
		}
		return count;
	}

	/** Count certified braking descents from (x,y,vx,vy) down to targetSpeed
	 *  (see canShedSpeed); proofs are first braking moves that are geometry-legal,
	 *  alive, not on a predicted opponent cell, recursively roomy when
	 *  {@code requireRoomy}, and complete the descent within 2 more moves. If
	 *  bestBrake is non-null, the accel of the proof move with the lowest
	 *  resulting speed (ties: Direction order) is written to it. Stops counting
	 *  at 2 (only "< 2" vs ">= 2" matters).
	 */
	private int countBrakeProofs(final int x, final int y, final int vx, final int vy, final double targetSpeed,
			final int[][] predicted, final int[] bestBrake, final boolean requireRoomy) {
		int proofs = 0;
		double bestSpeed = Double.MAX_VALUE;
		final double speed = Math.hypot(vx, vy);
		for (final Direction bd : Direction.values()) {
			final int bvx = vx + bd.dx;
			final int bvy = vy + bd.dy;
			if (Math.abs(bvx) > AI_MAX_SPEED || Math.abs(bvy) > AI_MAX_SPEED)
				continue;
			final double bSpeed = Math.hypot(bvx, bvy);
			if (bSpeed > speed)
				continue; // braking cone only
			final int bx = x + bvx;
			final int by = y + bvy;
			if (!isMoveLegalGeometryCached(x, y, bx, by))
				continue;
			if (!isAlive(bx, by, bvx, bvy))
				continue;
			if (cellOccupiedByPrediction(bx, by, predicted))
				continue;
			if (requireRoomy && !isRoomy(bx, by, bvx, bvy, 1))
				continue;
			// O(1) fast path via the precomputed min-|v|^2 maps:
			// canShedSpeed(..., 2, ...) succeeds iff SOME state on a <=2-step
			// braking chain has hypot <= targetSpeed, i.e. iff the minimum
			// |v|^2 over those chains is <= targetSpeed^2. Exact for the
			// integral targetSpeed of all callers (the widthBudget <= 14):
			// while targetSpeed^2 < 255 the clamp can't flip the compare.
			// Anything else falls back to the recursive reference code. The
			// aliveIdx access is in range: isAlive above returned true.
			final byte[] shedMap = requireRoomy ? minShed2Roomy : minShed2;
			final boolean shed;
			if (shedMap != null && targetSpeed >= 0 && targetSpeed == Math.rint(targetSpeed) && targetSpeed * targetSpeed < 255.0)
				shed = (shedMap[aliveIdx(bx, by, bvx, bvy)] & 0xFF) <= targetSpeed * targetSpeed;
			else
				shed = canShedSpeed(bx, by, bvx, bvy, targetSpeed, 2, requireRoomy);
			if (shed) {
				proofs++;
				if (bestBrake != null && bSpeed < bestSpeed) {
					bestSpeed = bSpeed;
					bestBrake[0] = bd.dx;
					bestBrake[1] = bd.dy;
				}
				if (proofs >= 2 && bestBrake == null)
					break;
			}
		}
		return proofs;
	}

	/** True iff speed can be reduced to <= targetSpeed within {@code depth} moves
	 *  using only non-speed-increasing, geometry-legal moves through alive
	 *  states -- additionally recursively roomy states when {@code requireRoomy}
	 *  ({@link #isRoomy} -- knife-edge single-file threads don't count).
	 *  Opponent-blind beyond the first move, like the reachability map. */
	private boolean canShedSpeed(final int x, final int y, final int vx, final int vy, final double targetSpeed, final int depth,
			final boolean requireRoomy) {
		if (Math.hypot(vx, vy) <= targetSpeed)
			return true;
		if (depth == 0)
			return false;
		final double speed = Math.hypot(vx, vy);
		for (final Direction d : Direction.values()) {
			final int nvx = vx + d.dx;
			final int nvy = vy + d.dy;
			if (Math.abs(nvx) > AI_MAX_SPEED || Math.abs(nvy) > AI_MAX_SPEED)
				continue;
			if (Math.hypot(nvx, nvy) > speed)
				continue; // braking cone only
			final int nx = x + nvx;
			final int ny = y + nvy;
			if (!isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			if (!isAlive(nx, ny, nvx, nvy))
				continue;
			if (requireRoomy && !isRoomy(nx, ny, nvx, nvy, 1))
				continue;
			if (canShedSpeed(nx, ny, nvx, nvy, targetSpeed, depth - 1, requireRoomy))
				return true;
		}
		return false;
	}

	/** True iff (x,y,vx,vy) has at least two one-step continuations that are
	 *  geometry-legal, alive and -- for depth > 0 -- themselves recursively
	 *  roomy. Finish-crossings count unconditionally. Distinguishes genuinely
	 *  open road from alive-but-knife-edge single-file threads. */
	private boolean isRoomy(final int x, final int y, final int vx, final int vy, final int depth) {
		// O(1) fast path via the maps precomputed in computeReachability()
		// (always ready in practice: ensureReachabilityReady() runs before any
		// AI move). States outside the precomputed space fall through to the
		// recursive body, which handles them exactly as before (its in-range
		// sub-calls hit the maps).
		final BitSet roomyMap = depth == 0 ? roomy0 : depth == 1 ? roomy1 : null;
		if (roomyMap != null && Math.abs(vx) <= aliveVMAX && Math.abs(vy) <= aliveVMAX && x >= 0 && y >= 0 && x < aliveW
				&& y < aliveH)
			return roomyMap.get(aliveIdx(x, y, vx, vy));
		int count = 0;
		for (final Direction d : Direction.values()) {
			final int nvx = vx + d.dx;
			final int nvy = vy + d.dy;
			if (Math.abs(nvx) > AI_MAX_SPEED || Math.abs(nvy) > AI_MAX_SPEED)
				continue;
			final int nx = x + nvx;
			final int ny = y + nvy;
			if (crossesFinish(x, y, nx, ny)) {
				count++;
			} else {
				if (!isMoveLegalGeometryCached(x, y, nx, ny))
					continue;
				if (!isAlive(nx, ny, nvx, nvy))
					continue;
				if (depth > 0 && !isRoomy(nx, ny, nvx, nvy, depth - 1))
					continue;
				count++;
			}
			if (count >= 2)
				return true;
		}
		return false;
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
