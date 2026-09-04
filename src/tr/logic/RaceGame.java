package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Path2D;
import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.Properties;
import java.util.Scanner;
import javax.swing.JOptionPane;
import javax.swing.SwingUtilities;
import javax.swing.Timer;
import tr.gui.GameUI;
import tr.gui.RaceUI;
import tr.gui.StartDialog;

/**
 * Main game logic component of TheoreticRacing.
 *
 * @version 0.3.0
 * @author CGH
 */
public final class RaceGame {
	private static final Direction[] DIRECTIONS = Direction.values();
	final static int			defCols				= 86;
	private final static Color[]		defPlayerColors		= new Color[]{Color.BLUE, Color.RED, Color.GREEN, Color.YELLOW, Color.CYAN,
			Color.ORANGE, Color.GRAY, Color.MAGENTA, Color.BLACK };
	final static int			defRows				= 48;
	private final static int			defWindowX			= 1500;
	private final static int			defWindowY			= 800;
	public final static String			NAME				= "Theoretical Racing";
	public final static String			VERSION				= "0.3.0";

	private int					finishedLast	= 0, finishedFirst = 0;
	/** Multi-lap mode: S/F crossings required to finish (laps property). */
	int							totalLaps		= 1;
	/** Multi-lap gates: [0] short real S/F line, [1] CP1, [2] CP2. */
	Line2D[]					lapGates;
	/** Multi-lap forward: the departure heading of the FIRST boundary
	 *  segments -- the legacy finishFwd uses the tail heading, which can
	 *  disagree at gate 0 when a drawing's end curls (monaco, hungaroring:
	 *  inverted forward seeded backward crossings into a dead pocket). */
	private double				lapFwdX, lapFwdY;
	private int[][]				lapGatePoints;
	/** Multi-lap: blue closing boundary across the two S/F side gaps --
	 *  per side a short polyline following the wall's natural extension. */
	private Line2D[][]			lapClosures;
	private int[][][]			lapClosurePoints;
	/** Gate-0 segment shrunk at both ends: the span a crossing must actually
	 *  intersect. An endpoint-only touch is not a crossing -- otherwise the
	 *  maps route arrivals from the exit side onto a one-cell endpoint tap
	 *  (arrive, stop, creep across), which in traffic is a death queue. */
	private Line2D				lapCrossGate;
	private final static double	LAP_CLOSURE_MAX	= 8.0;
	private boolean				startZoneGone;
	Line2D				finishLine;
	/** Unit vector of the racing direction at the finish line. A move only
	 *  counts as crossing the finish if it travels with this heading (positive
	 *  dot) — blocks the "cross the adjacent finish backward from the start"
	 *  exploit on closed-loop tracks with a small S/F gap. */
	private double				finishFwdX, finishFwdY;
	private final GameUI		gameFrame;
	private volatile GameState	gamestate		= GameState.PRESTART;
	private int					isShowingPrePath	= -1;
	private final int			maxPlayers;
	private final ArrayDeque<MoveSnapshot>	moveHistory	= new ArrayDeque<>();
	Player[]			players;
	private final Properties	prop;
	private RaceUI				rui;
	private float[][]			startZone;
	Area				startZoneA;
	int					subgamestate	= 0;
	Track				track;
	Area				trackA;
	int					gameCols, gameRows;
	private final StringBuilder	gameLog		= new StringBuilder();
	private int					turnCounter	= 0;
	boolean				autoMode	= false;
	/** Batch mode: a finished auto race calls this instead of exiting the
	 *  JVM, letting one process race many seeds (Main.runBatch). */
	private Runnable autoRaceEndHook = null;

	public void setAutoRaceEndHook(final Runnable r) {
		autoRaceEndHook = r;
	}

	/** Complete pre-move state used to undo a human move and every AI reply
	 *  that followed it. Auto-play does not allocate snapshots. */
	private static final class MoveSnapshot {
		final int		finishedFirst;
		final int		finishedLast;
		final int[]	finishedPlaces;
		final int		gameLogLength;
		final int[]	historySizes;
		final int[][]	lapStates;
		final int[][]	positions;
		final boolean	startZoneGone;
		final int		subgamestate;
		final int		turnCounter;
		final int[][]	velocities;

		MoveSnapshot(final RaceGame game) {
			subgamestate = game.subgamestate;
			startZoneGone = game.startZoneGone;
			finishedFirst = game.finishedFirst;
			finishedLast = game.finishedLast;
			turnCounter = game.turnCounter;
			gameLogLength = game.gameLog.length();
			positions = new int[game.players.length][];
			velocities = new int[game.players.length][];
			finishedPlaces = new int[game.players.length];
			historySizes = new int[game.players.length];
			lapStates = new int[game.players.length][];
			for (int i = 0; i < game.players.length; i++) {
				final Player player = game.players[i];
				positions[i] = player.getPosition().clone();
				velocities[i] = player.getVelocity().clone();
				finishedPlaces[i] = player.getFinishedPlace();
				historySizes[i] = player.getHistory().size();
				lapStates[i] = player.lapState();
			}
		}

		void restore(final RaceGame game) {
			game.subgamestate = subgamestate;
			game.finishedFirst = finishedFirst;
			game.finishedLast = finishedLast;
			game.turnCounter = turnCounter;
			game.gameLog.setLength(gameLogLength);
			game.startZoneGone = startZoneGone;
			for (int i = 0; i < game.players.length; i++) {
				final Player player = game.players[i];
				player.setPosition(positions[i].clone());
				player.setVelocity(velocities[i].clone());
				player.setFinishedPlace(finishedPlaces[i]);
				player.restoreLapState(lapStates[i]);
				while (player.getHistory().size() > historySizes[i])
					player.getHistory().removeLast();
			}
		}
	}

	/** Create new RaceGame. Call {@link #start()} afterwards. */
	public RaceGame(final Properties prop) {
		this.prop = prop;
		maxPlayers = sanitizeIntProp("maxPlayers", defPlayerColors.length, 1, defPlayerColors.length);
		sanitizeIntProp("nPlayers", 2, 1, maxPlayers);
		sanitizeIntProp("windowX", defWindowX, 200, 10000);
		sanitizeIntProp("windowY", defWindowY, 200, 10000);
		sanitizeIntProp("gameX", defCols, 2, 500);
		sanitizeIntProp("gameY", defRows, 2, 500);
		totalLaps = sanitizeIntProp("laps", 1, 1, 99);

		for (int i = 0; i < maxPlayers; i++) {
			final String prefix = "player" + (i + 1);
			final String name = prop.getProperty(prefix + "Name");
			prop.put(prefix + "Name", name == null ? "Player " + (i + 1) : name);
			final Color c = parseColor(prefix + "Color", i);
			prop.put(prefix + "Color", c.getRed() + " " + c.getGreen() + " " + c.getBlue());
			prop.put(prefix + "Kind", Player.Kind.parse(prop.getProperty(prefix + "Kind")).name());
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

	/** When set, build geometry + reachability headlessly, dump the
	 *  turnsToFinish map to this path, and exit (no game is played). */
	private String dumpReachPath = null;

	public void setDumpReachPath(final String p) {
		this.dumpReachPath = p;
	}

	/** Override the game-log output path (default: next to the JAR). Lets
	 *  concurrent --auto runs write distinct logs (pair with Main's --props). */
	private Path gameLogOverride = null;
	private Path propertiesOverride = null;

	/** Where saveProperties writes. Set from --props, so a session started on a
	 *  bench profile never writes that profile over the user's own settings. */
	public void setPropertiesPath(final String p) {
		propertiesOverride = Path.of(p);
	}

	public void setGameLogPath(final String p) {
		gameLogOverride = Path.of(p);
	}

	private Path gameLogPath() {
		return gameLogOverride != null ? gameLogOverride : TrackIO.gameLogPath();
	}

	/** When set, answer AI-move queries from a file (for DAgger data): each input
	 *  line "mover;x,y,vx,vy,fin;..." (one group per player) sets the board and
	 *  the reply is the champion AI's move "dx,dy". Headless; exits when done. */
	private String queryInPath = null, queryOutPath = null;
	/** "x,y" start cell for the exact shortest-solo-race search (--optimal-laps). */
	private String optimalStart = null;

	public void setOptimalStart(final String cell) {
		this.optimalStart = cell;
	}

	public void setQueryPaths(final String in, final String out) {
		this.queryInPath = in;
		this.queryOutPath = out;
	}

	private boolean isAutoRace() {
		return autoMode && dumpReachPath == null && queryInPath == null && optimalStart == null;
	}

	private void abortAutoRace(final String message) {
		System.err.println(message);
		System.exit(2);
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
		if (isAutoRace()) {
			for (final Player player : players) {
				if (!player.isAi()) {
					abortAutoRace("--auto requires every configured player to be AI: " + player.getName());
					return;
				}
			}
		}
		final boolean useLast = Boolean.parseBoolean(prop.getProperty("useLastTrack", "false")) || autoMode;
		final boolean trackLoaded = useLast && TrackIO.hasLastTrack(prop) && loadLastTrack();
		if (!autoMode)
			gameFrame.setupUI(rui.getGrid(), this, wx, wy, players);

		if (trackLoaded) {
			gamestate = GameState.PLACEPLAYERS;
			subgamestate = 0;
			gameFrame.setOkEnabled(false);
			autoPlaceAiPlayers();
			updatePlaceStatus();
			gameFrame.repaint();
			if (!autoMode)
				SwingUtilities.invokeLater(this::centerTrackStart);
			if (autoMode && subgamestate == players.length)
				SwingUtilities.invokeLater(this::clickedOK);
			return;
		}
		if (autoMode) {
			System.err.println("Headless mode requires a valid saved track. Aborting.");
			System.exit(2);
		}
		gameFrame.setStatus("Click OK to start.");
		gamestate = GameState.START;
	}

	private boolean checkFinished() {
		if (finishedLast + finishedFirst >= players.length - (players.length == 1 ? 0 : 1)) {
			gamestate = GameState.FINISHED;
			clearPointContainmentCacheForCurrentThread();
			rui.setVelVector(null, -1);
			rui.setPrePath(null);

			final String[] place = new String[players.length + 1];
			for (final Player p : players) {
				if (p.getFinishedPlace() == 0)
					p.setFinishedPlace(finishedFirst + 1);
				place[p.getFinishedPlace()] = p.getName();
			}
			final StringBuilder sb = new StringBuilder("The game has finished.\n");
			for (int i = 1; i <= players.length; i++)
				sb.append("\n").append(i).append(".   ").append(place[i]);
			gameFrame.setStatus("The game has finished");
			gameFrame.repaint();
			gameLog.append("# results\n");
			for (int i = 1; i <= players.length; i++)
				gameLog.append(i).append(". ").append(place[i]).append("\n");
			final boolean logWritten = writeGameLog();
			dispMessage(sb.toString() + (logWritten
					? "\n\nLog written to " + gameLogPath()
					: "\n\nCould not write log to " + gameLogPath()));
			gameFrame.setUndoEnabled(false);
			gameFrame.setDirectionsEnabled(false);
			gameFrame.repaint();
			if (denseEdgeLegalCache != null)
				denseEdgeLegalCache.saveIfDirty();
			if (autoMode) {
				final Runnable hook = autoRaceEndHook;
				autoRaceEndHook = null;
				SwingUtilities.invokeLater(hook != null ? hook : () -> System.exit(0));
			}
			return true;
		}
		return false;
	}

	/** Returns true if the move from `pos` to `newpos` is allowed for player i. */
	boolean isMoveLegal(final int[] pos, final int[] newpos, final int playerNumber) {
		return isMoveLegalGeometry(pos[0], pos[1], newpos[0], newpos[1])
				&& !isCrashingPlayer(newpos[0], newpos[1], playerNumber);
	}

	/** Round 111: conservative legality raster over unit cells. Bit 0 = the
	 *  cell's (margin-padded) closed square is provably fully inside trackA
	 *  or startZoneA (exact Area.contains(rect)); bit 1 = the cell lies in
	 *  the one-cell dilation of a boundary polyline's sampled cover. See
	 *  {@link #fastLegal} for the soundness argument. */
	private byte[] legalRaster;
	private int rasterH;

	/** Immutable exact raster pairs shared only by auto games carrying the same
	 * geometry key. One entry is one byte, so the access-ordered pool is capped
	 * at 64 MiB plus small object overhead. */
	private static final long RASTER_MEMO_MAX_BYTES = 64L << 20;
	private static final java.util.LinkedHashMap<String, RasterMaps> RASTER_MEMO =
			new java.util.LinkedHashMap<>(16, 0.75f, true);
	private static long rasterMemoBytes;

	static final class RasterMaps {
		final byte[] unit;
		final byte[] sub;
		final int unitW;
		final int unitH;
		final int subW;
		final int subH;
		final long byteCount;

		RasterMaps(final byte[] unit, final int unitW, final int unitH,
				final byte[] sub, final int subW, final int subH) {
			if (unit == null || sub == null || unitW <= 0 || unitH <= 0
					|| subW != unitW * SUB_RES || subH != unitH * SUB_RES
					|| (long) unitW * unitH != unit.length
					|| (long) subW * subH != sub.length)
				throw new IllegalArgumentException("invalid legality rasters");
			this.unit = unit;
			this.sub = sub;
			this.unitW = unitW;
			this.unitH = unitH;
			this.subW = subW;
			this.subH = subH;
			byteCount = (long) unit.length + sub.length;
		}
	}

	static synchronized RasterMaps findRasterMaps(final String key,
			final int unitW, final int unitH) {
		if (key == null)
			return null;
		final RasterMaps maps = RASTER_MEMO.get(key);
		return maps != null && maps.unitW == unitW && maps.unitH == unitH
				? maps : null;
	}

	static synchronized RasterMaps publishRasterMaps(final String key,
			final byte[] unit, final int unitW, final int unitH,
			final byte[] sub, final int subW, final int subH,
			final long maxBytes) {
		final RasterMaps created = new RasterMaps(unit, unitW, unitH,
				sub, subW, subH);
		if (key == null || maxBytes < 1 || created.byteCount > maxBytes)
			return created;
		final RasterMaps existing = RASTER_MEMO.get(key);
		if (existing != null && existing.unitW == unitW && existing.unitH == unitH)
			return existing;
		if (existing != null) {
			RASTER_MEMO.remove(key);
			rasterMemoBytes -= existing.byteCount;
		}
		while (!RASTER_MEMO.isEmpty()
				&& rasterMemoBytes + created.byteCount > maxBytes) {
			final java.util.Iterator<java.util.Map.Entry<String, RasterMaps>> it =
					RASTER_MEMO.entrySet().iterator();
			final RasterMaps evicted = it.next().getValue();
			it.remove();
			rasterMemoBytes -= evicted.byteCount;
		}
		RASTER_MEMO.put(key, created);
		rasterMemoBytes += created.byteCount;
		return created;
	}

	static synchronized void clearRasterMemoForTests() {
		RASTER_MEMO.clear();
		rasterMemoBytes = 0;
	}

	private void buildLegalRaster() {
		clearPointContainmentCacheForCurrentThread();
		final int w = gameCols + 2;
		final int h = gameRows + 2;
		final String memoKey = autoMode ? reach.geometryCacheKey() : null;
		final RasterMaps cached = findRasterMaps(memoKey, w, h);
		if (cached != null) {
			legalRaster = cached.unit;
			rasterH = cached.unitH;
			subRaster = cached.sub;
			subW = cached.subW;
			subH = cached.subH;
			return;
		}
		rasterH = h;
		final byte[] r = new byte[w * rasterH];
		for (int cx = 0; cx < w; cx++)
			for (int cy = 0; cy < rasterH; cy++) {
				final double x = cx - 0.001, y = cy - 0.001, s = 1.002;
				if (trackA.contains(x, y, s, s) || startZoneA.contains(x, y, s, s))
					r[cx * rasterH + cy] = 1;
			}
		markPath(r, w, track.getLeft());
		markPath(r, w, track.getRight());
		legalRaster = r;
		buildSubRaster(r, w);
		if (memoKey != null) {
			final RasterMaps shared = publishRasterMaps(memoKey, legalRaster,
					w, rasterH, subRaster, subW, subH, RASTER_MEMO_MAX_BYTES);
			legalRaster = shared.unit;
			rasterH = shared.unitH;
			subRaster = shared.sub;
			subW = shared.subW;
			subH = shared.subH;
		}
	}

	/** Round 112: RES=4 sub-raster refined only where the unit raster cannot
	 *  already prove an edge (boundary band); interior unit cells propagate
	 *  to all 16 subcells wholesale, so the exact Area work scales with the
	 *  track perimeter. Consulted only after the unit-cell walk fails. */
	private static final int SUB_RES = 4;
	private byte[] subRaster;
	private int subW;
	private int subH;
	private final ThreadLocal<PointContainmentCache> pointContainmentCaches =
			ThreadLocal.withInitial(() -> new PointContainmentCache(1 << 18));

	void clearPointContainmentCacheForCurrentThread() {
		pointContainmentCaches.remove();
	}

	private void buildSubRaster(final byte[] unit, final int unitW) {
		final int w = unitW * SUB_RES;
		subW = w;
		subH = rasterH * SUB_RES;
		final byte[] r = new byte[w * subH];
		final double sub = 1.0 / SUB_RES;
		for (int cx = 0; cx < unitW; cx++)
			for (int cy = 0; cy < rasterH; cy++) {
				final byte u = unit[cx * rasterH + cy];
				final boolean interiorClean = u == 1;
				// Refine only the true boundary band: non-clean cells with a
				// clean-interior neighbour. Deep-outside and deep-wall cells
				// stay 0 (the sub-walk correctly fails there), which keeps
				// the exact Area work proportional to the track perimeter.
				boolean refine = false;
				if (!interiorClean)
					for (int nx = cx - 1; nx <= cx + 1 && !refine; nx++)
						for (int ny = cy - 1; ny <= cy + 1; ny++)
							if (nx >= 0 && ny >= 0 && nx < unitW && ny < rasterH
									&& unit[nx * rasterH + ny] == 1) {
								refine = true;
								break;
							}
				if (!interiorClean && !refine)
					continue;
				for (int ox = 0; ox < SUB_RES; ox++)
					for (int oy = 0; oy < SUB_RES; oy++) {
						final int sx = cx * SUB_RES + ox, sy = cy * SUB_RES + oy;
						if (interiorClean) {
							r[sx * subH + sy] = 1;
							continue;
						}
						final double x = (cx + ox * sub) - 0.001, y = (cy + oy * sub) - 0.001;
						if (trackA.contains(x, y, sub + 0.002, sub + 0.002)
								|| startZoneA.contains(x, y, sub + 0.002, sub + 0.002))
							r[sx * subH + sy] = 1;
					}
			}
		markSubPath(r, w, track.getLeft());
		markSubPath(r, w, track.getRight());
		subRaster = r;
	}

	/**
	 * Reuse the conservative sub-raster for the exact legality scan's point
	 * probes. A subcell whose interior bit is set was built from an
	 * Area.contains(rect) proof (with a boundary-covering margin), so every
	 * point in it is inside the track or start zone. Unproven cells retain the
	 * exact Area.contains fallback; this helper can therefore only skip work,
	 * never change a geometry verdict.
	 */
	private boolean containsTrackOrStart(final double x, final double y) {
		final byte[] r = subRaster;
		if (r != null) {
			final int sx = (int) Math.floor(x * SUB_RES);
			final int sy = (int) Math.floor(y * SUB_RES);
			if (sx >= 0 && sy >= 0 && sx < subW && sy < subH
					&& (r[sx * subH + sy] & 1) != 0)
				return true;
		}
		final long xBits = Double.doubleToRawLongBits(x);
		final long yBits = Double.doubleToRawLongBits(y);
		final PointContainmentCache pointCache = pointContainmentCaches.get();
		final byte cached = pointCache.get(xBits, yBits);
		if (cached != 0)
			return cached == PointContainmentCache.TRUE;
		final boolean inside = trackA.contains(x, y) || startZoneA.contains(x, y);
		pointCache.put(xBits, yBits, inside);
		return inside;
	}

	private void markSubPath(final byte[] r, final int w, final java.util.List<int[]> path) {
		for (int i = 1; i < path.size(); i++) {
			final int[] a = path.get(i - 1);
			final int[] b = path.get(i);
			final int steps = 2 * SUB_RES * Math.max(Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1])) + 1;
			final double dx = (double) (b[0] - a[0]) / steps, dy = (double) (b[1] - a[1]) / steps;
			for (int j = 0; j <= steps; j++) {
				final int cx = (int) Math.floor((a[0] + j * dx) * SUB_RES);
				final int cy = (int) Math.floor((a[1] + j * dy) * SUB_RES);
				for (int ox = -1; ox <= 1; ox++)
					for (int oy = -1; oy <= 1; oy++) {
						final int qx = cx + ox, qy = cy + oy;
						if (qx >= 0 && qy >= 0 && qx < w && qy < subH && r[qx * subH + qy] == 1)
							r[qx * subH + qy] = 3;
					}
			}
		}
	}

	/** RES=4 band walk, same proof as the unit walk at subcell scale. */
	private boolean fastLegalSub(final int x1, final int y1, final int x2, final int y2) {
		final byte[] r = subRaster;
		if (r == null)
			return false;
		final int w = r.length / subH;
		final int steps = 2 * SUB_RES * Math.max(Math.abs(x2 - x1), Math.abs(y2 - y1)) + 1;
		final double dx = (double) (x2 - x1) * SUB_RES / steps;
		final double dy = (double) (y2 - y1) * SUB_RES / steps;
		final double sx0 = x1 * (double) SUB_RES, sy0 = y1 * (double) SUB_RES;
		int lastCx = Integer.MIN_VALUE, lastCy = Integer.MIN_VALUE;
		for (int j = 0; j <= steps; j++) {
			final double px = sx0 + j * dx, py = sy0 + j * dy;
			final int cx = (int) Math.floor(px - 0.5), cy = (int) Math.floor(py - 0.5);
			if (cx == lastCx && cy == lastCy)
				continue;
			if (cx < 0 || cy < 0 || cx + 1 >= w || cy + 1 >= subH)
				return false;
			if (r[cx * subH + cy] != 1 || r[cx * subH + cy + 1] != 1
					|| r[(cx + 1) * subH + cy] != 1 || r[(cx + 1) * subH + cy + 1] != 1)
				return false;
			lastCx = cx;
			lastCy = cy;
		}
		return true;
	}

	private void markPath(final byte[] r, final int w, final java.util.List<int[]> path) {
		for (int i = 1; i < path.size(); i++) {
			final int[] a = path.get(i - 1);
			final int[] b = path.get(i);
			final int steps = 2 * Math.max(Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1])) + 1;
			final double dx = (double) (b[0] - a[0]) / steps, dy = (double) (b[1] - a[1]) / steps;
			for (int j = 0; j <= steps; j++) {
				final int cx = (int) Math.floor(a[0] + j * dx), cy = (int) Math.floor(a[1] + j * dy);
				for (int ox = -1; ox <= 1; ox++)
					for (int oy = -1; oy <= 1; oy++) {
						final int qx = cx + ox, qy = cy + oy;
						if (qx >= 0 && qy >= 0 && qx < w && qy < rasterH)
							r[qx * rasterH + qy] |= 2;
					}
			}
		}
	}

	/** Fast path: LEGAL iff the 3x3 dilation of every sampled cell along the
	 *  segment is provably interior and away from both boundary polylines.
	 *  Axis-step is <= 0.5, so every point of the segment falls inside the
	 *  dilation of some sample's cell; interior cells cover all exact-check
	 *  sample points, and the path bitmap's own dilated cover means a
	 *  polyline intersection would need a cell both interior-clean and
	 *  path-marked -- excluded. Returns false to mean "unproven", never
	 *  "illegal". */
	private boolean fastLegal(final int x1, final int y1, final int x2, final int y2) {
		final byte[] r = legalRaster;
		if (r == null)
			return false;
		final int w = r.length / rasterH;
		final int steps = 2 * Math.max(Math.abs(x2 - x1), Math.abs(y2 - y1)) + 1;
		final double dx = (double) (x2 - x1) / steps, dy = (double) (y2 - y1) / steps;
		int lastCx = Integer.MIN_VALUE, lastCy = Integer.MIN_VALUE;
		for (int j = 0; j <= steps; j++) {
			final double px = x1 + j * dx, py = y1 + j * dy;
			// Any segment point lies within 0.5 per axis of some sample, so
			// its cell is one of the 2x2 block at floor(p - 0.5): a 2-wide
			// tube, half the former 3x3 dilation, still a provable cover.
			final int cx = (int) Math.floor(px - 0.5), cy = (int) Math.floor(py - 0.5);
			if (cx == lastCx && cy == lastCy)
				continue;
			if (cx < 0 || cy < 0 || cx + 1 >= w || cy + 1 >= rasterH)
				return false;
			if (r[cx * rasterH + cy] != 1 || r[cx * rasterH + cy + 1] != 1
					|| r[(cx + 1) * rasterH + cy] != 1 || r[(cx + 1) * rasterH + cy + 1] != 1)
				return false;
			lastCx = cx;
			lastCy = cy;
		}
		return true;
	}

	/**
	 * Round 215: is the run-up to a finishing crossing legal? The move may
	 * leave the track only at or after the point where it crosses the line, so
	 * everything strictly before that point must satisfy ordinary containment.
	 * A move that does not reach the line is judged in full.
	 */
	boolean finishRunUpLegal(final int x1, final int y1, final int x2, final int y2) {
		final Line2D line = lapGates != null ? lapCrossGate : finishLine;
		final double px = line.getX1(), py = line.getY1();
		final double rx = line.getX2() - px, ry = line.getY2() - py;
		final double sx = (double) x2 - x1, sy = (double) y2 - y1;
		final double denom = rx * sy - ry * sx;
		double u = 1.0;
		if (denom != 0.0) {
			final double qx = x1 - px, qy = y1 - py;
			final double along = (qx * ry - qy * rx) / denom;
			if (along >= 0.0 && along <= 1.0)
				u = along;
		}
		if (u >= 1.0)
			return isMoveLegalGeometry(x1, y1, x2, y2);
		if (!containsTrackOrStart(x1, y1))
			return false;
		final double ex = x1 + u * sx, ey = y1 + u * sy;
		final int n = Math.max(2, (int) Math.ceil(Math.hypot(ex - x1, ey - y1) * 2));
		for (int j = 1; j < n; j++) {
			final double c = (double) j / n;
			if (!containsTrackOrStart(x1 + c * u * sx, y1 + c * u * sy))
				return false;
		}
		return true;
	}

	/**
	 * Geometry-only legality (no player crash check). The interval scan is
	 * scaled by move length: ~2 samples per unit of euclidean distance. This
	 * keeps cost low for short moves while still catching cases where the line
	 * dips outside the polygon between two border vertices (e.g. tangent moves
	 * across an inside corner of the corridor).
	 */
	boolean isMoveLegalGeometry(final int x1, final int y1, final int x2, final int y2) {
		if (fastLegal(x1, y1, x2, y2) || fastLegalSub(x1, y1, x2, y2))
			return true;
		if (!containsTrackOrStart(x2, y2))
			return false;
		final long dxi = (long) x2 - x1, dyi = (long) y2 - y1;
		final int n = Math.max(2, (int) Math.min(Integer.MAX_VALUE, Math.ceil(Math.hypot(dxi, dyi) * 2)));
		final double dx = (double) dxi / n;
		final double dy = (double) dyi / n;
		for (int j = 1; j < n; j++) {
			final double cx = x1 + j * dx;
			final double cy = y1 + j * dy;
			if (!containsTrackOrStart(cx, cy))
				return false;
		}
		final int[] from = {x1, y1 };
		final int[] to = {x2, y2 };
		// Multi-lap: the blue closing segments are VISUAL -- the containment
		// polygon already seals the boundary gaps physically (its closing edge
		// spans them, and interior sampling catches any excursion), and a
		// physical closure check strangles narrow S/F corridors: approach
		// edges in a 3-wide gate clip the flanking stubs, emptying the maps
		// and blocking real cars alike (monaco alive=1390 of 400k).
		return !TrackGeometry.segmentCrossesPath(from, to, track.getLeft()) && !TrackGeometry.segmentCrossesPath(from, to, track.getRight());
	}

	/** Primitive cache for geometry edges. Reachability is the dominant writer,
	 *  but auto-mode games with identical geometry share the table, so its
	 *  representation must also tolerate unsynchronised concurrent writers. */
	private DenseEdgeLegalCache denseEdgeLegalCache;
	private EdgeLegalCache edgeLegalCache;

	private EdgeLegalCache fallbackEdgeLegalCache() {
		EdgeLegalCache cache = edgeLegalCache;
		if (cache == null) {
			cache = new EdgeLegalCache(1 << 16);
			edgeLegalCache = cache;
		}
		return cache;
	}

	boolean isMoveLegalGeometryCached(final int x1, final int y1, final int x2, final int y2) {
		final DenseEdgeLegalCache dense = denseEdgeLegalCache;
		final int denseIndex = dense == null ? -1 : dense.index(x1, y1, x2, y2);
		if (denseIndex >= 0) {
			final int cached = dense.get(denseIndex);
			if (cached == DenseEdgeLegalCache.LEGAL)
				return true;
			if (cached == DenseEdgeLegalCache.ILLEGAL)
				return false;
			final boolean legal = isMoveLegalGeometry(x1, y1, x2, y2);
			dense.put(denseIndex, legal);
			return legal;
		}
		final long packed = ((long) x1 & 0xFFFF) << 48 | ((long) y1 & 0xFFFF) << 32
				| ((long) x2 & 0xFFFF) << 16 | (long) y2 & 0xFFFF;
		final long key = mixEdgeKey(packed);
		final EdgeLegalCache fallback = fallbackEdgeLegalCache();
		final byte cached = fallback.get(key);
		if (cached != 0)
			return cached == EdgeLegalCache.TRUE;
		final boolean legal = isMoveLegalGeometry(x1, y1, x2, y2);
		fallback.put(key, legal);
		return legal;
	}

	/** Direct cache for in-grid, bounded-delta edges. Round 182: packed as
	 *  two-bit verdict states instead of one byte per
	 *  edge -- the 14MB byte table made nearly every sim lookup a DRAM miss
	 *  (33.7%% of all samples); at 3.6MB the table is L3-resident. Same
	 *  predicate and fill order. Plain int array-element loads and stores are
	 *  tear-free; a stale concurrent update can only erase a verdict to UNKNOWN,
	 *  causing benign recomputation instead of manufacturing a false result.
 *  Round 189: geometry-keyed tables persist beside the reach cache, so
 *  later processes load verdicts instead of re-running AWT geometry. */
	static final class DenseEdgeLegalCache {
		static final int UNKNOWN = 0;
		static final int ILLEGAL = 1;
		static final int LEGAL = 2;
		private static final int DELTA_SPAN = 2 * AI_MAX_SPEED + 1;
		private static final int DELTAS = DELTA_SPAN * DELTA_SPAN;
		private static final java.util.LinkedHashMap<String, DenseEdgeLegalCache> SHARED =
				new java.util.LinkedHashMap<>(16, 0.75f, true);
		private static long sharedEntries;

		final int width;
		final int height;
		final int entries;
		final int[] states;
		private java.nio.file.Path persistPath;
		private boolean dirty;

		private DenseEdgeLegalCache(final int width, final int height,
				final int entries) {
			this.width = width;
			this.height = height;
			this.entries = entries;
			states = new int[(entries + 15) >>> 4];
		}

		int get(final int index) {
			final int shift = (index & 15) << 1;
			return states[index >>> 4] >>> shift & 3;
		}

		void put(final int index, final boolean legal) {
			final int shift = (index & 15) << 1;
			final int mask = 3 << shift;
			final int word = index >>> 4;
			states[word] = states[word] & ~mask | (legal ? LEGAL : ILLEGAL) << shift;
			dirty = true;
		}

		static DenseEdgeLegalCache create(final int width, final int height,
				final long maxEntries) {
			final long entries = (long) width * height * DELTAS;
			if (width <= 0 || height <= 0 || entries <= 0 || entries > maxEntries
					|| entries > Integer.MAX_VALUE)
				return null;
			return new DenseEdgeLegalCache(width, height, (int) entries);
		}

		/** Reuse an exact table for the same immutable track geometry. The pool
		 * is access-ordered and measured in EDGE ENTRIES (2 bits each since
		 * round 182). A table larger than the pool cap remains private. */
		static synchronized DenseEdgeLegalCache shared(final String key,
				final int width, final int height, final long maxEntries,
				final long maxPoolEntries) {
			if (key == null)
				return create(width, height, maxEntries);
			final DenseEdgeLegalCache existing = SHARED.get(key);
			if (existing != null && existing.width == width && existing.height == height)
				return existing;
			if (existing != null) {
				SHARED.remove(key);
				sharedEntries -= existing.entries;
			}
			final DenseEdgeLegalCache created = create(width, height, maxEntries);
			if (created == null)
				return null;
			created.persistPath = java.nio.file.Path.of(key + ".edges");
			created.tryLoadPersisted();
			if (created.entries > maxPoolEntries)
				return created;
			while (!SHARED.isEmpty()
					&& sharedEntries + created.entries > maxPoolEntries) {
				final java.util.Iterator<java.util.Map.Entry<String, DenseEdgeLegalCache>> it =
						SHARED.entrySet().iterator();
				final DenseEdgeLegalCache evicted = it.next().getValue();
				it.remove();
				sharedEntries -= evicted.entries;
			}
			SHARED.put(key, created);
			sharedEntries += created.entries;
			return created;
		}

		/** Round 189: load the persisted verdict table (<geometry-key>.edges).
		 *  Verdicts are identical whether computed or loaded; any size, header
		 *  or CRC mismatch silently leaves the table empty. */
		private void tryLoadPersisted() {
			if (persistPath == null)
				return;
			try {
				final byte[] raw = java.nio.file.Files.readAllBytes(persistPath);
				if (raw.length != 16 + 4 * states.length + 4)
					return;
				final java.nio.ByteBuffer buf = java.nio.ByteBuffer.wrap(raw);
				if (buf.getInt() != 0x45443139 || buf.getInt() != width
						|| buf.getInt() != height || buf.getInt() != entries)
					return;
				final java.util.zip.CRC32 crc = new java.util.zip.CRC32();
				crc.update(raw, 16, 4 * states.length);
				if ((int) crc.getValue()
						!= java.nio.ByteBuffer.wrap(raw, raw.length - 4, 4).getInt())
					return;
				buf.asIntBuffer().get(states, 0, states.length);
			} catch (final IOException e) {
				// best effort: an unreadable file only costs the re-fill
			}
		}

		/** Best-effort atomic save; a failure only costs the next process its
		 *  re-fill. Concurrent savers publish whole tables via rename, and all
		 *  writers hold identical verdicts, so last-writer-wins is benign. */
		void saveIfDirty() {
			if (persistPath == null || !dirty)
				return;
			dirty = false;
			final byte[] raw = new byte[16 + 4 * states.length + 4];
			final java.nio.ByteBuffer buf = java.nio.ByteBuffer.wrap(raw);
			buf.putInt(0x45443139).putInt(width).putInt(height).putInt(entries);
			buf.asIntBuffer().put(states, 0, states.length);
			final java.util.zip.CRC32 crc = new java.util.zip.CRC32();
			crc.update(raw, 16, 4 * states.length);
			java.nio.ByteBuffer.wrap(raw, raw.length - 4, 4).putInt((int) crc.getValue());
			try {
				TrackIO.writeAtomically(persistPath, out -> out.write(raw));
			} catch (final IOException e) {
				System.err.println("[edges] cache write failed: " + e);
			}
		}

		int index(final int x1, final int y1, final int x2, final int y2) {
			final int dx = x2 - x1, dy = y2 - y1;
			if (x1 < 0 || y1 < 0 || x1 >= width || y1 >= height
					|| dx < -AI_MAX_SPEED || dx > AI_MAX_SPEED
					|| dy < -AI_MAX_SPEED || dy > AI_MAX_SPEED)
				return -1;
			return ((x1 * height + y1) * DELTA_SPAN + dx + AI_MAX_SPEED)
					* DELTA_SPAN + dy + AI_MAX_SPEED;
		}
	}

	/** Open-addressed long-to-boolean map. A separate state byte means every
	 *  64-bit key, including zero, is representable. Keys arrive already mixed,
	 *  so their low bits can select the initial slot directly. */
	static final class EdgeLegalCache {
		static final byte FALSE = 1;
		static final byte TRUE = 2;

		private long[] keys;
		private int mask;
		private int resizeAt;
		private int size;
		private byte[] states;

		EdgeLegalCache(final int initialCapacity) {
			if (initialCapacity < 1 || initialCapacity > 1 << 30)
				throw new IllegalArgumentException("invalid cache capacity");
			int capacity = 4;
			while (capacity < initialCapacity)
				capacity <<= 1;
			allocate(capacity);
		}

		byte get(final long key) {
			int slot = (int) key & mask;
			while (states[slot] != 0) {
				if (keys[slot] == key)
					return states[slot];
				slot = slot + 1 & mask;
			}
			return 0;
		}

		void put(final long key, final boolean value) {
			if (size >= resizeAt)
				grow();
			int slot = (int) key & mask;
			while (states[slot] != 0) {
				if (keys[slot] == key) {
					states[slot] = value ? TRUE : FALSE;
					return;
				}
				slot = slot + 1 & mask;
			}
			keys[slot] = key;
			states[slot] = value ? TRUE : FALSE;
			size++;
		}

		private void allocate(final int capacity) {
			keys = new long[capacity];
			states = new byte[capacity];
			mask = capacity - 1;
			resizeAt = capacity - capacity / 3;
		}

		private void grow() {
			if (keys.length == 1 << 30)
				throw new IllegalStateException("geometry cache is too large");
			final long[] oldKeys = keys;
			final byte[] oldStates = states;
			allocate(keys.length << 1);
			size = 0;
			for (int i = 0; i < oldStates.length; i++) {
				if (oldStates[i] == 0)
					continue;
				int slot = (int) oldKeys[i] & mask;
				while (states[slot] != 0)
					slot = slot + 1 & mask;
				keys[slot] = oldKeys[i];
				states[slot] = oldStates[i];
				size++;
			}
		}
	}

	/** Primitive exact-double-pair to boolean cache for the residual legality
	 * scan. Different edges repeatedly probe the same rational points; keeping
	 * both coordinate bit patterns avoids the collision risk of compressing a
	 * 128-bit identity into one key while retaining allocation-free lookup. */
	static final class PointContainmentCache {
		static final byte FALSE = 1;
		static final byte TRUE = 2;

		private long[] xKeys;
		private long[] yKeys;
		private int mask;
		private int resizeAt;
		private int size;
		private byte[] states;

		PointContainmentCache(final int initialCapacity) {
			if (initialCapacity < 1 || initialCapacity > 1 << 30)
				throw new IllegalArgumentException("invalid cache capacity");
			int capacity = 4;
			while (capacity < initialCapacity)
				capacity <<= 1;
			allocate(capacity);
		}

		byte get(final long xKey, final long yKey) {
			int slot = (int) pointHash(xKey, yKey) & mask;
			while (states[slot] != 0) {
				if (xKeys[slot] == xKey && yKeys[slot] == yKey)
					return states[slot];
				slot = slot + 1 & mask;
			}
			return 0;
		}

		void clear() {
			java.util.Arrays.fill(states, (byte) 0);
			size = 0;
		}

		void put(final long xKey, final long yKey, final boolean value) {
			if (size >= resizeAt)
				grow();
			int slot = (int) pointHash(xKey, yKey) & mask;
			while (states[slot] != 0) {
				if (xKeys[slot] == xKey && yKeys[slot] == yKey) {
					states[slot] = value ? TRUE : FALSE;
					return;
				}
				slot = slot + 1 & mask;
			}
			xKeys[slot] = xKey;
			yKeys[slot] = yKey;
			states[slot] = value ? TRUE : FALSE;
			size++;
		}

		private void allocate(final int capacity) {
			xKeys = new long[capacity];
			yKeys = new long[capacity];
			states = new byte[capacity];
			mask = capacity - 1;
			resizeAt = capacity - capacity / 3;
		}

		private void grow() {
			if (xKeys.length == 1 << 30)
				throw new IllegalStateException("point cache is too large");
			final long[] oldX = xKeys;
			final long[] oldY = yKeys;
			final byte[] oldStates = states;
			allocate(xKeys.length << 1);
			size = 0;
			for (int i = 0; i < oldStates.length; i++) {
				if (oldStates[i] == 0)
					continue;
				int slot = (int) pointHash(oldX[i], oldY[i]) & mask;
				while (states[slot] != 0)
					slot = slot + 1 & mask;
				xKeys[slot] = oldX[i];
			yKeys[slot] = oldY[i];
				states[slot] = oldStates[i];
				size++;
			}
		}
	}

	private static long pointHash(final long xKey, final long yKey) {
		return mixEdgeKey(xKey ^ Long.rotateLeft(yKey, 29));
	}

	/** Bijective SplitMix64 finalizer. Packed nearby endpoints have strongly
	 *  structured low bits, which would create long probe clusters in the
	 *  primitive table. One-to-one mixing spreads them without changing cache
	 *  identity or introducing collisions. */
	private static long mixEdgeKey(long key) {
		key = (key ^ (key >>> 30)) * 0xbf58476d1ce4e5b9L;
		key = (key ^ (key >>> 27)) * 0x94d049bb133111ebL;
		return key ^ (key >>> 31);
	}


	/** Round 214: exact distance-to-finish for a car with the track to itself.
	 *  Built once per (geometry, laps) and shared by every race in this JVM;
	 *  null when the board is too large for the budget. */
	private static final java.util.HashMap<String, OptimalPotential> OPTIMAL_MEMO =
			new java.util.HashMap<>();
	/** 1.5 GB covers every board in the fleet except the Nordschleife, whose
	 *  89M states would need 1.6 GB -- and which is already within about a
	 *  percent of optimal, so it keeps the ordinary policy. */
	private static final long OPTIMAL_BUDGET_BYTES = 1536L << 20;
	private OptimalPotential optimalPotential;
	private boolean optimalPotentialBuilt;

	OptimalPotential optimalPotential() {
		if (optimalPotentialBuilt)
			return optimalPotential;
		optimalPotentialBuilt = true;
		if (lapGates != null) {
			final String key = reach.geometryCacheKey() + "-laps" + totalLaps;
			synchronized (OPTIMAL_MEMO) {
				if (OPTIMAL_MEMO.containsKey(key)) {
					optimalPotential = OPTIMAL_MEMO.get(key);
				} else {
					final long t0 = System.nanoTime();
					optimalPotential = OptimalPotential.build(this, totalLaps, OPTIMAL_BUDGET_BYTES);
					OPTIMAL_MEMO.put(key, optimalPotential);
					if (autoMode)
						System.out.printf("[optimal] potential %s in %.1fs%n",
								optimalPotential == null ? "SKIPPED (over budget)" : "built",
								(System.nanoTime() - t0) / 1e9);
				}
			}
		}
		return optimalPotential;
	}

	final Reachability reach = new Reachability(this);
	boolean crossesFinish(final double x1, final double y1, final double x2, final double y2) {
		// Multi-lap: the real line is the short boundary-gap gate -- the raw
		// endpoint segment can slice diagonally through the infield and
		// produce phantom re-crossings. laps=1 keeps exact legacy semantics.
		final Line2D line = lapGates != null ? lapCrossGate : finishLine;
		if (!Line2D.linesIntersect(line.getX1(), line.getY1(), line.getX2(), line.getY2(), x1, y1, x2, y2))
			return false;
		// Only a forward crossing counts (move heads in the racing direction).
		// A zero-length or backward move across the line is not a finish.
		if (lapGates != null)
			return (x2 - x1) * lapFwdX + (y2 - y1) * lapFwdY > 0;
		return (x2 - x1) * finishFwdX + (y2 - y1) * finishFwdY > 0;
	}

	/** Multi-lap: three short cross-track gates -- [0] the real S/F line at
	 *  the boundary gap, [1]/[2] auto checkpoints at 1/3 and 2/3 of the
	 *  left-boundary index space, each pairing a left point with its nearest
	 *  right point (auto-computed, works on custom-drawn tracks). Degenerate
	 *  tracks disable laps instead of racing broken gates. */
	private void computeLapGates() {
		lapGates = null;
		lapGatePoints = null;
		lapCrossGate = null;
		final java.util.List<int[]> lefts = track.getLeft();
		final java.util.List<int[]> rights = track.getRight();
		if (lefts.size() < 8 || rights.size() < 8) {
			totalLaps = 1;
			System.out.println("[laps] track boundary too coarse for gates -- laps disabled");
			return;
		}
		// A loop that cannot be closed cannot be lapped: both boundary side
		// gaps must be small enough to bridge with a closing segment.
		final int[] lLast = lefts.get(lefts.size() - 1), lFirst = lefts.get(0);
		final int[] rLast = rights.get(rights.size() - 1), rFirst = rights.get(0);
		final double gapL = Math.hypot(lLast[0] - lFirst[0], lLast[1] - lFirst[1]);
		final double gapR = Math.hypot(rLast[0] - rFirst[0], rLast[1] - rFirst[1]);
		// Real-world circuits may declare lapClosable=true in their track
		// file: their S/F straight closes the loop beyond the auto clamp.
		final boolean declared = Boolean.parseBoolean(prop.getProperty("lapClosable", "false"));
		if (!declared && (gapL > LAP_CLOSURE_MAX || gapR > LAP_CLOSURE_MAX)) {
			totalLaps = 1;
			System.out.println("[laps] boundary gap too wide to close ("
					+ Math.round(Math.max(gapL, gapR)) + " cells) -- laps disabled");
			return;
		}
		lapClosures = new Line2D[][]{extendClosure(lefts), extendClosure(rights) };
		lapClosurePoints = new int[2][][];
		for (int s = 0; s < 2; s++) {
			lapClosurePoints[s] = new int[lapClosures[s].length][];
			for (int i = 0; i < lapClosures[s].length; i++) {
				final Line2D seg = lapClosures[s][i];
				lapClosurePoints[s][i] = new int[]{(int) Math.round(seg.getX1()),
						(int) Math.round(seg.getY1()), (int) Math.round(seg.getX2()),
						(int) Math.round(seg.getY2()) };
			}
		}
		double hx = 0, hy = 0;
		if (lefts.size() >= 2) {
			hx += lefts.get(1)[0] - lFirst[0];
			hy += lefts.get(1)[1] - lFirst[1];
		}
		if (rights.size() >= 2) {
			hx += rights.get(1)[0] - rFirst[0];
			hy += rights.get(1)[1] - rFirst[1];
		}
		final double hlen = Math.hypot(hx, hy);
		lapFwdX = hlen == 0 ? 0 : hx / hlen;
		lapFwdY = hlen == 0 ? 0 : hy / hlen;
		lapGates = new Line2D[3];
		lapGatePoints = new int[3][];
		final double[] fractions = {0.0, 1.0 / 3, 2.0 / 3 };
		for (int k = 0; k < 3; k++) {
			final int[] lp = lefts.get((int) Math.round(fractions[k] * (lefts.size() - 1)));
			int[] best = null;
			long bestD2 = Long.MAX_VALUE;
			for (final int[] rp : rights) {
				final long dx = rp[0] - lp[0], dy = rp[1] - lp[1];
				final long d2 = dx * dx + dy * dy;
				if (d2 < bestD2) {
					bestD2 = d2;
					best = rp;
				}
			}
			lapGates[k] = new Line2D.Double(lp[0], lp[1], best[0], best[1]);
			lapGatePoints[k] = new int[]{lp[0], lp[1], best[0], best[1] };
		}
		final double gx1 = lapGates[0].getX1(), gy1 = lapGates[0].getY1();
		final double gx2 = lapGates[0].getX2(), gy2 = lapGates[0].getY2();
		final double glen = Math.hypot(gx2 - gx1, gy2 - gy1);
		final double shrink = glen == 0 ? 0 : Math.min(0.3 / glen, 0.45);
		lapCrossGate = new Line2D.Double(
				gx1 + (gx2 - gx1) * shrink, gy1 + (gy2 - gy1) * shrink,
				gx2 - (gx2 - gx1) * shrink, gy2 - (gy2 - gy1) * shrink);
		if (autoMode)
			System.out.println("[laps] gate geometry: S/F " + java.util.Arrays.toString(lapGatePoints[0])
					+ " CP1 " + java.util.Arrays.toString(lapGatePoints[1])
					+ " CP2 " + java.util.Arrays.toString(lapGatePoints[2]));
	}

	/** Natural continuation closure for one boundary side: extend the final
	 *  segment's direction and the first segment's reverse direction to
	 *  their intersection, closing along the wall's own curve instead of
	 *  chord-cutting the corridor; straight fallback when degenerate. */
	private static Line2D[] extendClosure(final java.util.List<int[]> side) {
		final int[] last = side.get(side.size() - 1);
		final int[] first = side.get(0);
		if (last[0] == first[0] && last[1] == first[1])
			return new Line2D[0];
		final double gap = Math.hypot(last[0] - first[0], last[1] - first[1]);
		final int[] prevLast = side.get(side.size() - 2);
		final int[] nextFirst = side.get(1);
		final double d1x = last[0] - prevLast[0], d1y = last[1] - prevLast[1];
		final double d2x = first[0] - nextFirst[0], d2y = first[1] - nextFirst[1];
		final double det = d2x * d1y - d1x * d2y;
		if (Math.abs(det) > 1e-9) {
			final double fx = first[0] - last[0], fy = first[1] - last[1];
			final double t = (d2x * fy - d2y * fx) / det;
			final double s = (d1x * fy - d1y * fx) / det;
			final double reach = 3 * gap + 4;
			if (t > 0 && s > 0
					&& t * Math.hypot(d1x, d1y) < reach && s * Math.hypot(d2x, d2y) < reach) {
				final double mx = last[0] + t * d1x, my = last[1] + t * d1y;
				return new Line2D[]{new Line2D.Double(last[0], last[1], mx, my),
						new Line2D.Double(mx, my, first[0], first[1]) };
			}
		}
		return new Line2D[]{new Line2D.Double(last[0], last[1], first[0], first[1]) };
	}

	private static boolean segTouches(final Line2D gate, final int[] a, final int[] b) {
		return Line2D.linesIntersect(gate.getX1(), gate.getY1(), gate.getX2(), gate.getY2(),
				a[0], a[1], b[0], b[1]);
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
		if (gamestate != GameState.PLAY || players[subgamestate].isAi())
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
		// Multi-lap runaway safety: a broken race must not grow the log to the
		// VM limit. The cap scales with the field (it counts TOTAL moves), and
		// a capped car logs TIMEOUT, not CRASH -- benchmark metrics must not
		// confuse slow traffic with wrecks.
		if (lapGates != null && turnCounter > (long) totalLaps * 750 * players.length) {
			dispMessage(player.getName() + " retires (race turn limit).");
			logMove(player, directionOf(player.getVelocity(), vel), player.getVelocity().clone(),
					pos, vel, newpos, "TIMEOUT place=" + (players.length - finishedLast));
			finishPlayer(player, newpos, players.length - finishedLast);
			finishedLast++;
			if (checkFinished())
				return;
			advanceToNextPlayer();
			return;
		}
		final boolean crosses = crossesFinish(pos[0], pos[1], newpos[0], newpos[1]);
		// Multi-lap checkpoint order: CP1 -> CP2 -> S/F. A checkpoint touch
		// (direction-free) merely advances the gate; only a gate-complete S/F
		// crossing counts as a lap. Stray S/F crossings while a checkpoint is
		// still owed are ordinary moves.
		String cpMark = "";
		int gateAfter = player.getNextGate();
		boolean passCp1 = false, passCp2 = false;
		if (lapGates != null) {
			if (gateAfter == 1 && segTouches(lapGates[1], pos, newpos)) {
				gateAfter = 2;
				passCp1 = true;
				cpMark = " cp1";
			}
			if (gateAfter == 2 && segTouches(lapGates[2], pos, newpos)) {
				gateAfter = 0;
				passCp2 = true;
				cpMark = cpMark + " cp2";
			}
		}
		final boolean lapCross = crosses
				&& (lapGates == null || gateAfter == 0);
		final boolean finishes = lapCross && player.getLap() + 1 >= totalLaps;
		// A non-final crossing continues the race, so unlike the final one it
		// must also be an ordinarily legal move (landing on track, no body).
		final boolean legal = finishes
				? finishRunUpLegal(pos[0], pos[1], newpos[0], newpos[1])
				: isMoveLegal(pos, newpos, player.getNumber());

		if (!legal && !player.isAi()) {
			final int answer = JOptionPane.showConfirmDialog(gameFrame.getDialogParent(),
					"Going there will crash you. Do you really want to?", NAME, JOptionPane.YES_NO_OPTION);
			if (answer != JOptionPane.YES_OPTION)
				return;
		}
		if (!autoMode)
			moveHistory.push(new MoveSnapshot(this));
		// The gate credit belongs to a move that actually happens: the confirm
		// above can still abandon this one, and the snapshot has to record the
		// pre-move gate ledger so Undo can put it back.
		if (passCp1) {
			player.setNextGate(2);
			player.passGate(1);
		}
		if (passCp2) {
			player.setNextGate(0);
			player.passGate(2);
		}

		if (finishes) {
			finishedFirst++;
			dispMessage(player.getName() + " finishes on place " + finishedFirst + ".");
			logMove(player, d, velBefore, pos, vel, newpos, "FINISH place=" + finishedFirst);
			finishPlayer(player, newpos, finishedFirst);
			if (checkFinished())
				return;
		} else if (lapCross && legal) {
			final int lap = player.incrementLap();
			player.setNextGate(1);
			logMove(player, d, velBefore, pos, vel, newpos, "LAP " + lap + "/" + totalLaps);
			player.setVelocity(vel);
			player.setPosition(newpos);
			player.logPosition(newpos);
			player.passGate(0);
			redoPlayerLabels();
		} else if (!legal) {
			dispMessage(player.getName() + " crashes.");
			logMove(player, d, velBefore, pos, vel, newpos, "CRASH place=" + (players.length - finishedLast));
			finishPlayer(player, newpos, players.length - finishedLast);
			finishedLast++;
			if (checkFinished())
				return;
		} else {
			logMove(player, d, velBefore, pos, vel, newpos, "ok" + cpMark);
			player.setVelocity(vel);
			player.setPosition(newpos);
			player.logPosition(newpos);
			redoPlayerLabels();
		}
		maybeHideStartZone();
		advanceToNextPlayer();
	}

	private static Direction directionOf(final int[] velBefore, final int[] velAfter) {
		final int dx = velAfter[0] - velBefore[0];
		final int dy = velAfter[1] - velBefore[1];
		for (final Direction d : DIRECTIONS)
			if (d.dx == dx && d.dy == dy)
				return d;
		return Direction.NONE;
	}

	/** Direction-free touch test against one lap gate segment. */
	boolean touchesGate(final int gate, final int x1, final int y1,
			final int x2, final int y2) {
		return lapGates != null
				&& Line2D.linesIntersect(lapGates[gate].getX1(), lapGates[gate].getY1(),
						lapGates[gate].getX2(), lapGates[gate].getY2(), x1, y1, x2, y2);
	}

	/** The player's next required gate (0=S/F, 1=CP1, 2=CP2). */
	int nextGateOf(final int playerNum) {
		if (lapGates == null)
			return 0;
		for (final Player p : players)
			if (p.getNumber() == playerNum)
				return p.getNextGate();
		return 0;
	}

	/** Multi-lap: the containment polygon must cover the S/F gap band, so
	 *  each boundary closes through its blue closure polyline -- the legacy
	 *  polygon's closing edge slices the corridor at the lasts and walls off
	 *  the band (monaco x1.5's 6-8 cell band was an impassable ring cut:
	 *  alive=1438 of 400k, every lap dead at the gate).*/
	private java.util.LinkedList<int[]> lapClosedSide(final java.util.LinkedList<int[]> side,
			final Line2D[] closure) {
		if (lapGates == null || closure == null || closure.length == 0)
			return side;
		final java.util.LinkedList<int[]> out = new java.util.LinkedList<>(side);
		for (final Line2D seg : closure) {
			// midpoint first: a straight single-segment closure's endpoint IS
			// the list head, and appending nothing leaves the legacy band cut
			final int[] mid = {(int) Math.round((seg.getX1() + seg.getX2()) / 2),
					(int) Math.round((seg.getY1() + seg.getY2()) / 2) };
			if (!java.util.Arrays.equals(mid, out.getLast())
					&& !java.util.Arrays.equals(mid, out.getFirst()))
				out.add(mid);
			final int[] q = {(int) Math.round(seg.getX2()), (int) Math.round(seg.getY2()) };
			if (!java.util.Arrays.equals(q, out.getLast())
					&& !java.util.Arrays.equals(q, out.getFirst()))
				out.add(q);
		}
		return out;
	}

	private static String show(final int v) {
		return v == Integer.MAX_VALUE ? "INF" : String.valueOf(v);
	}

	/** True when this player's NEXT S/F crossing ends their race. */
	boolean onFinalLap(final int playerNum) {
		for (final Player p : players)
			if (p.getNumber() == playerNum)
				return p.getLap() + 1 >= totalLaps;
		return true;
	}

	/** The starting grid is special only while someone is still on it. */
	private void maybeHideStartZone() {
		if (startZoneGone || startZoneA == null)
			return;
		for (final Player p : players) {
			final int[] pp = p.getPosition();
			if (pp[0] != Player.INIT_POS && startZoneA.contains(pp[0], pp[1]))
				return;
		}
		startZoneGone = true;
		rui.hideStartZone();
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
		gameFrame.setDirectionsEnabled(!players[subgamestate].isAi());
		rui.setVelVector(new int[]{pos[0] + vel[0], pos[1] + vel[1] }, subgamestate);
		rui.setPrePath(null);
		isShowingPrePath = -1;
		gameFrame.setUndoEnabled(!players[subgamestate].isAi() && hasUndoableHumanMove());
	}

	private boolean hasUndoableHumanMove() {
		for (final MoveSnapshot snapshot : moveHistory)
			if (!players[snapshot.subgamestate].isAi())
				return true;
		return false;
	}

	private void maybeAiTurn() {
		if (gamestate != GameState.PLAY)
			return;
		if (!players[subgamestate].isAi())
			return;
		SwingUtilities.invokeLater(this::doAiTurn);
	}

	private void doAiTurn() {
		if (gamestate != GameState.PLAY || !players[subgamestate].isAi())
			return;
		if (!autoMode && !reach.isReady()) {
			// computeAiMove joins the background reachability BFS; polling keeps
			// the EDT painting instead of freezing the window until it finishes.
			gameFrame.setStatus("Computing track reachability...");
			final Timer poll = new Timer(150, e -> doAiTurn());
			poll.setRepeats(false);
			poll.start();
			return;
		}
		executeMove(ai.computeAiMove());
	}

	final static int		AI_MAX_SPEED	= 12;

	/** Direct comparisons avoid Math.abs(Integer.MIN_VALUE) wrapping negative. */
	static boolean aiVelocityOutOfRange(final int vx, final int vy) {
		return vx < -AI_MAX_SPEED || vx > AI_MAX_SPEED || vy < -AI_MAX_SPEED || vy > AI_MAX_SPEED;
	}

	final RaceAi ai = new RaceAi(this);

	private void autoPlaceAiPlayers() {
		while (subgamestate < players.length && players[subgamestate].isAi()) {
			final int[] pos = findStartPosition();
			if (pos == null) {
				final String message = players[subgamestate].getName() + " (AI) couldn't find a start position.";
				if (isAutoRace()) {
					abortAutoRace(message);
					return;
				}
				dispMessage(message);
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
		final java.util.List<int[]> free = new java.util.ArrayList<>();
		for (int x = Math.max(0, xMin); x <= Math.min(gameCols, xMax); x++)
			for (int y = Math.max(0, yMin); y <= Math.min(gameRows, yMax); y++) {
				if (!startZoneA.contains(x, y))
					continue;
				if (isCrashingPlayer(x, y, playerNum))
					continue;
				if (startRng == null)
					return new int[]{x, y }; // legacy: first free cell
				free.add(new int[]{x, y });
			}
		if (free.isEmpty())
			return null;
		return free.get(startRng.nextInt(free.size()));
	}

	/** Seeded start-placement randomization (statistical benching): when set,
	 *  each AI gets a random free start cell instead of the first free one.
	 *  Deterministic per seed; null (default) = legacy behavior. */
	private java.util.Random startRng = null;

	public void setStartSeed(final long seed) {
		this.startRng = new java.util.Random(seed);
	}

	private void updatePlaceStatus() {
		final boolean allPlaced = subgamestate >= players.length;
		gameFrame.setOkEnabled(allPlaced);
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
		return TrackGeometry.checkIntersect(closed, closed, false);
	}

	private void initGameLog() {
		gameLog.setLength(0);
		turnCounter = 0;
		gameLog.append("# Theoretical Racing ").append(VERSION).append(" — game log\n");
		gameLog.append("# Grid ").append(gameCols).append("x").append(gameRows).append("\n");
		if (totalLaps > 1)
			gameLog.append("# laps ").append(totalLaps).append("\n");
		gameLog.append("trackLeft=").append(TrackIO.pointListToString(track.getLeft())).append("\n");
		gameLog.append("trackRight=").append(TrackIO.pointListToString(track.getRight())).append("\n");
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

	private boolean writeGameLog() {
		final Path path = gameLogPath();
		try {
			final byte[] contents = gameLog.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8);
			TrackIO.writeAtomically(path, out -> out.write(contents));
			return true;
		} catch (final IOException e) {
			e.printStackTrace();
			return false;
		}
	}

	private void buildTrackGeometry() {
		final int[] fL = track.getLeft().getLast();
		final int[] fR = track.getRight().getLast();
		finishLine = new Line2D.Double(fL[0], fL[1], fR[0], fR[1]);
		computeFinishForward();
		computeLapGates();
		rui.setFinishLine(fL, fR);
		startZone = TrackGeometry.makeStartZone(track.getLeft().getFirst(), track.getRight().getFirst());
		rui.setStartZone(startZone);
		rui.setCheckpoints(lapGates != null && lapGatePoints != null
				? new int[][]{lapGatePoints[1], lapGatePoints[2] } : null);
		rui.setLoopClosure(lapGates != null && lapClosurePoints != null
				? java.util.stream.Stream.of(lapClosurePoints)
						.flatMap(java.util.stream.Stream::of).toArray(int[][]::new)
				: null);
		final Path2D.Float p = new Path2D.Float();
		p.moveTo(startZone[0][0], startZone[1][0]);
		for (int i = 1; i < 4; i++)
			p.lineTo(startZone[0][i], startZone[1][i]);
		p.closePath();
		startZoneA = TrackGeometry.getToleranceExpandedShape(p);
		// Lap mode: the corridor is an ANNULUS -- each boundary closes on
		// itself through its closure waypoints and the two rings even-odd
		// fill. The legacy single-ring path closes right-first to left-first,
		// which makes the S/F gate line itself a polygon wall: no move can
		// legally cross the span, and the maps degenerate to one-cell
		// endpoint taps (the traffic death funnel). laps=1 keeps the legacy
		// path byte-for-byte.
		trackA = TrackGeometry.getToleranceExpandedShape(lapGates != null
				? TrackGeometry.newTwoRingPath(
						lapClosedSide(track.getLeft(), lapClosures == null ? null : lapClosures[0]),
						lapClosedSide(track.getRight(), lapClosures == null ? null : lapClosures[1]))
				: TrackGeometry.newPrefilledPath(track.getLeft(), track.getRight()));
		final String denseKey = autoMode ? reach.geometryCacheKey() : null;
		denseEdgeLegalCache = denseKey == null
				? DenseEdgeLegalCache.create(gameCols + 1, gameRows + 1, 64L << 20)
				: DenseEdgeLegalCache.shared(denseKey, gameCols + 1, gameRows + 1,
						64L << 20, 128L << 20);
		buildLegalRaster();
		rui.finishTrack();
		reach.computeDistMap();
		reach.startReachabilityCompute();
		if (dumpReachPath != null) {
			reach.ensureReachabilityReady();
			reach.writeReachability(dumpReachPath);
			System.exit(0);
		}
		if (queryInPath != null) {
			reach.ensureReachabilityReady();
			processQueries(queryInPath, queryOutPath);
			System.exit(0);
		}
		if (optimalStart != null) {
			// The exact search needs the geometry and the gates, not the AI's
			// reachability maps -- it is measured against the referee.
			final String[] cell = optimalStart.split(",", -1);
			final int sx = Integer.parseInt(cell[0].trim());
			final int sy = Integer.parseInt(cell[1].trim());
			final long t0 = System.nanoTime();
			final int best = OptimalLap.solve(this, sx, sy, totalLaps);
			System.out.printf("[optimal] laps=%d start=(%d,%d) moves=%s in %.1fs%n",
					totalLaps, sx, sy, best < 0 ? "UNREACHABLE" : Integer.toString(best),
					(System.nanoTime() - t0) / 1e9);
			System.exit(0);
		}
		if (lapGates != null && autoMode) {
			reach.ensureReachabilityReady();
			final int[] lf = track.getLeft().getFirst();
			final int[] rf = track.getRight().getFirst();
			final int mx = (lf[0] + rf[0]) / 2, my = (lf[1] + rf[1]) / 2;
			System.out.println("[laps] gate-mid values @(" + mx + "," + my + "): g0="
					+ show(reach.turnsToGate(0, mx, my, 0, 0)) + " g1="
					+ show(reach.turnsToGate(1, mx, my, 0, 0)) + " g2="
					+ show(reach.turnsToGate(2, mx, my, 0, 0)));
		}
		saveTrackToProperties();
	}

	/** Answer AI-move queries (DAgger). Each line sets the whole board, and we
	 *  reply with the champion AI's chosen move for the named mover. The AI is a
	 *  pure function of the board + the (track-level) reachability map, so queries
	 *  are independent -- no state carries between them. */
	private void processQueries(final String inPath, final String outPath) {
		// "-" as the input path switches to interactive stdin/stdout mode (one
		// answer per query line, flushed) so a driver can roll positions
		// SEQUENTIALLY against one JVM instead of paying the reachability BFS
		// per query batch. Replies are "dx,dy;MMMMMMMMM" -- the mover's chosen
		// move plus a 9-char candidate mask in Direction.values() order
		// (NW,N,NE,W,NONE,E,SW,S,SE): F crosses finish, X illegal (speed cap or
		// geometry), B live body on the cell, D landing state cannot finish
		// (reachability-dead), A alive. The mask is what lets an offline roller
		// apply moves with the game's exact crash rules.
		final boolean interactive = "-".equals(inPath);
		try (java.io.BufferedReader br = interactive
				? new java.io.BufferedReader(new java.io.InputStreamReader(System.in))
				: java.nio.file.Files.newBufferedReader(java.nio.file.Path.of(inPath));
				java.io.BufferedWriter bw = interactive
						? new java.io.BufferedWriter(new java.io.OutputStreamWriter(System.out))
						: java.nio.file.Files.newBufferedWriter(java.nio.file.Path.of(outPath))) {
			String line;
			while ((line = br.readLine()) != null) {
				line = line.trim();
				if (line.isEmpty())
					continue;
				if ("quit".equals(line))
					break;
				if (line.length() > 8192)
					throw new IllegalArgumentException("Query line is too long");
				final String[] parts = line.split(";", -1);
				if (parts.length != players.length + 1)
					throw new IllegalArgumentException("Query must contain exactly " + players.length + " player groups");
				// Round 103: "sim,<mover>,<rounds>,<world>,<cap>" header runs the
				// in-game joint rollout instead of a move query -- me already AT
				// the queried landing in the board groups. world: smom | scorer |
				// true (scorer-set rivals unsuppressed). Reply "V=<verdict>";
				// SIMTRACE step lines go to stderr for line-by-line diffing
				// against the offline Python roll.
				if (parts[0].startsWith("sim,")) {
					final String[] h = parts[0].split(",", -1);
					final int smover = Integer.parseInt(h[1].trim());
					final int srounds = Integer.parseInt(h[2].trim());
					final String world = h[3].trim();
					final int scap = Integer.parseInt(h[4].trim());
					for (int i = 0; i < players.length; i++) {
						final String[] f = parts[i + 1].split(",", -1);
						players[i].setPosition(new int[]{Integer.parseInt(f[0].trim()),
								Integer.parseInt(f[1].trim()) });
						players[i].setVelocity(new int[]{Integer.parseInt(f[2].trim()),
								Integer.parseInt(f[3].trim()) });
						players[i].setFinishedPlace(Integer.parseInt(f[4].trim()));
					}
					subgamestate = smover;
					ai.simTrace = true;
					final int verdict;
					final int[] audit = new int[3];
					try {
						verdict = ai.querySimOutcome(smover, srounds,
								!"smom".equals(world), "true".equals(world), false, scap, audit);
					} finally {
						ai.simTrace = false;
					}
					System.err.flush();
					bw.write("V=" + verdict + ";tier=" + audit[0] + ";thread=" + audit[1]
							+ ";snug=" + audit[2]);
					bw.newLine();
					bw.flush();
					continue;
				}
				final int mover = Integer.parseInt(parts[0].trim());
				if (mover < 0 || mover >= players.length)
					throw new IllegalArgumentException("Mover index out of range: " + mover);
				final long[] liveCells = new long[players.length];
				int liveCount = 0;
				for (int i = 0; i < players.length; i++) {
					final String[] f = parts[i + 1].split(",", -1);
					if (f.length != 5 && f.length != 6)
						throw new IllegalArgumentException("Player " + i + " query group must contain x,y,vx,vy,finished[,gate]");
					final int x = Integer.parseInt(f[0].trim());
					final int y = Integer.parseInt(f[1].trim());
					final int vx = Integer.parseInt(f[2].trim());
					final int vy = Integer.parseInt(f[3].trim());
					final int finished = Integer.parseInt(f[4].trim());
					if (finished < 0)
						throw new IllegalArgumentException("Finished marker must be non-negative");
					if (aiVelocityOutOfRange(vx, vy))
						throw new IllegalArgumentException("Query velocity outside AI planning domain");
					if (finished == 0) {
						if (x < 0 || y < 0 || x > gameCols || y > gameRows)
							throw new IllegalArgumentException("Live player position outside grid");
						final long cell = (long) x << 32 | y & 0xffffffffL;
						for (int j = 0; j < liveCount; j++)
							if (liveCells[j] == cell)
								throw new IllegalArgumentException("Two live players occupy the same cell");
						liveCells[liveCount++] = cell;
					}
					players[i].setPosition(new int[]{x, y });
					players[i].setVelocity(new int[]{vx, vy });
					players[i].setFinishedPlace(finished);
					// Round 210 forensics: an optional 6th field sets the lap gate
					// (0=S/F, 1=CP1, 2=CP2) so a multi-lap board replays faithfully.
					if (f.length == 6 && lapGates != null)
						players[i].setNextGate(Integer.parseInt(f[5].trim()));
				}
				if (players[mover].isFinished())
					throw new IllegalArgumentException("Mover is already finished");
				subgamestate = mover;
				final Direction d = ai.computeAiMove();
				final Player me = players[mover];
				final int[] mp = me.getPosition(), mv = me.getVelocity();
				final StringBuilder mask = new StringBuilder(9);
				for (final Direction cd : DIRECTIONS) {
					final int nvx = mv[0] + cd.dx, nvy = mv[1] + cd.dy;
					final int nx = mp[0] + nvx, ny = mp[1] + nvy;
					final char c;
					if (aiVelocityOutOfRange(nvx, nvy))
						c = 'X';
					else if (crossesFinish(mp[0], mp[1], nx, ny))
						c = 'F';
					else if (!isMoveLegalGeometryCached(mp[0], mp[1], nx, ny))
						c = 'X';
					else if (isCrashingPlayer(nx, ny, me.getNumber()))
						c = 'B';
					else if (!reach.isAlive(nx, ny, nvx, nvy))
						c = 'D';
					else
						c = 'A';
					mask.append(c);
				}
				bw.write(d.dx + "," + d.dy + ";" + mask);
				bw.newLine();
				bw.flush();
			}
		} catch (final java.io.IOException e) {
			e.printStackTrace();
			System.exit(3);
		}
		if (!interactive)
			System.out.println("answered queries -> " + outPath);
	}

	private void saveTrackToProperties() {
		if (track == null)
			return;
		prop.put("lastTrackLeft", TrackIO.pointListToString(track.getLeft()));
		prop.put("lastTrackRight", TrackIO.pointListToString(track.getRight()));
	}

	private boolean loadLastTrack() {
		final TrackIO.TrackData data = TrackIO.loadLastTrackData(prop);
		if (data == null || data.gameX() != gameCols || data.gameY() != gameRows)
			return false;
		track = new Track();
		for (final int[] p : data.left())
			track.addLeft(p[0], p[1]);
		for (final int[] p : data.right())
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

	/** Put the selected circuit's start line and newly placed cars in view. */
	private void centerTrackStart() {
		if (track == null || track.getLeft().isEmpty() || track.getRight().isEmpty())
			return;
		final int[] left = track.getLeft().getFirst();
		final int[] right = track.getRight().getFirst();
		gameFrame.centerGridAt((left[0] + right[0]) * RaceUI.GRID_DIST / 2,
				(left[1] + right[1]) * RaceUI.GRID_DIST / 2);
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
			if (TrackGeometry.lastSegmentIntersects(active, other)) {
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
			gameFrame.setUndoEnabled(true);
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
			if (!TrackIO.validBorders(track.getLeft(), track.getRight())) {
				dispMessage("Start and finish lines must have non-zero width, and border points must be distinct.");
				return;
			}
			if (isTrackSelfIntersecting()) {
				dispMessage("Track/start line/finish line intersect.");
				return;
			}
			gamestate = GameState.PLACEPLAYERS;
			subgamestate = 0;
			gameFrame.setOkEnabled(false);
			buildTrackGeometry();
			autoPlaceAiPlayers();
			updatePlaceStatus();
		} else if (gamestate == GameState.PLACEPLAYERS && subgamestate == players.length) {
			gameFrame.setOkEnabled(false);
			gameFrame.setUndoEnabled(false);
			for (final Player player : players)
				player.logPosition(player.getPosition());
			gamestate = GameState.PLAY;
			moveHistory.clear();
			subgamestate = 0;
			gameFrame.setStatus(players[0].getName() + "'s turn...");
			gameFrame.setDirectionsEnabled(!players[0].isAi());
			rui.setVelVector(players[0].getPosition(), 0);
			rui.setPrePath(null);
			isShowingPrePath = -1;
			redoPlayerLabels();
			initGameLog();
			maybeAiTurn();
		}
		gameFrame.repaint();
	}

	/** Activated when the Undo button is clicked. */
	public void clickedUndo() {
		if (gamestate == GameState.DRAWTRACK) {
			if (track == null)
				return;
			if (subgamestate == 0)
				track.removeLastLeft();
			else
				track.removeLastRight();
		} else if (gamestate == GameState.PLACEPLAYERS && subgamestate > 0) {
			subgamestate--;
			players[subgamestate].setPosition(new int[]{Player.INIT_POS, Player.INIT_POS });
			updatePlaceStatus();
		} else if (gamestate == GameState.PLAY) {
			MoveSnapshot target = null;
			while (!moveHistory.isEmpty()) {
				final MoveSnapshot snapshot = moveHistory.pop();
				snapshot.restore(this);
				if (!players[subgamestate].isAi()) {
					target = snapshot;
					break;
				}
			}
			if (target == null)
				return;
			gamestate = GameState.PLAY;
			final int[] pos = players[subgamestate].getPosition();
			final int[] vel = players[subgamestate].getVelocity();
			gameFrame.setStatus(players[subgamestate].getName() + "'s turn...");
			rui.setVelVector(new int[]{pos[0] + vel[0], pos[1] + vel[1] }, subgamestate);
			rui.setPrePath(null);
			isShowingPrePath = -1;
			gameFrame.setUndoEnabled(hasUndoableHumanMove());
			gameFrame.setDirectionsEnabled(true);
			redoPlayerLabels();
		}
		gameFrame.repaint();
	}

	private void dispMessage(final String s) {
		if (autoMode) {
			System.out.println("[msg] " + s);
			return;
		}
		JOptionPane.showMessageDialog(gameFrame.getDialogParent(), s, NAME, JOptionPane.OK_OPTION);
	}

	/** Exit the game after a prompt. */
	public void exitMe() {
		if (confirmAndSave("Do you really want to exit?"))
			System.exit(0);
	}

	/** Restart the game after a prompt. */
	public void restartMe() {
		if (confirmAndSave("Do you really want to restart?")) {
			gameFrame.dispose();
			SwingUtilities.invokeLater(() -> new RaceGame(prop).start());
		}
	}

	private boolean confirmAndSave(final String question) {
		if (JOptionPane.showConfirmDialog(gameFrame.getDialogParent(), question, NAME, JOptionPane.YES_NO_OPTION) != JOptionPane.YES_OPTION)
			return false;
		saveProperties();
		return true;
	}

	/** Atomic property save. */
	public void saveProperties() {
		final Path target = propertiesOverride != null
				? propertiesOverride : TrackIO.userPropertiesPath();
		try {
			TrackIO.writeAtomically(target, out -> prop.store(out, null));
		} catch (final IOException e) {
			e.printStackTrace();
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
	boolean isCrashingPlayer(final int x, final int y, final int playerNumber) {
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
