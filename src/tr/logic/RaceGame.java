package tr.logic;

import java.awt.Color;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.awt.geom.Path2D;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.Properties;
import java.util.Scanner;
import javax.swing.JButton;
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
	final static int			defCols				= 86;
	private final static Color[]		defPlayerColors		= new Color[]{Color.BLUE, Color.RED, Color.GREEN, Color.YELLOW, Color.CYAN,
			Color.ORANGE, Color.GRAY, Color.MAGENTA, Color.BLACK };
	final static int			defRows				= 48;
	private final static int			defWindowX			= 1500;
	private final static int			defWindowY			= 800;
	public final static String			NAME				= "Theoretical Racing";
	public final static String			VERSION				= "0.3.0";

	private int					finishedLast	= 0, finishedFirst = 0;
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

	/** Complete pre-move state used to undo a human move and every AI reply
	 *  that followed it. Auto-play does not allocate snapshots. */
	private static final class MoveSnapshot {
		final int		finishedFirst;
		final int		finishedLast;
		final int[]	finishedPlaces;
		final int		gameLogLength;
		final int[]	historySizes;
		final int[][]	positions;
		final int		subgamestate;
		final int		turnCounter;
		final int[][]	velocities;

		MoveSnapshot(final RaceGame game) {
			subgamestate = game.subgamestate;
			finishedFirst = game.finishedFirst;
			finishedLast = game.finishedLast;
			turnCounter = game.turnCounter;
			gameLogLength = game.gameLog.length();
			positions = new int[game.players.length][];
			velocities = new int[game.players.length][];
			finishedPlaces = new int[game.players.length];
			historySizes = new int[game.players.length];
			for (int i = 0; i < game.players.length; i++) {
				final Player player = game.players[i];
				positions[i] = player.getPosition().clone();
				velocities[i] = player.getVelocity().clone();
				finishedPlaces[i] = player.getFinishedPlace();
				historySizes[i] = player.getHistory().size();
			}
		}

		void restore(final RaceGame game) {
			game.subgamestate = subgamestate;
			game.finishedFirst = finishedFirst;
			game.finishedLast = finishedLast;
			game.turnCounter = turnCounter;
			game.gameLog.setLength(gameLogLength);
			for (int i = 0; i < game.players.length; i++) {
				final Player player = game.players[i];
				player.setPosition(positions[i].clone());
				player.setVelocity(velocities[i].clone());
				player.setFinishedPlace(finishedPlaces[i]);
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

	public void setQueryPaths(final String in, final String out) {
		this.queryInPath = in;
		this.queryOutPath = out;
	}

	private boolean isAutoRace() {
		return autoMode && dumpReachPath == null && queryInPath == null;
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
		if (!autoMode)
			gameFrame.setupUI(rui.getGrid(), this, wx, wy, players);

		final boolean useLast = Boolean.parseBoolean(prop.getProperty("useLastTrack", "false")) || autoMode;
		if (useLast && TrackIO.hasLastTrack(prop) && loadLastTrack()) {
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
			System.err.println("Headless mode requires a valid saved track. Aborting.");
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
	boolean isMoveLegal(final int[] pos, final int[] newpos, final int playerNumber) {
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
	boolean isMoveLegalGeometry(final int x1, final int y1, final int x2, final int y2) {
		if (!trackA.contains(x2, y2) && !startZoneA.contains(x2, y2))
			return false;
		final long dxi = (long) x2 - x1, dyi = (long) y2 - y1;
		final int n = Math.max(2, (int) Math.min(Integer.MAX_VALUE, Math.ceil(Math.hypot(dxi, dyi) * 2)));
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
		return !TrackGeometry.segmentCrossesPath(from, to, track.getLeft()) && !TrackGeometry.segmentCrossesPath(from, to, track.getRight());
	}

	/** Primitive cache for geometry edges. Reachability owns it while building;
	 *  AI callers wait for that build, so the table has the same single-writer
	 *  lifecycle as the former HashMap without Long/Boolean/node allocation. */
	private final EdgeLegalCache	edgeLegalCache		= new EdgeLegalCache(1 << 16);

	boolean isMoveLegalGeometryCached(final int x1, final int y1, final int x2, final int y2) {
		final long packed = ((long) x1 & 0xFFFF) << 48 | ((long) y1 & 0xFFFF) << 32
				| ((long) x2 & 0xFFFF) << 16 | (long) y2 & 0xFFFF;
		final long key = mixEdgeKey(packed);
		final byte cached = edgeLegalCache.get(key);
		if (cached != 0)
			return cached == EdgeLegalCache.TRUE;
		final boolean legal = isMoveLegalGeometry(x1, y1, x2, y2);
		edgeLegalCache.put(key, legal);
		return legal;
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

	/** Bijective SplitMix64 finalizer. Packed nearby endpoints have strongly
	 *  structured low bits, which would create long probe clusters in the
	 *  primitive table. One-to-one mixing spreads them without changing cache
	 *  identity or introducing collisions. */
	private static long mixEdgeKey(long key) {
		key = (key ^ (key >>> 30)) * 0xbf58476d1ce4e5b9L;
		key = (key ^ (key >>> 27)) * 0x94d049bb133111ebL;
		return key ^ (key >>> 31);
	}


	final Reachability reach = new Reachability(this);
	boolean crossesFinish(final double x1, final double y1, final double x2, final double y2) {
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
		final boolean finishes = crossesFinish(pos[0], pos[1], newpos[0], newpos[1]);
		final boolean legal = finishes || isMoveLegal(pos, newpos, player.getNumber());

		if (!legal && !player.isAi()) {
			final int answer = JOptionPane.showConfirmDialog(gameFrame.getDialogParent(),
					"Going there will crash you. Do you really want to?", NAME, JOptionPane.YES_NO_OPTION);
			if (answer != JOptionPane.YES_OPTION)
				return;
		}
		if (!autoMode)
			moveHistory.push(new MoveSnapshot(this));

		if (finishes) {
			finishedFirst++;
			dispMessage(player.getName() + " finishes on place " + finishedFirst + ".");
			logMove(player, d, velBefore, pos, vel, newpos, "FINISH place=" + finishedFirst);
			finishPlayer(player, newpos, finishedFirst);
			if (checkFinished())
				return;
		} else if (!legal) {
			dispMessage(player.getName() + " crashes.");
			logMove(player, d, velBefore, pos, vel, newpos, "CRASH place=" + (players.length - finishedLast));
			finishPlayer(player, newpos, players.length - finishedLast);
			finishedLast++;
			if (checkFinished())
				return;
		} else {
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
		gameFrame.getBtnUndo().setEnabled(!players[subgamestate].isAi() && hasUndoableHumanMove());
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
		for (int x = xMin; x <= xMax; x++)
			for (int y = yMin; y <= yMax; y++) {
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
		return TrackGeometry.checkIntersect(closed, closed, false);
	}

	private void initGameLog() {
		gameLog.setLength(0);
		turnCounter = 0;
		gameLog.append("# Theoretical Racing ").append(VERSION).append(" — game log\n");
		gameLog.append("# Grid ").append(gameCols).append("x").append(gameRows).append("\n");
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

	private void writeGameLog() {
		try {
			final byte[] content = gameLog.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8);
			TrackIO.writeAtomically(gameLogPath(), out -> out.write(content));
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
		startZone = TrackGeometry.makeStartZone(track.getLeft().getFirst(), track.getRight().getFirst());
		rui.setStartZone(startZone);
		final Path2D.Float p = new Path2D.Float();
		p.moveTo(startZone[0][0], startZone[1][0]);
		for (int i = 1; i < 4; i++)
			p.lineTo(startZone[0][i], startZone[1][i]);
		p.closePath();
		startZoneA = TrackGeometry.getToleranceExpandedShape(p);
		trackA = TrackGeometry.getToleranceExpandedShape(TrackGeometry.newPrefilledPath(track.getLeft(), track.getRight()));
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
				final int mover = Integer.parseInt(parts[0].trim());
				if (mover < 0 || mover >= players.length)
					throw new IllegalArgumentException("Mover index out of range: " + mover);
				final long[] liveCells = new long[players.length];
				int liveCount = 0;
				for (int i = 0; i < players.length; i++) {
					final String[] f = parts[i + 1].split(",", -1);
					if (f.length != 5)
						throw new IllegalArgumentException("Player " + i + " query group must contain x,y,vx,vy,finished");
					final int x = Integer.parseInt(f[0].trim());
					final int y = Integer.parseInt(f[1].trim());
					final int vx = Integer.parseInt(f[2].trim());
					final int vy = Integer.parseInt(f[3].trim());
					final int finished = Integer.parseInt(f[4].trim());
					if (finished < 0)
						throw new IllegalArgumentException("Finished marker must be non-negative");
					if (Math.abs((long) vx) > AI_MAX_SPEED || Math.abs((long) vy) > AI_MAX_SPEED)
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
				}
				if (players[mover].isFinished())
					throw new IllegalArgumentException("Mover is already finished");
				subgamestate = mover;
				final Direction d = ai.computeAiMove();
				final Player me = players[mover];
				final int[] mp = me.getPosition(), mv = me.getVelocity();
				final StringBuilder mask = new StringBuilder(9);
				for (final Direction cd : Direction.values()) {
					final int nvx = mv[0] + cd.dx, nvy = mv[1] + cd.dy;
					final int nx = mp[0] + nvx, ny = mp[1] + nvy;
					final char c;
					if (Math.abs(nvx) > AI_MAX_SPEED || Math.abs(nvy) > AI_MAX_SPEED)
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
			moveHistory.clear();
			subgamestate = 0;
			gameFrame.setStatus(players[0].getName() + "'s turn...");
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
			gameFrame.getBtnUndo().setEnabled(hasUndoableHumanMove());
			for (final JButton button : gameFrame.getBtnDirections())
				button.setEnabled(true);
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

	/** Atomically persist user settings without sharing a temporary filename. */
	public void saveProperties() {
		try {
			TrackIO.writeAtomically(TrackIO.userPropertiesPath(), out -> prop.store(out, null));
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
