package tr.logic;

import java.util.BitSet;

/**
 * The vector-racing AI extracted from {@link RaceGame}: move selection (the
 * AI1 and AI2 kinds are two labels for one promoted policy since round 222;
 * an experiment gates one kind while it is being measured), opponent
 * prediction, box-seal detection, the danger search (the round-232 kinematic
 * confirm's engine since round 310), the
 * faithful-world chooser and the N-ply escape-headroom search. Reads the reachability maps and its host's
 * legality/geometry predicates through back-refs; returns the chosen move.
 */
final class RaceAi {
	private final RaceGame game;
	private final Reachability reach;
	private final RaceAiPrivateLane privateLane;
	/** Cached because the compiler-generated values() method clones on every call. */
	private static final Direction[] DIRECTIONS = Direction.values();
	/** Scratch storage is instance-owned: one RaceAi drives one single-threaded game. */
	private TwoRoundWorkspace twoRoundWorkspace;
	/** Nested-scorer reference world. A scorer's candidate landing is the sole
	 *  varying blocker in the first projected opponent round, so candidates that
	 *  do not hit any reference landing can reuse both projected rounds exactly. */
	private TwoRoundWorkspace nestedScorerTwoRoundReferenceWorkspace;
	private PredictionWorkspace predictionWorkspace;
	private RolloutWorkspace[] rolloutsByDepth = new RolloutWorkspace[4];
	private final int[] sealEscapes = new int[DIRECTIONS.length * 2];
	private final int[] sealCover = new int[DIRECTIONS.length];
	private final int[] sealMatch = new int[Integer.SIZE];
	private final int[] mobilityMove = new int[4];
	private MobilitySearch outerMobilityWorkspace;
	private MobilitySearch nestedMobilityWorkspace;
	private byte[] liveOccupancy;
	private int[] liveOccupancyTouched;
	private int liveOccupancyTouchedCount;
	private final long[] rolloutFieldCost = new long[1];
	/** Candidate rows per rollout depth. A decision's rows must stay live while
	 *  the rollouts it runs invoke nested scorers for rivals -- and an
	 *  unsuppressed (true-rival) nested scorer used to take the OUTER rows,
	 *  because it runs with inScorerSim off, wiping the decision still reading
	 *  them (round 223). Keyed by simDepth, every compute owns its level. */
	private CandidateWorkspace[] candidatesByDepth = new CandidateWorkspace[4];

	private static final class CandidateWorkspace {
		final double[] trapByDirection = new double[DIRECTIONS.length];
		final int[] turnsByDirection = new int[DIRECTIONS.length];
		final double[] scoreByDirection = new double[DIRECTIONS.length];

		void reset() {
			java.util.Arrays.fill(trapByDirection, 0.0);
			java.util.Arrays.fill(turnsByDirection, Integer.MAX_VALUE);
			java.util.Arrays.fill(scoreByDirection, Double.MAX_VALUE);
		}

	}

	/** Exact touched-cell occupancy counts for one projected board. Counts,
	 * rather than booleans, preserve duplicate-cell semantics while allowing
	 * O(1) successor tests and O(1) mover removal/reinsertion. */
	static final class CellOccupancy {
		final byte[] counts;
		final int[] touched;
		final long[] recorded;	// cells already listed in touched during this clear epoch
		final int width;
		final int height;
		int touchedCount;

		CellOccupancy(final int width, final int height) {
			this.width = width;
			this.height = height;
			counts = new byte[width * height];
			touched = new int[width * height];
			recorded = new long[(width * height + 63) >>> 6];
		}

		void clear() {
			for (int i = 0; i < touchedCount; i++) {
				final int index = touched[i];
				counts[index] = 0;
				recorded[index >>> 6] &= ~(1L << (index & 63));
			}
			touchedCount = 0;
		}

		void rebuild(final int[][] cells) {
			clear();
			for (final int[] cell : cells)
				if (cell != null)
					add(cell[0], cell[1]);
		}

		void add(final int x, final int y) {
			if (x < 0 || y < 0 || x >= width || y >= height)
				return;
			final int index = x * height + y;
			if (counts[index] == 0) {
				final int word = index >>> 6;
				final long mask = 1L << (index & 63);
				if ((recorded[word] & mask) == 0) {
					recorded[word] |= mask;
					touched[touchedCount++] = index;
				}
			}
			counts[index]++;
		}

		void remove(final int x, final int y) {
			if (x < 0 || y < 0 || x >= width || y >= height)
				return;
			final int index = x * height + y;
			if (counts[index] != 0)
				counts[index]--;
		}

		boolean contains(final int x, final int y) {
			return x >= 0 && y >= 0 && x < width && y < height
					&& counts[x * height + y] != 0;
		}
	}

	/** The simulated next opponent round. It was two rounds until 2026-09-26;
	 *  the second fed only the ply-2 price, which round 247's one-level
	 *  lookahead never reaches. */
	private static final class TwoRoundWorkspace {
		final int[][] current;
		final int[][] world1;
		final int[][] simulatedVelocity;
		final int[][] round1Position;
		final int[][] round1Velocity;
		final CellOccupancy blockedOccupancy;
		final CellOccupancy world1Occupancy;

		TwoRoundWorkspace(final int players, final int width, final int height) {
			current = new int[players][];
			world1 = new int[players][];
			simulatedVelocity = new int[players][];
			round1Position = new int[players][2];
			round1Velocity = new int[players][2];
			blockedOccupancy = new CellOccupancy(width, height);
			world1Occupancy = new CellOccupancy(width, height);
		}
	}

	/** Each opponent's predicted next cell, and those cells as an occupancy. */
	private static final class PredictionWorkspace {
		final int[][] result;
		final int[][] cells;
		final CellOccupancy occupancy;

		PredictionWorkspace(final int players, final int width, final int height) {
			result = new int[players][];
			cells = new int[players][2];
			occupancy = new CellOccupancy(width, height);
		}
	}

	private static final class ScorerWorkspace {
		final int[][] originalPosition;
		final int[][] originalVelocity;
		final int[][] simulatedPosition;
		final int[][] simulatedVelocity;
		final int[] finishedPlace;
		final int[][] originalLapState;
		final int[] frameGate;
		final int[] frameRemaining;
		final boolean[] frameLapAware;

		ScorerWorkspace(final int players) {
			originalPosition = new int[players][];
			originalVelocity = new int[players][];
			simulatedPosition = new int[players][2];
			simulatedVelocity = new int[players][2];
			finishedPlace = new int[players];
			originalLapState = new int[players][];
			frameGate = new int[players];
			frameRemaining = new int[players];
			frameLapAware = new boolean[players];
		}
	}

	private static final class RolloutWorkspace {
		final int[] laps;
		final int[] gates;
		final int[] remaining;
		final boolean[] lapAware;
		int turns;
		final int[] px;
		final int[] py;
		final int[] vx;
		final int[] vy;
		final boolean[] alive;
		final boolean[] scorerSet;
		final int[] move = new int[4];
		final ScorerWorkspace scorer;
		/** perf_bnb: written by a chooser's own rollout under a bound (simOutcomeCore), read
		 *  by jointChooser right after it: the highest lower bound on the rollout's verdict
		 *  met (-1 for none), and the mover's moves made and aware moves left when the bound
		 *  first passed the cutoff (-1: never). */
		long bnbBound;
		int bnbStopMoves, bnbStopAware;

		RolloutWorkspace(final int players) {
			laps = new int[players];
			gates = new int[players];
			remaining = new int[players];
			lapAware = new boolean[players];
			px = new int[players];
			py = new int[players];
			vx = new int[players];
			vy = new int[players];
			alive = new boolean[players];
			scorerSet = new boolean[players];
			scorer = new ScorerWorkspace(players);
		}
	}

	RaceAi(final RaceGame game) {
		this.game = game;
		this.reach = game.reach;
		privateLane = new RaceAiPrivateLane(game);
	}

	private CandidateWorkspace candidateWorkspace() {
		if (simDepth >= candidatesByDepth.length)
			candidatesByDepth = java.util.Arrays.copyOf(candidatesByDepth, simDepth + 4);
		CandidateWorkspace workspace = candidatesByDepth[simDepth];
		if (workspace == null)
			workspace = candidatesByDepth[simDepth] = new CandidateWorkspace();
		workspace.reset();
		return workspace;
	}

	/** The move for the player to move. Every AI kind runs the one promoted
	 * body; an experiment must add an explicit kind gate to keep a control. */
	Direction computeAiMove() {
		reach.ensureReachabilityReady();
		// Round 175: retire per-compute memo entries (the hold-overspeed
		// verdict depends on the board, which is fixed only within one
		// compute). Mobility searches take their own fresh epoch at build,
		// so their entries are unaffected beyond correct retirement.
		fmMemoEpoch++;
		final Player p = game.players[game.subgamestate];
		final int[] vel = p.getVelocity();
		final int[] pos = p.getPosition();
		final int playerNum = p.getNumber();
		if (simDepth != 0)
			return optimalMoveAI1(pos, vel, playerNum);
		// perf_aware: a top-level decision owns the suppressed-move memo, empty at its start.
		suppressedMoves.clear();
		suppressedMovesOwned = true;
		try {
			// perf (upmemo): and the race-scoped upgraded memo's generations and world.
			maintainUpgradedMemo();
			return optimalMoveAI1(pos, vel, playerNum);
		} finally {
			suppressedMovesOwned = false;
		}
	}

	/**
	 * Pure min-turns lookup, no opponent reasoning. Used internally to predict
	 * opponent moves; we DON'T want recursion through the smart AI variants.
	 */
	private Direction pureMinTurnsMove(final int x, final int y, final int vx, final int vy,
			final int playerNum) {
		// Round 223: this player's own lap frame, not the mover's.
		final int idx = playerNum - 1;
		final boolean scanLapAware = frameLapAware[idx];
		final int scanGate = frameGate[idx];
		final int sm = succMask(x, y, vx, vy);
		// perf_aisearch (exact): the one-pass scan returned at the first precedence
		// in Direction order and otherwise kept, among the legal landings free of
		// live bodies, the first with the fewest turns. Every test is free of side
		// effects, so the precedences run first and the pace compare then walks the
		// landings in their stable turns order (ttfOrder): the same landing.
		for (final Direction d : DIRECTIONS) {
			final int bit = 1 << d.ordinal();
			final int newVx = vx + d.dx;
			final int newVy = vy + d.dy;
			if ((sm & bit << 16) == 0)
				continue;
			final int newX = x + newVx;
			final int newY = y + newVy;
			// perf_aisearch (exact): the precedence below needs !scanLapAware or
			// scanGate == 0, so only that frame asks for the crossing.
			if ((!scanLapAware || scanGate == 0) && game.crossesFinishLegally(x, y, newX, newY)) {
				// Multi-lap: a non-final crossing keeps its precedence only when
				// survivable (legal edge, no body, alive landing beyond the line)
				// AND shedable -- the map prices every crossing at turns=1
				// regardless of landing speed, so hot arrivals must not count.
				if (!scanLapAware && game.onFinalLap(playerNum) || scanGate == 0 && ((sm & bit) != 0
						&& !game.isCrashingPlayer(newX, newY, playerNum)
						&& reach.shedableLanding(newX, newY, newVx, newVy)
						&& reach.turnsToGate(1, newX, newY, newVx, newVy) != Integer.MAX_VALUE
						&& needleHeadway(newX, newY, newVx, newVy, playerNum, 1))) {
					if (AI_DEBUG_PLAYER == playerNum && !inScorerSim)
						System.err.println("AIDBG SCAN-CROSS p=" + playerNum + " chosen=" + d);
					return d;
				}
				// Stray or unshedable crossing: an ordinary legal move (cars
				// spawn BEHIND the line -- excluding these walls them in).
			}
			// Checkpoint touch precedence: the post-touch landing prices a
			// full lap on the CURRENT gate map, so slow approaches would bob
			// one cell before the line forever (the gate-0 stall, at the CPs).
			// A touch with a continuing landing is progress -- take it. In
			// traffic the landing must also hold needle headway: without it
			// the precedence rams the car into an occupied one-cell pocket
			// at unstoppable speed (the scorer then prices the wait instead,
			// and the touch fires the moment the queue clears).
			if (scanLapAware && scanGate != 0 && (sm & bit) != 0
					&& game.touchesGate(scanGate, x, y, newX, newY)
					&& !game.isCrashingPlayer(newX, newY, playerNum)
					&& reach.isAlive(newX, newY, newVx, newVy)
					&& reach.turnsToGate(scanGate == 1 ? 2 : 0, newX, newY, newVx, newVy)
							!= Integer.MAX_VALUE
					&& needleHeadway(newX, newY, newVx, newVy, playerNum, scanGate == 1 ? 2 : 0)) {
				if (AI_DEBUG_PLAYER == playerNum && !inScorerSim)
					System.err.println("AIDBG SCAN-CP p=" + playerNum + " gate=" + scanGate + " chosen=" + d);
				return d;
			}
		}
		final long order = ttfOrder(idx, x, y, vx, vy);
		for (int i = 0; i < DIRECTIONS.length; i++) {
			final int ordinal = (int) (order >>> 4 * i) & 0xF;
			if (ordinal == 0xF)
				break;
			final Direction d = DIRECTIONS[ordinal];
			if ((sm & 1 << ordinal) == 0 || game.isCrashingPlayer(x + vx + d.dx, y + vy + d.dy, playerNum))
				continue;
			if (AI_DEBUG_PLAYER == playerNum && !inScorerSim)
				System.err.println("AIDBG scan1 p=" + playerNum + " pos=(" + x + "," + y
						+ ") vel=(" + vx + "," + vy + ") chosen=" + d + " t="
						+ ttfFor(idx, x + vx + d.dx, y + vy + d.dy, vx + d.dx, vy + d.dy)
						+ " gate=" + lapGate);
			return d;
		}
		int fallbackLegalMask = 0;
		int fallbackIllegalMask = 0;
		for (final Direction d : DIRECTIONS) {
			final int bit = 1 << d.ordinal();
			if ((sm & bit << 16) == 0)
				continue;
			if ((sm & bit) == 0)
				fallbackIllegalMask |= bit;
			else if (!game.isCrashingPlayer(x + vx + d.dx, y + vy + d.dy, playerNum))
				fallbackLegalMask |= bit;
		}
		if (AI_DEBUG_PLAYER == playerNum && !inScorerSim)
			System.err.println("AIDBG scan1-FB p=" + playerNum + " pos=(" + x + "," + y
					+ ") vel=(" + vx + "," + vy + ") legal=" + fallbackLegalMask
					+ " illegal=" + fallbackIllegalMask + " gate=" + lapGate);
		return scoreMinTurnsFallback(x, y, vx, vy,
				fallbackLegalMask, fallbackIllegalMask, Direction.NONE);
	}

	/** perf_aisearch: an order with no entry -- nine 0xF nibbles (packOrder). */
	private static final long ORDER_NONE = (1L << 36) - 1;
	/** perf_aisearch: log2 of the ttfOrder table's slots. */
	private static final int TTF_ORDER_BITS = 14;
	/** perf_aisearch: the ttfOrder table (direct-mapped, each entry its whole key
	 *  and its order) and what it was filled against beyond its keys. */
	private long[] ttfOrderKeys, ttfOrderVals;
	private OptimalPotential ttfOrderPot;
	private int[] ttfOrderTurns;
	private int[][] ttfOrderGates;
	private int ttfOrderCols = -1, ttfOrderRows = -1, ttfOrderAliveW = -1, ttfOrderAliveH = -1,
			ttfOrderVmax = -1;
	private final int[] ttfOrderTurnsScratch = new int[DIRECTIONS.length];
	private final int[] ttfOrderOrdinalScratch = new int[DIRECTIONS.length];

	/** perf_aisearch: the accelerations of (x, y, vx, vy) whose velocity is in the
	 *  AI range and whose landing has a finite ttfFor in player {@code idx}'s
	 *  frame, sorted stably by that value (equal values keep Direction order) and
	 *  packed by packOrder. ttfFor reads the frame -- events owed, next gate,
	 *  lap-awareness, all in the key -- and fixed race products: the exact
	 *  potential and the finish and gate maps. The table checks their identities
	 *  and the board and map dimensions and empties itself when one changes; an
	 *  entry keeps its whole key, so a hit returns what the scan computes. */
	private long ttfOrder(final int idx, final int x, final int y, final int vx, final int vy) {
		final int max = RaceGame.AI_MAX_SPEED;
		final int remaining = frameRemaining[idx], gate = frameGate[idx];
		if (x < 0 || y < 0 || x > game.gameCols || y > game.gameRows
				|| game.gameCols > 4095 || game.gameRows > 4095
				|| vx < -max || vx > max || vy < -max || vy > max
				|| remaining < 0 || remaining > 255 || gate < 0 || gate > 2)
			return ttfOrderCompute(idx, x, y, vx, vy);
		final Reachability r = reach;
		if (ttfOrderKeys == null || ttfOrderPot != exactPot || ttfOrderTurns != r.turnsArr
				|| ttfOrderGates != r.gateTurns || ttfOrderCols != game.gameCols
				|| ttfOrderRows != game.gameRows || ttfOrderAliveW != r.aliveW
				|| ttfOrderAliveH != r.aliveH || ttfOrderVmax != r.aliveVMAX) {
			if (ttfOrderKeys == null) {
				ttfOrderKeys = new long[1 << TTF_ORDER_BITS];
				ttfOrderVals = new long[1 << TTF_ORDER_BITS];
			}
			java.util.Arrays.fill(ttfOrderKeys, -1L);
			ttfOrderPot = exactPot;
			ttfOrderTurns = r.turnsArr;
			ttfOrderGates = r.gateTurns;
			ttfOrderCols = game.gameCols;
			ttfOrderRows = game.gameRows;
			ttfOrderAliveW = r.aliveW;
			ttfOrderAliveH = r.aliveH;
			ttfOrderVmax = r.aliveVMAX;
		}
		final int span = 2 * max + 1;
		final long state = ((long) x * (game.gameRows + 1) + y) * (span * span) + (vx + max) * span + vy + max;
		final long key = ((state << 8 | remaining) << 2 | gate) << 1 | (frameLapAware[idx] ? 1 : 0);
		final int slot = (int) (key * 0x9E3779B97F4A7C15L >>> 64 - TTF_ORDER_BITS);
		if (ttfOrderKeys[slot] == key)
			return ttfOrderVals[slot];
		final long order = ttfOrderCompute(idx, x, y, vx, vy);
		ttfOrderKeys[slot] = key;
		ttfOrderVals[slot] = order;
		return order;
	}

	/** perf_aisearch: ttfOrder computed (an insertion sort that moves an entry
	 *  only past strictly larger turns, so equal turns keep Direction order). */
	private long ttfOrderCompute(final int idx, final int x, final int y, final int vx, final int vy) {
		final int[] turnsBy = ttfOrderTurnsScratch, ordinals = ttfOrderOrdinalScratch;
		int n = 0;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
				continue;
			final int turns = ttfFor(idx, x + nvx, y + nvy, nvx, nvy);
			if (turns == Integer.MAX_VALUE)
				continue;
			int i = n++;
			while (i > 0 && turnsBy[i - 1] > turns) {
				turnsBy[i] = turnsBy[i - 1];
				ordinals[i] = ordinals[i - 1];
				i--;
			}
			turnsBy[i] = turns;
			ordinals[i] = d.ordinal();
		}
		return packOrder(ordinals, n);
	}

	/** perf_aisearch: Direction ordinals {@code ordinals[0..n)}, one per nibble from
	 *  the lowest, every unused nibble 0xF. */
	private static long packOrder(final int[] ordinals, final int n) {
		long order = ORDER_NONE;
		for (int i = 0; i < n; i++)
			order = order & ~(0xFL << 4 * i) | (long) ordinals[i] << 4 * i;
		return order;
	}

	/** Score-only terminal tier shared by the live, smart, and simulated
	 *  min-turns choosers. Candidate masks capture the original pass so nested
	 *  simulations cannot make the fallback re-read occupancy or legality. */
	private Direction scoreMinTurnsFallback(final int x, final int y,
			final int vx, final int vy, final int legalMask,
			final int illegalMask, final Direction emptyFallback) {
		Direction bestAlive = null;
		double bestAliveScore = Double.MAX_VALUE;
		Direction bestLegal = null;
		double bestLegalScore = Double.MAX_VALUE;
		Direction fallback = emptyFallback;
		double fallbackScore = Double.MAX_VALUE;
		final int candidateMask = legalMask | illegalMask;
		for (final Direction d : DIRECTIONS) {
			final int bit = 1 << d.ordinal();
			if ((candidateMask & bit) == 0)
				continue;
			final int newVx = vx + d.dx;
			final int newVy = vy + d.dy;
			final double sc = reach.scorePos(x + newVx, y + newVy, newVx, newVy);
			if ((legalMask & bit) != 0) {
				// Round 198: lap traffic blanks every finite candidate far
				// more often than laps=1 ever did, and this last resort must
				// not steer into a legal-but-doomed spur while an alive
				// landing exists (rand2 (110,8)v(-3,-1): entered legal,
				// selfAlive=false, all nine successors illegal). laps=1
				// keeps the legacy tiering byte-for-byte.
				if (game.lapGates != null && sc < bestAliveScore
						&& reach.isAlive(x + newVx, y + newVy, newVx, newVy)) {
					bestAliveScore = sc;
					bestAlive = d;
				}
				if (sc < bestLegalScore) {
					bestLegalScore = sc;
					bestLegal = d;
				}
			} else if (sc < fallbackScore) {
				fallbackScore = sc;
				fallback = d;
			}
		}
		if (bestAlive != null)
			return bestAlive;
		return bestLegal != null ? bestLegal : fallback;
	}

	/** Explicit search depth of the soft search
	 *  ({@link #searchMinTurnsCountedSoft3}): my next move is searched against
	 *  the simulated next opponent round, then the opponent-blind map takes
	 *  over. Two levels priced a second simulated round (AI1_PLY2_PRICE, the
	 *  ahead-rival bodies of round two); that machinery was removed on
	 *  2026-09-26, so raising this needs it back (git history). */
	private final static int		AI1_DEEP_LOOKAHEAD	= 1;	// round 247: one round of world-step, not two -- the second round priced where seven rivals might be and cost 0.155 places (three rounds cost 0.279)
	private final static int		AI1_SEAL_MAXRIVALS	= 3;	// endgame seal fires when <= this many rivals remain
	private final static double	AI1_PACE_FLOOR	= 0.60;	// min poRoom to take an unsealable faster move (sparse field only)
	private final static int		AI1_SPARSE_RIVALS	= 3;
	private final static int		AI1_DJS_ROUNDS	= 3;
	private final static int		AI1_TRUE_CONFIRM_ROUNDS	= 4;	// round 99: horizon for the true-rival confirm; round 100: 4 -- the s74 box seals at round index 3 (s32 sealed at 2); every extra round multiplies full-champion rival computes and widens the false-kill window
	// danger joint search: rollout depth in rounds	// aggressive pace floor applies only when <= this many rivals remain
	private final static int		AI1_DJS_SPD2	= 49;	// round 55 (AI1): DJS also fires at landing speed^2 >= this -- the ancestral speed-7-10 corner-entry class keeps the trap ladder at 0 until every alternative is dead, so the trap gate alone triggers too late; round 310: this trigger and the danger block are gone, the pace overrides keep it as their high-speed bar
	private final static int		AI1_DJS_SLOW_ROUNDS	= 5;	// round 59: rollout horizon for slow-class fires (landing spd^2 < AI1_DJS_SPD2) -- the slow queue dooms commit 3-5 rounds out (lemans-s4 start funnel, oracle-measured); since round 310 the private pace override's and the round-175 hold leg's horizon
	private final static int		AI1_CHOOSER_MAXDIST	= 20;	// the owner's rule (rounds 262, 274): no live rival within this many cells -> the exact solo descent in every race mode (round 279), no chooser
	private final static int		AI1_CHOOSER_ROUNDS	= 12;	// round 256/257: rounds of everyone's real policy behind a close call
	private final static double	AI1_CHOOSER_WINDOW	= 1.0;	// round 256/259: a landing is a close call within this much score
	private final static int		AI1_AWARE_SELF_MOVES	= 5;	// round 305: the mover's forecast continuation moves played by its full policy
	private final static int		AI1_CHOOSER_WIDTH	= 3;	// round 256/259: at most this many close calls are rolled
	private final static int		AI1_SCORER_NEAR	= 10;	// round 59: Chebyshev radius for real-scorer rivals in slow-class rollouts
	private final static int		AI1_SCORER_MAXRIVALS	= 3;	// round 59: at most this many nearest real-scorer rivals per rollout (cost bound; the box formers are always adjacent)
	private final static int		AI1_TRAP_SOLO_R	= 16;	// round 61: trap relief radius -- L1/L2 threads are only dangerous if a rival can contest them; no live rival within this Chebyshev range of the landing = the map's own certification suffices (max per-axis closure is |v|+1 <= 13 per round)
	private final static int		AI1_ROBUST_RANGE	= 12;	// a live rival ahead or beside requires robust checkpoint/crossing continuations
	private final static int		AI1_ROBUST_KIN_CAP	= 24;	// round 212: the needle gate reaches as far as my stopping distance s(s+1)/2, capped here -- the rand6 long needle was entered at speed 7 with the parked pack 13 cells ahead, one outside the fixed radius
	private final static int		AI1_KIN_CONFIRM_R	= 3;	// round 232: a live rival within this Chebyshev radius of the thin landing arms the kinematic confirm (the audited closers stood 1-3 cells away)
	private final static int		AI1_KIN_HORIZON_CAP	= 10;	// round 205: kinematic DJS horizon cap (rounds-to-stop, lap mode)
	private final static int		AI1_DEEP_HORIZON	= 8;	// round 65: rollout horizon for pack-gated deep escalations -- the hairpin-s10 doom commits 7 rounds out (oracle: three candidates FINISH @r6 while the chosen dies @r7); round 310: the escalations are gone, the sprint's field proof and the danger search's speed legs and target walk read it
	private final static int		AI1_DEEP_PACK_R	= 10;	// round 65: Chebyshev pack radius for the deep escalation gate (gone in round 310); the private pace override's field comparison reads it
	private final static int		AI1_SLOW_PACK_SPD2	= 16;	// round 67: the dense slow-pack trigger's speed floor (the trigger went in round 310); the staged pace override reads it
	private final static int		AI1_FUNNEL_WIDTH	= 4;	// round 83: static funnel escalation threshold -- the zandvoort corner and coil spiral pinch to ring width 4 while every measured open corridor is >= 7 (silverstone s1 distribution); round 310: the escalation is gone, the field-acceleration ring check reads it
	private final static int		AI1_DEEP_CERT_RIVALS	= 6;	// round 73: scorer-rival cap for the ahead-pack corridor certification -- the interlagos-s10 m103 killers are ranks 4-6 by landing distance, beyond the round-59 nearest-3 set; round 310: the corridor certification is gone, it stays the certification cap of the sprint, finish denial, the pace overrides and the danger search's confirms
	private final static long	ROLLOUT_FAILURE_COST	= 1_000_000L;	// field comparison: one simulated rival failure dominates all finite TTF sums
	private final static int		AI1_FINISH_CERT_TTF	= 15;	// round 75 (promoted): legacy mixed-field cap for the dual-model finish sprint
	private final static int		AI1_FINISH_TRUE_CONFIRM_ROUNDS	= 5;	// round 176: faithful-rival veto for one-successor sprint lines
	private final static int		AI1_FINISH_DENIAL_ROUNDS	= 8;	// bounded faithful horizon for a contested finish pocket
	private final static int		AI1_FINISH_DENIAL_RIVALS	= 2;	// nearest full-fidelity rivals suffice for the measured denial class
	private final static int		AI1_FINISH_DENIAL_MAX_TTF	= 5;	// only the final one-turn map-gain commitment
	private final static int		AI1_FINISH_DENIAL_MIN_SPEED2	= 64;	// high-energy approach that can overrun a closing pocket
	private final static int		AI1_FINISH_DENIAL_MIN_BRAKE2	= 16;	// require a materially lower-energy escape
	private final static int		AI1_FINISH_DENIAL_NEAR_RIVALS	= 4;	// compact finish pack, not open-line racing
	private final static int		AI1_FINISH_DENIAL_ALIGNED_RIVALS	= 2;	// similarly moving bodies ahead can close the lane
	private final static int		AI1_FINISH_HOMOGENEOUS_TTF	= 20;	// round 94: extend only in mover-kind homogeneous fields; the new band forbids coasting
	private final static int		AI1_FINISH_EXTENDED_TTF	= 30;	// round 96: one-turn, non-coasting homogeneous extension of the full finish proof
	private final static int		AI1_PRIVATE_BASE_HORIZON	= 3;	// round 77: cheap rectangular private-lane certificate
	private final static int		AI1_PRIVATE_EXACT_HORIZON	= 4;	// round 77: geometry-clipped fallback horizon
	private final static int		AI1_PRIVATE_BASE_ESCAPES	= 3;	// broad rectangles need the original wide frontier
	private final static int		AI1_PRIVATE_EXACT_ESCAPES	= 2;	// clipped slow or homogeneous moderate-risk lines may use two exits
	private final static int		AI1_PRIVATE_EXACT_NODES	= 512;	// per-turn exact-search budget; exhaustion fails closed
	private final static double	AI1_PRIVATE_FRONTIER_REST_SLACK	= 0.25;	// round 169: bounded exact-private/scorer-field frontier
	private final static int		AI1_PRIVATE_FRONTIER_MIN_TTF	= 46;	// incumbent phase; the candidate is exactly one turn faster
	private final static int		AI1_PRIVATE_FRONTIER_MAX_TTF	= 90;	// keep the eight-round field proof in medium range
	private final static int		AI1_PRIVATE_FIELD_MIN_RIVALS	= 5;	// round 78: compare field effects only in compressed large fields
	private final static int		AI1_PRIVATE_CONVOY_RADIUS_V	= 2;	// round 79: look two mover-velocity spans along a nearly collinear train
	private final static int		AI1_PRIVATE_CONVOY_HALF_WIDTH	= 4;	// maximum perpendicular distance from the mover's velocity ray
	private final static int		AI1_PRIVATE_CONVOY_MAX_AHEAD	= 1;	// the externality case is a compact rear train, not a two-sided pack
	private final static double	AI1_STAGED_REST_SLACK	= 1.00;	// round 81: one scorer point still needs strict rollout and field proof
	private final static int		AI1_STAGED_HORIZON	= 8;	// strict gain + non-worsening field
	private final static int		AI1_STAGED_MIN_TURNS	= 35;	// leave the existing finish sprint in charge near the line
	private final static int		AI1_STAGED_MAX_SPEED2_GAIN	= 9;	// at most one |v|=4->5 axis of extra energy vs the scorer
	private final static int		AI1_FIELD_ACCEL_MIN_SPEED2_GAIN	= 16;	// round 106: decisive one-turn energy gain
	private final static int		AI1_FIELD_ACCEL_MIN_AHEAD	= 2;	// require a real forward pack
	private final static int		AI1_FIELD_ACCEL_MAX_AHEAD	= 5;	// bounded proof excludes full-tail six-ahead cases
	private final static int		AI1_FIELD_ACCEL_MAX_TTF	= 90;	// keep the 8-round proof in the medium-range race phase
	private final static int		AI1_FIELD_ACCEL_FRONTIER_MIN_SPEED2_GAIN	= 9;	// round 115 frontier: moderate acceleration floor
	private final static int		AI1_FIELD_ACCEL_FRONTIER_LOW_GAIN_MAX_TTF	= 45;	// round 115: short-range boundary for speed2 gains 9..15
	private final static int		AI1_FIELD_ACCEL_SIX_AHEAD_ROUNDS	= 8;	// round 117: synchronized six-ahead formations retain the established proof depth
	private final static int		AI1_FIELD_ACCEL_SIX_AHEAD_MODERATE_MIN_SPEED2	= 49;	// round 175: cross the high-speed threshold with a bounded gain
	private final static int		AI1_MOBILITY_DEPTH	= 4;	// frontier; projection/cache shared per turn
	/** Forensic gates: -Dai.debug.player=N per-turn pick dump for that player;
	 *  -Dai.debug.djs DJS-death events for all players. All are off by default.
	 *  (-Dai.debug.fieldVector printed the round-177 field proof, removed with
	 *  it on 2026-09-26; the flag is now ignored.) */
	private final static int		AI_DEBUG_PLAYER	= Integer.getInteger("ai.debug.player", -1);
	private final static boolean	AI_DEBUG_DJS	= Boolean.getBoolean("ai.debug.djs");
	private final static boolean	AI_DEBUG_FINISH_DENIAL	=
			Boolean.getBoolean("ai.debug.finishDenial");
	private final static int		AI_DEBUG_FINISH_DENIAL_RIVAL_CAP	=
			Integer.getInteger("ai.debug.finishDenialRivalCap", AI1_FINISH_DENIAL_RIVALS);
	private final static boolean	AI_DEBUG_COMP	= Boolean.getBoolean("ai.debug.comp");
	/** True while this game instance computes a rollout move with the real
	 *  scorer. Instance scope prevents concurrent games from suppressing each
	 *  other's recursive machinery; the flag is restored in a finally. */
	private boolean				inScorerSim;
	/** Instance-scoped recursion guard for the rare finish-denial proof. */
	private boolean				inFinishDenialConfirm;
	/** Round 99 latch, round 103 DEPTH: a binary latch stripped the confirm
	 *  from every in-confirm rival -- and since round 99 the confirm IS part
	 *  of champion behavior, so latched rivals diverged from real ones by
	 *  exactly one arm (zigzag s76: oracle-i0 claims the kill cell its
	 *  latched twin vacates -- the recursion boundary regenerating one level
	 *  up). One nested level is allowed; depth 2 blocks (cost recursion). */
	private int					trueConfirmDepth;
	private final static int		AI1_TRUE_CONFIRM_MAXDEPTH	= 2;
	private final static int		AI1_FASTV_MAX	= 11;	// round 133: max-axis speed from which the vmax overspeed deep check arms -- the serpentine2 dooms commit exactly at the 10->11 acceleration (VMAX-1); braking from 11 overruns what a hairpin absorbs once traffic fills the escape rows
	private final static int		AI1_FASTV_PACK_R	= 6;	// round 133: the vmax doom needs a train -- a rival within this Chebyshev radius of the mover; the three commitments carry theirs at 1, 2 and 5, and the gate excludes the lone-runner false kill (golden lemans-s1-4p)
	// multi-lap shedability now lives in Reachability.shedableLanding (minShed2 <= 36)
	private final static int		AI1_HOLDV_MAX	= 10;	// round 175: max-axis speed from which the hold-overspeed cheap-world check arms (hold or accel, with a train rival) -- the harvest-30 cross-track commitments hold 10 down a straight and die 4-7 oracle rounds out
	private final static int		AI1_EG_ETA		= 12;		// endgame solver: both cars within this many turns of the finish
	private final static int		AI1_EG_DEPTH	= 10;		// endgame solver: rounds of exact search (2x plies)
	private final static int		AI1_EG_NODES	= 50_000;	// endgame solver: node budget; blown -> claim nothing (200k added ~2x 1v1 bench time on unprovable positions; real proofs are shallow forcing lines found far below 50k)
	// Gate thresholds (round 39 tuning surface): each was hand-picked in a
	// past forensic and never jointly optimized. Values = champion's.
	private final static double	AI1_PO_ROOM_HI	= 0.88;	// paceOverride: fully-roomy clause
	private final static double	AI1_PO_ROOM_MID	= 0.78;	// paceOverride: mid-roominess clause (slow landings)
	private final static int		AI1_PO_SPD_MAX	= 4;		// paceOverride: max |v| component for the mid clause
	private final static double	AI1_BRAKE_SPEED	= 4.0;	// arming gate + slope base of the speed brakes
	private final static int		AI1_PACK_R2		= 36;	// cornerEntry pack radius^2
	private final static int		AI1_VACATE_SPEED2	= 9;	// |v| >= 3: predicted cell nulled (transiting)
	private final static int		STALLED_RIVAL_SPEED2	= 6;	// integer |v| <= 2.5
	private final static double	AI1_TRAP_L1		= 2.0;	// trap ladder: 1 safe successor
	private final static double	AI1_TRAP_L2		= 0.5;	// trap ladder: 2 safe successors
	private final static int		AI1_NEEDLE_RIVAL_R	= 8;	// round 197: traffic radius for the needle-headway law
	private final static double	AI1_NEEDLE_TRAP	= 30.0;	// round 197: surcharge for an unstoppable no-headway landing
	private final static double	AI1_LANE_STYLE	= 0.12;	// round 201: per-player tie-break style spread in lap traffic (multi-seed: 0.12 -> 89 crashes, 0.20 -> 105 -- past the sweet spot the style sacrifice costs more than spreading buys)

	/**
	 * The promoted policy, for every AI kind. Round 129 established one scorer
	 * body by delegation after promoting the measured Round 115/117/124
	 * field-acceleration frontier and Round 126's homogeneous false-target
	 * veto. Later promoted gates live in this body too: Round 169's
	 * exact-private slack, Round 174's squeeze check, Round 175's bounded
	 * high-speed six-ahead acceleration, Rounds 178-180's thin-ridge check,
	 * Round 216's exact-potential pace number, and -- promoted on the user's
	 * word on 2026-09-04 after a fleet grid -- the immediate-finish precedence,
	 * the finish-denial override and the exact axial-vmax ridge extension. No
	 * kind-gated arm remains; a candidate experiment gates on candidate(playerNum)
	 * -- the slots a race's candidateSlots names -- until its own independently
	 * measured promotion. Round 310 removed the danger block, and with it Round
	 * 126's false-target veto, Round 174's squeeze check, the thin-ridge check and
	 * its axial-vmax extension.
	 */
	private Direction optimalMoveAI1(final int[] pos, final int[] vel, final int playerNum) {
		// Endgame seal (frontier, per "force the last rival to crash = win"): with
		// few rivals left, if a SAFE move of mine leaves the decisive rival with no
		// legal move (a forced crash), take it. Only a rival that moves after me this
		// round (ri > subgamestate) can be forced; gated on my own safety so I never
		// trap myself to trap them.
		prepareDecisionFrame(pos, vel, playerNum);
		final Direction tacticalWin = RaceAiTactics.winNow(game, playerNum,
				!inScorerSim && trueConfirmDepth == 0 && simDepth == 0);
		if (tacticalWin != null)
			return tacticalWin;
		// Round 214: with nobody near, the race is a shortest-path problem and
		// the exact potential solves it. Every caution term below is priced
		// against a rival that is not there, and the measured cost of that was
		// 3.45% of the fleet's solo moves. The descent cannot crash: a state
		// with a finite value always has a successor one move closer.
		// Round 274, the owner's single-player rule made literal: the radius is
		// the rule's twenty cells, not forty. Round 279: point-to-point courses
		// descend the reachability map, the exact distance to their one crossing.
		if (!rivalWithinCheb(pos[0], pos[1], playerNum, AI1_CHOOSER_MAXDIST)) {
			final Direction alone = optimalAloneMove(pos, vel, playerNum);
			if (alone != null)
				return alone;
		}
		final int sealRivals = liveRivalsRemaining(playerNum);
		// Candidate: crossing now permanently secures this place, so it dominates
		// every seal that forgoes the finish to crash a later mover. Lap mode:
		// only once the gates are complete is a crossing actually the finish --
		// with a checkpoint still owed the referee treats it as an ordinary move,
		// so the legality-waived immediate crossing would drive into the wall.
		if (sealRivals >= 1 && sealRivals <= AI1_SEAL_MAXRIVALS && game.onFinalLap(playerNum)
				&& lapGate == 0) {
			final Direction finish = immediateFinishMove(pos, vel);
			if (finish != null)
				return finish;
		}
		// Round 279 (round 277): the seal fights for places, so a car we have
		// lapped is neither its target nor part of the field it waits for.
		final int placeRivals = placeRivalsRemaining(playerNum);
		if (placeRivals >= 1 && placeRivals <= AI1_SEAL_MAXRIVALS) {
			final int ri = decisivePlaceRival(playerNum);
			if (ri > game.subgamestate && rivalEscapes(ri, -1, -1, playerNum) >= 1) {
				final Direction sd = findForcedCrashMove(pos, vel, ri, playerNum);
				if (sd != null)
					return sd;
			}
		}
		// Endgame solver (round 43, lever 5, shared champion): 1v1 exact paranoid
		// minimax near the finish. Acts ONLY on proven wins (I finish first or
		// the rival is forced to crash under its best defense) -- the deep
		// generalization of the 1-ply seal above; unproven values fall through
		// to the normal scorer (insurance-premium law: no paranoid defense).
		if (sealRivals == 1 && !inScorerSim) {
			final Direction eg = endgameSolve(pos, vel, playerNum);
			if (eg != null) {
				if (AI_DEBUG_PLAYER == playerNum || AI_DEBUG_DJS)
					System.err.println("AIDBG EG p=" + playerNum + " pos=(" + pos[0] + "," + pos[1]
							+ ") vel=(" + vel[0] + "," + vel[1] + ") WIN via " + eg);
				return eg;
			}
		}
		// paceOverride (round 34, PROMOTED): AI2.9 was NOT pace-optimal -- pure
		// greedy min-turnsToFinish measurably beat it crash-free (sprint 14.1 vs
		// 14.9, hairpin, curve, bigoval) because the robustness/momentum tie-breaks
		// pay for traffic uncertainty even on lines that are provably safe. So take
		// a strictly-faster move than the cautious scorer's pick ONLY when its 2-ply
		// escape route is FULLY roomy (robust to opponent-prediction error -- lower
		// thresholds crashed 1 h2h game). Pinches keep full caution.
		int poBestT = Integer.MAX_VALUE, poScorerT = Integer.MAX_VALUE;
		Direction poDir = null;
		// perf_lean (exact): a suppressed decision (inScorerSim: a scorer car in a rollout, or any
		// decision beneath an upgraded move) runs none of the legs after the candidate loop. Of
		// the per-landing caution terms -- the opponent prediction (predictedOccupancyNow), the
		// safe-successor counts, the trap ladder with its needle surcharge, the corner-entry
		// brake -- it reads only what reaches queueBox, and of the round-34 pace scan only a
		// landing faster than the score's pick. A lean decision computes just those: queueBox
		// lazily, the prediction built at its first need, and the pace landing after the loop;
		// every value it uses is the eager one. The debug flags, the query sim trace and
		// -Dai.perf.noLean keep the eager decision; -Dai.perf.check races on the eager values
		// and compares the lean ones (PERF-AWARE LEAN MISMATCH).
		final boolean lean = inScorerSim && suppressedMovesOn() && !PERF_NO_LEAN;
		final boolean leanSkip = lean && !PERF_CHECK;
		CellOccupancy predictedOccupancy = leanSkip ? null
				: predictedOccupancyNow(playerNum, predictionWorkspace());
		CellOccupancy leanCheckOccupancy = null;
		final int stalledRivals = lean ? stalledLiveRivals(playerNum) : 0;
		if (PERF_LEAN_STATS && lean)
			LEAN_STATS.incrementAndGet(LEAN_DECISIONS);
		// Exact nested-scorer fast path. With the mover absent, record the
		// reference first-round landings once. If a candidate landing is not one
		// of those cells, adding it as a blocker cannot change the first mover;
		// inductively no later mover changes either, and round two (where the
		// blocker is removed) is therefore identical. Any hit falls back to the
		// original candidate-conditioned simulation.
		final TwoRoundWorkspace twoRoundReference = trueConfirmDepth > 0 || inScorerSim
				? prepareTwoRoundReference(playerNum) : null;
		// The ply-2 foresight (fore2) that priced the bodies of rivals AHEAD of
		// me in a second simulated round ended with round 247: the lookahead is
		// one level (AI1_DEEP_LOOKAHEAD), so the search never reaches a second
		// ply. The second round, its ahead-occupancy map and AI1_PLY2_PRICE were
		// removed on 2026-09-26; a deeper lookahead needs them back (git history).

		final CandidateWorkspace candidateWorkspace = candidateWorkspace();
		final double[] trapByDir = candidateWorkspace.trapByDirection;
		// round 49 arm C: raw map ttf per candidate, for the certified pace
		// tie-break after the loop.
		final int[] poTByDir = candidateWorkspace.turnsByDirection;
		// round 62: the score per candidate, for the pace overrides after the loop.
		final double[] scoreByDir = candidateWorkspace.scoreByDirection;
		MobilitySearch paceMobility = null;
		Direction best = null;
		double bestScore = Double.MAX_VALUE;
		int fallbackLegalMask = 0;
		int fallbackIllegalMask = 0;
		final int sm = succMask(pos[0], pos[1], vel[0], vel[1]);

		for (final Direction d : DIRECTIONS) {
			final int bit = 1 << d.ordinal();
			final int newVx = vel[0] + d.dx;
			final int newVy = vel[1] + d.dy;
			if ((sm & bit << 16) == 0)
				continue;
			final int newX = pos[0] + newVx;
			final int newY = pos[1] + newVy;
			// Round 296: a move that finishes the race is taken, CP2 touched on
			// the way included -- the precedence below needs it collected first.
			if (game.lapGates != null && lapAware && finishingMove(pos[0], pos[1], newX, newY))
				return d;
			// perf_aisearch (exact): the precedence below needs !lapAware or lapGate == 0.
			if ((!lapAware || lapGate == 0) && game.crossesFinishLegally(pos[0], pos[1], newX, newY)) {
				// Multi-lap: survivable-and-shedable crossing precedence (see pure scan).
				if (!lapAware && game.onFinalLap(playerNum) || lapGate == 0 && ((sm & bit) != 0
						&& !game.isCrashingPlayer(newX, newY, playerNum)
						&& reach.shedableLanding(newX, newY, newVx, newVy)
						&& reach.turnsToGate(1, newX, newY, newVx, newVy) != Integer.MAX_VALUE
						&& needleHeadway(newX, newY, newVx, newVy, playerNum, 1)
						// Round 211: in traffic the landing must keep an out (see the
						// checkpoint precedence below).
						&& (!robustMode || reach.isRobust(1, newX, newY, newVx, newVy)))) {
					if (AI_DEBUG_PLAYER == playerNum && !inScorerSim)
						System.err.println("AIDBG SCAN-CROSS p=" + playerNum + " chosen=" + d);
					return d;
				}
				// Stray or unshedable crossing: an ordinary legal move (cars
				// spawn BEHIND the line -- excluding these walls them in),
				// priced after the move since round 296.
			}
			// Checkpoint touch precedence: the post-touch landing prices a
			// full lap on the CURRENT gate map, so slow approaches would bob
			// one cell before the line forever (the gate-0 stall, at the CPs).
			// A touch with a continuing landing is progress -- take it (in
			// traffic only with needle headway; see pure scan). Since round 296
			// the exact potential prices a touch after the move: a touch refused
			// here is an ordinary move at its true distance, no longer ruled out
			// by a price that owed the gate again (the review, 2026-09-30).
			if (lapAware && lapGate != 0 && (sm & bit) != 0
					&& game.touchesGate(lapGate, pos[0], pos[1], newX, newY)
					&& !game.isCrashingPlayer(newX, newY, playerNum)
					&& reach.isAlive(newX, newY, newVx, newVy)
					&& reach.turnsToGate(lapGate == 1 ? 2 : 0, newX, newY, newVx, newVy)
							!= Integer.MAX_VALUE
					&& needleHeadway(newX, newY, newVx, newVy, playerNum, lapGate == 1 ? 2 : 0)
					// Round 211: needle headway is a snapshot -- both continuing
					// cells free NOW, one of them a rival's next landing (hybrid12
					// west side: the touch at (17,67) v(-5,8) scored 105 against 41
					// for the safe move and the precedence took it). In traffic the
					// landing must be in the robust set of the next gate; else the
					// scorer prices the touch (after the move since round 296, so
					// it may take it now) or takes it a move later.
					&& (!robustMode
							|| reach.isRobust(lapGate == 1 ? 2 : 0, newX, newY, newVx, newVy))) {
				if (AI_DEBUG_PLAYER == playerNum && !inScorerSim)
					System.err.println("AIDBG SCAN-CP p=" + playerNum + " gate=" + lapGate + " chosen=" + d);
				return exactPot != null
						? bestCheckpointMove(pos, vel, playerNum, sm, d) : d;
			}
			if ((sm & bit) == 0) {
				fallbackIllegalMask |= bit;
				continue;
			}
			if (game.isCrashingPlayer(newX, newY, playerNum))
				continue;
			fallbackLegalMask |= bit;
			// Round 296: the landing and its continuations are priced in the
			// frame after the move -- the gate events it collects are paid, not
			// owed again (a continuation past an owed checkpoint read as owing it).
			final boolean paidFrame = exactPot != null && game.lapGates != null;
			final int moveEvents = paidFrame ? game.gateEventsOnMove(lapGate, pos[0], pos[1], newX, newY) : 0;
			final int ownTurns = moveEvents == 0 ? ttf(newX, newY, newVx, newVy)
					: exactPot.movesToFinish(exactRemaining - moveEvents, newX, newY, newVx, newVy);
			if (ownTurns == Integer.MAX_VALUE)
				continue;

			// SOFT WORLD-STEP: simulate the next whole opponent round in actual
			// turn order, conditioned on THIS candidate landing. It answers the
			// round-r+1 questions: safe successors, and the ply-1 price of a
			// follow-up landing on a simulated body.
			final TwoRoundWorkspace worlds = simulateTwoRounds(playerNum, newX, newY,
					twoRoundReference);
			final double[] deepCounted = paidFrame && AI1_DEEP_LOOKAHEAD == 1
					? searchCountedAfter(newX, newY, newVx, newVy, worlds.world1Occupancy,
							gateAfter(lapGate, moveEvents), exactRemaining - moveEvents)
					: searchMinTurnsCountedSoft3(newX, newY, newVx, newVy, AI1_DEEP_LOOKAHEAD,
							worlds.world1Occupancy);
			final double deep = deepCounted[0];
			// Soft trap: if every depth-2 continuation is blocked but the state
			// itself can still reach the finish, keep the move alive with a
			// large finite surcharge instead of hard-skipping (which would drop
			// the AI to the foresight-free bestLegal/fallback pick).
			final double costToFinish = deep == Double.MAX_VALUE ? ownTurns + 20.0 : deep;

			// perf_lean: the speed is hoisted out of the eager block below (the same expression);
			// a lean decision keeps the three terms at these values, queueBox set lazily after it.
			final double speed = Math.hypot(newVx, newVy);
			double trapPenalty = 0.0, cornerEntry = 0.0, queueBox = 0.0;
			if (!leanSkip) {
				// Optimism-floored safe-successor count: the sim removing phantom
				// stale bodies ADDS safe successors (pace), while its model-dependent
				// pessimism (a mispredicted fast leader) can only LOWER the timed
				// count -- so max() with the frozen count keeps the optimism and
				// discards the pessimism, never more cautious than the crash-free
				// frozen standard.
				final int d2SafeCount = Math.max(countFutureSafeSuccessors(newX, newY, newVx, newVy,
						playerNum, predictedOccupancy),
						countFutureSafeSuccessorsTimed(newX, newY, newVx, newVy, worlds.world1Occupancy));
				trapPenalty = d2SafeCount == 0 ? 50.0
						: d2SafeCount == 1 ? AI1_TRAP_L1
								: d2SafeCount == 2 ? AI1_TRAP_L2
										: 0.0;
				// round 61 (AI1): rival-conditional trap relief. The ladder prices a
				// 1-2-wide certified thread as if a rival could claim the escape,
				// but with NO live rival within AI1_TRAP_SOLO_R of the landing the
				// thread is provably uncontestable for its consumption window and
				// the map's reach-certification suffices (monaco (116,46): every
				// car conceded 1 ttf to trap=2.0 on a SOLO thread the deep search
				// itself preferred). 0-safe stays 50 -- entering a dead fan is bad
				// even alone.
				if (trapPenalty > 0.0 && d2SafeCount > 0 && !rivalWithinCheb(newX, newY, playerNum, AI1_TRAP_SOLO_R))
					trapPenalty = 0.0;
				// Needle headway surcharge (round 197): an UNSTOPPABLE landing
				// without two body-free alive continuations under CURRENT
				// occupancy is one leader-stall from death -- the d2SafeCount
				// world-step credits rivals with vacating, which a stall wave
				// falsifies. Queues form at gates AND at narrow turns (rand2's
				// westward pocket), so the law is traffic-gated, not gate-gated.
				// Price it above every free approach so a stoppable entry wins.
				if (game.lapGates != null && lapAware && trapPenalty < 50.0
						&& !needleHeadway(newX, newY, newVx, newVy, playerNum, lapGate))
					trapPenalty = Math.max(trapPenalty, AI1_NEEDLE_TRAP);
				trapByDir[d.ordinal()] = trapPenalty;
				// Pack-gated knife-edge corner-entry brake: price roomy-successor
				// scarcity when a pack is packed at a corner entry (>= 2 rivals
				// within squared distance 36 and <= 1 roomy escape) -- fires where
				// the converging-opponent surcharge reads false. The pack gate
				// spares the lone fast knife-edge that is the racing line on tight
				// circuits, so only genuine corner-entry traffic jams brake.
				if (speed > AI1_BRAKE_SPEED) {
					final int roomySucc = countRoomySuccessors(newX, newY, newVx, newVy);
					if (roomySucc <= 1 && countNearbyOpponents(newX, newY, playerNum, AI1_PACK_R2) >= 2)
						cornerEntry = (speed - AI1_BRAKE_SPEED) * (roomySucc == 0 ? 3.0 : 1.5);
				}
				// v5.1 queue-compression corner guard (zandvoort forensic, AI1
				// only): the corner-entry brake above is opponent-BLIND in its
				// escape count, the brake proofs ignore transiting (|v| >= 3)
				// rivals, and the round-sims behind d2SafeCount and the ply-2
				// price assume a hairpin queue keeps flowing -- so a fast coast
				// whose timed margin is already thin (d2SafeCount <= 2) while
				// >= 2 STALLED rivals sit within squared distance 36 at-or-ahead
				// of the landing (compression, not a chase) is one round from
				// being boxed: on zandvoort both alive continuations of
				// (43,66)v(-4,3) were bodily occupied by the compressed queue
				// when the victim arrived, after the coast had beaten the
				// covered brake by 0.278. Price the coast like the survivable
				// knife-edge corner entry ((speed-4) * 1.5) so the brake wins.
				if (speed > AI1_BRAKE_SPEED && cornerEntry == 0.0) {
					if (d2SafeCount <= 2 && countStalledRivalsAhead(newX, newY, playerNum) >= 2)
						queueBox = (speed - AI1_BRAKE_SPEED) * 1.5;
					else {
						// v3 long-range trigger: the near trigger needs d2SafeCount
						// to collapse, but at speed 5+ the zandvoort pinch killed
						// from 10-20 cells out -- by the time the local box shows,
						// stopping is impossible (the victims were in forced-move
						// territory two moves before death; 3rd kill in 3 rounds).
						// Fire when >= 2 STALLED rivals sit ahead INSIDE my
						// stopping distance ~ (s^2 - 2.5^2) / 2 cells (shedding
						// ~1/round from s down to the stalled threshold 2.5).
						final double stopCells = (speed * speed - 6.25) / 2.0;
						if (stopCells > 0 && countStalledRivalsWithin(newX, newY, stopCells, playerNum) >= 2)
							queueBox = (speed - AI1_BRAKE_SPEED) * 1.5;
					}
				}
			}
			// perf_lean (exact): queueBox, lazily and the same value. The eager form is
			// (speed - 4) * 1.5 iff speed > 4, cornerEntry == 0.0 and (two stalled rivals ahead
			// with d2SafeCount <= 2, or two stalled rivals within my stopping distance); for
			// speed > 4, cornerEntry is 0.0 iff !(roomySucc <= 1 && pack >= 2), as speed - 4 is
			// then positive. The same pure predicates, cheapest first: both stalled counts are
			// bounded by the live stalled rivals counted once per decision, and d2SafeCount (the
			// prediction built at its first need) is asked only for the near trigger.
			if (lean) {
				double leanBox = 0.0;
				if (speed > AI1_BRAKE_SPEED && stalledRivals >= 2) {
					final double stopCells = (speed * speed - 6.25) / 2.0;
					boolean box = stopCells > 0
							&& countStalledRivalsWithin(newX, newY, stopCells, playerNum) >= 2;
					if (!box && countStalledRivalsAhead(newX, newY, playerNum) >= 2) {
						// Check mode builds its own rows: the eager prediction stays untouched.
						final CellOccupancy prediction;
						if (leanSkip) {
							if (predictedOccupancy == null) {
								predictedOccupancy = predictedOccupancyNow(playerNum, predictionWorkspace());
								if (PERF_LEAN_STATS)
									LEAN_STATS.incrementAndGet(LEAN_PREDICTIONS);
							}
							prediction = predictedOccupancy;
						} else {
							if (leanCheckOccupancy == null) {
								leanCheckOccupancy = predictedOccupancyNow(playerNum,
										leanCheckPredictionWorkspace());
								if (PERF_LEAN_STATS)
									LEAN_STATS.incrementAndGet(LEAN_PREDICTIONS);
							}
							prediction = leanCheckOccupancy;
						}
						if (PERF_LEAN_STATS)
							LEAN_STATS.incrementAndGet(LEAN_D2);
						box = Math.max(countFutureSafeSuccessors(newX, newY, newVx, newVy,
								playerNum, prediction),
								countFutureSafeSuccessorsTimed(newX, newY, newVx, newVy,
										worlds.world1Occupancy)) <= 2;
					}
					if (box) {
						final int roomySucc = countRoomySuccessors(newX, newY, newVx, newVy);
						if (!(roomySucc <= 1 && countNearbyOpponents(newX, newY, playerNum, AI1_PACK_R2) >= 2))
							leanBox = (speed - AI1_BRAKE_SPEED) * 1.5;
					}
				}
				if (leanSkip)
					queueBox = leanBox;
				else if (Double.compare(leanBox, queueBox) != 0)
					System.err.println("PERF-AWARE LEAN MISMATCH queueBox p=" + playerNum + " pos=("
							+ pos[0] + "," + pos[1] + ") vel=(" + vel[0] + "," + vel[1] + ") d=" + d
							+ " eager=" + queueBox + " lean=" + leanBox);
			}
			// AI2.9 intentionally has no soft conflict term; the hard live-body check remains.
			// Round 233: the round-201 lane spread no longer prices a landing. It
			// charged 0.3 for every rival within two cells of the landing and 0.1
			// within three, and it was tuned on the multi-seed CRASH census. Asked
			// by places it is the same mistake as the car-following law: a car that
			// steers away from company concedes the position it is racing for.
			// Head-to-head, mirrored, 840 pairs a slice: -0.641 +- 0.035 on seeds
			// 1-10 and -0.655 +- 0.035 on seeds 11-20, and the candidate crashes no
			// more than the champion doing it (77 against 92, 75 against 77). It was
			// still computed and multiplied by zero -- a loop over every rival for
			// every candidate -- until 2026-09-26; adding that exact 0.0 changed no
			// score, so its removal changes no decision.
			// Racing-line momentum tie-break: among moves of otherwise-equal cost,
			// prefer the one carrying more usable speed.
			final double momentum = AI2_MOMENTUM_TIEBREAK * speed;
			// Plateau-width robustness tie-break: prefer candidates whose best
			// follow-up is achievable many ways over knife-edge lines.
			final double robustness = AI2_PLATEAU_TIEBREAK * Math.min((int) deepCounted[1], 5);
			// Lane spreading (round 201): every magnet death in the multi-seed
			// census begins as displacement off a SINGLE shared geodesic --
			// eight cars stacked on one line. In lap traffic each driver weighs
			// the two tie-breaks slightly differently (deterministic by player
			// index; player 0 keeps the exact champion weights, laps=1
			// untouched), so the field fans across parallel near-optimal lines
			// instead of queueing nose-to-tail through the poison states.
			// The unstyled path keeps the LEGACY floating-point shape
			// (- momentum - robustness, two subtractions): folding them into
			// one subtraction is a one-ULP change that flips near-exact ties
			// (monza s30 trajectory pin caught it).
			// Round 229: the soft caution stack -- trap ladder, speed cap,
			// uncertified brake, corner-entry brake -- no longer prices a landing:
			// measured by places, every term was a veto over the one-move quantum
			// (-0.82 places without it). The ladder still feeds trapByDir and the
			// corner-entry brake still arms queueBox; the score is the exact race
			// distance, the traffic gates and the tie-breaks.
			final double score;
			if (game.lapGates != null && playerNum > 0) {
				final double f = 1.0 + AI1_LANE_STYLE * ((playerNum % 3) - 1);
				score = costToFinish + queueBox - (momentum * f + robustness * (2.0 - f));
			} else {
				score = costToFinish + queueBox - momentum - robustness;
			}
			final int poT = ownTurns;
			if (AI_DEBUG_COMP)
				System.err.println("R49C p=" + playerNum + " pos=(" + pos[0] + "," + pos[1] + ") vel=("
						+ vel[0] + "," + vel[1] + ") d=" + d + " land=(" + newX + "," + newY + ") ttf=" + poT
						+ " score=" + score + " cost=" + costToFinish + " trap=" + trapPenalty
						+ " ce=" + cornerEntry
						+ " qb=" + queueBox + " mom=" + momentum
						+ " rob=" + robustness);
			poTByDir[d.ordinal()] = poT;
			scoreByDir[d.ordinal()] = score;
			if (!leanSkip && poT < poBestT) {
				if (paceMobility == null)
					paceMobility = mobilitySearch(playerNum, true, AI1_MOBILITY_DEPTH);
				final double poRoom = futureMobility(newX, newY, newVx, newVy, paceMobility);
				final int poSpd = Math.max(Math.abs(newVx), Math.abs(newVy));
				if (poRoom >= AI1_PO_ROOM_HI || (poRoom >= AI1_PO_ROOM_MID && poSpd <= AI1_PO_SPD_MAX)
						|| (sealRivals <= AI1_SPARSE_RIVALS && poRoom >= AI1_PACE_FLOOR
							&& !sealable(newX, newY, newVx, newVy, playerNum))) {
					poBestT = poT;
					poDir = d;
				}
			}
			if (score < bestScore) {
				bestScore = score;
				best = d;
				poScorerT = poT;
			}
		}
		// Round 256: the faithful joint world was a veto with a vote it never
		// cast. Where the score cannot separate two landings, ask it. Measured
		// at -1.194 places over the round-254 champion at twelve rounds (83
		// boards of 84, crashes 123 against 189); three rounds bought -0.501,
		// six -0.952, nine -1.129, and the increments halve (round 257).
		// Round 262, the owner's rule: with no car within AI1_CHOOSER_MAXDIST cells
		// the car races the single-player optimum -- the score's landing, the
		// exact remaining distance -- exactly as it drives alone. Round 261
		// priced the gate at 20 cells: +0.001 places in packs (81 boards tied),
		// +0.004 scattered, one synthetic course; the guarantee is worth that.
		// perf_lean (exact), ahead of the chooser's code below: a lean decision's round-34 pace
		// landing. The eager scan in the loop keeps, among the landings that pass the room
		// test, the first in Direction order with the fewest map turns, and a suppressed
		// decision takes it only below poScorerT (the swap after the chooser, which it never
		// consults). So test only the landings below poScorerT, in ascending (turns, ordinal)
		// order, and stop at the first that passes: the same landing, or none. The projection
		// is built at the first test, from the board the loop left unchanged.
		if (lean) {
			Direction leanDir = null;
			int leanT = Integer.MAX_VALUE;
			MobilitySearch leanMobility = null;
			for (int tested = 0;;) {
				int pick = -1, pickT = poScorerT;
				for (int o = 0; o < DIRECTIONS.length; o++)
					if ((tested & 1 << o) == 0 && poTByDir[o] < pickT) {
						pick = o;
						pickT = poTByDir[o];
					}
				if (pick < 0)
					break;
				tested |= 1 << pick;
				final Direction d = DIRECTIONS[pick];
				final int newVx = vel[0] + d.dx, newVy = vel[1] + d.dy;
				final int newX = pos[0] + newVx, newY = pos[1] + newVy;
				if (leanMobility == null) {
					leanMobility = mobilitySearch(playerNum, true, AI1_MOBILITY_DEPTH);
					if (PERF_LEAN_STATS)
						LEAN_STATS.incrementAndGet(LEAN_PACE_DECISIONS);
				}
				if (PERF_LEAN_STATS)
					LEAN_STATS.incrementAndGet(LEAN_PACE_TESTS);
				final double poRoom = futureMobility(newX, newY, newVx, newVy, leanMobility);
				final int poSpd = Math.max(Math.abs(newVx), Math.abs(newVy));
				if (poRoom >= AI1_PO_ROOM_HI || (poRoom >= AI1_PO_ROOM_MID && poSpd <= AI1_PO_SPD_MAX)
						|| (sealRivals <= AI1_SPARSE_RIVALS && poRoom >= AI1_PACE_FLOOR
							&& !sealable(newX, newY, newVx, newVy, playerNum))) {
					leanDir = d;
					leanT = pickT;
					break;
				}
			}
			if (PERF_LEAN_STATS && leanDir != null)
				LEAN_STATS.incrementAndGet(LEAN_PACE_SWAPS);
			if (leanSkip) {
				poDir = leanDir;
				poBestT = leanT;
			} else {
				// Check mode: the eager scan's poDir stands; compare the landings they take.
				final Direction eager = poDir != null && poBestT < poScorerT ? poDir : best;
				final Direction shadow = leanDir != null && leanT < poScorerT ? leanDir : best;
				if (eager != shadow)
					System.err.println("PERF-AWARE LEAN MISMATCH pace p=" + playerNum + " pos=(" + pos[0]
							+ "," + pos[1] + ") eager=" + eager + " lean=" + shadow);
			}
		}
		// The round-256 chooser, described above the perf_lean walk:
		boolean chooserConsulted = false;
		chooserJudgedPace = false;
		if (best != null && !inScorerSim
			&& nearestLiveRival(pos, playerNum) <= AI1_CHOOSER_MAXDIST) {
			best = jointChooser(pos, vel, playerNum, best, scoreByDir, bestScore, poDir);
			poScorerT = poTByDir[best.ordinal()];
			chooserConsulted = true;
		}
		// Round 49 arm C (AI1): certified pace tie-break. The lateral-spacing
		// term `spread` outranks raw pace -- in every decision it flips, the
		// traffic-priced deep search rates the alternative EXACTLY equal on
		// costToFinish and the alternative is strictly faster on the map
		// (comp_counterfactual, 5 traffic sinks: 46 ttf recoverable, ZERO cases
		// where the search preferred the slower cell). Deleting spread outright
		// (arm A) buys ~0.45% pace but costs crashes where spacing is really
		// load-bearing (hungaroring 1->6, lemans 1->5 over 10 seeds). So take
		// the faster line only when it is CERTIFIED: weakly better on every
		// non-spread term (spread is the sole reason it lost), zero trap
		// penalty, not sealable, and it survives the same 3-round joint
		// roll-forward DJS trusts. Survival-only asymmetry -- an uncertified
		// faster line is never taken.
		// Round 278 (round 269 promoted): once the chooser has ranked the landings
		// the score cannot separate, its pick stands -- this tie-break took the
		// score's argmin back from 315 of 356 chooser picks in 8-car races.
		// -0.047 +- 0.011 places against round 274.
		if (best != null && !inScorerSim && !chooserConsulted) {
			final double bestNS = scoreByDir[best.ordinal()];
			int fastT = poTByDir[best.ordinal()];
			Direction fast = null;
			for (final Direction d : DIRECTIONS) {
				if (d == best || poTByDir[d.ordinal()] >= fastT)
					continue;
				if (scoreByDir[d.ordinal()] > bestNS + 1e-9)
					continue;
				if (trapByDir[d.ordinal()] != 0.0)
					continue;
				final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
				final int nx = pos[0] + nvx, ny = pos[1] + nvy;
				if (sealable(nx, ny, nvx, nvy, playerNum))
					continue;
				if (simOutcome(nx, ny, nvx, nvy, playerNum, AI1_DJS_ROUNDS, true, true, false, false) < 0)
					continue;
				fast = d;
				fastT = poTByDir[d.ordinal()];
			}
			if (fast != null) {
				best = fast;
				poScorerT = fastT; // round 279: the pace comparison below reads the landing taken
			}
		}
		// Round 292b: once the chooser has judged a pace landing it added, its pick
		// stands (-0.023 places as a lone entrant against round 299, -0.026 on
		// computed starts); a pace landing the window already held keeps the swap.
		Direction chosen = (poDir != null && poBestT < poScorerT && !chooserJudgedPace)
				? poDir : best;
		// Round 75-77 (AI1): recover a strictly-faster line only when a
		// conservative rival-occupancy proof leaves an empty-track-optimal escape
		// private, then require the independent real-scorer rollout to agree. Of the
		// guards below that kept the final veto only the round-232 kinematic confirm
		// is left (the seal guard went in round 234, the danger guards in round 310).
		if (chosen != null && !inScorerSim) {
			chosen = privatePaceOverride(pos, vel, playerNum, chosen, scoreByDir, trapByDir, poTByDir);
			chosen = stagedPaceOverride(pos, vel, playerNum, chosen, scoreByDir, trapByDir, poTByDir);
			chosen = guardedFieldPaceOverride(pos, vel, playerNum, chosen, trapByDir, poTByDir);
		}
		// Round 232: the last-resort kinematic confirm. Every guard leg below
		// certifies the chosen move with a world that ends BEFORE the car could
		// stop -- the round-93 fast-fragile leg looks four rounds ahead and
		// switches to a line that dies in seven; the round-197 'unstoppable, no
		// headway' tier arms no leg at all. The audited self-play deaths are all
		// one shape: a thin landing taken beside a rival 40-60 cells before a
		// merge, closed three to eight rounds later. So before those legs run,
		// check the pick the pace overrides leave with ONE faithful joint search,
		// with the horizon round 205 gave the cheap world: the rounds this
		// landing needs to stop. Survival-only, like every other guard -- the
		// pick is kept unless it provably dies and an alternative survives.
		// Measured head-to-head (mirrored, 840 pairs a slice): -0.024 places
		// with 72 candidate crashes against the champion's 125 in the same
		// races; a whole field of these cars crashes 79 times per 730 races
		// against 127, for half a percent of moves. Lengthening the existing
		// legs instead moved nothing (-0.002); arming it on a slower leader
		// ahead in the lane cut more crashes but gave the places back, which is
		// the round-206 following law again and the rule forbids it.
		// Round 310: the guard legs it ran ahead of are gone; it is the danger
		// search's one caller now.
		if (!inScorerSim && chosen != null && game.lapGates != null) {
			final int kvx = vel[0] + chosen.dx, kvy = vel[1] + chosen.dy;
			final int kx = pos[0] + kvx, ky = pos[1] + kvy;
			final int kspd = Math.max(Math.abs(kvx), Math.abs(kvy));
			if (trapByDir[chosen.ordinal()] >= AI1_TRAP_L2 && trapByDir[chosen.ordinal()] <= AI1_NEEDLE_TRAP
					&& !finishingMove(pos[0], pos[1], kx, ky)
					&& countRivalsWithinCheb(kx, ky, playerNum, AI1_KIN_CONFIRM_R) >= 1) {
				final int kRounds = Math.min(AI1_KIN_HORIZON_CAP, Math.max(AI1_DJS_ROUNDS, kspd));
				// Round 301c: the mover plays its own scorer here, as in the main danger
				// search since round 254, not the selfMove proxy -- and in the deep-pack,
				// corridor and fast-fragile searches below (-0.020 places on held-out
				// seeds, -0.019 computed, -0.011 as a lone entrant against round 300a;
				// CPU 1.01x). Round 310: the main danger search and those three are gone.
				final Direction kChoice = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
						true, kRounds, AI1_SCORER_MAXRIVALS, true);
				if (AI_DEBUG_DJS && kChoice != chosen)
					System.err.println("AIDBG KINCONF p=" + playerNum + " pos=(" + pos[0] + "," + pos[1]
							+ ") " + chosen + " -> " + kChoice + " r" + kRounds);
				chosen = kChoice;
			}
		}
		if (chosen != null) {
			// Round 234: the round-50 seal guard is gone. It replaced a chosen landing
			// that a worst-case distinct-opponent matching could box with the fastest
			// unsealable alternative, and it is the fourth caution rule in a row to
			// fail its own justification: removing it is worth -0.196 +- 0.024 places
			// on random starts, -0.182 on fresh seeds, -0.174 on computed starts, and
			// the cars that stop obeying it crash LESS in the same races (57 against
			// 71, 53 against 69). A worst-case box is a possibility, not a fact, and
			// paying a whole line for it hands the position to whoever does not.
			// sealable() stays: the pace overrides and the round-232 confirm ask it.
			// Round 75 (PROMOTED): a bounded, proof-gated finish sprint. Local trap and
			// uncertainty terms can spend a whole turn protecting a line even when
			// a faster candidate is already close enough to certify all the way to
			// the flag. Monaco s16 m789 is the minimal example: S has map ttf=15
			// and finishes in 15 rounds, while narrow SW has ttf=14 and finishes in
			// exactly 14; every other move dies. Accept a strictly-faster candidate
			// only if BOTH the score-shaped-rival and scorer-rival joint worlds reach
			// the finish at the empty-map lower bound (ttf+1 simulation rounds; the
			// first partial round contains only players after me). The normal DJS
			// ran afterwards with its own survival veto until round 310.
			if (!inScorerSim) {
				final int chosenT = poTByDir[chosen.ordinal()];
				final boolean homogeneousLive = chosenT > AI1_FINISH_CERT_TTF
						&& kindHomogeneousField(playerNum);
				final boolean extendedContext = chosenT >= AI1_FINISH_HOMOGENEOUS_TTF + 2
						&& chosenT <= AI1_FINISH_EXTENDED_TTF + 1
						&& kindHomogeneousRoster(playerNum)
						&& liveRivalsRemaining(playerNum) >= AI1_PRIVATE_FIELD_MIN_RIVALS
						&& hasAdjacentPriorVelocityPeer(pos, vel, playerNum);
				// Multi-lap: the sprint exists to cross ASAP -- final lap only.
				int sprintT = game.onFinalLap(playerNum) ? chosenT : Integer.MIN_VALUE;
				Direction sprint = null;
				for (final Direction d : DIRECTIONS) {
					final int t = poTByDir[d.ordinal()];
					final boolean extendedFrontier = t > AI1_FINISH_HOMOGENEOUS_TTF
							&& t <= AI1_FINISH_EXTENDED_TTF && t + 1 == chosenT
							&& d != Direction.NONE && extendedContext
							&& trapByDir[d.ordinal()] == AI1_TRAP_L2;
					if (d == chosen || t >= sprintT
							|| (t > AI1_FINISH_HOMOGENEOUS_TTF && !extendedFrontier)
							|| (t > AI1_FINISH_CERT_TTF && (d == Direction.NONE
									|| !homogeneousLive))
							|| trapByDir[d.ordinal()] > AI1_TRAP_L1)
						continue;
					final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
					final int nx = pos[0] + nvx, ny = pos[1] + nvy;
					if (extendedFrontier && sealable(nx, ny, nvx, nvy, playerNum))
						continue;
					final int rounds = t + 1;
					if (simOutcome(nx, ny, nvx, nvy, playerNum, rounds, true, true, true, false) % VERDICT_PLACE_STRIDE != 0)
						continue;
					if (simOutcome(nx, ny, nvx, nvy, playerNum, rounds, true, true, true, true,
							AI1_DEEP_CERT_RIVALS, null) % VERDICT_PLACE_STRIDE != 0)
						continue;
					// Round 176: a one-successor sprint can pass both proxy worlds
					// while faithful rivals occupy its only continuation one round
					// later. Confirm only that narrow, traffic-dependent class;
					// wider sprint lines retain the established cheaper certificate.
					if (t >= AI1_FINISH_TRUE_CONFIRM_ROUNDS
							&& trapByDir[d.ordinal()] >= AI1_TRAP_L1
							&& liveRivalsRemaining(playerNum) > 0) {
						if (trueConfirmDepth >= AI1_TRUE_CONFIRM_MAXDEPTH)
							continue;
						trueConfirmDepth++;
						try {
							if (simOutcome(nx, ny, nvx, nvy, playerNum,
									AI1_FINISH_TRUE_CONFIRM_ROUNDS, true, true, true, true,
									false, true, AI1_DEEP_CERT_RIVALS, null, null, null) < 0)
								continue;
						} finally {
							trueConfirmDepth--;
						}
					}
					if (extendedFrontier) {
						final int frontierCvx = vel[0] + chosen.dx, frontierCvy = vel[1] + chosen.dy;
						// Round 279: the field's cost is no veto (the racecraft rule), so
						// neither rollout rolls the rivals on past the mover's finish to
						// price it (review, 2026-09-29): the verdicts are the same.
						final int chosenFinal = scorerFieldOutcome(pos[0] + frontierCvx,
								pos[1] + frontierCvy, frontierCvx, frontierCvy, playerNum,
								AI1_DEEP_HORIZON, AI1_DEEP_CERT_RIVALS, null);
						final int candidateFinal = scorerFieldOutcome(nx, ny, nvx, nvy, playerNum,
								AI1_DEEP_HORIZON, AI1_DEEP_CERT_RIVALS, null);
						if (chosenFinal < 0 || candidateFinal < 0 || candidateFinal >= chosenFinal)
							continue;
					}
					sprint = d;
					sprintT = t;
				}
				if (sprint != null) {
					if (AI_DEBUG_DJS)
						System.err.println("AIDBG SPRINT p=" + playerNum + " pos=(" + pos[0] + ","
								+ pos[1] + ") " + chosen + " -> " + sprint + " ttf=" + sprintT);
					chosen = sprint;
				}
			}
			// A high-energy one-turn finish approach can be denied by a leader
			// braking into the pocket after every cheap world has declared the
			// line safe. Pay for a faithful confirm only on the measured compact,
			// aligned, last-slot class. Since round 310 its pick is final: the danger
			// block that held the last veto is gone.
			if (!inScorerSim)
				chosen = finishDenialOverride(pos, vel, playerNum, chosen,
						candidateWorkspace);

			// Round 310: the danger joint search family is gone -- the round-40 guard
			// that ran here and every leg only it armed (ridge, deep pack, corridor, queue,
			// fast-fragile, pair, thread, smoke, dense pack, funnel, squeeze, ESC). Off
			// for a candidate car against the round-305/309 champion it read random
			// starts -0.021 +- 0.009 places, held-out -0.026 +- 0.009, computed -0.009
			// +- 0.009, scattered +0.001 +- 0.001, duels -0.002 +- 0.001, and -0.026 +-
			// 0.008 as a lone entrant. Its survival-only switches overrode the score's
			// and the chooser's pick; without them the cars crash more, which the
			// racecraft rule allows, and finish better.
			if (AI_DEBUG_PLAYER == playerNum)
				System.err.println("AIDBG turn" + (inScorerSim ? "-sim" : "-REAL") + " p=" + playerNum + " pos=(" + pos[0] + "," + pos[1] + ") vel=("
						+ vel[0] + "," + vel[1] + ") chosen=" + chosen + " trap=" + trapByDir[chosen.ordinal()]
						+ " gate=" + lapGate + " ttf=" + ttf(pos[0] + vel[0] + chosen.dx,
								pos[1] + vel[1] + chosen.dy, vel[0] + chosen.dx, vel[1] + chosen.dy));
			return chosen;
		}
		// Multi-lap survival fallback: when the lap map prices every candidate
		// MAX (the single-file shedable approach is blocked by bodies), stay
		// ALIVE by the finish map at minimum speed instead of dead-coasting --
		// circle, then cross when the line unblocks.
		if (lapAware) {
			if (AI_DEBUG_PLAYER == playerNum && !inScorerSim) {
				final StringBuilder sb = new StringBuilder("AIDBG SURVIVAL p=" + playerNum
						+ " pos=(" + pos[0] + "," + pos[1] + ") vel=(" + vel[0] + ","
						+ vel[1] + ") gate=" + lapGate
						+ " selfAlive=" + reach.isAlive(pos[0], pos[1], vel[0], vel[1])
						+ " selfG0=" + reach.turnsToGate(0, pos[0], pos[1], vel[0], vel[1])
						+ " selfG1=" + reach.turnsToGate(1, pos[0], pos[1], vel[0], vel[1])
						+ " vals=");
				for (final Direction d : DIRECTIONS) {
					final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
					final int t = reach.turnsToGate(lapGate, pos[0] + nvx, pos[1] + nvy, nvx, nvy);
					final int da = reach.distAt(pos[0] + nvx, pos[1] + nvy);
					sb.append(d.ordinal()).append(':').append(t == Integer.MAX_VALUE ? "INF" : t)
							.append('/').append(da == Integer.MAX_VALUE ? "X" : da).append(' ');
				}
				System.err.println(sb);
			}
			Direction alive = null;
			int aliveT = Integer.MAX_VALUE;
			int aliveSpd = Integer.MAX_VALUE;
			for (final Direction d : DIRECTIONS) {
				if ((fallbackLegalMask & 1 << d.ordinal()) == 0)
					continue;
				final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
				final int nx = pos[0] + nvx, ny = pos[1] + nvy;
				if (game.isCrashingPlayer(nx, ny, playerNum)
						|| !reach.isAlive(nx, ny, nvx, nvy))
					continue;
				final int t = reach.turnsToFinish(nx, ny, nvx, nvy);
				final int spd = speedSquared(nvx, nvy);
				if (spd < aliveSpd || spd == aliveSpd && t < aliveT) {
					alive = d;
					aliveSpd = spd;
					aliveT = t;
				}
			}
			if (alive != null)
				return alive;
		}
		return scoreMinTurnsFallback(pos[0], pos[1], vel[0], vel[1],
				fallbackLegalMask, fallbackIllegalMask, Direction.NONE);
	}

	/** Certificate for a high-energy line that a rival can close at the flag.
	 * The incumbent must die under faithful policies; an escape must survive
	 * both the deep scorer world and the same faithful world. */
	private Direction finishDenialOverride(final int[] pos, final int[] vel,
			final int playerNum, final Direction chosen,
			final CandidateWorkspace candidates) {
		if (inFinishDenialConfirm
				|| trueConfirmDepth >= AI1_TRUE_CONFIRM_MAXDEPTH
				|| game.subgamestate != game.players.length - 1
				|| !game.onFinalLap(playerNum) || lapGate != 0)
			return chosen;
		final double[] trapByDir = candidates.trapByDirection;
		final int[] turnsByDir = candidates.turnsByDirection;
		final int chosenT = turnsByDir[chosen.ordinal()];
		if (chosenT < 0 || chosenT > AI1_FINISH_DENIAL_MAX_TTF
				|| ttf(pos[0], pos[1], vel[0], vel[1]) != chosenT + 1)
			return chosen;
		final int cvx = vel[0] + chosen.dx, cvy = vel[1] + chosen.dy;
		final int cx = pos[0] + cvx, cy = pos[1] + cvy;
		// Final lap, no gate owed: the scan has already returned any move that
		// crosses the line legally, so neither the chosen landing nor a brake
		// alternative below (a scanned row) finishes.
		final int chosenSpeed2 = speedSquared(cvx, cvy);
		if (chosenSpeed2 < AI1_FINISH_DENIAL_MIN_SPEED2
				|| countRivalsWithinCheb(pos[0] + vel[0], pos[1] + vel[1], playerNum, 1) == 0
				|| countRivalsWithinCheb(cx, cy, playerNum, AI1_SCORER_NEAR)
						< AI1_FINISH_DENIAL_NEAR_RIVALS)
			return chosen;
		int alignedAhead = 0;
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			if (Math.abs(pp[0] - cx) > AI1_SCORER_NEAR
					|| Math.abs(pp[1] - cy) > AI1_SCORER_NEAR
					|| (long) (pp[0] - cx) * cvx + (long) (pp[1] - cy) * cvy <= 0L)
				continue;
			final int[] pv = p.getVelocity();
			if (Math.abs(pv[0] - cvx) <= 2 && Math.abs(pv[1] - cvy) <= 2)
				alignedAhead++;
		}
		if (alignedAhead < AI1_FINISH_DENIAL_ALIGNED_RIVALS)
			return chosen;

		int brakeMask = 0;
		for (final Direction d : DIRECTIONS) {
			if (d == chosen || turnsByDir[d.ordinal()] > chosenT + 1
					|| trapByDir[d.ordinal()] > AI1_TRAP_L1)
				continue;
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			if (chosenSpeed2 - speedSquared(nvx, nvy) >= AI1_FINISH_DENIAL_MIN_BRAKE2)
				brakeMask |= 1 << d.ordinal();
		}
		if (brakeMask == 0)
			return chosen;

		final int faithfulCap = AI_DEBUG_FINISH_DENIAL
				? Math.max(1, Math.min(game.players.length,
						AI_DEBUG_FINISH_DENIAL_RIVAL_CAP))
				: AI1_FINISH_DENIAL_RIVALS;
		// The nested confirms run a level deeper, on their own candidate rows
		// (round 223): this level's rows need no snapshot (review, 2026-09-29).
		inFinishDenialConfirm = true;
		trueConfirmDepth++;
		try {
			final int chosenFinal = faithfulFinishDenialOutcome(cx, cy, cvx, cvy,
					playerNum, faithfulCap);
			if (chosenFinal >= 0) {
				if (AI_DEBUG_FINISH_DENIAL)
					System.err.println("AIDBG FINISH-DENIAL cap=" + faithfulCap
							+ " p=" + playerNum + " pos=(" + pos[0] + "," + pos[1]
							+ ") chosen=" + chosen + " keep sim=" + chosenFinal);
				return chosen;
			}
			Direction best = null;
			int bestFinal = Integer.MAX_VALUE;
			int bestSpeed2 = Integer.MAX_VALUE;
			int bestT = Integer.MAX_VALUE;
			for (final Direction d : DIRECTIONS) {
				if ((brakeMask & 1 << d.ordinal()) == 0)
					continue;
				final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
				final int speed2 = speedSquared(nvx, nvy);
				final int nx = pos[0] + nvx, ny = pos[1] + nvy;
				final int t = ttf(nx, ny, nvx, nvy);
				if (!game.aiMoveLegal(pos[0], pos[1], nx, ny)
						|| game.isCrashingPlayer(nx, ny, playerNum)
						|| !reach.isAlive(nx, ny, nvx, nvy))
					continue;
				final int scorerFinal = simOutcome(nx, ny, nvx, nvy, playerNum,
						AI1_FINISH_DENIAL_ROUNDS, true, true, true, true, true,
						AI1_DEEP_CERT_RIVALS, null);
				final int candidateFinal = scorerFinal < 0 ? -1
						: faithfulFinishDenialOutcome(nx, ny, nvx, nvy,
								playerNum, faithfulCap);
				if (AI_DEBUG_FINISH_DENIAL || AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum)
					System.err.println("AIDBG FINISH-DENIAL cap=" + faithfulCap
							+ " alt=" + d + " t=" + t + " speed2=" + speed2
							+ " scorer=" + scorerFinal + " faithful=" + candidateFinal);
				if (candidateFinal < 0)
					continue;
				if (candidateFinal < bestFinal
						|| candidateFinal == bestFinal && speed2 < bestSpeed2
						|| candidateFinal == bestFinal && speed2 == bestSpeed2 && t < bestT) {
					best = d;
					bestFinal = candidateFinal;
					bestSpeed2 = speed2;
					bestT = t;
				}
			}
			if (AI_DEBUG_FINISH_DENIAL || AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum)
				System.err.println("AIDBG FINISH-DENIAL cap=" + faithfulCap
						+ " p=" + playerNum + " pos=(" + pos[0] + "," + pos[1]
						+ ") chosen=" + chosen + " dies -> "
						+ (best == null ? "keep (no survivor)" : "switch " + best
								+ " sim=" + bestFinal + " speed2=" + bestSpeed2));
			return best != null ? best : chosen;
		} finally {
			trueConfirmDepth--;
			inFinishDenialConfirm = false;
		}
	}

	private int faithfulFinishDenialOutcome(final int x, final int y, final int vx,
			final int vy, final int playerNum, final int faithfulCap) {
		return simOutcome(x, y, vx, vy, playerNum, AI1_FINISH_DENIAL_ROUNDS,
				true, true, true, true, true, true, faithfulCap, null, null, null);
	}

	/** Round 226: the mover whose decision this is, for candidate gating inside
	 *  pricing helpers that have no player argument. Part of the decision frame:
	 *  a nested rival compute sets its own and scorerMoveOverState restores it. */
	private int moverNumber;

	/** Identical frame preparation for normal decisions and standalone sim queries. */
	private void prepareDecisionFrame(final int[] pos, final int[] vel, final int playerNum) {
		moverNumber = playerNum;
		// Round 276, the owner's approximation of the grid rule: the deciding car
		// models every car on the track with the grid until it has passed its
		// first checkpoint, and without it afterwards. Set at the top level only,
		// so nested rival decisions share the decider's world.
		if (simDepth == 0 && !inScorerSim)
			game.aiGridLegal = !passedFirstCheckpoint(playerNum);
		lapGate = game.nextGateOf(playerNum);
		lapAware = !game.onFinalLap(playerNum) || lapGate != 0;
		final int robustSp = Math.max(Math.abs(vel[0]), Math.abs(vel[1]));
		robustMode = lapAware && rivalAheadWithinCheb(pos[0], pos[1], vel[0], vel[1], playerNum,
				Math.max(AI1_ROBUST_RANGE, Math.min(robustSp * (robustSp + 1) / 2, AI1_ROBUST_KIN_CAP)));
		exactPot = game.optimalPotential();
		// Round 291 (round 287): the events owed need no potential; finishingMove
		// reads them on the Nordschleife too.
		int lapsDone = 0;
		for (final Player q : game.players)
			if (q.getNumber() == playerNum)
				lapsDone = q.getLap();
		exactRemaining = OptimalPotential.remainingEvents(lapGate, lapsDone, game.totalLaps);
		recordPlayerFrames();
	}

	/** Multi-lap: true while choosing for a mover NOT on its final lap --
	 *  every turns-to-finish read then uses the shedable-crossing lap map.
	 *  Set at optimalMoveAI1 entry; the dispatcher is only entered from
	 *  RaceGame (no recursion), so a plain field is safe per instance. */
	private boolean lapAware;
	/** Multi-lap: the mover's next gate (0=S/F, 1=CP1, 2=CP2). */
	private int lapGate;
	/** In nearby traffic, checkpoint/crossing precedence needs a robust
	 *  continuation. Race-distance pricing itself stays opponent-independent. */
	private boolean robustMode;
	/** Round 216: the exact distance-to-finish map, and the gate events this
	 *  mover still owes. Null on a board too large for the potential's budget
	 *  and on a course without lap gates; the gate maps then serve as before.
	 *  Round 222: like lapGate/lapAware/robustMode these are the MOVER's and
	 *  a nested rival compute reassigns them -- scorerMoveOverState restores
	 *  all four. */
	private OptimalPotential	exactPot;
	private int					exactRemaining;
	/** Round 222: every player's own lap frame, by player index, recorded at
	 *  each decision entry so a rival's state is priced on the rival's gate
	 *  schedule and not the mover's. */
	private int[]				frameGate		= new int[0];
	private int[]				frameRemaining	= new int[0];
	private boolean[]			frameLapAware	= new boolean[0];

	/** Round 222: each player's gate, lap-awareness and remaining events, by
	 *  player index. Per-player facts, so a nested rival compute records the
	 *  projected values. Rollouts and nested scorers own separate frame arrays. */
	private void recordPlayerFrames() {
		final int n = game.players.length;
		if (frameGate.length < n) {
			frameGate = new int[n];
			frameRemaining = new int[n];
			frameLapAware = new boolean[n];
		}
		for (int i = 0; i < n; i++) {
			final Player q = game.players[i];
			final int number = q.getNumber();
			frameGate[i] = game.nextGateOf(number);
			frameLapAware[i] = !game.onFinalLap(number) || frameGate[i] != 0;
			frameRemaining[i] = OptimalPotential.remainingEvents(frameGate[i], q.getLap(),
					game.totalLaps);
		}
	}

	/** Round 222: ttf() in player {@code idx}'s own frame -- its gate,
	 *  remaining events and lap-awareness. */
	private int ttfFor(final int idx, final int x, final int y, final int vx, final int vy) {
		if (exactPot != null)
			return exactPot.movesToFinish(frameRemaining[idx], x, y, vx, vy);
		if (!frameLapAware[idx])
			return reach.turnsToFinish(x, y, vx, vy);
		return reach.turnsToGate(frameGate[idx], x, y, vx, vy);
	}

	/** Round 222: the crossing rule of the rollout's move models, in player
	 *  {@code idx}'s frame: a crossing is a finish or a lap only when that
	 *  player owes nothing else. */
	private boolean crossingCountsFor(final int idx, final int nx, final int ny, final int nvx,
			final int nvy) {
		return !frameLapAware[idx]
				|| frameGate[idx] == 0 && reach.shedableLanding(nx, ny, nvx, nvy);
	}

	private int ttf(final int x, final int y, final int vx, final int vy) {
		// Round 216: the exact remaining distance whenever the potential exists.
		// The gate maps answer "how far to the NEXT gate", which is not what a
		// race minimises -- arriving at a gate in a poor state is paid for after
		// it, and measurement put half the pace given up on landings the policy
		// would happily take beyond what the gate map can see. Round 228:
		// narrow lanes carry their real distance too. Collision, headway,
		// seal and rollout checks price the actual traffic around that line.
		if (exactPot != null)
			return exactPot.movesToFinish(exactRemaining, x, y, vx, vy);
		if (!lapAware)
			return reach.turnsToFinish(x, y, vx, vy);
		return reach.turnsToGate(lapGate, x, y, vx, vy);
	}

	/** Whether every live rival runs the mover's policy. Since the 2026-09-04
	 *  promotion every AI kind is the one policy, so the question is whether a
	 *  human is among the live rivals; before it the gates compared kind labels,
	 *  which kept them off in the mixed-label fleet field for no reason. */
	private boolean kindHomogeneousField(final int playerNum) {
		for (final Player p : game.players)
			if (p.getNumber() != playerNum && !p.isFinished() && !p.isAi())
				return false;
		return true;
	}

	/** Whether every racer in the starting roster runs the mover's policy.
	 *  Unlike the live-field gate, this cannot become true late in a mixed race
	 *  after the human has finished or crashed. */
	private boolean kindHomogeneousRoster(final int playerNum) {
		for (final Player p : game.players)
			if (p.getNumber() != playerNum && !p.isAi())
				return false;
		return true;
	}

	/** Whether a previously moved live rival is adjacent, shares the mover's
	 *  current velocity, and has a lateral (or nearly lateral) offset. */
	private boolean hasAdjacentPriorVelocityPeer(final int[] pos, final int[] vel,
			final int playerNum) {
		for (int i = 0; i < game.subgamestate; i++) {
			final Player p = game.players[i];
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			final int dx = pp[0] - pos[0], dy = pp[1] - pos[1];
			if (Math.max(Math.abs(dx), Math.abs(dy)) != 1)
				continue;
			final int[] pv = p.getVelocity();
			if (pv[0] == vel[0] && pv[1] == vel[1]
					&& Math.abs((long) dx * vel[0] + (long) dy * vel[1]) <= 1L)
				return true;
		}
		return false;
	}


	/** Round 117 candidate-formation proof: a previously moved rival is
	 * adjacent to the proposed landing and already carries its exact velocity.
	 * The lateral dot bound keeps the peer alongside rather than directly in
	 * the mover's path. */
	private boolean hasAdjacentPriorCandidateVelocityPeer(final int x, final int y,
			final int vx, final int vy, final int playerNum) {
		for (int i = 0; i < game.subgamestate; i++) {
			final Player p = game.players[i];
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			final int dx = pp[0] - x, dy = pp[1] - y;
			if (Math.max(Math.abs(dx), Math.abs(dy)) != 1)
				continue;
			final int[] pv = p.getVelocity();
			if (pv[0] == vx && pv[1] == vy
					&& Math.abs((long) dx * vx + (long) dy * vy) <= 1L)
				return true;
		}
		return false;
	}

	/** Round 106: recover a one-turn acceleration only in a bounded forward
	 * pack when the same eight-round scorer world proves strict mover and
	 * aggregate-field gains. Round 117 admits an exact-six-ahead high-energy
	 * formation only with an adjacent prior candidate-velocity peer. Round 124
	 * additionally admits a positive L1/L2 candidate only for the first two
	 * movers inside TTF 45; the partial-round counterexamples remain excluded.
	 * Round 175 admits a bounded moderate-gain six-ahead move only when it
	 * crosses into the high-speed band. (Round 177's mildly uncertain five-ahead
	 * winner needed a positive uncertainty, which nothing has written since round
	 * 229; its arm and its faithful vector proof were removed on 2026-09-26.) */
	private Direction guardedFieldPaceOverride(final int[] pos, final int[] vel,
			final int playerNum, final Direction chosen, final double[] trapByDir,
			final int[] turnsByDir) {
		final int chosenT = turnsByDir[chosen.ordinal()];
		if (chosenT == Integer.MAX_VALUE || chosenT < AI1_FINISH_HOMOGENEOUS_TTF + 2
				|| chosenT > AI1_FIELD_ACCEL_MAX_TTF || !kindHomogeneousRoster(playerNum))
			return chosen;
		int liveRivals = 0, rivalsAhead = 0;
		long aheadProgress = 0L;
		final boolean stagedLaunch = useTrackDistanceForStagedLaunch(vel[0], vel[1],
				game.startZoneA.contains(pos[0], pos[1]));
		final int moverProgress = reach.distAt(pos[0], pos[1]);
		for (final Player rival : game.players) {
			if (rival.getNumber() == playerNum || rival.isFinished())
				continue;
			liveRivals++;
			final int[] rivalPos = rival.getPosition();
			final int rivalProgress = reach.distAt(rivalPos[0], rivalPos[1]);
			final boolean ahead = stagedLaunch
					? isStrictlyAheadByTrackDistance(moverProgress, rivalProgress)
					: ((long) rivalPos[0] - pos[0]) * vel[0]
							+ ((long) rivalPos[1] - pos[1]) * vel[1] > 0L;
			if (ahead) {
				rivalsAhead++;
				if (moverProgress != Integer.MAX_VALUE && rivalProgress != Integer.MAX_VALUE)
					aheadProgress += (long) moverProgress - rivalProgress;
			}
		}
		// Round 129 promotion: Rounds 115, 117 and 124 cleared the
		// frontier census; every car uses the certified pace arms.
		final boolean sixAheadFrontier = rivalsAhead == AI1_FIELD_ACCEL_MAX_AHEAD + 1;
		final boolean sixAheadHighSpeedModerateFrontier = sixAheadFrontier;
		final boolean earlyRoundTrapFrontier = game.subgamestate <= 1
				&& chosenT <= AI1_FIELD_ACCEL_FRONTIER_LOW_GAIN_MAX_TTF
				&& rivalsAhead <= AI1_FIELD_ACCEL_MAX_AHEAD;
		if (liveRivals < AI1_PRIVATE_FIELD_MIN_RIVALS
				|| rivalsAhead < AI1_FIELD_ACCEL_MIN_AHEAD
				|| rivalsAhead > AI1_FIELD_ACCEL_MAX_AHEAD && !sixAheadFrontier
				|| aheadProgress <= 0L)
			return chosen;

		final int chosenVx = vel[0] + chosen.dx, chosenVy = vel[1] + chosen.dy;
		final int chosenX = pos[0] + chosenVx, chosenY = pos[1] + chosenVy;
		final int chosenSpeed2 = speedSquared(chosenVx, chosenVy);
		final int fieldProofRounds = sixAheadFrontier
				? AI1_FIELD_ACCEL_SIX_AHEAD_ROUNDS : AI1_STAGED_HORIZON;
		int chosenFinal = Integer.MIN_VALUE;
		long chosenField = Long.MAX_VALUE;
		Direction best = null;
		int bestFinal = Integer.MAX_VALUE;
		long bestField = Long.MAX_VALUE;
		for (final Direction d : DIRECTIONS) {
			final int turns = turnsByDir[d.ordinal()];
			final double candidateTrap = trapByDir[d.ordinal()];
			final boolean frontierTrapCandidate = earlyRoundTrapFrontier
					&& candidateTrap > 0.0 && candidateTrap <= AI1_TRAP_L2;
			if (d == chosen || d == Direction.NONE || turns == Integer.MAX_VALUE
					|| turns + 1 != chosenT
					|| candidateTrap != 0.0 && !frontierTrapCandidate)
				continue;
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			final int speed2 = speedSquared(nvx, nvy);
			final int speed2Gain = speed2 - chosenSpeed2;
			final boolean frontierModerateGain = chosen != Direction.NONE
					&& chosenSpeed2 < AI1_DJS_SPD2
					&& chosenT <= AI1_FIELD_ACCEL_FRONTIER_LOW_GAIN_MAX_TTF
					&& speed2Gain >= AI1_FIELD_ACCEL_FRONTIER_MIN_SPEED2_GAIN;
			final boolean sixAheadHighSpeedModerateGain = sixAheadHighSpeedModerateFrontier
					&& chosen != Direction.NONE
					&& chosenSpeed2 < AI1_FIELD_ACCEL_SIX_AHEAD_MODERATE_MIN_SPEED2
					&& speed2 >= AI1_FIELD_ACCEL_SIX_AHEAD_MODERATE_MIN_SPEED2
					&& speed2Gain >= AI1_FIELD_ACCEL_FRONTIER_MIN_SPEED2_GAIN
					&& speed2Gain < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN;
			if (speed2Gain < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN
					&& !frontierModerateGain && !sixAheadHighSpeedModerateGain)
				continue;
			// Six-ahead moderate acceleration is limited to Round 175's bounded
			// transition into the high-speed band; the broad class stays excluded.
			if (sixAheadFrontier && speed2Gain < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN
					&& !sixAheadHighSpeedModerateGain)
				continue;
			if (turns <= AI1_FINISH_EXTENDED_TTF && speed2 < AI1_DJS_SPD2)
				continue;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
			if (sixAheadFrontier && !sixAheadHighSpeedModerateGain
					&& !hasAdjacentPriorCandidateVelocityPeer(
					nx, ny, nvx, nvy, playerNum))
				continue;
			final int candidateInf = Math.max(Math.abs(nvx), Math.abs(nvy));
			final int candidateSpan = candidateInf * (candidateInf + 1) / 2;
			final int candidateRing = reach.minRingWidthAhead(nx, ny, candidateSpan);
			if (candidateRing < AI1_FUNNEL_WIDTH) {
				final int chosenInf = Math.max(Math.abs(chosenVx), Math.abs(chosenVy));
				final int chosenSpan = chosenInf * (chosenInf + 1) / 2;
				if (rivalsAhead < AI1_FIELD_ACCEL_MAX_AHEAD
						|| aheadProgress < (long) chosenSpan + candidateSpan)
					continue;
			}
			if (sealable(nx, ny, nvx, nvy, playerNum))
				continue;
			if (chosenFinal == Integer.MIN_VALUE) {
				chosenFinal = scorerFieldOutcome(chosenX, chosenY, chosenVx, chosenVy, playerNum,
						fieldProofRounds, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);
				chosenField = rolloutFieldCost[0];
				// Round 291 (round 289): the field's cost is no veto (the racecraft rule).
				if (chosenFinal < 0)
					return chosen;
			}
			final int candidateFinal = scorerFieldOutcome(nx, ny, nvx, nvy, playerNum,
					fieldProofRounds, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);
			final long candidateField = rolloutFieldCost[0];
			// Round 279: the field's cost is no veto (the racecraft rule).
			if (candidateFinal < 0 || candidateFinal >= chosenFinal)
				continue;
			if (best == null || candidateFinal < bestFinal
					|| candidateFinal == bestFinal && candidateField < bestField) {
				best = d;
				bestFinal = candidateFinal;
				bestField = candidateField;
			}
		}
		if (best != null && AI_DEBUG_DJS)
			System.err.println("AIDBG FIELD-ACCEL p=" + playerNum + " pos=(" + pos[0]
					+ "," + pos[1] + ") " + chosen + " -> " + best + " ttf " + chosenT
					+ " -> " + turnsByDir[best.ordinal()] + " ahead=" + rivalsAhead
					+ " progress=" + aheadProgress + " self " + chosenFinal + " -> "
					+ bestFinal + " field " + chosenField + " -> " + bestField);
		return best != null ? best : chosen;
	}

	private Direction privatePaceOverride(final int[] pos, final int[] vel, final int playerNum,
			final Direction chosen, final double[] scoreByDir, final double[] trapByDir,
			final int[] turnsByDir) {
		final int chosenT = turnsByDir[chosen.ordinal()];
		if (chosenT == Integer.MAX_VALUE)
			return chosen;
		final double chosenRest = scoreByDir[chosen.ordinal()] - trapByDir[chosen.ordinal()];
		RaceAiPrivateLane.ProofSession privateProof = null;
		RaceAiPrivateLane.ProofSession slackProof = null;
		// Promotion semantics (round 83 mirror, round 223): "self-play" means
		// every rival runs the mover's policy -- since the 2026-09-04 promotion
		// that is every AI kind, so only a human breaks it.
		final int slackChosenVx = vel[0] + chosen.dx;
		final int slackChosenVy = vel[1] + chosen.dy;
		final int slackChosenSpeed2 = speedSquared(slackChosenVx, slackChosenVy);
		final int slackCurrentSpeed2 = speedSquared(vel[0], vel[1]);
		final boolean slackFrontier = chosenT >= AI1_PRIVATE_FRONTIER_MIN_TTF
				&& chosenT <= AI1_PRIVATE_FRONTIER_MAX_TTF
				&& chosen != Direction.NONE
				&& kindHomogeneousRoster(playerNum);
		final boolean homogeneousFrontier = kindHomogeneousField(playerNum);
		Direction best = null;
		Direction slackBest = null;
		int bestT = chosenT;
		int slackChosenFinal = Integer.MIN_VALUE;
		long slackChosenField = Long.MAX_VALUE;
		int slackBestFinal = Integer.MAX_VALUE;
		long slackBestField = Long.MAX_VALUE;
		double slackBestScore = Double.MAX_VALUE;
		double slackBestRestDelta = Double.MAX_VALUE;
		double bestTrap = Double.MAX_VALUE;
		double bestScore = Double.MAX_VALUE;
		for (final Direction d : DIRECTIONS) {
			final int turns = turnsByDir[d.ordinal()];
			if (turns >= chosenT || turns > bestT)
				continue;
			final double trap = trapByDir[d.ordinal()];
			// Spread-only lanes already have their own certified override. This
			// stronger proof targets the residual trap pool; skipping pure lateral
			// ties also bounds scorer-rollout exposure on open tracks.
			if (trap == 0.0)
				continue;
			final double rest = scoreByDir[d.ordinal()] - trap;
			if (rest > chosenRest + 1e-9) {
				final double restDelta = rest - chosenRest;
				// Frontier experiment: a tiny non-trap score concession may recover
				// exactly one map turn only for a kind-homogeneous starting roster. Keep this
				// candidate separate so it cannot displace an existing private-lane
				// winner. Keep the eight-round field proof in its established
				// non-overlapping medium-range phase; both moves must be non-coasting,
				// and the low-energy candidate must preserve current energy while
				// improving on and remaining aligned with the chosen acceleration. It
				// must otherwise be exact-L2 with zero uncertainty and unsealable,
				// exact-private with two exits, and strictly better for the mover while
				// non-worsening for the field in the longer eight-round scorer world.
				if (slackFrontier && restDelta <= AI1_PRIVATE_FRONTIER_REST_SLACK + 1e-9
						&& turns + 1 == chosenT && d != Direction.NONE
						&& chosen.dx * d.dx + chosen.dy * d.dy > 0
						&& trap == AI1_TRAP_L2) {
					final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
					final int nx = pos[0] + nvx, ny = pos[1] + nvy;
					final int speed2 = speedSquared(nvx, nvy);
					if (speed2 < AI1_DJS_SPD2 && speed2 >= slackCurrentSpeed2
							&& speed2 > slackChosenSpeed2
							&& !sealable(nx, ny, nvx, nvy, playerNum)) {
						if (slackProof == null)
							slackProof = privateLane.begin(playerNum,
									AI1_PRIVATE_EXACT_HORIZON + 1, AI1_PRIVATE_EXACT_NODES);
						if (slackProof.certifiesExact(nx, ny, nvx, nvy, turns,
								AI1_PRIVATE_EXACT_HORIZON, AI1_PRIVATE_EXACT_ESCAPES)) {
							if (slackChosenFinal == Integer.MIN_VALUE) {
								slackChosenFinal = scorerFieldOutcome(pos[0] + slackChosenVx,
										pos[1] + slackChosenVy, slackChosenVx, slackChosenVy, playerNum,
										AI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS,
										rolloutFieldCost);
								slackChosenField = rolloutFieldCost[0];
							}
							if (slackChosenFinal >= 0
									&& slackChosenFinal != Integer.MAX_VALUE) {
								final int candidateFinal = scorerFieldOutcome(nx, ny, nvx, nvy,
										playerNum, AI1_STAGED_HORIZON,
										AI1_DEEP_CERT_RIVALS, rolloutFieldCost);
								final long candidateField = rolloutFieldCost[0];
								final double score = scoreByDir[d.ordinal()];
								if (candidateFinal >= 0 && candidateFinal != Integer.MAX_VALUE
										&& candidateFinal < slackChosenFinal
										&& (slackBest == null || candidateFinal < slackBestFinal
												|| candidateFinal == slackBestFinal
														&& (candidateField < slackBestField
																|| candidateField == slackBestField
																		&& score < slackBestScore))) {
									slackBest = d;
									slackBestFinal = candidateFinal;
									slackBestField = candidateField;
									slackBestScore = score;
									slackBestRestDelta = restDelta;
								}
							}
						}
					}
				}
				continue;
			}
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
			if (sealable(nx, ny, nvx, nvy, playerNum))
				continue;
			if (privateProof == null)
				privateProof = privateLane.begin(playerNum, AI1_PRIVATE_EXACT_HORIZON + 1,
						AI1_PRIVATE_EXACT_NODES);
			boolean certified = privateProof.certifiesApproximate(nx, ny, nvx, nvy, turns,
					AI1_PRIVATE_BASE_HORIZON, AI1_PRIVATE_BASE_ESCAPES);
			if (!certified) {
				// The narrower two-exit proof is safe only when every live rival uses
				// the same frontier policy. In mixed fields, one car's acceleration
				// can perturb a frozen-policy rival and create a delayed crash for a
				// third car, so fast moves retain the broader three-exit certificate.
				final int requiredEscapes = speedSquared(nvx, nvy) < AI1_DJS_SPD2
						|| homogeneousFrontier
						? AI1_PRIVATE_EXACT_ESCAPES : AI1_PRIVATE_BASE_ESCAPES;
				certified = privateProof.certifiesExact(nx, ny, nvx, nvy, turns,
						AI1_PRIVATE_EXACT_HORIZON, requiredEscapes);
			}
			if (!certified)
				continue;
			final double score = scoreByDir[d.ordinal()];
			if (turns < bestT || turns == bestT && (trap < bestTrap
					|| trap == bestTrap && score < bestScore)) {
				best = d;
				bestT = turns;
				bestTrap = trap;
				bestScore = score;
			}
		}
		if (best == null) {
			if (slackBest != null && AI_DEBUG_DJS)
				System.err.println("AIDBG PRIVATE-SLACK p=" + playerNum + " pos=(" + pos[0]
						+ "," + pos[1] + ") " + chosen + " -> " + slackBest + " ttf "
						+ chosenT + " -> " + turnsByDir[slackBest.ordinal()] + " self "
						+ slackChosenFinal + " -> " + slackBestFinal + " field "
						+ slackChosenField + " -> " + slackBestField + " trap "
						+ AI1_TRAP_L2 + " restDelta " + slackBestRestDelta);
			return slackBest != null ? slackBest : chosen;
		}
		final int bestVx = vel[0] + best.dx, bestVy = vel[1] + best.dy;
		final int bestX = pos[0] + bestVx, bestY = pos[1] + bestVy;
		// Cross-model check once, after the adversarial certificate has ranked all
		// candidates. Calling the full scorer rollout per candidate made open
		// circuits needlessly expensive without strengthening proof.
		final boolean compareField = privateFieldComparisonRequired(bestX, bestY, bestVx, bestVy,
				playerNum);
		final int scorerCap = compareField ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS;
		final int bestFinal = scorerFieldOutcome(bestX, bestY, bestVx, bestVy, playerNum,
				AI1_DJS_SLOW_ROUNDS, scorerCap, null);
		if (bestFinal < 0)
			return chosen;
		if (compareField) {
			final int chosenVx = vel[0] + chosen.dx, chosenVy = vel[1] + chosen.dy;
			final int chosenX = pos[0] + chosenVx, chosenY = pos[1] + chosenVy;
			final int chosenFinal = scorerFieldOutcome(chosenX, chosenY, chosenVx, chosenVy,
					playerNum, AI1_DJS_SLOW_ROUNDS, AI1_DEEP_CERT_RIVALS, null);
			// In a compressed fast pack, take the private lane only when the same
			// scorer-rival world proves strict self progress. Round 279: the field's
			// cost is no veto (the racecraft rule), so it is not priced.
			if (chosenFinal < 0 || bestFinal >= chosenFinal) {
				if (AI_DEBUG_DJS)
					System.err.println("AIDBG PRIVATE-FIELD p=" + playerNum + " pos=(" + pos[0]
							+ "," + pos[1] + ") keep " + chosen + " over " + best + " self "
							+ chosenFinal + " -> " + bestFinal);
				return chosen;
			}
		}
		if (AI_DEBUG_DJS)
			System.err.println("AIDBG PRIVATE p=" + playerNum + " pos=(" + pos[0] + "," + pos[1]
					+ ") " + chosen + " -> " + best + " ttf " + chosenT + " -> " + bestT);
		return best;
	}


	/**
	 * Round 82 frontier experiment: recover a one-turn map gain in the slow
	 * class when the candidate is almost tied on every non-trap/non-uncertainty
	 * score term. The broad class still requires four rivals ahead. Exactly
	 * three may qualify only at slow-pack speed with a finite incumbent field
	 * rollout. An eight-round six-rival scorer rollout must prove strict self
	 * progress without increasing aggregate rival cost. High-speed candidates,
	 * deaths, field regressions, ties, and model ambiguity fail closed. The seal
	 * guard and the danger guards that ran afterwards went in rounds 234 and 310;
	 * the round-232 kinematic confirm still does.
	 */
	private Direction stagedPaceOverride(final int[] pos, final int[] vel, final int playerNum,
			final Direction chosen, final double[] scoreByDir, final double[] trapByDir,
			final int[] turnsByDir) {
		final int chosenT = turnsByDir[chosen.ordinal()];
		if (chosenT == Integer.MAX_VALUE || chosenT < AI1_STAGED_MIN_TURNS)
			return chosen;
		// Round 79's convoy counterexample established that a mover-safe pace
		// change can destabilise a different policy hundreds of moves later.
		// This new long-horizon certificate is therefore self-play-only until a
		// mixed-policy externality proof exists.
		int rivalsAhead = 0;
		final boolean stagedLaunch = useTrackDistanceForStagedLaunch(vel[0], vel[1],
				game.startZoneA.contains(pos[0], pos[1]));
		final int moverProgress = reach.distAt(pos[0], pos[1]);
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			if (!p.isAi())
				return chosen;
			final int[] rivalPos = p.getPosition();
			// Round 91: a stationary starting-grid car has no velocity
			// half-plane, so use the track-distance heuristic for that launch
			// only. Moving cars retain the promoted geometric rule. Equal or
			// unavailable map distances fail closed.
			final boolean ahead = stagedLaunch
					? isStrictlyAheadByTrackDistance(moverProgress,
							reach.distAt(rivalPos[0], rivalPos[1]))
					: ((long) rivalPos[0] - pos[0]) * vel[0]
							+ ((long) rivalPos[1] - pos[1]) * vel[1] > 0L;
			if (ahead)
				rivalsAhead++;
		}
		// Round 82 opens the adjacent three-ahead class, but only after the
		// incumbent reaches the established slow-pack speed floor and its own
		// scorer-world field outcome is finite. The four-ahead class is unchanged.
		if (rivalsAhead < 3)
			return chosen;
		final double chosenRest = scoreByDir[chosen.ordinal()] - trapByDir[chosen.ordinal()];
		final int chosenVx = vel[0] + chosen.dx, chosenVy = vel[1] + chosen.dy;
		final int chosenSpeed2 = speedSquared(chosenVx, chosenVy);
		if (rivalsAhead == 3 && chosenSpeed2 < AI1_SLOW_PACK_SPD2)
			return chosen;
		final int chosenX = pos[0] + chosenVx, chosenY = pos[1] + chosenVy;
		int chosenFinal = Integer.MIN_VALUE;
		long chosenField = Long.MAX_VALUE;
		Direction best = null;
		double bestRestDelta = Double.MAX_VALUE;
		for (final Direction d : DIRECTIONS) {
			final int turns = turnsByDir[d.ordinal()];
			if (turns == Integer.MAX_VALUE || chosenT - turns != 1
					|| scoreByDir[d.ordinal()] == Double.MAX_VALUE)
				continue;
			final double trap = trapByDir[d.ordinal()];
			if (trap > 0.0)
				continue;
			final double rest = scoreByDir[d.ordinal()] - trap;
			final double restDelta = rest - chosenRest;
			if (restDelta > AI1_STAGED_REST_SLACK)
				continue;
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			final int speed2 = speedSquared(nvx, nvy);
			if (speed2 >= AI1_DJS_SPD2)
				continue;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
			// A high-energy candidate needed a positive uncertainty to pass, and
			// nothing has written one since round 229: it used to run the exact
			// private-lane proof and two eight-round rollouts first (2026-09-26).
			if (speed2 - chosenSpeed2 > AI1_STAGED_MAX_SPEED2_GAIN)
				continue;
			if (sealable(nx, ny, nvx, nvy, playerNum))
				continue;
			if (chosenFinal == Integer.MIN_VALUE) {
				chosenFinal = scorerFieldOutcome(chosenX, chosenY, chosenVx, chosenVy, playerNum,
						AI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);
				chosenField = rolloutFieldCost[0];
			}
			if (chosenFinal < 0)
				return chosen;
			// Round 279: the field's cost is no veto (the racecraft rule).
			final int candidateFinal = scorerFieldOutcome(nx, ny, nvx, nvy, playerNum,
					AI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, null);
			if (candidateFinal < 0 || candidateFinal >= chosenFinal)
				continue;
			if (best == null || restDelta < bestRestDelta) {
				best = d;
				bestRestDelta = restDelta;
			}
		}
		if (best != null && AI_DEBUG_DJS)
			System.err.println("AIDBG STAGED p=" + playerNum + " pos=(" + pos[0] + ","
					+ pos[1] + ") " + chosen + " -> " + best + " ttf " + chosenT
					+ " -> " + turnsByDir[best.ordinal()] + " trap="
					+ trapByDir[best.ordinal()]);
		return best != null ? best : chosen;
	}

	private boolean privateFieldComparisonRequired(final int x, final int y, final int vx,
			final int vy, final int playerNum) {
		final int speed2 = speedSquared(vx, vy);
		if (speed2 < AI1_DJS_SPD2)
			return false;
		int rivals = 0, rivalsAhead = 0;
		boolean compactPack = true, alignedConvoy = true;
		final int convoyRadius = Math.max(AI1_DEEP_PACK_R,
				AI1_PRIVATE_CONVOY_RADIUS_V * Math.max(Math.abs(vx), Math.abs(vy)));
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			rivals++;
			final int[] position = p.getPosition();
			final long dx = (long) position[0] - x, dy = (long) position[1] - y;
			if (Math.abs(dx) > AI1_DEEP_PACK_R || Math.abs(dy) > AI1_DEEP_PACK_R)
				compactPack = false;
			final long cross = dx * vy - dy * vx;
			final long corridorLimit = (long) AI1_PRIVATE_CONVOY_HALF_WIDTH
					* AI1_PRIVATE_CONVOY_HALF_WIDTH * speed2;
			if (Math.max(Math.abs(dx), Math.abs(dy)) > convoyRadius
					|| squareExceeds(cross, corridorLimit))
				alignedConvoy = false;
			if (dx * vx + dy * vy > 0L)
				rivalsAhead++;
			if (!compactPack && !alignedConvoy)
				return false;
		}
		return rivals >= AI1_PRIVATE_FIELD_MIN_RIVALS
				&& (compactPack || alignedConvoy
						&& rivalsAhead <= AI1_PRIVATE_CONVOY_MAX_AHEAD);
	}

	/** Queue-compression support: count live STALLED rivals within squared
	 *  distance 36 of the candidate landing that are at-or-ahead in track
	 *  progress. Ahead-ness keeps the same-progress +3 slack and the 15-cell
	 *  wall exclusion used by the original Zandvoort forensic. */
	private int countStalledRivalsAhead(final int x, final int y, final int playerNum) {
		final int myDist = reach.distAt(x, y);
		if (myDist == Integer.MAX_VALUE)
			return 0;
		int count = 0;
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			final int dx = x - pp[0];
			final int dy = y - pp[1];
			if (distanceSquared(dx, dy) > 36L)
				continue;
			final int oDist = reach.distAt(pp[0], pp[1]);
			if (oDist == Integer.MAX_VALUE || Math.abs(oDist - myDist) > 15 || oDist > myDist + 3)
				continue; // behind me, or across a wall: no compression
			final int[] pv = p.getVelocity();
			// v2: only genuinely STALLED rivals count as a boxing queue (the
			// zandvoort doom queue crawled at |v| 1-2). A merely-slower but
			// FLOWING train clears the corridor before I arrive -- braking for
			// it is pure place-ceding in mixed fields (h2h: zandvoort 4.75,
			// interlagos 4.62 under the old relative test). With the outer
			// speed > 4 gate, <= 2.5 also implies the old mySpeed-1 margin.
			if (speedSquared(pv[0], pv[1]) <= STALLED_RIVAL_SPEED2)
				count++;
		}
		return count;
	}

	/** Shared champion frontier (queueBox v3 long-range trigger): count STALLED
	 *  rivals (|v| <= 2.5, the {@link #countStalledRivalsAhead} threshold)
	 *  at-or-ahead of (x,y) in track progress within {@code reachCells}
	 *  euclidean cells -- my stopping distance, so unlike the near trigger
	 *  this must see the queue BEFORE the local successor count collapses.
	 *  Ahead-ness keeps the +3 same-progress slack; the wall exclusion
	 *  scales with reach (a rival physically near but further along the
	 *  corridor than I can even travel while stopping is across a wall). */
	private int countStalledRivalsWithin(final int x, final int y, final double reachCells, final int playerNum) {
		final int myDist = reach.distAt(x, y);
		if (myDist == Integer.MAX_VALUE)
			return 0;
		final double reachSq = reachCells * reachCells;
		int count = 0;
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			final int dx = x - pp[0];
			final int dy = y - pp[1];
			if (distanceSquared(dx, dy) > reachSq)
				continue;
			final int oDist = reach.distAt(pp[0], pp[1]);
			if (oDist == Integer.MAX_VALUE || myDist - oDist > reachCells + 3 || oDist > myDist + 3)
				continue; // behind me, or across a wall: no compression
			final int[] pv = p.getVelocity();
			if (speedSquared(pv[0], pv[1]) <= STALLED_RIVAL_SPEED2)
				count++;
		}
		return count;
	}

	/** {@link #pureMinTurnsMove} against an exact counted simulated occupancy
	 *  instead of the live player positions; used by
	 *  {@link #simulateRoundPass}. */
	private Direction pureMinTurnsMoveSim(final int idx, final int[] pos, final int[] vel,
			final CellOccupancy occupied) {
		Direction best = null;
		int bestTurns = Integer.MAX_VALUE;
		int fallbackLegalMask = 0;
		final int sm = succMask(pos[0], pos[1], vel[0], vel[1]);
		for (final Direction d : DIRECTIONS) {
			final int bit = 1 << d.ordinal();
			final int newVx = vel[0] + d.dx;
			final int newVy = vel[1] + d.dy;
			if ((sm & bit << 16) == 0)
				continue;
			final int newX = pos[0] + newVx;
			final int newY = pos[1] + newVy;
			if (finishesFor(idx, pos[0], pos[1], newX, newY))
				return d; // round 296: CP2 on the way included
			// perf_aisearch (exact): the precedence below needs !frameLapAware[idx] or
			// frameGate[idx] == 0, so only that frame asks for the crossing.
			if ((!frameLapAware[idx] || frameGate[idx] == 0)
					&& game.crossesFinishLegally(pos[0], pos[1], newX, newY)) {
				// Round 224: the twin's precedence, in this car's own frame. A
				// crossing ends the race only on the final lap with nothing owed;
				// a lap-scoring one must be survivable (legal edge, no simulated
				// body, a shedable landing that can still reach CP1). Anything
				// else is an ordinary move and falls through to the pace compare.
				if (!frameLapAware[idx]
					|| frameGate[idx] == 0 && (sm & bit) != 0
						&& !occupied.contains(newX, newY)
						&& reach.shedableLanding(newX, newY, newVx, newVy)
						&& reach.turnsToGate(1, newX, newY, newVx, newVy) != Integer.MAX_VALUE)
					return d;
			}
			// Round 224: the twin's checkpoint precedence -- a touch with a
			// continuing landing is progress the gate map cannot price.
			if (frameLapAware[idx] && frameGate[idx] != 0 && (sm & bit) != 0
				&& game.touchesGate(frameGate[idx], pos[0], pos[1], newX, newY)
				&& !occupied.contains(newX, newY)
				&& reach.isAlive(newX, newY, newVx, newVy)
				&& reach.turnsToGate(frameGate[idx] == 1 ? 2 : 0, newX, newY, newVx, newVy)
					!= Integer.MAX_VALUE)
				return d;
			if ((sm & bit) == 0)
				continue;
			if (occupied.contains(newX, newY))
				continue;
			fallbackLegalMask |= bit;
			final int turns = ttfForAfter(idx, pos[0], pos[1], newX, newY, newVx, newVy); // round 296
			if (turns < bestTurns) {
				bestTurns = turns;
				best = d;
			}
		}
		if (best != null)
			return best;
		return scoreMinTurnsFallback(pos[0], pos[1], vel[0], vel[1],
				fallbackLegalMask, 0, null);
	}

	/** perf_aisearch: simMove's code when pureMinTurnsMoveSim finds no move. */
	private static final int SIM_MOVE_NONE = 9;
	/** perf_aisearch: simMove's flag for a move whose succMask bit is set. */
	private static final int SIM_MOVE_LEGAL = 16;
	/** perf_aisearch: log2 of the simMove table's slots. */
	private static final int SIM_MOVE_BITS = 16;
	/** perf_aisearch: the simMove table (direct-mapped, entry = key << 5 | code) and
	 *  what it was filled against beyond its keys. */
	private long[] simMoveTab;
	private int[] simMoveTurns;
	private BitSet simMoveAlive;
	private int[][] simMoveGates;
	private byte[] simMoveShed;
	private int[][] simMoveDist;
	private OptimalPotential simMovePot;
	private int simMoveAliveW = -1, simMoveAliveH = -1, simMoveVmax = -1;
	private java.awt.geom.Line2D[] simMoveLapGates;
	private java.awt.geom.Line2D simMoveFinish, simMoveGate0, simMoveGate1, simMoveGate2;

	/** perf_aisearch: pureMinTurnsMoveSim's move for simulated car {@code idx} as a
	 *  code -- the direction's ordinal, SIM_MOVE_NONE when there is none -- plus
	 *  SIM_MOVE_LEGAL when that move's succMask bit is set, memoised. The scan reads
	 *  the state; the car's lap frame (next gate, events owed, lap-awareness);
	 *  {@code occupied} at its in-range landing cells and nowhere else; the AI's
	 *  grid world; the reachability maps, the distance map, the exact potential,
	 *  the lap gates and the finish line, whose identities (and the map dimensions)
	 *  simMoveTable checks; and the borders, fixed for the game as succMask and the
	 *  edge caches already take them. The key packs every varying input and an
	 *  entry keeps its whole key, so a hit returns what the scan computes. */
	private int simMove(final int idx, final int[] pos, final int[] vel, final CellOccupancy occupied) {
		final int x = pos[0], y = pos[1], vx = vel[0], vy = vel[1];
		final int gate = frameGate[idx], remaining = frameRemaining[idx];
		final int max = RaceGame.AI_MAX_SPEED;
		if (x < 0 || y < 0 || x > 511 || y > 511 || vx < -max || vx > max || vy < -max || vy > max
				|| gate < 0 || gate > 2 || remaining < 0 || remaining > 255
				|| game.lapGates != null && game.lapGates.length != 3)
			return simMoveCompute(idx, pos, vel, occupied);
		int landings = 0;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (!RaceGame.aiVelocityOutOfRange(nvx, nvy) && occupied.contains(x + nvx, y + nvy))
				landings |= 1 << d.ordinal();
		}
		long key = x;
		key = key << 9 | y;
		key = key << 5 | (vx + max);
		key = key << 5 | (vy + max);
		key = key << 2 | gate;
		key = key << 8 | remaining;
		key = key << 1 | (frameLapAware[idx] ? 1 : 0);
		key = key << 9 | landings;
		key = key << 1 | (game.aiGridLegal ? 1 : 0);
		final long[] table = simMoveTable();
		final int slot = (int) (key * 0x9E3779B97F4A7C15L >>> 64 - SIM_MOVE_BITS);
		final long entry = table[slot];
		if (entry >>> 5 == key)
			return (int) entry & 0x1F;
		final int code = simMoveCompute(idx, pos, vel, occupied);
		table[slot] = key << 5 | code;
		return code;
	}

	/** perf_aisearch: simMove computed -- the scan's move and its succMask bit. */
	private int simMoveCompute(final int idx, final int[] pos, final int[] vel,
			final CellOccupancy occupied) {
		final Direction direction = pureMinTurnsMoveSim(idx, pos, vel, occupied);
		if (direction == null)
			return SIM_MOVE_NONE;
		return (succMask(pos[0], pos[1], vel[0], vel[1]) & 1 << direction.ordinal()) != 0
				? direction.ordinal() | SIM_MOVE_LEGAL : direction.ordinal();
	}

	/** perf_aisearch: the simMove table, emptied whenever a map, the potential, a map
	 *  dimension, the lap gates or the finish line it was filled against is replaced
	 *  (hand-built test games reassign gates and lines; a race never does). */
	private long[] simMoveTable() {
		final Reachability r = reach;
		final java.awt.geom.Line2D[] gates = game.lapGates;
		if (simMoveTab == null || simMoveTurns != r.turnsArr || simMoveAlive != r.aliveStates
				|| simMoveGates != r.gateTurns || simMoveShed != r.minShed2
				|| simMoveDist != r.distToFinish || simMovePot != exactPot
				|| simMoveAliveW != r.aliveW || simMoveAliveH != r.aliveH || simMoveVmax != r.aliveVMAX
				|| simMoveLapGates != gates || simMoveFinish != game.finishLine
				|| gates != null && (simMoveGate0 != gates[0] || simMoveGate1 != gates[1]
						|| simMoveGate2 != gates[2])) {
			if (simMoveTab == null)
				simMoveTab = new long[1 << SIM_MOVE_BITS];
			java.util.Arrays.fill(simMoveTab, -1L);
			simMoveTurns = r.turnsArr;
			simMoveAlive = r.aliveStates;
			simMoveGates = r.gateTurns;
			simMoveShed = r.minShed2;
			simMoveDist = r.distToFinish;
			simMovePot = exactPot;
			simMoveAliveW = r.aliveW;
			simMoveAliveH = r.aliveH;
			simMoveVmax = r.aliveVMAX;
			simMoveLapGates = gates;
			simMoveFinish = game.finishLine;
			simMoveGate0 = gates == null ? null : gates[0];
			simMoveGate1 = gates == null ? null : gates[1];
			simMoveGate2 = gates == null ? null : gates[2];
		}
		return simMoveTab;
	}

	/** Reusable two-round opponent projection. The reference arrays and every
	 *  generated coordinate/velocity pair are retained across candidate moves;
	 *  each pass only rewrites primitive values and swaps row references. */
	private TwoRoundWorkspace twoRoundWorkspace() {
		final int players = game.players.length;
		if (twoRoundWorkspace == null || twoRoundWorkspace.current.length != players)
			twoRoundWorkspace = new TwoRoundWorkspace(players,
					game.gameCols + 1, game.gameRows + 1);
		return twoRoundWorkspace;
	}

	private TwoRoundWorkspace nestedScorerTwoRoundReferenceWorkspace() {
		final int players = game.players.length;
		if (nestedScorerTwoRoundReferenceWorkspace == null
				|| nestedScorerTwoRoundReferenceWorkspace.current.length != players)
			nestedScorerTwoRoundReferenceWorkspace = new TwoRoundWorkspace(players,
					game.gameCols + 1, game.gameRows + 1);
		return nestedScorerTwoRoundReferenceWorkspace;
	}

	/** Build the no-mover reference used only inside a nested scorer. */
	private TwoRoundWorkspace prepareTwoRoundReference(final int playerNum) {
		return simulateTwoRounds(nestedScorerTwoRoundReferenceWorkspace(), playerNum,
				0, 0, false);
	}

	/** Reuse is exact unless the candidate blocks a landing selected in the
	 *  no-mover first round. A hit takes the unchanged conditioned path. */
	private TwoRoundWorkspace simulateTwoRounds(final int playerNum, final int candX,
			final int candY, final TwoRoundWorkspace reference) {
		if (reference != null && !reference.world1Occupancy.contains(candX, candY))
			return reference;
		return simulateTwoRounds(playerNum, candX, candY);
	}

	/** Simulate the next complete opponent round in actual turn order,
	 *  conditioned on my candidate landing: {@code world1} contains the cells
	 *  for my next move. (A second round, the cells for the move after that,
	 *  fed only the ply-2 price and was removed on 2026-09-26.) */
	private TwoRoundWorkspace simulateTwoRounds(final int playerNum, final int candX, final int candY) {
		return simulateTwoRounds(twoRoundWorkspace(), playerNum, candX, candY, true);
	}

	private TwoRoundWorkspace simulateTwoRounds(final TwoRoundWorkspace workspace,
			final int playerNum, final int candX, final int candY,
			final boolean blockCandidate) {
		final int[][] current = workspace.current;
		final int[][] simulatedVelocity = workspace.simulatedVelocity;
		java.util.Arrays.fill(current, null);
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int idx = p.getNumber() - 1;
			current[idx] = p.getPosition();
			simulatedVelocity[idx] = p.getVelocity();
		}
		workspace.blockedOccupancy.rebuild(current);
		if (blockCandidate)
			workspace.blockedOccupancy.add(candX, candY);
		simulateRoundPass(playerNum, current, simulatedVelocity,
				workspace.blockedOccupancy, workspace.round1Position, workspace.round1Velocity);
		System.arraycopy(current, 0, workspace.world1, 0, current.length);
		workspace.world1Occupancy.rebuild(workspace.world1);
		return workspace;
	}

	/** One two-pass opponent round. A mover always receives a fresh logical
	 *  position row, but that row is caller-owned and reused on the next root;
	 *  a velocity row is replaced only when the move is legal, matching the
	 *  original stay-put semantics exactly. */
	private void simulateRoundPass(final int playerNum, final int[][] occupancy,
			final int[][] simulatedVelocity, final CellOccupancy blockedOccupancy,
			final int[][] nextPosition, final int[][] nextVelocity) {
		for (int pass = 0; pass < 2; pass++) {
			for (final Player p : game.players) {
				final boolean later = p.getNumber() > playerNum;
				if (p.getNumber() == playerNum || p.isFinished() || (pass == 0 ? !later : later))
					continue;
				final int idx = p.getNumber() - 1;
				final int[] current = occupancy[idx];
				blockedOccupancy.remove(current[0], current[1]);
				final int[] velocity = simulatedVelocity[idx];
				// perf_aisearch (exact): the move and its succMask bit -- velocity in range
				// and aiMoveLegal, the very tests made here -- memoised (simMove).
				final int code = simMove(idx, current, velocity, blockedOccupancy);
				int nx = current[0];
				int ny = current[1];
				if (code != SIM_MOVE_NONE) {
					final Direction direction = DIRECTIONS[code & 0xF];
					final int nvx = velocity[0] + direction.dx;
					final int nvy = velocity[1] + direction.dy;
					if ((code & SIM_MOVE_LEGAL) != 0
							&& !blockedOccupancy.contains(current[0] + nvx, current[1] + nvy)) {
						nx = current[0] + nvx;
						ny = current[1] + nvy;
						final int[] velocityOut = nextVelocity[idx];
						velocityOut[0] = nvx;
						velocityOut[1] = nvy;
						simulatedVelocity[idx] = velocityOut;
					}
				}
				final int[] positionOut = nextPosition[idx];
				positionOut[0] = nx;
				positionOut[1] = ny;
				occupancy[idx] = positionOut;
				blockedOccupancy.add(nx, ny);
			}
		}
	}

	/** The search below the first ply: a plain min-turns search {@code levels}
	 *  moves deep over live geometry, a finish crossing ending it. Round 247 set
	 *  the lookahead at one level (AI1_DEEP_LOOKAHEAD), so it is reached with
	 *  {@code levels == 0} and reads the map. Until 2026-09-26 its first ply
	 *  priced the bodies of rivals ahead of me in a second simulated round
	 *  (AI1_PLY2_PRICE); one level never reached it, and a deeper lookahead needs
	 *  that pricing back (git history). */
	private double searchMinTurnsSoft3(final int x, final int y, final int vx, final int vy, final int levels) {
		if (levels == 0) {
			final int t = ttf(x, y, vx, vy);
			return t == Integer.MAX_VALUE ? Double.MAX_VALUE : t;
		}
		double best = Double.MAX_VALUE;
		final int sm = succMask(x, y, vx, vy);
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if ((sm & 1 << 16 + d.ordinal()) == 0)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (game.crossesFinishLegally(x, y, nx, ny) && (!lapAware || lapGate == 0 && reach.shedableLanding(nx, ny, nvx, nvy)))
				return 1;
			if ((sm & 1 << d.ordinal()) == 0)
				continue;
			final double sub = searchMinTurnsSoft3(nx, ny, nvx, nvy, levels - 1);
			if (sub == Double.MAX_VALUE)
				continue;
			if (1.0 + sub < best)
				best = 1.0 + sub;
		}
		return best;
	}

	/** The first ply of the soft-priced search, counting its plateau (both AI
	 *  bodies): a follow-up landing on a body of the simulated next round is
	 *  priced (+3.0, the conflict weight) rather than hard-skipped, and the
	 *  plateau width (how many follow-ups achieve the minimum) feeds the
	 *  robustness tie-break. Prices stay exact small constants, so the plateau
	 *  compare remains an exact {@code ==}. Geometry stays hard; a finish
	 *  crossing escapes pricing. */
	private double[] searchMinTurnsCountedSoft3(final int x, final int y, final int vx, final int vy, final int levels,
			final CellOccupancy occupancy) {
		double best = Double.MAX_VALUE;
		int countAtMin = 0;
		final int sm = succMask(x, y, vx, vy);
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if ((sm & 1 << 16 + d.ordinal()) == 0)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			// perf_aisearch (exact): the same AND, the frame and landing tests first
			// (lap-aware with a checkpoint owed no crossing counts).
			if ((!lapAware || lapGate == 0 && reach.shedableLanding(nx, ny, nvx, nvy))
					&& game.crossesFinishLegally(x, y, nx, ny))
				return new double[]{1, 9 };
			if ((sm & 1 << d.ordinal()) == 0)
				continue;
			final double price = occupancy.contains(nx, ny) ? 3.0 : 0.0;
			final double sub = searchMinTurnsSoft3(nx, ny, nvx, nvy, levels - 1);
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
	 * exactly once (see {@link #simulateRoundPass} for the move-order
	 * derivation) -- so the stale-body check ({@link #isCrashingPlayer}) and
	 * the nulled prediction check are replaced by a single test against
	 * {@code occupancy}, the simulated round-step positions of all live
	 * opponents (current cells as conservative fallback where unmoved).
	 */
	private int countFutureSafeSuccessorsTimed(final int x, final int y, final int vx, final int vy,
			final CellOccupancy occupancy) {
		int count = 0;
		final int sm = succMask(x, y, vx, vy);
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx;
			final int nvy = vy + d.dy;
			if ((sm & 1 << 16 + d.ordinal()) == 0)
				continue;
			final int nx = x + nvx;
			final int ny = y + nvy;
			// perf_aisearch (exact): the same AND, the frame and landing tests first
			// (lap-aware with a checkpoint owed no crossing counts).
			if ((!lapAware || lapGate == 0 && reach.shedableLanding(nx, ny, nvx, nvy))
					&& game.crossesFinishLegally(x, y, nx, ny))
				return 9;
			if ((sm & 1 << d.ordinal()) == 0)
				continue;
			if (occupancy.contains(nx, ny))
				continue;
			if (reach.isAlive(nx, ny, nvx, nvy))
				count++;
		}
		return count;
	}

	/** perf_lean (exact) switches: -Dai.perf.noLean=true keeps the eager suppressed decision
	 *  everywhere (a same-jar CPU control); -Dai.perf.leanStats=true prints the lean counters at
	 *  exit (PERF-STATS LEAN): lean decisions, those that tested a pace landing, landings tested,
	 *  pace landings found, lazy predictions, lazy d2 counts. No decision reads the counters. */
	private static final boolean PERF_NO_LEAN = Boolean.getBoolean("ai.perf.noLean");
	private static final boolean PERF_LEAN_STATS = Boolean.getBoolean("ai.perf.leanStats");
	private static final int LEAN_DECISIONS = 0, LEAN_PACE_DECISIONS = 1, LEAN_PACE_TESTS = 2,
			LEAN_PACE_SWAPS = 3, LEAN_PREDICTIONS = 4, LEAN_D2 = 5;
	private static final java.util.concurrent.atomic.AtomicLongArray LEAN_STATS = leanStats();

	private static java.util.concurrent.atomic.AtomicLongArray leanStats() {
		if (!PERF_LEAN_STATS)
			return null;
		final java.util.concurrent.atomic.AtomicLongArray stats =
				new java.util.concurrent.atomic.AtomicLongArray(LEAN_D2 + 1);
		Runtime.getRuntime().addShutdownHook(new Thread(() -> System.err.println(
				"PERF-STATS LEAN decisions=" + stats.get(LEAN_DECISIONS)
				+ " paceDecisions=" + stats.get(LEAN_PACE_DECISIONS)
				+ " paceTests=" + stats.get(LEAN_PACE_TESTS)
				+ " paceSwaps=" + stats.get(LEAN_PACE_SWAPS)
				+ " predictions=" + stats.get(LEAN_PREDICTIONS)
				+ " d2=" + stats.get(LEAN_D2))));
		return stats;
	}

	/** perf_lean: check mode's own prediction rows, so its lazy shadow never touches the rows
	 *  the eager decision reads. Allocated only when check mode meets a lean decision. */
	private PredictionWorkspace leanCheckPrediction;

	/** The decision's prediction rows, sized to the roster (allocated inside
	 *  predictedOpponentCells until perf_lean gave that method its workspace). */
	private PredictionWorkspace predictionWorkspace() {
		if (predictionWorkspace == null || predictionWorkspace.result.length != game.players.length)
			predictionWorkspace = new PredictionWorkspace(game.players.length,
					game.gameCols + 1, game.gameRows + 1);
		return predictionWorkspace;
	}

	private PredictionWorkspace leanCheckPredictionWorkspace() {
		if (leanCheckPrediction == null || leanCheckPrediction.result.length != game.players.length)
			leanCheckPrediction = new PredictionWorkspace(game.players.length,
					game.gameCols + 1, game.gameRows + 1);
		return leanCheckPrediction;
	}

	/** The round-34 frozen opponent step as an occupancy, built into {@code workspace}: each
	 *  live rival's pure min-turns cell, transiting rivals nulled. optimalMoveAI1 ran this at
	 *  every decision's entry; since perf_lean an eager decision still does and a lean one
	 *  only when its queueBox asks for d2SafeCount. */
	private CellOccupancy predictedOccupancyNow(final int playerNum, final PredictionWorkspace workspace) {
		final int[][] predictedCells = predictedOpponentCells(playerNum, workspace);
		// Vacated-cell awareness: a fast-moving opponent (|v| >= 3) will have
		// moved through/off its predicted cell by the time I could occupy it --
		// blocking those cells causes phantom detours. Null out transiting
		// opponents' predictions; only slow/parked rivals stay blocked.
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pv = p.getVelocity();
			if (speedSquared(pv[0], pv[1]) >= AI1_VACATE_SPEED2)
				predictedCells[p.getNumber() - 1] = null;
		}
		workspace.occupancy.rebuild(predictedCells);
		return workspace.occupancy;
	}

	/** perf_lean: live rivals stalled at |v| <= 2.5 (STALLED_RIVAL_SPEED2) -- the filters of
	 *  countStalledRivalsAhead and countStalledRivalsWithin without their position tests, so
	 *  it bounds both counts. Keep the three in step. */
	private int stalledLiveRivals(final int playerNum) {
		int count = 0;
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pv = p.getVelocity();
			if (speedSquared(pv[0], pv[1]) <= STALLED_RIVAL_SPEED2)
				count++;
		}
		return count;
	}

	/**
	 * Project each live opponent one move with the pure min-turns policy:
	 * {@code result[opponentIdx]} is its next cell, or null when it has none.
	 * One move since round 247 (a one-level lookahead); the multi-step
	 * generality had no caller (review, 2026-09-28). The rows are
	 * {@code workspace}'s: the decision's, or perf_lean check mode's own.
	 */
	private int[][] predictedOpponentCells(final int myPlayerNum, final PredictionWorkspace workspace) {
		java.util.Arrays.fill(workspace.result, null);
		for (final Player player : game.players) {
			if (player.getNumber() == myPlayerNum || player.isFinished())
				continue;
			final int px = player.getPosition()[0], py = player.getPosition()[1];
			final int pvx = player.getVelocity()[0], pvy = player.getVelocity()[1];
			final Direction direction = pureMinTurnsMove(px, py, pvx, pvy, player.getNumber());
			if (direction == null)
				continue;
			final int nvx = pvx + direction.dx;
			final int nvy = pvy + direction.dy;
			if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
				continue;
			final int[] cell = workspace.cells[player.getNumber() - 1];
			cell[0] = px + nvx;
			cell[1] = py + nvy;
			workspace.result[player.getNumber() - 1] = cell;
		}
		return workspace.result;
	}


	private static int speedSquared(final int vx, final int vy) {
		return vx * vx + vy * vy;
	}

	static boolean isStrictlyAheadByTrackDistance(final int moverDistance,
			final int rivalDistance) {
		return moverDistance != Integer.MAX_VALUE && rivalDistance != Integer.MAX_VALUE
				&& rivalDistance < moverDistance;
	}

	static boolean useTrackDistanceForStagedLaunch(final int vx, final int vy,
			final boolean inStartZone) {
		return inStartZone && vx == 0 && vy == 0;
	}

	private static boolean squareExceeds(final long value, final long limit) {
		if (limit < 0L || value == Long.MIN_VALUE)
			return true;
		final long magnitude = Math.abs(value);
		return magnitude != 0L && magnitude > limit / magnitude;
	}

	private static long distanceSquared(final int dx, final int dy) {
		return (long) dx * dx + (long) dy * dy;
	}

	private static boolean occupiedByOther(final int x, final int y, final int self,
			final int[] px, final int[] py, final boolean[] alive) {
		for (int i = 0; i < px.length; i++)
			if (i != self && alive[i] && px[i] == x && py[i] == y)
				return true;
		return false;
	}

	private static boolean writeMove(final int[] out, final int x, final int y,
			final int vx, final int vy) {
		out[0] = x;
		out[1] = y;
		out[2] = vx;
		out[3] = vy;
		return true;
	}

	/** Greedy min-turnsToFinish move for a car at (x,y) vel (cvx,cvy) over a
	 *  DETACHED array board (alive cars at px/py). Writes {nx,ny,nvx,nvy} to
	 *  {@code out} and returns true, or returns false if boxed. */
	private boolean greedyMoveOverState(final int x, final int y, final int cvx, final int cvy, final int self,
			final int[] px, final int[] py, final boolean[] alive, final int[] out) {
		int bestT = Integer.MAX_VALUE;
		int bestX = 0, bestY = 0, bestVx = 0, bestVy = 0;
		boolean found = false;
		for (final Direction d : DIRECTIONS) {
			final int nvx = cvx + d.dx, nvy = cvy + d.dy;
			if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (finishesFor(self, x, y, nx, ny))
				return writeMove(out, nx, ny, nvx, nvy); // round 296: CP2 on the way included
			if (game.crossesFinishLegally(x, y, nx, ny) && crossingCountsFor(self, nx, ny, nvx, nvy)
					&& (!frameLapAware[self] || game.aiMoveLegal(x, y, nx, ny)
							&& !occupiedByOther(nx, ny, self, px, py, alive)))
				return writeMove(out, nx, ny, nvx, nvy);
			if (!game.aiMoveLegal(x, y, nx, ny))
				continue;
			if (occupiedByOther(nx, ny, self, px, py, alive) || !reach.isAlive(nx, ny, nvx, nvy))
				continue;
			final int turns = ttfForAfter(self, x, y, nx, ny, nvx, nvy); // round 296
			if (turns < bestT) {
				bestT = turns;
				bestX = nx;
				bestY = ny;
				bestVx = nvx;
				bestVy = nvy;
				found = true;
			}
		}
		return found && writeMove(out, bestX, bestY, bestVx, bestVy);
	}

	/** Count the legal, alive, unoccupied 1-step successors of (x,y,vx,vy) over
	 *  a DETACHED sim board. Stops at 3: only the trap ladder's zero-penalty
	 *  boundary (>= 3 safe successors) matters to the caller. */
	private int safeSuccessorsOverState(final int x, final int y, final int cvx, final int cvy, final int self,
			final int[] px, final int[] py, final boolean[] alive) {
		int count = 0;
		final int sm = succMask(x, y, cvx, cvy);
		for (final Direction d : DIRECTIONS) {
			final int nvx = cvx + d.dx, nvy = cvy + d.dy;
			if ((sm & 1 << 16 + d.ordinal()) == 0)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			// perf_aisearch (exact): the same AND, crossingCountsFor first.
			if (crossingCountsFor(self, nx, ny, nvx, nvy) && game.crossesFinishLegally(x, y, nx, ny)
					&& (!frameLapAware[self] || game.aiMoveLegal(x, y, nx, ny)
							&& !occupiedByOther(nx, ny, self, px, py, alive)))
				return 3;
			if ((sm & 1 << d.ordinal()) == 0)
				continue;
			if (occupiedByOther(nx, ny, self, px, py, alive) || !reach.isAlive(nx, ny, nvx, nvy))
				continue;
			if (++count >= 3)
				return 3;
		}
		return count;
	}

	/** Round 51 (shared champion): MY move inside the joint rollout. The real me is the
	 *  full scorer, whose trap ladder refuses landings with <= 2 safe
	 *  successors -- so a greedy sim-self drives into boxes the real me would
	 *  never enter and simOutcome reports a FALSE death ("zandvoort s7 is
	 *  greedy-me model error, not horizon"). Maximise safe successors (capped at
	 *  3, the ladder's zero-penalty boundary), then minimise turnsToFinish -- so
	 *  among genuinely roomy landings this is exactly the greedy pace policy,
	 *  and it only diverges where the real me would have refused. Round 56:
	 *  also the RIVAL policy inside the DJS rollout (exactRivals) -- the r55
	 *  forensic proved greedy rivals dissolve every real box in-sim. */
	private boolean selfMoveOverState(final int x, final int y, final int cvx, final int cvy, final int self,
			final int[] px, final int[] py, final boolean[] alive, final int[] out) {
		int bestTier = -1, bestT = Integer.MAX_VALUE;
		int bestX = 0, bestY = 0, bestVx = 0, bestVy = 0;
		boolean found = false;
		final int sm = succMask(x, y, cvx, cvy);
		for (final Direction d : DIRECTIONS) {
			final int nvx = cvx + d.dx, nvy = cvy + d.dy;
			if ((sm & 1 << 16 + d.ordinal()) == 0)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (finishesFor(self, x, y, nx, ny))
				return writeMove(out, nx, ny, nvx, nvy); // round 296: CP2 on the way included
			// perf_aisearch (exact): the same AND, crossingCountsFor first.
			if (crossingCountsFor(self, nx, ny, nvx, nvy) && game.crossesFinishLegally(x, y, nx, ny)
					&& (!frameLapAware[self] || game.aiMoveLegal(x, y, nx, ny)
							&& !occupiedByOther(nx, ny, self, px, py, alive)))
				return writeMove(out, nx, ny, nvx, nvy);
			if ((sm & 1 << d.ordinal()) == 0)
				continue;
			if (occupiedByOther(nx, ny, self, px, py, alive) || !reach.isAlive(nx, ny, nvx, nvy))
				continue;
			final int tier = safeSuccessorsOverState(nx, ny, nvx, nvy, self, px, py, alive);
			final int turns = ttfForAfter(self, x, y, nx, ny, nvx, nvy); // round 296
			if (tier > bestTier || tier == bestTier && turns < bestT) {
				bestTier = tier;
				bestT = turns;
				bestX = nx;
				bestY = ny;
				bestVx = nvx;
				bestVy = nvy;
				found = true;
			}
		}
		return found && writeMove(out, bestX, bestY, bestVx, bestVy);
	}

	/** Round 57 (AI1): RIVAL move inside the joint rollout -- the two loudest
	 *  terms of the real scorer, correctly WEIGHTED: minimise turnsToFinish
	 *  PLUS the trap ladder of the landing (50 / 2.0 / 0.5 / 0 for 0/1/2/>=3
	 *  safe successors). The oracle forensic proved why both prior proxies
	 *  miss real kills: greedy is trap-blind, and the lexicographic selfMove
	 *  policy (tier first) REFUSES the one-lane corridor cells the real
	 *  pace-seeking scorer claims (ttf gain > trap 2.0), so neither
	 *  reconstructs the queue boxes that actually kill (silverstone s6 m145,
	 *  hungaroring s6 m181: chosen dies in 2 rounds under real-scorer rivals,
	 *  survivors exist -- both invisible under greedy AND selfMove rivals). */
	private boolean rivalMoveOverState(final int x, final int y, final int cvx, final int cvy, final int self,
			final int[] px, final int[] py, final boolean[] alive, final int[] out) {
		double bestScore = Double.MAX_VALUE;
		int bestSpd2 = -1;
		int bestX = 0, bestY = 0, bestVx = 0, bestVy = 0;
		boolean found = false;
		final int sm = succMask(x, y, cvx, cvy);
		for (final Direction d : DIRECTIONS) {
			final int nvx = cvx + d.dx, nvy = cvy + d.dy;
			if ((sm & 1 << 16 + d.ordinal()) == 0)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (finishesFor(self, x, y, nx, ny))
				return writeMove(out, nx, ny, nvx, nvy); // round 296: CP2 on the way included
			// perf_aisearch (exact): the same AND, crossingCountsFor first.
			if (crossingCountsFor(self, nx, ny, nvx, nvy) && game.crossesFinishLegally(x, y, nx, ny)
					&& (!frameLapAware[self] || game.aiMoveLegal(x, y, nx, ny)
							&& !occupiedByOther(nx, ny, self, px, py, alive)))
				return writeMove(out, nx, ny, nvx, nvy);
			if ((sm & 1 << d.ordinal()) == 0)
				continue;
			if (occupiedByOther(nx, ny, self, px, py, alive) || !reach.isAlive(nx, ny, nvx, nvy))
				continue;
			final int tier = safeSuccessorsOverState(nx, ny, nvx, nvy, self, px, py, alive);
			final double trap = tier == 0 ? 50.0 : tier == 1 ? AI1_TRAP_L1 : tier == 2 ? AI1_TRAP_L2 : 0.0;
			final double score = ttfForAfter(self, x, y, nx, ny, nvx, nvy) + trap; // round 296
			// Momentum tie-break (policy matrix "smom"): among score-equal
			// candidates the real scorer HOLDS SPEED down the racing line
			// (deep cost + momentum), so prefer the faster landing. This is
			// what reproduces the silverstone box; the trap term reproduces
			// the hungaroring corridor claim -- smom matches the real-scorer
			// reference on all four site/candidate cells of the matrix.
			final int spd2 = speedSquared(nvx, nvy);
			if (score < bestScore || score == bestScore && spd2 > bestSpd2) {
				bestScore = score;
				bestSpd2 = spd2;
				bestX = nx;
				bestY = ny;
				bestVx = nvx;
				bestVy = nvy;
				found = true;
			}
		}
		return found && writeMove(out, bestX, bestY, bestVx, bestVy);
	}

	/** Round 59: a rival's rollout move computed by its REAL scorer -- the
	 *  only world model faithful enough for the slow queue dooms (the smom
	 *  proxy drifts within ~2 rounds in dense slow traffic; oracle-validated
	 *  at the hungaroring-(64,115) pocket and the lemans-s4 start funnel,
	 *  where real-scorer rivals flag both deaths with survivors intact).
	 *  Installs the sim board into the live Player objects (the
	 *  processQueries pattern), runs the mover's own scorer with the
	 *  recursive machinery suppressed ({@code inScorerSim}), restores everything
	 *  in a finally. Writes the landing to {@code out} and returns true, or
	 *  returns false only when no action was supplied. Legality/retirement is
	 *  decided by the rollout's referee transition, not the solo map. */
	private boolean scorerMoveOverState(final int i, final int[] px, final int[] py,
			final int[] vx, final int[] vy, final boolean[] alive, final int[] out,
			final RolloutWorkspace rollout) {
		return scorerMoveOverState(i, px, py, vx, vy, alive, out, rollout, true);
	}

	/** suppress=false (round 99): the rival's computeAiMove runs its FULL pace
	 *  stack -- the zandvoort-s32 killer move is a private-lane pace-arm
	 *  product, invisible to every suppressed world. The rival's own nested
	 *  sims still self-suppress (each nested scorer move re-sets the flag).
	 *  Per-depth workspaces and separately saved frames prevent the rival's
	 *  rollouts from clobbering their parent's projected state. */
	private boolean scorerMoveOverState(final int i, final int[] px, final int[] py,
			final int[] vx, final int[] vy, final boolean[] alive, final int[] out,
			final RolloutWorkspace rollout, final boolean suppress) {
		final ScorerWorkspace workspace = rollout.scorer;
		final int n = game.players.length;
		final int ss = game.subgamestate;
		final boolean previousScorerSim = inScorerSim;
		final boolean upgrade = awareUpgrade;
		awareUpgrade = false;
		final int outerAwarePolicyDepth = awarePolicyDepth;
		// perf_aware (exact): a suppressed decision is a function of the board installed below
		// and the decider's grid world (RaceAiMoveMemo), so a board this top-level decision
		// already met replays its move. Only suppressed decisions qualify: never an upgraded
		// (aware) move, never an unsuppressed true rival.
		final boolean memoized = !upgrade && (suppress || awarePolicyDepth > 0) && suppressedMovesOn();
		final int known = memoized ? suppressedMoves.find(i, rollout.turns, game.aiGridLegal, px, py,
				vx, vy, alive, rollout.laps, rollout.gates) : RaceAiMoveMemo.MISS;
		if (known != RaceAiMoveMemo.MISS && !PERF_CHECK)
			return replayScorerMove(i, px, py, vx, vy, out, RaceAiMoveMemo.move(known));
		// perf (upmemo, exact): an upgraded move this race already made on this board, in
		// this race world, replays too -- from the new generation, or from the old one and
		// refreshed into the new (upgradedMemoOn). The gate asserts the one context every
		// upgraded move has; it excludes the suppressed memo (memoized needs !upgrade).
		final boolean upMemo = upgrade && suppressedMovesOwned && upgradedMemoOn() && !suppress
				&& !previousScorerSim && simDepth == 1 && trueConfirmDepth == 0
				&& outerAwarePolicyDepth == 0 && !inFinishDenialConfirm && placeKeyDepth == 1
				&& awareDepth == 1;
		int upKnown = RaceAiMoveMemo.MISS;
		boolean upFromOld = false;
		if (upMemo) {
			upKnown = upgradedNew.find(i, rollout.turns, game.aiGridLegal, px, py, vx, vy, alive,
					rollout.laps, rollout.gates);
			if (upKnown == RaceAiMoveMemo.MISS) {
				upKnown = upgradedOld.find(i, rollout.turns, game.aiGridLegal, px, py, vx, vy, alive,
						rollout.laps, rollout.gates);
				upFromOld = upKnown != RaceAiMoveMemo.MISS;
			}
			if (PERF_UPMEMO_STATS)
				countUpgradedLookup(i == ss, upKnown, upFromOld);
			if (upKnown != RaceAiMoveMemo.MISS && !PERF_CHECK) {
				if (upFromOld)
					storeUpgraded(RaceAiMoveMemo.move(upKnown));
				return replayScorerMove(i, px, py, vx, vy, out, RaceAiMoveMemo.move(upKnown));
			}
		}
		// Round 222: the rival's compute assigns ITS lap frame at entry --
		// gate, lap-awareness, robust flag, remaining events. Put the mover's
		// back afterwards, or the rest of this decision is priced on the
		// rival's map.
		final int outerLapGate = lapGate, outerExactRemaining = exactRemaining;
		final int outerMoverNumber = moverNumber;
		final boolean outerLapAware = lapAware, outerRobustMode = robustMode;
		final int[] outerFrameGate = frameGate, outerFrameRemaining = frameRemaining;
		final boolean[] outerFrameLapAware = frameLapAware;
		final int outerTurns = game.turnCount();
		for (int j = 0; j < n; j++) {
			final Player player = game.players[j];
			workspace.originalPosition[j] = player.getPosition();
			workspace.originalVelocity[j] = player.getVelocity();
			workspace.finishedPlace[j] = player.getFinishedPlace();
			workspace.originalLapState[j] = player.lapState();
		}
		final Direction direction;
		try {
			frameGate = workspace.frameGate;
			frameRemaining = workspace.frameRemaining;
			frameLapAware = workspace.frameLapAware;
			game.setQueryTurnCounter(rollout.turns);
			for (int j = 0; j < n; j++) {
				final Player player = game.players[j];
				final int[] position = workspace.simulatedPosition[j];
				position[0] = px[j];
				position[1] = py[j];
				final int[] velocity = workspace.simulatedVelocity[j];
				velocity[0] = vx[j];
				velocity[1] = vy[j];
				player.setPosition(position);
				player.setVelocity(velocity);
				player.setFinishedPlace(alive[j] ? 0 : 77);
				player.restoreLapState(new int[]{rollout.laps[j], rollout.gates[j], 0, 0, 0, 0});
			}
			game.subgamestate = i;
			inScorerSim = suppress || awarePolicyDepth > 0;
			if (upgrade)
				awarePolicyDepth++;
			direction = computeAiMove();
		} finally {
			inScorerSim = previousScorerSim;
			awarePolicyDepth = outerAwarePolicyDepth;
			lapGate = outerLapGate;
			lapAware = outerLapAware;
			robustMode = outerRobustMode;
			exactRemaining = outerExactRemaining;
			moverNumber = outerMoverNumber;
			frameGate = outerFrameGate;
			frameRemaining = outerFrameRemaining;
			frameLapAware = outerFrameLapAware;
			game.setQueryTurnCounter(outerTurns);
			for (int j = 0; j < n; j++) {
				final Player player = game.players[j];
				player.setPosition(workspace.originalPosition[j]);
				player.setVelocity(workspace.originalVelocity[j]);
				player.setFinishedPlace(workspace.finishedPlace[j]);
				player.restoreLapState(workspace.originalLapState[j]);
			}
			game.subgamestate = ss;
		}
		if (memoized)
			recordSuppressedMove(i, rollout.turns, known, direction);
		if (upMemo)
			recordUpgradedMove(i, rollout.turns, upKnown, upFromOld, direction);
		if (direction == null)
			return false;
		final int nvx = vx[i] + direction.dx, nvy = vy[i] + direction.dy;
		// Replay the actual selected action, including a legal map-dead blockade
		// or a genuine crash. The solo map is neither a referee nor a policy veto:
		// this car may win before it ever needs another move.
		return writeMove(out, px[i] + nvx, py[i] + nvy, nvx, nvy);
	}

	/** perf_aware: scorerMoveOverState's tail for a replayed decision. */
	private static boolean replayScorerMove(final int i, final int[] px, final int[] py,
			final int[] vx, final int[] vy, final int[] out, final Direction direction) {
		if (direction == null)
			return false;
		final int nvx = vx[i] + direction.dx, nvy = vy[i] + direction.dy;
		return writeMove(out, px[i] + nvx, py[i] + nvy, nvx, nvy);
	}

	/** perf_aware: store a computed suppressed decision, or (self-check) compare a
	 *  recomputed hit with its stored move. */
	private void recordSuppressedMove(final int i, final int turns, final int known,
			final Direction direction) {
		if (known == RaceAiMoveMemo.MISS)
			suppressedMoves.store(direction);
		else if (RaceAiMoveMemo.move(known) != direction)
			System.err.println("PERF-AWARE MEMO MISMATCH slot=" + i + " turns=" + turns + " memo="
					+ RaceAiMoveMemo.move(known) + " computed=" + direction);
	}

	/** perf_aware: the memo stays off wherever a suppressed decision prints (the debug
	 *  flags) and in the query sim trace, so their output is unchanged. */
	private boolean suppressedMovesOn() {
		return !simTrace && AI_DEBUG_PLAYER < 0 && !AI_DEBUG_DJS && !AI_DEBUG_COMP;
	}

	/** perf (upmemo, exact): may scorerMoveOverState replay upgraded moves from the
	 *  race-scoped memo? An upgraded move is made only by awareMoveOverState in a top-level
	 *  chooser's rollout (awareDepth 1), so always in one context: simDepth 1, inScorerSim
	 *  false, no true or finish-denial confirm, placeKeyDepth 1, and every decision beneath
	 *  it suppressed (awarePolicyDepth 0 -> 1). scorerMoveOverState asserts all of it, and
	 *  that a top-level decision owns the memo (maintainUpgradedMemo ran), so any other
	 *  context bypasses it. There the move is a function of the suppressed memo's key --
	 *  the installed board, the mover's slot, the turn counter and the decider's grid
	 *  world -- and of the race world, which maintainUpgradedMemo validates. Budgets are
	 *  per call, there is no clock and no RNG, and what a replay skips is rewritten before
	 *  it is read (placeKey, chooserJudgedPace, the workspaces), compared only at deeper
	 *  rollouts (allScorerRolloutDepth, awareDepth) or a pure cache. Off with the kill
	 *  switch, wherever a suppressed decision prints, and under the finish-denial debug
	 *  lines, which an upgraded decision prints (it runs unsuppressed). An arm that makes
	 *  nested behaviour depend on the top-level decider must turn it off. */
	private boolean upgradedMemoOn() {
		return !PERF_NO_UPMEMO && suppressedMovesOn() && !AI_DEBUG_FINISH_DENIAL;
	}

	/** perf (upmemo): first in every top-level decision. Both generations are emptied
	 *  when the turn counter has not advanced since the last one (Undo, a restart, a
	 *  query, a test) or when the race world changed; otherwise they rotate once every
	 *  players.length turns, so a car's next decision and its rivals' in between still
	 *  find the entries of its last one. */
	private void maintainUpgradedMemo() {
		if (PERF_NO_UPMEMO)
			return;
		final int t = game.turnCount();
		// Every decision records the world, so a clear records it too; prepareDecisionFrame
		// asks for the potential next anyway.
		final boolean changed = upgradedWorld.sync(game, reach, game.optimalPotential());
		if (t <= upgradedLastTurn || changed) {
			upgradedNew.clear();
			upgradedOld.clear();
			upgradedGenTurn = t;
			if (PERF_UPMEMO_STATS)
				countUpmemo(UPMEMO_CLEARS);
		} else if (t - upgradedGenTurn >= game.players.length) {
			final RaceAiMoveMemo spare = upgradedOld;
			spare.clear();
			upgradedOld = upgradedNew;
			upgradedNew = spare;
			upgradedGenTurn = t;
			if (PERF_UPMEMO_STATS)
				countUpmemo(UPMEMO_ROTATIONS);
		}
		upgradedLastTurn = t;
	}

	/** perf (upmemo): store a computed upgraded move in the new generation when its lookup
	 *  missed or found it only in the old one, and (self-check) compare a recomputed hit.
	 *  Nothing beneath the move touched upgradedNew since its lookup (every decision there
	 *  is suppressed), so the key it left pending is still the move's. */
	private void recordUpgradedMove(final int i, final int turns, final int known, final boolean fromOld,
			final Direction direction) {
		if (known == RaceAiMoveMemo.MISS || fromOld)
			storeUpgraded(direction);
		if (known != RaceAiMoveMemo.MISS && RaceAiMoveMemo.move(known) != direction)
			System.err.println("PERF-AWARE UPMEMO MISMATCH upgraded slot=" + i + " turns=" + turns
					+ " gen=" + (fromOld ? "old" : "new") + " memo=" + RaceAiMoveMemo.move(known)
					+ " computed=" + direction);
	}

	/** perf (upmemo): commit the key upgradedNew's last lookup left pending. */
	private void storeUpgraded(final Direction move) {
		if (!PERF_UPMEMO_STATS) {
			upgradedNew.store(move);
			return;
		}
		final int before = upgradedNew.size();
		upgradedNew.store(move);
		countUpmemo(upgradedNew.size() > before ? UPMEMO_STORES : UPMEMO_CAPPED);
	}

	private static void countUpgradedLookup(final boolean self, final int known, final boolean fromOld) {
		countUpmemo(UPMEMO_LOOKUPS);
		if (self)
			countUpmemo(UPMEMO_SELF_LOOKUPS);
		if (known == RaceAiMoveMemo.MISS)
			return;
		countUpmemo(fromOld ? UPMEMO_HITS_OLD : UPMEMO_HITS_NEW);
		countUpmemo(self ? UPMEMO_SELF_HITS : UPMEMO_RIVAL_HITS);
	}

	private static void countUpmemo(final int counter) {
		if (UPMEMO_COUNTS != null)
			UPMEMO_COUNTS.incrementAndGet(counter);
	}

	/** perf (upmemo) stats: the counters, and the shutdown hook that prints them. */
	private static java.util.concurrent.atomic.AtomicLongArray upmemoCounters() {
		final java.util.concurrent.atomic.AtomicLongArray counts =
				new java.util.concurrent.atomic.AtomicLongArray(UPMEMO_STAT_NAMES.length);
		Runtime.getRuntime().addShutdownHook(new Thread(() -> {
			final StringBuilder line = new StringBuilder("PERF-STATS UPMEMO");
			for (int k = 0; k < UPMEMO_STAT_NAMES.length; k++)
				line.append(' ').append(UPMEMO_STAT_NAMES[k]).append('=').append(counts.get(k));
			System.err.println(line);
		}, "perf-stats-upmemo"));
		return counts;
	}

	/** perf (upmemo C3, exact): endgameSolve's result for this root as a RaceAiMoveMemo
	 *  code, or MISS (always MISS with the kill switch). Past endgameSolve's guards the
	 *  search reads only the two cars' states, the mover's ttf (exactRemaining on the exact
	 *  potential, else the finish map: lapAware is false there), the turn counter (only
	 *  through endgameTimedOut), the car count, the grid world (crossing and move
	 *  legality), and the maps and course; egMemo and egNodes are its own, and nothing in
	 *  it prints. The key holds the root's part, egResultWorld the rest -- checked at every
	 *  lookup, so direct calls (tests) are safe too. Top-level, upgraded and true-confirm
	 *  decisions compute the same function and share entries. */
	private int egResultFind(final int playerNum, final int ri, final int[] pos, final int[] vel,
			final int[] rp, final int[] rv) {
		egResultSlot = -1;
		if (PERF_NO_UPMEMO)
			return RaceAiMoveMemo.MISS;
		if (egResultKeys == null) {
			egResultKeys = new int[EG_RESULT_SLOTS * EG_RESULT_INTS];
			egResultCodes = new byte[EG_RESULT_SLOTS];
		}
		if (egResultWorld.sync(game, reach, exactPot))
			java.util.Arrays.fill(egResultCodes, (byte) 0);
		final int[] key = egResultProbe;
		key[0] = playerNum;
		key[1] = ri;
		key[2] = game.players.length;
		key[3] = game.turnCount();
		key[4] = game.aiGridLegal ? 1 : 0;
		key[5] = exactPot == null ? -1 : exactRemaining;
		key[6] = pos[0];
		key[7] = pos[1];
		key[8] = vel[0];
		key[9] = vel[1];
		key[10] = rp[0];
		key[11] = rp[1];
		key[12] = rv[0];
		key[13] = rv[1];
		long h = 0xCBF29CE484222325L;
		for (final int k : key) {
			h ^= k;
			h *= 0x100000001B3L;
		}
		h ^= h >>> 33;
		h *= 0xFF51AFD7ED558CCDL;
		h ^= h >>> 33;
		final int slot = (int) h & EG_RESULT_SLOTS - 1;
		egResultSlot = slot;
		if (PERF_UPMEMO_STATS)
			countUpmemo(UPMEMO_EG_LOOKUPS);
		if (egResultCodes[slot] == 0)
			return RaceAiMoveMemo.MISS;
		for (int k = 0, at = slot * EG_RESULT_INTS; k < EG_RESULT_INTS; k++, at++)
			if (egResultKeys[at] != key[k])
				return RaceAiMoveMemo.MISS;
		if (PERF_UPMEMO_STATS)
			countUpmemo(UPMEMO_EG_HITS);
		return egResultCodes[slot] - 2;
	}

	/** perf (upmemo C3): store a searched result in the slot of the root egResultFind just
	 *  probed when it missed (a colliding root is overwritten), and (self-check) compare a
	 *  recomputed hit. */
	private void egResultRecord(final int known, final int playerNum, final Direction solved) {
		if (egResultSlot < 0)
			return;
		if (known == RaceAiMoveMemo.MISS) {
			System.arraycopy(egResultProbe, 0, egResultKeys, egResultSlot * EG_RESULT_INTS, EG_RESULT_INTS);
			egResultCodes[egResultSlot] = (byte) (RaceAiMoveMemo.code(solved) + 2);
			if (PERF_UPMEMO_STATS)
				countUpmemo(UPMEMO_EG_STORES);
		} else if (RaceAiMoveMemo.move(known) != solved)
			System.err.println("PERF-AWARE UPMEMO MISMATCH endgame p=" + playerNum + " turns="
					+ game.turnCount() + " memo=" + RaceAiMoveMemo.move(known) + " computed=" + solved);
	}

	/** perf (upmemo): the race world a race-scoped memo's entries were computed in -- what an
	 *  upgraded decision or an endgame search reads beyond its key: the reachability maps
	 *  and their dimensions, the exact potential, the course (with the finish crossing's
	 *  line and forward direction by value) and the roster (the Player objects, whose kind
	 *  and number are final). Compared by identity or value; sync records the current world
	 *  and says whether it differs from the one recorded last. */
	private static final class WorldStamp {
		private final java.lang.ref.WeakReference<?>[] refs = new java.lang.ref.WeakReference<?>[13];
		private final boolean[] nulls = new boolean[13];
		private final int[] values = new int[7];
		private final long[] crossing = new long[6];
		private Object[] gates = new Object[0];
		private Object[] roster = new Object[0];
		private boolean recorded;
		private boolean differs;

		boolean sync(final RaceGame game, final Reachability reach, final Object potential) {
			differs = !recorded;
			recorded = true;
			ref(0, potential);
			ref(1, reach.turnsArr);
			ref(2, reach.aliveStates);
			ref(3, reach.gateTurns);
			ref(4, reach.minShed2);
			ref(5, reach.distToFinish);
			ref(6, reach.robustReach);
			ref(7, reach.roomy0);
			ref(8, game.lapGates);
			ref(9, game.finishLine);
			ref(10, game.trackA);
			ref(11, game.startZoneA);
			ref(12, game.players);
			value(0, reach.aliveW);
			value(1, reach.aliveH);
			value(2, reach.aliveVMAX);
			value(3, reach.aliveSpan);
			value(4, game.totalLaps);
			value(5, game.gameCols);
			value(6, game.gameRows);
			final double[] line = game.crossingIdentity();
			for (int k = 0; k < crossing.length; k++) {
				final long bits = Double.doubleToRawLongBits(line[k]);
				if (crossing[k] != bits) {
					crossing[k] = bits;
					differs = true;
				}
			}
			gates = elements(gates, game.lapGates);
			roster = elements(roster, game.players);
			return differs;
		}

		/** Weakly held, so a stamp does not pin maps a restart released: a cleared referent
		 *  is never == a live object, so it reads as a change and only clears the memos. */
		private void ref(final int k, final Object now) {
			final java.lang.ref.WeakReference<?> was = refs[k];
			if (now == null ? !nulls[k] : was == null || was.get() != now) {
				refs[k] = now == null ? null : new java.lang.ref.WeakReference<Object>(now);
				nulls[k] = now == null;
				differs = true;
			}
		}

		private void value(final int k, final int now) {
			if (values[k] != now) {
				values[k] = now;
				differs = true;
			}
		}

		/** An array's elements against the recorded ones (null holds none). */
		private Object[] elements(final Object[] was, final Object[] now) {
			final int n = now == null ? 0 : now.length;
			Object[] kept = was;
			if (kept.length != n) {
				kept = new Object[n];
				differs = true;
			}
			for (int k = 0; k < n; k++)
				if (kept[k] != now[k]) {
					kept[k] = now[k];
					differs = true;
				}
			return kept;
		}
	}

	/** A proxy may find no preferred/map-alive move even though physical moves
	 * remain. Keep a deterministic legal continuation in that approximate world;
	 * never promote search abstention into a confirmed referee retirement. This
	 * fallback is used only when no action was selected, not to replace an actual
	 * scorer-selected crash. All physical accelerations are considered. */
	private boolean physicalMoveOverState(final int i, final int[] px, final int[] py,
			final int[] vx, final int[] vy, final boolean[] alive, final int[] out,
			final RolloutWorkspace rollout) {
		boolean found = false;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx[i] + d.dx, nvy = vy[i] + d.dy;
			final int nx = px[i] + nvx, ny = py[i] + nvy;
			final RaceGame.MoveResult move = game.evaluateMove(rollout.laps[i], rollout.gates[i],
					px[i], py[i], nx, ny, occupiedByOther(nx, ny, i, px, py, alive));
			if (move.finishes())
				return writeMove(out, nx, ny, nvx, nvy);
			if (move.legal() && !found) {
				writeMove(out, nx, ny, nvx, nvy);
				found = true;
			}
		}
		return found;
	}

	/** Disjoint storage for every active rollout, including suppressed nested
	 * scorers. Parent proof vectors and progress ledgers remain live. */
	private RolloutWorkspace rolloutWorkspace() {
		if (simDepth >= rolloutsByDepth.length)
			rolloutsByDepth = java.util.Arrays.copyOf(rolloutsByDepth, simDepth + 4);
		final int players = game.players.length;
		if (rolloutsByDepth[simDepth] == null || rolloutsByDepth[simDepth].px.length != players)
			rolloutsByDepth[simDepth] = new RolloutWorkspace(players);
		return rolloutsByDepth[simDepth];
	}

	/** Roll the joint game forward from MY candidate landing over a DETACHED
	 *  board copy: every car plays greedy min-turnsToFinish; move-order aware
	 *  (the first simulated round covers only the players who still move after
	 *  me this round). Returns my turnsToFinish after {@code rounds} full
	 *  rounds, or -1 if I end up boxed (no legal alive move at one of my
	 *  slots). No mutation of live players[] -- deterministic, cannot
	 *  livelock. Shared champion logic (round 40 danger joint search). */
	private int simOutcome(final int myX, final int myY, final int myVx, final int myVy,
			final int playerNum, final int rounds, final boolean simFinishVanish, final boolean exactSelf,
			final boolean exactRivals, final boolean scorerRivals) {
		return simOutcome(myX, myY, myVx, myVy, playerNum, rounds, simFinishVanish, exactSelf,
				exactRivals, scorerRivals, AI1_SCORER_MAXRIVALS, null);
	}

	private int simOutcome(final int myX, final int myY, final int myVx, final int myVy,
			final int playerNum, final int rounds, final boolean simFinishVanish, final boolean exactSelf,
			final boolean exactRivals, final boolean scorerRivals, final int scorerCap,
			final int[] outFinalTier) {
		return simOutcome(myX, myY, myVx, myVy, playerNum, rounds, simFinishVanish, exactSelf,
				exactRivals, scorerRivals, false, scorerCap, outFinalTier, null);
	}

	/** Field-neutral scorer rollout used by the private and staged pace proofs.
	 *  Naming this fixed flag bundle keeps the safety-critical call sites out of
	 *  the boolean-argument soup used by the general simulator. */
	private int scorerFieldOutcome(final int myX, final int myY, final int myVx, final int myVy,
			final int playerNum, final int rounds, final int scorerCap, final long[] outFieldCost) {
		return simOutcome(myX, myY, myVx, myVy, playerNum, rounds, true, true, true, true,
				false, scorerCap, null, outFieldCost);
	}

	/** scorerSelf (round 78): model ME with the recursion-guarded real scorer
	 *  (scorerMoveOverState) instead of the selfMove proxy -- the zandvoort
	 *  m920 survivor exists only under the champion's own continued play, so
	 *  selfMove-me kills it and survival-only switching finds nothing. */
	private int simOutcome(final int myX, final int myY, final int myVx, final int myVy,
			final int playerNum, final int rounds, final boolean simFinishVanish, final boolean exactSelf,
			final boolean exactRivals, final boolean scorerRivals, final boolean scorerSelf,
			final int scorerCap, final int[] outFinalTier) {
		return simOutcome(myX, myY, myVx, myVy, playerNum, rounds, simFinishVanish, exactSelf,
				exactRivals, scorerRivals, scorerSelf, scorerCap, outFinalTier, null);
	}

	private int simOutcome(final int myX, final int myY, final int myVx, final int myVy,
			final int playerNum, final int rounds, final boolean simFinishVanish, final boolean exactSelf,
			final boolean exactRivals, final boolean scorerRivals, final boolean scorerSelf,
			final int scorerCap, final int[] outFinalTier, final long[] outFieldCost) {
		return simOutcome(myX, myY, myVx, myVy, playerNum, rounds, simFinishVanish, exactSelf,
				exactRivals, scorerRivals, scorerSelf, false, scorerCap, outFinalTier, outFieldCost, null);
	}

	/** Round 103 probe: when armed (query-sim protocol), the TOP-LEVEL
	 *  rollout prints one SIMTRACE line per mover step to stderr -- the
	 *  in-game twin of the Python roll, diffable line by line. Nested
	 *  rollouts (inside scorer/true rival computes) stay silent. */
	volatile boolean				simTrace;
	private int						simDepth;
	/** Round 281: the rollout depth at which every live rival plays its real
	 *  scorer -- the chooser's own rollout; -1 for none. */
	private int allScorerRolloutDepth = -1;

	/** Query-sim entry (round 103): verdict of the core rollout from the
	 *  installed board, me already AT the queried landing. */
	int querySimOutcome(final int mover, final int rounds, final boolean scorerRivals,
			final boolean trueRivals, final boolean scorerSelf, final int scorerCap,
			final int[] outAudit) {
		reach.ensureReachabilityReady();
		fmMemoEpoch++;
		final Player me = game.players[mover];
		final int[] mp = me.getPosition(), mv = me.getVelocity();
		prepareDecisionFrame(mp, mv, me.getNumber());
		final int[] ft = { 3 };
		final int[] tr = { 0, 0 };
		final int v = simulate(mp[0], mp[1], mv[0], mv[1], me.getNumber(), rounds, true, true,
				true, scorerRivals, scorerSelf, trueRivals, scorerCap, ft, null, tr, false);
		if (outAudit != null) {
			outAudit[0] = ft[0];
			outAudit[1] = tr[0];
			outAudit[2] = tr[1];
		}
		return v;
	}

	/** trueRivals (round 99): scorer-set rivals run their UNSUPPRESSED real
	 *  champion -- pace arms included. Reserved for the rare bounded confirm;
	 *  cost is rivals x rounds full computeAiMove calls.
	 *  outThreadRounds (round 98): counts my move slots entered with at most ONE
	 *  viable candidate (legal, unoccupied, reachability-alive). An alive verdict
	 *  that threads a one-lane needle on EVERY slot is no certificate at all in
	 *  pack traffic -- chicane s51 m121 rolls alive through viable=1,1,1,1 in
	 *  every affordable rival world while the real pack's champion braking (their
	 *  own suppressed arms) seals the lane @r2; the two true survivors roll
	 *  viable>=2 on all slots in the same cheap world. The count is model-free:
	 *  no rival fidelity needed, no extra simulations, just the candidate
	 *  enumeration my own sim move already performs. Round 98's thread search went
	 *  in round 310; legHold11's thread tell and the sim2 query audit read the count. */
	private int simOutcome(final int myX, final int myY, final int myVx, final int myVy,
			final int playerNum, final int rounds, final boolean simFinishVanish, final boolean exactSelf,
			final boolean exactRivals, final boolean scorerRivals, final boolean scorerSelf,
			final boolean trueRivals, final int scorerCap, final int[] outFinalTier,
			final long[] outFieldCost, final int[] outThreadRounds) {
		return simulate(myX, myY, myVx, myVy, playerNum, rounds, simFinishVanish, exactSelf,
				exactRivals, scorerRivals, scorerSelf, trueRivals, scorerCap, outFinalTier,
				outFieldCost, outThreadRounds, true);
	}

	private int simulate(final int myX, final int myY, final int myVx, final int myVy,
			final int playerNum, final int rounds, final boolean simFinishVanish, final boolean exactSelf,
			final boolean exactRivals, final boolean scorerRivals, final boolean scorerSelf,
			final boolean trueRivals, final int scorerCap, final int[] outFinalTier,
			final long[] outFieldCost, final int[] outThreadRounds, final boolean candidatePending) {
		final int outerGate = lapGate, outerRemaining = exactRemaining;
		final boolean outerAware = lapAware, outerRobust = robustMode;
		final int[] outerGates = frameGate, outerRemainingByPlayer = frameRemaining;
		final boolean[] outerAwareByPlayer = frameLapAware;
		// perf_aware: a rollout outside a top-level decision (a query, a direct call) owns an
		// empty memo of its own.
		if (simDepth == 0 && !suppressedMovesOwned)
			suppressedMoves.clear();
		simDepth++;
		try {
			final RolloutWorkspace workspace = rolloutWorkspace();
			frameGate = workspace.gates;
			frameRemaining = workspace.remaining;
			frameLapAware = workspace.lapAware;
			return simOutcomeCore(myX, myY, myVx, myVy, playerNum, rounds, simFinishVanish,
					exactSelf, exactRivals, scorerRivals, scorerSelf, trueRivals, scorerCap,
					outFinalTier, outFieldCost, outThreadRounds, candidatePending);
		} finally {
			frameGate = outerGates;
			frameRemaining = outerRemainingByPlayer;
			frameLapAware = outerAwareByPlayer;
			lapGate = outerGate;
			exactRemaining = outerRemaining;
			lapAware = outerAware;
			robustMode = outerRobust;
			simDepth--;
		}
	}

	private void updateRolloutFrame(final RolloutWorkspace workspace, final int i) {
		frameLapAware[i] = workspace.laps[i] + 1 < game.totalLaps || frameGate[i] != 0;
		frameRemaining[i] = OptimalPotential.remainingEvents(frameGate[i], workspace.laps[i], game.totalLaps);
	}

	private void usePlayerFrame(final int i) {
		lapGate = frameGate[i];
		lapAware = frameLapAware[i];
		exactRemaining = frameRemaining[i];
	}

	/** Round 274, rank first: a live rollout verdict is
	 *  {@code ahead * VERDICT_PLACE_STRIDE + time}, where {@code ahead} counts the
	 *  rivals that FINISHED (never the ones that crashed) before the mover finished,
	 *  was classified, or the horizon ran out. Every comparison of two verdicts
	 *  therefore ranks place first and time second; with nobody ahead it is the
	 *  pre-274 verdict exactly. Pass/fail readings take the time part,
	 *  {@code verdict % VERDICT_PLACE_STRIDE}. */
	static final int VERDICT_PLACE_STRIDE = 1_000_000;

	static int rankVerdict(final int ahead, final int time) {
		if (ahead == 0 || time == Integer.MAX_VALUE)
			return time;
		return ahead * VERDICT_PLACE_STRIDE + Math.min(time, VERDICT_PLACE_STRIDE - 1);
	}

	/** Round 270 (the chooser's finer key): the same place, with the mover's
	 *  projected total turns as time -- its finishing round rather than 0 -- for
	 *  the rollout started at simDepth == placeKeyDepth. */
	private static final long PLACE_KEY_STRIDE = VERDICT_PLACE_STRIDE;
	/** Round 285: the forecast depth whose mover and relevant rival make their
	 *  first move with the full policy; -1 for none. */
	private int awareDepth = -1, awareRival = -1;
	/** perf_aware (exact): the moves of suppressed decisions met in this top-level decision
	 *  (or standalone rollout), and whether a top-level decision owns that memo now. */
	private final RaceAiMoveMemo suppressedMoves = new RaceAiMoveMemo();
	private boolean suppressedMovesOwned;
	/** perf (upmemo, exact): the moves of upgraded (aware) forecast decisions, kept for the
	 *  whole race in two generations (upgradedMemoOn, maintainUpgradedMemo): a car's next
	 *  decision meets its forecast's boards again when the field followed that forecast, and
	 *  a rival's decision meets the board another car's forecast gave it. Each holds at
	 *  most 1 << 12 entries and 1 << 18 key ints (eight-car keys are 60 ints: 245,760 at the
	 *  entry cap); a full generation stops storing, which only recomputes. */
	private RaceAiMoveMemo upgradedNew = new RaceAiMoveMemo(1 << 12, 1 << 18),
			upgradedOld = new RaceAiMoveMemo(1 << 12, 1 << 18);
	/** perf (upmemo): the turn the new generation began, the turn of the last top-level
	 *  decision, and the race world both generations were computed in. */
	private int upgradedGenTurn, upgradedLastTurn = -1;
	private final WorldStamp upgradedWorld = new WorldStamp();
	/** perf (upmemo): -Dai.perf.noUpMemo=true keeps both race-scoped memos off, which is the
	 *  round-310 path, for a CPU comparison within one jar. */
	private static final boolean PERF_NO_UPMEMO = Boolean.getBoolean("ai.perf.noUpMemo");
	/** perf (upmemo C3, exact): endgameSolve's searched results by root (egResultFind),
	 *  direct-mapped: EG_RESULT_SLOTS slots of EG_RESULT_INTS key ints and a code byte, the
	 *  RaceAiMoveMemo move code plus 2 (0 is an empty slot); a colliding root overwrites,
	 *  which only recomputes. egResultSlot is the slot of the last lookup. */
	private static final int EG_RESULT_SLOTS = 1 << 10, EG_RESULT_INTS = 14;
	private int[] egResultKeys;
	private byte[] egResultCodes;
	private final int[] egResultProbe = new int[EG_RESULT_INTS];
	private int egResultSlot = -1;
	private final WorldStamp egResultWorld = new WorldStamp();
	/** perf (upmemo) stats, -Dai.perf.upmemoStats=true: counters over the whole JVM, printed
	 *  to stderr as one PERF-STATS UPMEMO line by a shutdown hook. No decision reads them. */
	private static final boolean PERF_UPMEMO_STATS = Boolean.getBoolean("ai.perf.upmemoStats");
	private static final String[] UPMEMO_STAT_NAMES = {"lookups", "selfLookups", "hitsNew", "hitsOld",
			"selfHits", "rivalHits", "stores", "capped", "clears", "rotations", "egLookups", "egHits",
			"egStores"};
	private static final int UPMEMO_LOOKUPS = 0, UPMEMO_SELF_LOOKUPS = 1, UPMEMO_HITS_NEW = 2,
			UPMEMO_HITS_OLD = 3, UPMEMO_SELF_HITS = 4, UPMEMO_RIVAL_HITS = 5, UPMEMO_STORES = 6,
			UPMEMO_CAPPED = 7, UPMEMO_CLEARS = 8, UPMEMO_ROTATIONS = 9, UPMEMO_EG_LOOKUPS = 10,
			UPMEMO_EG_HITS = 11, UPMEMO_EG_STORES = 12;
	private static final java.util.concurrent.atomic.AtomicLongArray UPMEMO_COUNTS =
			PERF_UPMEMO_STATS ? upmemoCounters() : null;
	/** perf_aware (exact): the relevant-rival fronts of one top-level chooser call. */
	private final ChooserTraffic.FrontCache trafficFronts = new ChooserTraffic.FrontCache();
	/** perf_aware self-check, -Dai.perf.check=true: recompute every memo hit and the
	 *  original relevant-rival graph, race on the recomputed values and print any
	 *  difference to stderr. Off by default. */
	private static final boolean PERF_CHECK = Boolean.getBoolean("ai.perf.check");
	/** Lab port: set by awareMoveOverState for exactly one scorerMoveOverState
	 *  call; every policy call beneath that upgraded move runs suppressed. */
	private boolean awareUpgrade;
	private int awarePolicyDepth;
	private long placeKey = -1;
	private int placeKeyDepth = -1;

	private int simOutcomeCore(final int myX, final int myY, final int myVx, final int myVy,
			final int playerNum, final int rounds, final boolean simFinishVanish, final boolean exactSelf,
			final boolean exactRivals, final boolean scorerRivals, final boolean scorerSelf,
			final boolean trueRivals, final int scorerCap, final int[] outFinalTier,
			final long[] outFieldCost, final int[] outThreadRounds, final boolean candidatePending) {
		final RolloutWorkspace workspace = rolloutWorkspace();
		final int[] px = workspace.px;
		final int[] py = workspace.py;
		final int[] vx = workspace.vx;
		final int[] vy = workspace.vy;
		final boolean[] alive = workspace.alive;
		final boolean[] scorerSet = workspace.scorerSet;
		final int[] move = workspace.move;
		workspace.turns = game.turnCount();
		// perf_bnb (exact): the bound jointChooser hands its own rollout (bnbPotential); any
		// other rollout runs without one. boundBase is the mover's moves made (rounds played)
		// plus its exact distance, boundMoves its moves made.
		OptimalPotential boundPot = simDepth == placeKeyDepth ? bnbPot : null;
		final long boundCut = bnbCutoff;
		long boundBase = 0L;
		int boundMoves = 0;
		if (boundPot != null) {
			workspace.bnbBound = -1L;
			workspace.bnbStopMoves = -1;
			workspace.bnbStopAware = 0;
		}
		java.util.Arrays.fill(scorerSet, false);
		if (outFieldCost != null)
			outFieldCost[0] = 0L;
		long failedRivalCost = 0L;
		boolean myFinished = false;
		int rivalsFinished = 0, aheadAtMyFinish = 0, myFinishRound = 0, endRound = 0;
		int liveCount = 0;
		int myIdx = 0;
		for (int i = 0; i < game.players.length; i++) {
			final Player player = game.players[i];
			final int[] position = player.getPosition();
			final int[] velocity = player.getVelocity();
			px[i] = position[0];
			py[i] = position[1];
			vx[i] = velocity[0];
			vy[i] = velocity[1];
			alive[i] = !player.isFinished();
			if (alive[i])
				liveCount++;
			workspace.laps[i] = player.getLap();
			workspace.gates[i] = game.lapGates == null ? 0 : player.getNextGate();
			updateRolloutFrame(workspace, i);
			if (player.getNumber() == playerNum)
				myIdx = i;
		}
		if (candidatePending) {
			// The referee retires the mover before evaluating its destination.
			if (game.raceTurnLimitReached())
				return -1;
			final RaceGame.MoveResult candidate = game.evaluateMove(workspace.laps[myIdx], workspace.gates[myIdx],
					px[myIdx], py[myIdx], myX, myY, occupiedByOther(myX, myY, myIdx, px, py, alive));
			if (!candidate.legal())
				return -1;
			workspace.laps[myIdx] = candidate.lapAfter();
			workspace.gates[myIdx] = game.lapGates == null ? 0 : candidate.gateAfter();
			updateRolloutFrame(workspace, myIdx);
			workspace.turns++;
			if (candidate.finishes() && simFinishVanish) {
				alive[myIdx] = false;
				liveCount--;
				myFinished = true;
				if (outFinalTier != null)
					outFinalTier[0] = 3;
				if (outFieldCost == null) {
					if (simDepth == placeKeyDepth)
						placeKey = 0;
					return 0;
				}
			}
		}
		px[myIdx] = myX;
		py[myIdx] = myY;
		vx[myIdx] = myVx;
		vy[myIdx] = myVy;
		// perf_bnb: the base at the landing, in the frame after the candidate's move: no move
		// made, P0 to go. A landing the potential cannot price gets no bound.
		if (boundPot != null) {
			final int startP = boundPot.movesToFinish(frameRemaining[myIdx], myX, myY, myVx, myVy);
			if (startP == Integer.MAX_VALUE)
				boundPot = null;
			else
				workspace.bnbBound = boundBase = startP;
		}
		// Round 59: slow-class fires roll the nearest rivals with their REAL
		// scorer (recursion-guarded); the rest keep the smom proxy.
		// Membership is fixed at rollout start: the nearest
		// AI1_SCORER_MAXRIVALS within Chebyshev AI1_SCORER_NEAR. Round 281: in the
		// chooser's own rollout every live rival plays its scorer. Round 300a: in
		// every rollout a real decision starts too -- the danger, thread and pace
		// searches (-0.031 places on held-out seeds, -0.029 computed, CPU 1.09x);
		// nested rollouts and the true-rival confirms keep the cap. Round 310: the
		// slow-class fires and the thread search are gone; the danger search runs only
		// as the kinematic confirm.
		if (scorerRivals && (simDepth == allScorerRolloutDepth || simDepth == 1 && !trueRivals)) {
			for (int i = 0; i < game.players.length; i++)
				if (i != myIdx && alive[i])
					scorerSet[i] = true;
		} else if (scorerRivals) {
			// Round 102: for TRUE-RIVAL confirms only, the membership radius
			// scales with MY speed -- monza s80 commits at spd-inf 10 toward a
			// braking car 11 cells downstream; a fixed Chebyshev-10 net can
			// never contain the rivals a fast landing reaches within the
			// horizon. Suppressed worlds keep the pinned radius (a global
			// change slowed the round-96 coil finish frontier by four moves).
			final int spdInf = Math.max(Math.abs(myVx), Math.abs(myVy));
			final int scorerNear = trueRivals ? Math.max(AI1_SCORER_NEAR, 2 * spdInf)
					: AI1_SCORER_NEAR;
			for (int k = 0; k < scorerCap; k++) {
				int nearest = -1, nearestD = scorerNear + 1;
				for (int j = 0; j < game.players.length; j++) {
					if (j == myIdx || !alive[j] || scorerSet[j])
						continue;
					final int distance = Math.max(Math.abs(px[j] - myX), Math.abs(py[j] - myY));
					if (distance < nearestD) {
						nearestD = distance;
						nearest = j;
					}
				}
				if (nearest < 0)
					break;
				scorerSet[nearest] = true;
			}
		}
		// Round 285: in an aware forecast the mover's and the relevant rival's first
		// moves use the full policy. Round 305: the mover's first AI1_AWARE_SELF_MOVES
		// continuation moves do; the rival keeps one.
		final boolean awareRollout = simDepth == awareDepth;
		int awareSelfLeft = awareRollout ? AI1_AWARE_SELF_MOVES : 0;
		boolean awareRivalDone = !awareRollout || awareRival < 0;
		final int awareRivalIdx = awareRival;
		final boolean trace = simTrace && simDepth == 1;
		if (trace) {
			final StringBuilder sb = new StringBuilder("SIMTRACE start me=i").append(myIdx)
					.append(" (").append(myX).append(',').append(myY).append(")v(")
					.append(myVx).append(',').append(myVy).append(") scorerSet=");
			for (int i = 0; i < game.players.length; i++)
				if (scorerSet[i])
					sb.append('i').append(i).append(' ');
			System.err.println(sb);
		}
		// RaceGame.checkFinished classifies the last survivor without another move.
		// A solo time trial is the exception: its only car must still finish.
		final int terminalLiveCount = game.players.length == 1 ? 0 : 1;
		boolean raceOver = liveCount <= terminalLiveCount;
		for (int round = 0; round < rounds && !raceOver; round++) {
			endRound = round;
			// First simulated round: only players after me in this real round's
			// move order still move before my next slot.
			final int from = round == 0 ? game.subgamestate + 1 : 0;
			for (int i = from; i < game.players.length; i++) {
				if (!alive[i] || i == myIdx && round == 0)
					continue;
				usePlayerFrame(i);
				if (i == myIdx && outThreadRounds != null) {
					int viable = 0;
					for (final Direction d : DIRECTIONS) {
						final int tvx = vx[i] + d.dx, tvy = vy[i] + d.dy;
						if (RaceGame.aiVelocityOutOfRange(tvx, tvy))
							continue;
						final int tx = px[i] + tvx, ty = py[i] + tvy;
						if (game.evaluateMove(workspace.laps[i], workspace.gates[i], px[i], py[i], tx, ty,
								occupiedByOther(tx, ty, i, px, py, alive)).finishes()) {
							viable = DIRECTIONS.length;
							break;
						}
						if (!game.aiMoveLegal(px[i], py[i], tx, ty))
							continue;
						if (occupiedByOther(tx, ty, i, px, py, alive)
								|| !reach.isAlive(tx, ty, tvx, tvy))
							continue;
						viable++;
					}
					if (viable <= 1)
						outThreadRounds[0]++;
					if (viable <= 2 && outThreadRounds.length > 1)
						outThreadRounds[1]++;
				}
				// Round 51: my car follows the trap-aware policy. Round 57:
				// rivals use the score-shaped ttf + trap proxy; selected close
				// rivals instead use their recursion-guarded real scorer.
				boolean moved;
				if (awareSelfLeft > 0 && i == myIdx) {
					awareSelfLeft--;
					moved = awareMoveOverState(i, px, py, vx, vy, alive, move, workspace);
				} else if (!awareRivalDone && i == awareRivalIdx) {
					awareRivalDone = true;
					moved = awareMoveOverState(i, px, py, vx, vy, alive, move, workspace);
				} else if (i == myIdx)
					moved = scorerSelf
							? scorerMoveOverState(i, px, py, vx, vy, alive, move, workspace)
							: exactSelf
									? selfMoveOverState(px[i], py[i], vx[i], vy[i], i, px, py, alive, move)
									: greedyMoveOverState(px[i], py[i], vx[i], vy[i], i, px, py, alive, move);
				else if (scorerSet[i])
					moved = scorerMoveOverState(i, px, py, vx, vy, alive, move, workspace,
							!trueRivals);
				else if (exactRivals)
					moved = rivalMoveOverState(px[i], py[i], vx[i], vy[i], i, px, py, alive, move);
				else
					moved = greedyMoveOverState(px[i], py[i], vx[i], vy[i], i, px, py, alive, move);
				if (!moved)
					moved = physicalMoveOverState(i, px, py, vx, vy, alive, move, workspace);
				final RaceGame.MoveResult transition = moved
						? game.evaluateMove(workspace.laps[i], workspace.gates[i], px[i], py[i], move[0], move[1],
								occupiedByOther(move[0], move[1], i, px, py, alive)) : null;
				final boolean timedOut = game.lapGates != null
						&& workspace.turns > (long) game.totalLaps * 750 * game.players.length;
				workspace.turns++;
				if (trace)
					System.err.println("SIMTRACE r=" + round + " i=" + i + " "
							+ (i == myIdx ? (scorerSelf ? "scorerME" : exactSelf ? "selfME" : "greedyME")
									: scorerSet[i] ? (trueRivals ? "TRUE" : "scorer")
											: exactRivals ? "smom" : "greedy")
							+ " (" + px[i] + "," + py[i] + ")v(" + vx[i] + "," + vy[i] + ") -> "
							+ (!moved ? "STUCK"
									: "(" + move[0] + "," + move[1] + ")v(" + move[2] + "," + move[3]
											+ ")" + (timedOut ? " TIMEOUT" : !transition.legal() ? " CRASH"
													: transition.finishes() ? " FINISH" : transition.lapCross() ? " LAP" : "")
											+ " progress=" + transition.lapAfter() + "," + transition.gateAfter()));
				// Round 223: only a FINISHING crossing takes the car off the board
				// -- final lap, nothing owed, in the crosser's own frame; a lap
				// scored or a stray crossing keeps it in the race.
				if (simFinishVanish && !timedOut && moved && transition.finishes()) {
					alive[i] = false;
					liveCount--;
					if (i == myIdx) {
						myFinishRound = round;
						aheadAtMyFinish = rivalsFinished;
						if (outFinalTier != null)
							outFinalTier[0] = 3;
						if (outFieldCost == null) {
							if (simDepth == placeKeyDepth)
								placeKey = rivalsFinished * PLACE_KEY_STRIDE + round;
							return rankVerdict(rivalsFinished, 0);
						}
						myFinished = true;
					} else {
						rivalsFinished++;
					}
					if (liveCount <= terminalLiveCount) {
						raceOver = true;
						break;
					}
					// perf_bnb: a rival's finish that leaves the race on adds a stride.
					if (boundPot != null && i != myIdx && bnbStop(workspace, rivalsFinished, boundBase,
							boundCut, boundMoves, awareSelfLeft))
						return -1;
					continue;
				}
				if (!moved || timedOut || !transition.legal()) {
					if (i == myIdx)
						return -1;
					alive[i] = false;
					liveCount--;
					if (outFieldCost != null)
						failedRivalCost += ROLLOUT_FAILURE_COST;
					// Round 309: in the chooser's own rollout a rival's crash is no win. The forecast's
					// rival is a model and its crash a possibility, not a fact (the duel proof keeps the
					// proven ones); a forecast that ended the race there made the chooser chase phantom
					// wins in duels. The mover races on alone and is ranked by its own time: duels
					// -0.028 +- 0.005 places against round 303's champion, 8-car fields as round 305 alone.
					if (liveCount <= terminalLiveCount && simDepth != placeKeyDepth) {
						raceOver = true;
						break;
					}
					continue;
				}
				workspace.laps[i] = transition.lapAfter();
				workspace.gates[i] = game.lapGates == null ? 0 : transition.gateAfter();
				updateRolloutFrame(workspace, i);
				px[i] = move[0];
				py[i] = move[1];
				vx[i] = move[2];
				vy[i] = move[3];
				// perf_bnb: after the mover's move in this round, rf * S + round + P; where P has
				// no value the base keeps its last value (the mover can then never finish).
				if (boundPot != null && i == myIdx) {
					boundMoves++;
					final int boundP = boundPot.movesToFinish(frameRemaining[i], px[i], py[i], vx[i], vy[i]);
					if (boundP != Integer.MAX_VALUE)
						boundBase = (long) round + boundP;
					if (bnbStop(workspace, rivalsFinished, boundBase, boundCut, boundMoves, awareSelfLeft))
						return -1;
				}
			}
		}
		if (raceOver) {
			// Classification has zero remaining distance, even for a survivor whose
			// next physical move would crash. Preserve costs already incurred, but
			// do not charge phantom future moves or a failure to a surviving rival.
			for (int i = 0; i < game.players.length; i++) {
				if (!alive[i])
					continue;
				alive[i] = false;
				if (i == myIdx) {
					myFinishRound = endRound;
					aheadAtMyFinish = rivalsFinished;
					myFinished = true;
					if (outFinalTier != null)
						outFinalTier[0] = 3;
				}
			}
		}
		if (outFieldCost != null) {
			long fieldCost = failedRivalCost;
			for (int i = 0; i < game.players.length; i++) {
				if (i == myIdx || !alive[i])
					continue;
				final int turns = ttfFor(i, px[i], py[i], vx[i], vy[i]);
				fieldCost += turns == Integer.MAX_VALUE ? ROLLOUT_FAILURE_COST : turns;
			}
			outFieldCost[0] = fieldCost;
		}
		usePlayerFrame(myIdx);
		// Round 65: a surviving-but-fragile final (tier <= 1) was the
		// escalation signal for the 5-7-round doom class; since round 310 only
		// the sim2 query audit (querySimOutcome) asks for it.
		if (outFinalTier != null && !myFinished)
			outFinalTier[0] = safeSuccessorsOverState(px[myIdx], py[myIdx], vx[myIdx], vy[myIdx],
					myIdx, px, py, alive);
		final int myTime = myFinished ? 0 : ttf(px[myIdx], py[myIdx], vx[myIdx], vy[myIdx]);
		if (simDepth == placeKeyDepth)
			placeKey = myFinished
					? aheadAtMyFinish * PLACE_KEY_STRIDE + myFinishRound
					: rivalsFinished * PLACE_KEY_STRIDE + (rounds - 1) + Math.min(myTime, PLACE_KEY_STRIDE / 2);
		return rankVerdict(myFinished ? aheadAtMyFinish : rivalsFinished, myTime);
	}

	/** Danger joint search (round 40, shared champion): if the chosen landing DIES in
	 *  the joint rollout, switch to the surviving candidate with the best
	 *  sim-final turnsToFinish; keep the chosen move in every other case.
	 *  Round 310: the round-232 kinematic confirm is its one caller. The legs only
	 *  the danger block armed went with it -- round 98's thread search, the round
	 *  99-107 corridor, slow-pack, deep-tier and ESC confirms, round 102's forced
	 *  target confirm, round 114's pair and round 128's fast finish-funnel legs;
	 *  the round 133, 175 and 176 speed legs stay. */
	private Direction dangerJointSearch(final int[] pos, final int[] vel, final int playerNum,
			final Direction chosen, final boolean simFinishVanish, final boolean exactSelf,
			final boolean exactRivals, final boolean scorerRivals, final int rounds, final int scorerCap,
			final boolean scorerSelf) {
		final int cvx = vel[0] + chosen.dx, cvy = vel[1] + chosen.dy;
		final int cx = pos[0] + cvx, cy = pos[1] + cvy;
		if (finishingMove(pos[0], pos[1], cx, cy))
			return chosen;
		boolean trueDead = false;
		final int chosenT = simOutcome(cx, cy, cvx, cvy, playerNum, rounds, simFinishVanish, exactSelf,
				exactRivals, scorerRivals, scorerSelf, scorerCap, null);
		if (chosenT >= 0) {
			// Round 133: the vmax overspeed deep check -- every harvest-25
			// slow-track crash is one serpentine2 commitment: accelerating to
			// max-axis 11 on the bottom straight is a 5-9-round joint doom
			// (the reach map holds a solo escape; traffic occupies it). The
			// smom fire carries no tell and even the true confirm worlds read
			// the doomed line alive; the deep suppressed world at the
			// certification cap is the one shipped world that kills it, so
			// the confirm rides it alone (r107 single-world precedent). Armed
			// on ACCELERATION into the band at this depth for every entry
			// path (the commitments route via the deep-pack escalation, not
			// the fallback); measured zero false kills and wall-free. Round 310: both
			// routes are gone; the round-232 kinematic confirm is its one entry now.
			// The doom needs a TRAIN: without a rival close behind or alongside
			// there is nobody to seal the escape rows, and the deep world's
			// pessimism false-killed a lone-runner line on 4-player lemans
			// (golden lemans-s1-4p, outcome-identical but trajectory-diverged).
			// The three commitments carry rivals at Chebyshev 1, 2 and 5.
			final boolean legFastV = Math.max(Math.abs(cvx), Math.abs(cvy)) >= AI1_FASTV_MAX
					&& Math.max(Math.abs(cvx), Math.abs(cvy)) > Math.max(Math.abs(vel[0]),
							Math.abs(vel[1]))
					&& countRivalsWithinCheb(pos[0], pos[1], playerNum, AI1_FASTV_PACK_R) >= 1;
			// Round 175: the hold-overspeed check -- harvest-30's cross-track
			// family HOLDS max-axis 10 down a straight (no acceleration, so
			// the round-133 arm never sees it) and dies 4-7 oracle rounds
			// out; one-unit deviations survive. The CHEAP slow world (smoke
			// shape: 5 rounds, cap 3) kills both reachable commitments and
			// measured ZERO false deads across 1459 probed fires on eight
			// tracks -- cheaper AND cleaner than the certification cap,
			// whose serpentine2 hold false-positives vanish at cap 3.
			// In OR LEAVING the top band: the rand16-s43 sibling commits by
			// DECELERATING 10->9 at the same straight-end (dies @r8, holding
			// 10 survives) -- the cheap world kills it too; only the arm
			// missed it.
			// EXACTLY the 10-band: at max-axis 11-12 the cheap world
			// false-killed a surviving braking line in mixed-front lemans s7
			// (m246, the round-93 pin race) -- that regime belongs to the
			// round-133 cert-cap leg; the harvest-30 commitments all live at
			// 10 (hold) or 9-leaving-10 (decel).
			// Train bar at Chebyshev 3: the commitments carry their pressing
			// rival at 1 (rand16 s31, two adjacent), 3 (s43) -- and the tight
			// bar cuts the speed-10-native cruise flood roughly in half.
			final boolean legHoldV = (Math.max(Math.abs(cvx), Math.abs(cvy)) == AI1_HOLDV_MAX
					|| Math.max(Math.abs(cvx), Math.abs(cvy)) == AI1_HOLDV_MAX - 1
							&& Math.max(Math.abs(vel[0]), Math.abs(vel[1])) >= AI1_HOLDV_MAX)
					&& countRivalsWithinCheb(pos[0], pos[1], playerNum, 3) >= 1;
			// Round 176: the 11-12 HOLD band (accel stays with the round-133
			// leg). lobe5-s35 holds 11 and dies @r4 with every scorer world
			// alive -- but the scorer-8 audit is loud (thread 4/7) and the
			// true world kills. Audit-only s8: its one band DEAD verdict
			// sits in the round-93 pin race, which survives it, so only
			// alive-with-thread>=4 escalates to the true-4 verdict; probe:
			// zero escalations in 282 canon band fires. No train bar -- the
			// lobe5 rival is 11 away; the thread tell is the selectivity.
			final boolean legHold11 = Math.max(Math.abs(cvx), Math.abs(cvy)) >= AI1_FASTV_MAX
					&& Math.max(Math.abs(cvx), Math.abs(cvy)) <= Math.max(Math.abs(vel[0]),
							Math.abs(vel[1]));
			if ((legFastV || legHoldV || legHold11)
					&& trueConfirmDepth < AI1_TRUE_CONFIRM_MAXDEPTH) {
				trueConfirmDepth++;
				try {
					// Round 103: confirms ALWAYS run the certification cap --
					// zigzag s76 m234 is true-alive at cap 3 (the smom flow of
					// the uncapped cars hands the key rival a context where it
					// vacates the kill cell) and true-DEAD at cap 6, matching
					// the offline all-champion roll and the real race.
					final int confirmCap = Math.max(scorerCap, AI1_DEEP_CERT_RIVALS);
					if (legFastV) {
						trueDead = simOutcome(cx, cy, cvx, cvy, playerNum, AI1_DEEP_HORIZON,
								simFinishVanish, exactSelf, exactRivals, true, scorerSelf, false,
								confirmCap, null, null, null) < 0;
					} else if (legHoldV) {
						// Its round-175 verdict memo never hit: every nested compute bumps the
						// epoch before a repeat (0 hits in 497 lookups on four fast courses;
						// review, 2026-09-28).
						trueDead = simOutcome(cx, cy, cvx, cvy, playerNum,
								AI1_DJS_SLOW_ROUNDS, simFinishVanish, exactSelf,
								exactRivals, true, scorerSelf, false,
								AI1_SCORER_MAXRIVALS, null, null, null) < 0;
					} else if (legHold11) {
						final int[] h11Tr = { 0, 0 };
						simOutcome(cx, cy, cvx, cvy, playerNum,
								AI1_DEEP_HORIZON, simFinishVanish, exactSelf, exactRivals,
								true, scorerSelf, false, confirmCap, null, null, h11Tr);
						// Round 177: the s8 verdict is ignored entirely (both
						// worlds false-kill the round-93 pin fire, thread=1);
						// the THREAD level is the separator -- pin 1, the
						// lobe5 siblings 3 and 4, canon 279x0/3x1 -- so the
						// true-4 verdict runs at thread >= 2.
						trueDead = h11Tr[0] >= 2
								&& simOutcome(cx, cy, cvx, cvy, playerNum,
										AI1_TRUE_CONFIRM_ROUNDS, simFinishVanish,
										exactSelf, exactRivals, true, scorerSelf, true,
										confirmCap, null, null, null) < 0;
					}
				} finally {
					trueConfirmDepth--;
				}
				if (AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum)
					System.err.println("AIDBG TRUECONF p=" + playerNum + " pos=(" + pos[0] + ","
							+ pos[1] + ") chosen=" + chosen + " tier=-1 thread=-1" // no audit since round 310
							+ " -> true rivals "
							+ (trueDead ? "KILL @" + AI1_TRUE_CONFIRM_ROUNDS + "r, switching"
									: "keep alive"));
			}
			if (!trueDead)
				return chosen;
		}
		final boolean dbg = AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum;
		if (dbg)
			System.err.println("AIDBG DJS p=" + playerNum + " pos=(" + pos[0] + "," + pos[1] + ") vel=(" + vel[0]
					+ "," + vel[1] + ") chosen=" + chosen + " DIES in-sim");
		Direction best = null;
		int bestT = Integer.MAX_VALUE;
		final boolean[] rejected = new boolean[DIRECTIONS.length];
		for (final Direction d : DIRECTIONS) {
			if (d == chosen)
				continue;
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
				continue;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
			if (finishingMove(pos[0], pos[1], nx, ny))
				return d;
			if (!game.aiMoveLegal(pos[0], pos[1], nx, ny))
				continue;
			if (game.isCrashingPlayer(nx, ny, playerNum))
				continue;
			if (!reach.isAlive(nx, ny, nvx, nvy))
				continue;
			final int t = simOutcome(nx, ny, nvx, nvy, playerNum, rounds, simFinishVanish, exactSelf, exactRivals,
					scorerRivals, scorerSelf, scorerCap, null);
			if (dbg)
				System.err.println("AIDBG DJS  alt " + d + " land=(" + nx + "," + ny + ") simT="
						+ (t < 0 ? "DIES" : String.valueOf(t)));
			if (t >= 0 && t < bestT) {
				bestT = t;
				best = d;
			}
		}
		if (trueDead && best != null) {
			// Round 99: the cheap world proposed the switch target; make the
			// target itself survive the true-rival world too (a cheap-alive
			// but truly-dead escape would trade one crash for another). Walk
			// candidates by cheap sim-final ttf, first true-survivor wins.
			Direction confirmed = null;
			for (int pass = 0; pass < DIRECTIONS.length && confirmed == null; pass++) {
				Direction cand = null;
				int candT = Integer.MAX_VALUE;
				int candSpd = Integer.MAX_VALUE;
				for (final Direction d : DIRECTIONS) {
					if (d == chosen || rejected[d.ordinal()])
						continue;
					final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
					if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
						continue;
					final int nx = pos[0] + nvx, ny = pos[1] + nvy;
					if (!game.aiMoveLegal(pos[0], pos[1], nx, ny)
							|| game.isCrashingPlayer(nx, ny, playerNum)
							|| !reach.isAlive(nx, ny, nvx, nvy)
							|| finishingMove(pos[0], pos[1], nx, ny))
						continue;
					final int t = simOutcome(nx, ny, nvx, nvy, playerNum, rounds, simFinishVanish,
							exactSelf, exactRivals, scorerRivals, scorerSelf, scorerCap, null);
					// Round 105: slower-first -- the shelf invariant governs
					// switch targets too: a fast sibling passing both ladder
					// worlds can still be a depth-7 doom (zandvoort s128).
					final int spd = Math.max(Math.abs(nvx), Math.abs(nvy));
					if (t >= 0 && (spd < candSpd || spd == candSpd && t < candT)) {
						candT = t;
						candSpd = spd;
						cand = d;
					}
				}
				if (cand == null)
					break;
				final int ncvx = vel[0] + cand.dx, ncvy = vel[1] + cand.dy;
				trueConfirmDepth++;
				final boolean survives;
				try {
					survives = simOutcome(pos[0] + ncvx, pos[1] + ncvy, ncvx, ncvy, playerNum,
							AI1_DEEP_HORIZON, simFinishVanish, exactSelf, exactRivals, true,
							scorerSelf, false, Math.max(scorerCap, AI1_DEEP_CERT_RIVALS),
							null, null, null) >= 0
							&& simOutcome(pos[0] + ncvx, pos[1] + ncvy, ncvx, ncvy, playerNum,
									AI1_TRUE_CONFIRM_ROUNDS, simFinishVanish, exactSelf,
									exactRivals, true, scorerSelf, true,
									Math.max(scorerCap, AI1_DEEP_CERT_RIVALS),
									null, null, null) >= 0;
				} finally {
					trueConfirmDepth--;
				}
				if (dbg)
					System.err.println("AIDBG TRUECONF  alt " + cand + " simT=" + candT
							+ (survives ? " true-ALIVE" : " true-DIES"));
				if (survives)
					confirmed = cand;
				else
					rejected[cand.ordinal()] = true;
			}
			// A confirm-capable search must never hand the race to an
			// UNCERTIFIED escape: when every candidate fails the true-rival
			// certification, keep the chosen (spielberg s252 m159: the cheap
			// world false-killed the true survivor E, certification correctly
			// rejected the doomed NE as true-DIES, and the old fallthrough
			// switched into NE anyway -- trading no crash for a crash).
			best = confirmed;
		}
		if (dbg)
			System.err.println("AIDBG DJS  -> " + (best != null ? "SWITCH " + best + " simT=" + bestT
					: "KEEP " + chosen + " (no survivor)"));
		return best != null ? best : chosen;
	}

	private final static double	AI2_MOMENTUM_TIEBREAK	= 0.02;
	private final static double	AI2_PLATEAU_TIEBREAK	= 0.05;

	/** Round 183: per-state successor mask -- bits 16-24 velocity-in-range,
	 *  bits 0-8 in-range AND geometry-legal, per Direction ordinal. Geometry
	 *  is immutable per track, so cached entries never invalidate; the
	 *  direct-mapped table (full-key verify) resets on reach change. One
	 *  probe replaces the nine range checks and nine edge-legality calls of
	 *  every candidate enumeration (49.5%% of all samples pre-round). */
	private int succMask(final int x, final int y, final int vx, final int vy) {
		final int max = RaceGame.AI_MAX_SPEED;
		if (x < 0 || y < 0 || x > game.gameCols || y > game.gameRows
				|| vx < -max || vx > max || vy < -max || vy > max)
			return succMaskCompute(x, y, vx, vy);
		if (smReach != reach) {
			if (smTabGrid == null) {
				smTabGrid = new long[1 << 18];
				smTabNoGrid = new long[1 << 18];
			}
			java.util.Arrays.fill(smTabGrid, -1L);
			java.util.Arrays.fill(smTabNoGrid, -1L);
			smReach = reach;
		}
		// Round 291 (round 286): the legal plane depends on the grid world, which
		// differs between a decider on the grid and one past CP1.
		final long[] tab = game.aiGridLegal ? smTabGrid : smTabNoGrid;
		final int span = 2 * max + 1;
		final int vkey = (vx + max) * span + vy + max;
		final int key = (x * (game.gameRows + 1) + y) * (span * span) + vkey;
		final int slot = key * 0x9E3779B1 >>> 14;
		final long entry = tab[slot];
		// round 184: one interleaved slot (key<<32 | 9-bit legal plane); the
		// velocity-range plane is position-independent and read from the
		// static table instead of being stored per state
		if ((int) (entry >>> 32) == key)
			return RANGE9[vkey] | (int) entry;
		final int legal = succMaskLegal(x, y, vx, vy);
		tab[slot] = (long) key << 32 | legal;
		return RANGE9[vkey] | legal;
	}

	private int succMaskCompute(final int x, final int y, final int vx, final int vy) {
		int mask = 0;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
				continue;
			mask |= 1 << 16 + d.ordinal();
			if (game.aiMoveLegal(x, y, x + nvx, y + nvy))
				mask |= 1 << d.ordinal();
		}
		return mask;
	}

	/** The 9-bit legal plane only (range-plane bits come from RANGE9). */
	private int succMaskLegal(final int x, final int y, final int vx, final int vy) {
		int mask = 0;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
				continue;
			if (game.aiMoveLegal(x, y, x + nvx, y + nvy))
				mask |= 1 << d.ordinal();
		}
		return mask;
	}

	/** Round 184: the velocity-range plane (bits 16-24) per packed (vx,vy). */
	private static final int[] RANGE9 = buildRange9();

	private static int[] buildRange9() {
		final int max = RaceGame.AI_MAX_SPEED;
		final int span = 2 * max + 1;
		final int[] table = new int[span * span];
		for (int vx = -max; vx <= max; vx++)
			for (int vy = -max; vy <= max; vy++) {
				int mask = 0;
				for (final Direction d : DIRECTIONS)
					if (!RaceGame.aiVelocityOutOfRange(vx + d.dx, vy + d.dy))
						mask |= 1 << 16 + d.ordinal();
				table[(vx + max) * span + vy + max] = mask;
			}
		return table;
	}

	private Reachability smReach;
	private long[] smTabGrid, smTabNoGrid;

	private int countRivalsWithinCheb(final int x, final int y, final int playerNum, final int cheb) {
		int count = 0;
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			if (Math.abs(pp[0] - x) <= cheb && Math.abs(pp[1] - y) <= cheb)
				count++;
		}
		return count;
	}

	/** Round 210: a live rival within the radius that is AHEAD of or beside
	 *  me along my heading (dot with my velocity >= -2 speed) -- only such a
	 *  rival can occupy my continuation cell; a car behind me cannot turn my
	 *  needle into a wall. At rest every rival counts. Gating on all rivals
	 *  cost twice the pace for the same crash cut. */
	private boolean rivalAheadWithinCheb(final int x, final int y, final int vx, final int vy,
			final int playerNum, final int cheb) {
		final int sp = Math.max(Math.abs(vx), Math.abs(vy));
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			final int dx = pp[0] - x, dy = pp[1] - y;
			if (Math.abs(dx) > cheb || Math.abs(dy) > cheb)
				continue;
			if (sp == 0 || dx * vx + dy * vy >= -2 * sp)
				return true;
		}
		return false;
	}

	/** Round 214: the exact optimal move for a car with the track to itself (round
	 *  279: the reach-map descent on point-to-point courses), or null when a lap
	 *  race's potential was not built (over budget) or no finite continuation. */
	private Direction optimalAloneMove(final int[] pos, final int[] vel, final int playerNum) {
		final OptimalPotential potential = game.optimalPotential();
		if (potential == null)
			return game.lapGates == null ? reachAloneMove(pos, vel) : null;
		int lapsDone = 0;
		for (final Player p : game.players)
			if (p.getNumber() == playerNum)
				lapsDone = p.getLap();
		return potential.bestMove(game, pos[0], pos[1], vel[0], vel[1],
				OptimalPotential.remainingEvents(lapGate, lapsDone, game.totalLaps));
	}

	/** Round 61: any live opponent within Chebyshev distance {@code cheb} of
	 *  (x,y)? Chebyshev (not d^2) because the safety argument is per-axis:
	 *  max per-axis displacement in one move is |v|+1 <= 13. */
	private boolean rivalWithinCheb(final int x, final int y, final int playerNum, final int cheb) {
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			if (Math.abs(pp[0] - x) <= cheb && Math.abs(pp[1] - y) <= cheb)
				return true;
		}
		return false;
	}

	/** Count live opponents within squared distance r2 of (x,y). */
	private int countNearbyOpponents(final int x, final int y, final int playerNum, final int r2) {
		int count = 0;
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			final int dx = x - pp[0];
			final int dy = y - pp[1];
			if (distanceSquared(dx, dy) <= r2)
				count++;
		}
		return count;
	}

	/**
	 * Count alive 1-step successors of (x,y,vx,vy) that are NOT also predicted
	 * to be occupied by an opponent's next move. Approximates the number of
	 * still-viable continuations after one opponent reaction.
	 */
	private int countFutureSafeSuccessors(final int x, final int y, final int vx, final int vy,
			final int playerNum, final CellOccupancy predicted) {
		int count = 0;
		final int sm = succMask(x, y, vx, vy);
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx;
			final int nvy = vy + d.dy;
			if ((sm & 1 << 16 + d.ordinal()) == 0)
				continue;
			final int nx = x + nvx;
			final int ny = y + nvy;
			// perf_aisearch (exact): the same AND, the frame and landing tests first
			// (lap-aware with a checkpoint owed no crossing counts).
			if ((!lapAware || lapGate == 0 && reach.shedableLanding(nx, ny, nvx, nvy))
					&& game.crossesFinishLegally(x, y, nx, ny))
				return 9;
			if ((sm & 1 << d.ordinal()) == 0)
				continue;
			if (game.isCrashingPlayer(nx, ny, playerNum))
				continue;
			if (predicted.contains(nx, ny))
				continue;
			if (reach.isAlive(nx, ny, nvx, nvy))
				count++;
		}
		return count;
	}

	/**
	 * Shared scorer twin of {@link #countFutureSafeSuccessors} keyed on ROOMINESS
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
	private int countRoomySuccessors(final int x, final int y, final int vx, final int vy) {
		int count = 0;
		// perf_aisearch (exact): the velocity range and aiMoveLegal from succMask.
		final int sm = succMask(x, y, vx, vy);
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx;
			final int nvy = vy + d.dy;
			if ((sm & 1 << 16 + d.ordinal()) == 0)
				continue;
			final int nx = x + nvx;
			final int ny = y + nvy;
			// perf_aisearch (exact): the same AND, the frame and landing tests first
			// (lap-aware with a checkpoint owed no crossing counts).
			if ((!lapAware || lapGate == 0 && reach.shedableLanding(nx, ny, nvx, nvy))
					&& game.crossesFinishLegally(x, y, nx, ny))
				return 9;
			if ((sm & 1 << d.ordinal()) == 0)
				continue;
			if (reach.isAlive(nx, ny, nvx, nvy) && isRoomy(nx, ny, nvx, nvy))
				count++;
		}
		return count;
	}

	/** Rebuild the exact live-cell set once per mobility projection. Only cells
	 * touched by the preceding projection are cleared. */
	private void refreshLiveOccupancy() {
		final int cells = (game.gameCols + 1) * (game.gameRows + 1);
		if (liveOccupancy == null || liveOccupancy.length != cells) {
			liveOccupancy = new byte[cells];
			liveOccupancyTouched = new int[game.players.length];
			liveOccupancyTouchedCount = 0;
		} else {
			for (int i = 0; i < liveOccupancyTouchedCount; i++)
				liveOccupancy[liveOccupancyTouched[i]] = 0;
			liveOccupancyTouchedCount = 0;
		}
		final int h = game.gameRows + 1;
		for (final Player p : game.players) {
			if (p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			if (pp[0] < 0 || pp[1] < 0 || pp[0] > game.gameCols
					|| pp[1] > game.gameRows)
				continue;
			final int index = pp[0] * h + pp[1];
			if (liveOccupancy[index] != 0)
				continue;
			liveOccupancy[index] = 1;
			liveOccupancyTouched[liveOccupancyTouchedCount++] = index;
		}
	}

	/** True iff a live player other than the one at (sx,sy) occupies (nx,ny). */
	private boolean cellOccupiedByLive(final int nx, final int ny, final int sx, final int sy) {
		if (nx == sx && ny == sy)
			return false;
		if (nx < 0 || ny < 0 || nx > game.gameCols || ny > game.gameRows)
			return false;
		return liveOccupancy[nx * (game.gameRows + 1) + ny] != 0;
	}

	/** Round 231: rank the already-permitted checkpoint touches in the successor's own lap
	 * frame. Preserve enum order on equal values and the old choice when the
	 * exact potential cannot price any qualifying continuation. */
	private Direction bestCheckpointMove(final int[] pos, final int[] vel,
			final int playerNum, final int mask, final Direction fallback) {
		Direction best = fallback;
		int bestValue = Integer.MAX_VALUE;
		final int nextGate = lapGate == 1 ? 2 : 0;
		for (final Direction d : DIRECTIONS) {
			final int bit = 1 << d.ordinal();
			if ((mask & bit << 16) == 0 || (mask & bit) == 0)
				continue;
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
			final boolean progress = game.touchesGate(lapGate, pos[0], pos[1], nx, ny)
					&& reach.isAlive(nx, ny, nvx, nvy);
			if (!progress || game.isCrashingPlayer(nx, ny, playerNum)
					|| reach.turnsToGate(nextGate, nx, ny, nvx, nvy) == Integer.MAX_VALUE
					|| !needleHeadway(nx, ny, nvx, nvy, playerNum, nextGate)
					|| robustMode && !reach.isRobust(nextGate, nx, ny, nvx, nvy))
				continue;
			final int events = game.gateEventsOnMove(lapGate, pos[0], pos[1], nx, ny);
			final int value = exactPot.movesToFinish(exactRemaining - events, nx, ny, nvx, nvy);
			if (value < bestValue) {
				bestValue = value;
				best = d;
			}
		}
		if (best != fallback && AI_DEBUG_DJS)
			System.err.println("AIDBG CHECKPOINT-CHOICE p=" + playerNum + " gate=" + lapGate
					+ " " + fallback + " -> " + best + " remaining=" + bestValue);
		return best;
	}

	/** Round 256: among the landings the score cannot separate -- every legal
	 *  landing within AI1_CHOOSER_WINDOW turns of the best score, at most
	 *  AI1_CHOOSER_WIDTH of them, in score order -- choose by the faithful joint
	 *  world (the mover driven by its own scorer, every rival by theirs): the
	 *  lowest time-to-finish after AI1_CHOOSER_ROUNDS rounds wins, a dead
	 *  verdict never beats a live one, and equal verdicts keep the score's
	 *  order. The score ranks landings by facts local to the landing; this
	 *  ranks them by what the whole field actually does next. Round 257
	 *  measured the horizon (3 rounds -0.501, 6 -0.952, 9 -1.129, 12 -1.194
	 *  places, saturating); round 259 found ranking by projected place and a
	 *  wider vote both within noise of this. Round 292b: the pace landing the
	 *  round-34 swap would take is rolled out too when the window left it out. */
	private Direction jointChooser(final int[] pos, final int[] vel, final int playerNum,
			final Direction best, final double[] scoreByDir, final double bestScore,
			final Direction pace) {
		final Direction[] order = new Direction[DIRECTIONS.length];
		int n = 0;
		for (final Direction d : DIRECTIONS) {
			final double s = scoreByDir[d.ordinal()];
			if (s == Double.MAX_VALUE || s > bestScore + AI1_CHOOSER_WINDOW)
				continue;
			int i = n++;
			while (i > 0 && scoreByDir[order[i - 1].ordinal()] > s) {
				order[i] = order[i - 1];
				i--;
			}
			order[i] = d;
		}
		// Round 292b: the pace landing gets a rollout too, after the score's
		// candidates, when the window left it out.
		final int width = Math.min(n, AI1_CHOOSER_WIDTH);
		boolean paceInSet = false;
		for (int k = 0; k < width; k++)
			paceInSet |= order[k] == pace;
		final boolean addPace = pace != null && !paceInSet;
		final Direction[] cands = java.util.Arrays.copyOf(order, width + (addPace ? 1 : 0));
		if (addPace)
			cands[width] = pace;
		if (cands.length < 2)
			return best;
		// perf_aware: the relevant-rival fronts serve this call's landings only.
		if (simDepth == 0 && !inScorerSim && trueConfirmDepth == 0)
			trafficFronts.clear();
		Direction pick = null;
		long pickVerdict = -1;
		long paceVerdict = Long.MIN_VALUE;
		// perf_bnb (exact, tie-preserving; bnbPotential): a later landing whose lower bound
		// passes the live incumbent's verdict STRICTLY is not rolled, or its rollout stops, and
		// counts as dead. Check mode rolls every landing and plays that loop beside this one
		// (bnbPick, bnbPickVerdict, bnbPaceVerdict), comparing the two after it.
		final OptimalPotential boundPot = bnbPotential(playerNum);
		final boolean boundTop = simDepth == 0 && !inScorerSim && trueConfirmDepth == 0;
		Direction bnbPick = null;
		long bnbPickVerdict = -1, bnbPaceVerdict = Long.MIN_VALUE;
		if (PERF_BNB_STATS)
			bnbCount(boundPot != null ? BNB_CALLS : BNB_OFF, 1L);
		for (final Direction d : cands) {
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
			// A finish is already decided by the precedence rules above; a crossing
			// with a lap or a checkpoint still owed is an ordinary move (round 291).
			if (finishingMove(pos[0], pos[1], nx, ny))
				return best;
			// perf_bnb: the cutoff is the live incumbent's verdict (the pruned loop's: outside
			// check mode the real one); P0, the landing's exact distance in the frame after its
			// move, bounds its verdict from below before any rollout.
			long boundCut = Long.MAX_VALUE;
			int boundP0 = Integer.MAX_VALUE;
			boolean boundSkip = false;
			if (boundPot != null) {
				final Direction incumbent = PERF_CHECK ? bnbPick : pick;
				final long incumbentVerdict = PERF_CHECK ? bnbPickVerdict : pickVerdict;
				if (incumbent != null && incumbentVerdict >= 0)
					boundCut = incumbentVerdict;
				if (boundCut != Long.MAX_VALUE || PERF_CHECK) {
					boundP0 = boundPot.movesToFinish(exactRemaining
							- game.gateEventsOnMove(lapGate, pos[0], pos[1], nx, ny), nx, ny, nvx, nvy);
					boundSkip = boundP0 != Integer.MAX_VALUE && boundP0 > boundCut;
				}
				if (PERF_BNB_STATS)
					bnbLandingStats(boundTop, boundCut != Long.MAX_VALUE, boundSkip);
				if (boundSkip && !PERF_CHECK) {
					if (d == pace)
						paceVerdict = -1;
					continue;
				}
			}
			// Round 270/274: a live rollout ranks by place, then by the mover's
			// projected total turns (its finishing round when it finishes).
			final int outerKeyDepth = placeKeyDepth;
			placeKeyDepth = simDepth + 1;
			placeKey = -1;
			// Round 303 (the chooser lab's aware, promoted): in a top-level chooser's forecast
			// the mover's own first continuation and the most-interacting rival's first move
			// play their full policy (-0.150 places on held-out seeds, -0.142 as a lone
			// entrant against round 301c; CPU 2.65x, accepted by the owner). Round 305: the
			// mover's first AI1_AWARE_SELF_MOVES continuation moves (see simOutcomeCore).
			final int outerAwareDepth = awareDepth, outerAwareRival = awareRival;
			if (simDepth == 0 && !inScorerSim && trueConfirmDepth == 0) {
				awareDepth = simDepth + 1;
				awareRival = relevantRival(playerNum, pos, nx, ny, nvx, nvy);
			} else
				awareDepth = -1;
			// Round 281: every live rival plays its scorer in this rollout, at any
			// distance -- not only the three nearest within AI1_SCORER_NEAR, the rest
			// by the smom proxy (-0.172 places on held-out seeds, CPU 1.32x).
			final int outcome;
			allScorerRolloutDepth = simDepth + 1;
			// perf_bnb: the rollout carries the bound under a live incumbent (check mode: always,
			// to verify it); simOutcomeCore takes it at entry.
			final boolean boundRolled = boundPot != null && (boundCut != Long.MAX_VALUE || PERF_CHECK);
			bnbPot = boundRolled ? boundPot : null;
			bnbCutoff = boundCut;
			try {
				outcome = simOutcome(nx, ny, nvx, nvy, playerNum, AI1_CHOOSER_ROUNDS,
						true, true, true, true, true, AI1_SCORER_MAXRIVALS, null);
			} finally {
				allScorerRolloutDepth = -1;
				bnbPot = null;
				bnbCutoff = Long.MAX_VALUE;
			}
			final long key = placeKey;
			placeKeyDepth = outerKeyDepth;
			awareDepth = outerAwareDepth;
			awareRival = outerAwareRival;
			final long verdict = outcome >= 0 && key >= 0 ? key : outcome;
			// perf_bnb: the pruned loop's verdict (dead where the rollout passed the cutoff;
			// outside check mode it stopped there and is dead already), with the stats and
			// check mode's verification of every bound against the verdict.
			final long bnbVerdict = boundRolled
					? bnbAfterRollout(playerNum, d, verdict, boundCut, boundP0, boundSkip, boundTop)
					: verdict;
			if (d == pace)
				paceVerdict = verdict;
			if (pick == null || verdict >= 0 && (pickVerdict < 0 || verdict < pickVerdict)) {
				pick = d;
				pickVerdict = verdict;
			}
			if (PERF_CHECK && boundPot != null) {
				if (d == pace)
					bnbPaceVerdict = bnbVerdict;
				if (bnbPick == null || bnbVerdict >= 0 && (bnbPickVerdict < 0 || bnbVerdict < bnbPickVerdict)) {
					bnbPick = d;
					bnbPickVerdict = bnbVerdict;
				}
			}
		}
		// perf_bnb, check mode: the pruned loop must make the same pick and pace verdict.
		if (PERF_CHECK && boundPot != null) {
			final boolean judged = addPace || paceInSet && paceVerdict != pickVerdict;
			final boolean bnbJudged = addPace || paceInSet && bnbPaceVerdict != bnbPickVerdict;
			if (bnbPick != pick || bnbJudged != judged)
				System.err.println("PERF-AWARE BNB MISMATCH pick p=" + playerNum + " depth=" + simDepth
						+ " pos=(" + pos[0] + "," + pos[1] + ") vel=(" + vel[0] + "," + vel[1] + ") pick="
						+ pick + " bnb=" + bnbPick + " judged=" + judged + " bnbJudged=" + bnbJudged);
		}
		// Round 301a', the rank-first rule (the owner, 2026-10-06): a pace landing the
		// window held and the faithful world ranked strictly worse than the pick is
		// refused too; only an exact tie still goes to the swap's map time.
		chooserJudgedPace = addPace || paceInSet && paceVerdict != pickVerdict;
		return pick == null ? best : pick;
	}

	/** Round 292b: did the last chooser call roll out a pace landing it added
	 *  itself, or (round 301a') rank one it already held strictly worse than its
	 *  pick? Then the pick stands against the round-34 pace swap. */
	private boolean chooserJudgedPace;

	/** perf_bnb (exact, tie-preserving): branch-and-bound on the chooser's landings. A live
	 *  verdict of the chooser's own rollout is rf * S + time (S = PLACE_KEY_STRIDE, rf the
	 *  rivals finished, which only grows): the mover's finishing round; the round a rival's
	 *  finish left it alone, with that rival in rf; or rounds - 1 plus its exact distance at
	 *  the horizon (crashes never end this rollout). The exact potential obeys the rollout's
	 *  referee for the mover: every legal mover move is an edge or a seed of its backward
	 *  search -- the same edge legality and gate events in the frame's remaining events, every
	 *  velocity within AI_MAX_SPEED (each decision returns a direction in range, so the
	 *  physical fallback never moves the mover), every landing in the corridor and the
	 *  corridor on the potential's board (the gate's corridorOnBoard: a drawn loop's rounded
	 *  closure corner can leave it, and then the gate is off), and the grid rule: aiGridLegal
	 *  false forbids every pocket touch, and a course
	 *  without a pocket has none to touch. So the distance P falls by at most one per move,
	 *  never returns from no value to a value, and a finish needs P = 1 first: after the
	 *  mover's move in round r (before its first, r = 0 and P0 at the landing), every
	 *  continuation is dead or at least rf * S + r + P, and a later rival finish adds a
	 *  stride, more than any time part. A landing whose bound is STRICTLY greater than the
	 *  live incumbent's verdict can neither take the pick nor tie it (the incumbent's verdict
	 *  only falls), and its pace verdict differs from the final pick's either way; so it is
	 *  not rolled, or its rollout stops, and counts as dead: pick, pickVerdict and
	 *  chooserJudgedPace are the full loop's, every landing tied with the incumbent or the
	 *  final pick is rolled in full, and so is the first. A skipped rollout's effects are
	 *  restored, rebuilt before they are read, or pure caches (only hit rates change).
	 *  Gated to the potential's domain: a lap course with the potential built, aiGridLegal
	 *  false or no pocket, and a live rival (the rollout cannot start with the race over).
	 *  Off wherever a skipped decision would print (suppressedMovesOn, finish-denial debug).
	 *  -Dai.perf.noBnb=true rolls every landing (the round-310 loop, a same-jar CPU control);
	 *  -Dai.perf.bnbStats=true prints PERF-STATS BNB at exit (in check mode the cuts and
	 *  stops it counts are the ones the pruned loop would make). Under PERF_CHECK every
	 *  landing is rolled in full: every bound is checked against the verdict it bounds and
	 *  the pruned loop's pick against the real one (PERF-AWARE BNB MISMATCH). */
	private static final boolean PERF_NO_BNB = Boolean.getBoolean("ai.perf.noBnb");
	private static final boolean PERF_BNB_STATS = Boolean.getBoolean("ai.perf.bnbStats");
	private static final String[] BNB_STAT_NAMES = {"calls", "off", "offGrid", "landings", "eligible",
			"cut0", "stops", "movesSaved", "topEligible", "topCut0", "topStops", "topAwareSaved",
			"offBoard"};
	private static final int BNB_CALLS = 0, BNB_OFF = 1, BNB_OFF_GRID = 2, BNB_LANDINGS = 3,
			BNB_ELIGIBLE = 4, BNB_CUT0 = 5, BNB_STOPS = 6, BNB_MOVES_SAVED = 7, BNB_TOP_ELIGIBLE = 8,
			BNB_TOP_CUT0 = 9, BNB_TOP_STOPS = 10, BNB_TOP_AWARE_SAVED = 11, BNB_OFF_BOARD = 12;
	private static final java.util.concurrent.atomic.AtomicLongArray BNB_COUNTS =
			PERF_BNB_STATS ? bnbCounters() : null;
	/** perf_bnb: the bound jointChooser hands its next rollout, taken by simOutcomeCore at
	 *  entry when simDepth == placeKeyDepth (only a chooser's own rollout runs there): the
	 *  potential (null: no bound) and the live incumbent's verdict (Long.MAX_VALUE: none). */
	private OptimalPotential bnbPot;
	private long bnbCutoff = Long.MAX_VALUE;
	/** perf_bnb: coursePocketless's verdict and the areas it was computed from. */
	private java.awt.geom.Area bnbPocketZone, bnbPocketTrack;
	private boolean bnbPocketKnown, bnbPocketless;

	/** perf_bnb: the exact potential when it bounds this chooser call's verdicts from below
	 *  (see PERF_NO_BNB), else null. */
	private OptimalPotential bnbPotential(final int playerNum) {
		if (PERF_NO_BNB || exactPot == null || game.lapGates == null || !suppressedMovesOn()
				|| AI_DEBUG_FINISH_DENIAL)
			return null;
		boolean liveRival = false;
		for (final Player p : game.players)
			if (p.getNumber() != playerNum && !p.isFinished())
				liveRival = true;
		if (!liveRival)
			return null;
		if (game.aiGridLegal && !coursePocketless()) {
			if (PERF_BNB_STATS)
				bnbCount(BNB_OFF_GRID, 1L);
			return null;
		}
		// The potential has states only on [0, gameCols] x [0, gameRows]. A lap corridor also
		// closes through its rounded closure corners (RaceGame.extendClosure, lapClosedSide),
		// which no grid check bounds: a drawn loop by the board's edge can hold landings off
		// it, where P has no state and no edge and is no lower bound.
		if (!corridorOnBoard()) {
			if (PERF_BNB_STATS)
				bnbCount(BNB_OFF_BOARD, 1L);
			return null;
		}
		return exactPot;
	}

	/** perf_bnb: corridorOnBoard's verdict and the areas it was computed from. */
	private java.awt.geom.Area bnbBoardTrack, bnbBoardZone;
	private boolean bnbBoardKnown, bnbBoardOn;

	/** perf_bnb: do the corridor and the start zone lie on the potential's board, so that every
	 *  legal landing is one of its states? Computed once per pair of areas, like
	 *  coursePocketless. */
	private boolean corridorOnBoard() {
		final java.awt.geom.Area track = game.trackA, zone = game.startZoneA;
		if (!bnbBoardKnown || track != bnbBoardTrack || zone != bnbBoardZone) {
			bnbBoardOn = track != null && areaOnBoard(track) && (zone == null || areaOnBoard(zone));
			bnbBoardTrack = track;
			bnbBoardZone = zone;
			bnbBoardKnown = true;
		}
		return bnbBoardOn;
	}

	private boolean areaOnBoard(final java.awt.geom.Area area) {
		final java.awt.geom.Rectangle2D b = area.getBounds2D();
		return b.getMinX() > -1 && b.getMinY() > -1
				&& b.getMaxX() < game.gameCols + 1 && b.getMaxY() < game.gameRows + 1;
	}

	/** perf_bnb: does the course have no pocket -- RaceGame.pocketBounds() null, so that
	 *  touchesPocket is false for every move? The same test on the same areas: no start zone
	 *  or corridor, or the start zone minus the corridor empty. Computed once per pair of
	 *  areas (the geometry build assigns new ones; nothing changes one in place). */
	private boolean coursePocketless() {
		final java.awt.geom.Area zone = game.startZoneA, track = game.trackA;
		if (!bnbPocketKnown || zone != bnbPocketZone || track != bnbPocketTrack) {
			boolean empty = true;
			if (zone != null && track != null) {
				final java.awt.geom.Area pocket = new java.awt.geom.Area(zone);
				pocket.subtract(track);
				empty = pocket.isEmpty();
			}
			bnbPocketZone = zone;
			bnbPocketTrack = track;
			bnbPocketless = empty;
			bnbPocketKnown = true;
		}
		return bnbPocketless;
	}

	/** perf_bnb: record the rollout's bound rf * S + base; true when it passes the cutoff and
	 *  the rollout stops. Check mode never stops: it records where the pruned loop would. */
	private static boolean bnbStop(final RolloutWorkspace w, final int rivalsFinished, final long base,
			final long cut, final int moves, final int awareLeft) {
		final long bound = rivalsFinished * PLACE_KEY_STRIDE + base;
		if (bound > w.bnbBound)
			w.bnbBound = bound;
		if (bound <= cut)
			return false;
		if (w.bnbStopMoves < 0) {
			w.bnbStopMoves = moves;
			w.bnbStopAware = awareLeft;
		}
		return !PERF_CHECK;
	}

	/** perf_bnb: after a rollout that carried the bound -- the stats, and in check mode the
	 *  bound's verification; returns the pruned loop's verdict (dead where the bound passed
	 *  the cutoff, before the rollout or during it). */
	private long bnbAfterRollout(final int playerNum, final Direction d, final long verdict,
			final long cut, final int p0, final boolean skipped, final boolean top) {
		final RolloutWorkspace w = rolloutsByDepth[simDepth + 1];
		final boolean stopped = !skipped && w.bnbStopMoves >= 0;
		if (PERF_BNB_STATS && stopped) {
			bnbCount(BNB_STOPS, 1L);
			bnbCount(BNB_MOVES_SAVED, AI1_CHOOSER_ROUNDS - 1 - w.bnbStopMoves);
			if (top) {
				bnbCount(BNB_TOP_STOPS, 1L);
				bnbCount(BNB_TOP_AWARE_SAVED, w.bnbStopAware);
			}
		}
		if (!PERF_CHECK)
			return verdict;
		final long bound = Math.max(p0 == Integer.MAX_VALUE ? -1L : p0, w.bnbBound);
		if (verdict >= 0 && verdict < bound)
			System.err.println("PERF-AWARE BNB MISMATCH bound p=" + playerNum + " depth=" + simDepth
					+ " d=" + d + " verdict=" + verdict + " bound=" + bound + " cutoff="
					+ (cut == Long.MAX_VALUE ? "none" : String.valueOf(cut)));
		return skipped || stopped ? -1L : verdict;
	}

	/** perf_bnb stats: a landing of a call under the bound; whether an incumbent's verdict
	 *  cut it off and whether it was cut before its rollout. */
	private static void bnbLandingStats(final boolean top, final boolean eligible, final boolean cut0) {
		bnbCount(BNB_LANDINGS, 1L);
		if (eligible) {
			bnbCount(BNB_ELIGIBLE, 1L);
			if (top)
				bnbCount(BNB_TOP_ELIGIBLE, 1L);
		}
		if (cut0) {
			bnbCount(BNB_CUT0, 1L);
			bnbCount(BNB_MOVES_SAVED, AI1_CHOOSER_ROUNDS - 1);
			if (top) {
				bnbCount(BNB_TOP_CUT0, 1L);
				bnbCount(BNB_TOP_AWARE_SAVED, AI1_AWARE_SELF_MOVES);
			}
		}
	}

	private static void bnbCount(final int counter, final long amount) {
		if (BNB_COUNTS != null)
			BNB_COUNTS.addAndGet(counter, amount);
	}

	/** perf_bnb stats: the counters, and the shutdown hook that prints them. */
	private static java.util.concurrent.atomic.AtomicLongArray bnbCounters() {
		final java.util.concurrent.atomic.AtomicLongArray counts =
				new java.util.concurrent.atomic.AtomicLongArray(BNB_STAT_NAMES.length);
		Runtime.getRuntime().addShutdownHook(new Thread(() -> {
			final StringBuilder line = new StringBuilder("PERF-STATS BNB");
			for (int k = 0; k < BNB_STAT_NAMES.length; k++)
				line.append(' ').append(BNB_STAT_NAMES[k]).append('=').append(counts.get(k));
			System.err.println(line);
		}, "perf-stats-bnb"));
		return counts;
	}

	/** Round 285 (lab port): one upgraded forecast move -- the car's full,
	 *  unsuppressed policy, its own chooser included. The nested decision
	 *  writes the pace flag the OUTER chooser owns; put it back. */
	private boolean awareMoveOverState(final int i, final int[] px, final int[] py,
			final int[] vx, final int[] vy, final boolean[] alive, final int[] out,
			final RolloutWorkspace rollout) {
		final boolean outerJudgedPace = chooserJudgedPace;
		awareUpgrade = true;
		try {
			return scorerMoveOverState(i, px, py, vx, vy, alive, out, rollout, false);
		} finally {
			awareUpgrade = false;
			chooserJudgedPace = outerJudgedPace;
		}
	}

	/** Round 285: the rival with the strongest two-cycle interaction with the
	 *  mover once it lands on (nx, ny) at (nvx, nvy) -- the lab's relevant car. */
	private int relevantRival(final int playerNum, final int[] pos, final int nx, final int ny,
			final int nvx, final int nvy) {
		final int n = game.players.length;
		final int[] x = new int[n], y = new int[n], vx = new int[n], vy = new int[n];
		final int[] lap = new int[n], gate = new int[n];
		final boolean[] alive = new boolean[n];
		int focal = -1;
		for (int i = 0; i < n; i++) {
			final Player p = game.players[i];
			final int[] q = p.getPosition(), w = p.getVelocity();
			x[i] = q[0]; y[i] = q[1]; vx[i] = w[0]; vy[i] = w[1];
			lap[i] = p.getLap();
			gate[i] = game.lapGates == null ? 0 : p.getNextGate();
			alive[i] = !p.isFinished();
			if (p.getNumber() == playerNum)
				focal = i;
		}
		if (focal < 0)
			return -1;
		final RaceGame.MoveResult landed = game.evaluateMove(lap[focal], gate[focal], pos[0], pos[1],
				nx, ny, false);
		x[focal] = nx; y[focal] = ny; vx[focal] = nvx; vy[focal] = nvy;
		lap[focal] = landed.lapAfter();
		gate[focal] = game.lapGates == null ? 0 : landed.gateAfter();
		final int fast = ChooserTraffic.relevant(game, trafficFronts, x, y, vx, vy, lap, gate, alive,
				focal);
		if (PERF_CHECK) {
			final int original = ChooserTraffic.relevant(game, x, y, vx, vy, lap, gate, alive, focal);
			if (original != fast) {
				System.err.println("PERF-AWARE TRAFFIC MISMATCH p=" + playerNum + " landing=(" + nx + ","
						+ ny + ") fronts=" + fast + " graph=" + original);
				return original;
			}
		}
		return fast;
	}

	/** Round 262: Chebyshev distance to the nearest live rival, or Integer.MAX_VALUE
	 *  when every rival has finished. */
	private int nearestLiveRival(final int[] pos, final int playerNum) {
		int near = Integer.MAX_VALUE;
		for (final Player rival : game.players)
			if (rival.getNumber() != playerNum && !rival.isFinished()) {
				final int[] q = rival.getPosition();
				near = Math.min(near, Math.max(Math.abs(q[0] - pos[0]), Math.abs(q[1] - pos[1])));
			}
		return near;
	}

	/** Round 226: does this car run the candidate branch of a mixed field? False
	 *  for every car unless the game's candidateSlots property names its slot. */
	private boolean candidate(final int playerNum) {
		return game.candidatePolicy(playerNum);
	}

	/** Number of rivals still racing (not finished, not crashed). */
	private int liveRivalsRemaining(final int playerNum) {
		int n = 0;
		for (final Player p : game.players)
			if (p.getNumber() != playerNum && !p.isFinished())
				n++;
		return n;
	}

	/** Round 277: has the mover lapped this rival -- is it a full lap of gate
	 *  events or more behind? Point-to-point races have no laps. */
	private boolean lappedByMover(final Player rival, final int playerNum) {
		if (game.lapGates == null)
			return false;
		for (final Player me : game.players)
			if (me.getNumber() == playerNum)
				return OptimalPotential.remainingEvents(rival.getNextGate(), rival.getLap(), game.totalLaps)
						>= OptimalPotential.remainingEvents(me.getNextGate(), me.getLap(), game.totalLaps) + 3;
		return false;
	}

	/** Round 277: live rivals the mover can still gain or lose a place to. */
	private int placeRivalsRemaining(final int playerNum) {
		int n = 0;
		for (final Player p : game.players)
			if (p.getNumber() != playerNum && !p.isFinished() && !lappedByMover(p, playerNum))
				n++;
		return n;
	}

	/** Round 277: decisiveRival among the rivals the mover has not lapped. */
	private int decisivePlaceRival(final int playerNum) {
		int best = -1, bestDist = Integer.MAX_VALUE;
		for (int i = 0; i < game.players.length; i++) {
			final Player p = game.players[i];
			if (p.getNumber() == playerNum || p.isFinished() || lappedByMover(p, playerNum))
				continue;
			final int[] pp = p.getPosition();
			final int dd = reach.distAt(pp[0], pp[1]);
			if (dd < bestDist) {
				bestDist = dd;
				best = i;
			}
		}
		return best;
	}

	/** The decisive rival to pressure: the live rival nearest the finish (the
	 *  one to beat; in 1v1 the sole rival). Array index, or -1 if none. */
	private int decisiveRival(final int playerNum) {
		int best = -1, bestDist = Integer.MAX_VALUE;
		for (int i = 0; i < game.players.length; i++) {
			final Player p = game.players[i];
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			final int dd = reach.distAt(pp[0], pp[1]);
			if (dd < bestDist) {
				bestDist = dd;
				best = i;
			}
		}
		return best;
	}

	/** Count rival {@code ri}'s viable immediate moves: geometry-legal next
	 *  cells, not my landing (blockX,blockY), not occupied by another live car.
	 *  0 => the rival has no legal move and must crash; 99 => it can finish
	 *  (unsealable). Uses the rival's CURRENT velocity, so it is exact only for
	 *  a rival that has not moved yet this round. */
	private int rivalEscapes(final int ri, final int blockX, final int blockY, final int playerNum) {
		final int[] rp = game.players[ri].getPosition();
		final int[] rv = game.players[ri].getVelocity();
		final int riNum = game.players[ri].getNumber();
		// Round 296: the AI cap binds AI rivals only; a human may take any of
		// the nine accelerations, as RaceAiTactics counts them.
		final boolean capped = game.players[ri].isAi();
		int n = 0;
		for (final Direction d : DIRECTIONS) {
			final int nvx = rv[0] + d.dx, nvy = rv[1] + d.dy;
			if (capped && RaceGame.aiVelocityOutOfRange(nvx, nvy))
				continue;
			final int nx = rp[0] + nvx, ny = rp[1] + nvy;
			if (game.crossesFinishLegally(rp[0], rp[1], nx, ny))
				return 99;
			if (!game.aiMoveLegal(rp[0], rp[1], nx, ny))
				continue;
			if (nx == blockX && ny == blockY)
				continue;
			boolean blocked = false;
			for (final Player q : game.players) {
				if (q.isFinished() || q.getNumber() == playerNum || q.getNumber() == riNum)
					continue;
				final int[] qp = q.getPosition();
				if (qp[0] == nx && qp[1] == ny) {
					blocked = true;
					break;
				}
			}
			if (!blocked)
				n++;
		}
		return n;
	}

	/** Round 197 needle headway: TRUE when a landing may take a lap-gate
	 *  precedence in traffic. Stoppable (both velocity components <= 1: the
	 *  car can park next turn and absorb a queue stall the way a leader
	 *  does), no rival near the landing, or two body-free alive
	 *  continuations proven under CURRENT occupancy. The world-step trap
	 *  ladder predicts rivals vacating -- exactly wrong in a stall wave:
	 *  the first follower above stoppable speed one cell behind a parked
	 *  leader is dead (hybrid20 CP2 pocket: p5/p7 parked and lived, p8
	 *  entered at vy=2 and died). */
	private boolean needleHeadway(final int nx, final int ny, final int nvx, final int nvy,
			final int playerNum, final int gate) {
		if (Math.abs(nvx) <= 1 && Math.abs(nvy) <= 1)
			return true;
		if (!rivalWithinCheb(nx, ny, playerNum, AI1_NEEDLE_RIVAL_R))
			return true;
		// A queue-DEPTH extension (>= 2 stalled rivals within stopping
		// distance, direction-agnostic) was probed here in round 198 and
		// REGRESSED the fleet (hybrid12 1 -> 3, lobe2 0 -> 1, monaco
		// 1 -> 2, rand2 unmoved): heading-blind stall counting brakes for
		// flowing trains -- the place-ceding trap the queue-box v2 note
		// warns about. Deeper queue awareness needs heading, not radius.
		return currentFreeContinuingSuccessors(nx, ny, nvx, nvy, playerNum, gate, 2) >= 2;
	}

	/** Successor landings that are velocity-valid, geometry-legal, body-free
	 *  RIGHT NOW, alive, and -- in lap mode -- able to CONTINUE the lap on
	 *  the given gate map. Surviving is not continuing: a successor that
	 *  cannot reach the next gate is a parking lot, not headway (round 199,
	 *  rand2: a speed-7 crossing's landing counted 2+ alive successors, all
	 *  of them lap-INF threads into a dead upper band, while the single
	 *  certified continuation cell was occupied by the car ahead). A
	 *  successor that itself crosses the S/F while heading for gate 0
	 *  continues on the gate-1 map. A negative {@code gate} would skip the
	 *  continuation requirement, but no caller passes one: round 199 threads
	 *  the post-landing gate through every site, the scorer surcharge included
	 *  (the comment here used to say the surcharge counted alive successors
	 *  only; the shipped round priced continuation there too).
	 *  Early-exits at {@code cap}. */
	private int currentFreeContinuingSuccessors(final int x, final int y, final int vx, final int vy,
			final int playerNum, final int gate, final int cap) {
		int n = 0;
		// perf_aisearch (exact): the velocity range and aiMoveLegal from succMask.
		final int sm = succMask(x, y, vx, vy);
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if ((sm & 1 << 16 + d.ordinal()) == 0)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if ((sm & 1 << d.ordinal()) == 0
					|| game.isCrashingPlayer(nx, ny, playerNum)
					|| !reach.isAlive(nx, ny, nvx, nvy))
				continue;
			if (gate >= 0 && lapAware
					&& reach.turnsToGate(gate, nx, ny, nvx, nvy) == Integer.MAX_VALUE
					&& !(gate == 0 && reach.turnsToGate(1, nx, ny, nvx, nvy) != Integer.MAX_VALUE
							&& game.crossesFinishLegally(x, y, nx, ny))) // perf_aisearch: map test first
				continue;
			if (++n >= cap)
				return n;
		}
		return n;
	}

	/** Round 276: has this car passed its first checkpoint (lap races), or left
	 *  the grid (point-to-point races, which have none)? */
	private boolean passedFirstCheckpoint(final int playerNum) {
		for (final Player p : game.players)
			if (p.getNumber() == playerNum)
				return game.lapGates != null ? p.getLap() > 0 || p.getNextGate() != 1 : !game.gridLegalFor(p);
		return true;
	}

	/** Round 296: the next owed gate after {@code events} gate events from
	 *  {@code gate} (1, 2, 0, 1, ...). */
	private static int gateAfter(int gate, final int events) {
		for (int e = 0; e < events; e++)
			gate = gate == 1 ? 2 : gate == 2 ? 0 : 1;
		return gate;
	}

	/** Round 296: ttfFor at the landing of a move from (x,y) with the gate
	 *  events the move collects paid -- the landing owes them no more, as
	 *  bestCheckpointMove and the private lane price it (the third review,
	 *  2026-09-29: a landing past an owed checkpoint read as owing it again). */
	private int ttfForAfter(final int idx, final int x, final int y, final int nx, final int ny,
			final int nvx, final int nvy) {
		if (exactPot == null || game.lapGates == null)
			return ttfFor(idx, nx, ny, nvx, nvy);
		final int events = game.gateEventsOnMove(frameGate[idx], x, y, nx, ny);
		return events == 0 ? ttfFor(idx, nx, ny, nvx, nvy)
				: exactPot.movesToFinish(frameRemaining[idx] - events, nx, ny, nvx, nvy);
	}

	/** Round 296: does this move finish player idx's race, a checkpoint touched
	 *  on the way included? crossingCountsFor needs every checkpoint collected
	 *  before the move. */
	private boolean finishesFor(final int idx, final int x, final int y, final int nx, final int ny) {
		// perf_aisearch (exact): a move collects at most three gate events (CP1, CP2,
		// the line), so with more owed it finishes nothing and the crossing is not asked.
		return (game.lapGates == null || frameRemaining[idx] <= 3)
				&& game.crossesFinishLegally(x, y, nx, ny) && (game.lapGates == null
				|| game.gateEventsOnMove(frameGate[idx], x, y, nx, ny) >= frameRemaining[idx]);
	}

	/** Round 296: the one-move lookahead from a candidate landing in the frame
	 *  AFTER the candidate's move (next gate, remaining events), each successor
	 *  paying the gate events it collects. searchMinTurnsCountedSoft3 at one
	 *  level, in that frame: the same prices, plateau count and crossing
	 *  precedence (a finish, or a counted lap crossing). */
	private double[] searchCountedAfter(final int x, final int y, final int vx, final int vy,
			final CellOccupancy occupancy, final int gate, final int remaining) {
		double best = Double.MAX_VALUE;
		int countAtMin = 0;
		final int sm = succMask(x, y, vx, vy);
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if ((sm & 1 << 16 + d.ordinal()) == 0)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			// perf_aisearch (exact): a move collects at most three gate events, so the
			// precedence below needs remaining <= 3 or gate == 0.
			if ((remaining <= 3 || gate == 0) && game.crossesFinishLegally(x, y, nx, ny)) {
				final int events = game.gateEventsOnMove(gate, x, y, nx, ny);
				if (events >= remaining || remaining <= 1
						|| gate == 0 && reach.shedableLanding(nx, ny, nvx, nvy))
					return new double[]{1, 9 };
			}
			if ((sm & 1 << d.ordinal()) == 0)
				continue;
			final double price = occupancy.contains(nx, ny) ? 3.0 : 0.0;
			final int t = exactPot.movesToFinish(remaining - game.gateEventsOnMove(gate, x, y, nx, ny),
					nx, ny, nvx, nvy);
			if (t == Integer.MAX_VALUE)
				continue;
			final double total = 1.0 + price + t;
			if (total < best) {
				best = total;
				countAtMin = 1;
			} else if (total == best)
				countAtMin++;
		}
		return new double[]{best, countAtMin };
	}

	/** Round 279 (round 272): does this move FINISH the race for the car whose
	 *  frame is active? In lap mode a crossing with a lap or a checkpoint still
	 *  owed is an ordinary move and must pass the ordinary landing checks. */
	private boolean finishingMove(final int x, final int y, final int nx, final int ny) {
		// perf_aisearch (exact): a move collects at most three gate events (CP1, CP2,
		// the line), so with more owed it finishes nothing and the crossing is not asked.
		return (game.lapGates == null || exactRemaining <= 3)
				&& game.crossesFinishLegally(x, y, nx, ny) && (game.lapGates == null
				|| game.gateEventsOnMove(lapGate, x, y, nx, ny) >= exactRemaining);
	}

	/** Round 279 (round 275): the single-player optimum on a point-to-point
	 *  course. No exact potential is built without lap gates, but the
	 *  reachability map is the exact distance to the one crossing, so the same
	 *  descent applies: a legal finishing move if there is one, otherwise the
	 *  legal landing the map puts closest to the line. */
	private Direction reachAloneMove(final int[] pos, final int[] vel) {
		Direction best = null;
		int bestValue = Integer.MAX_VALUE;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
				continue;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
			if (game.crossesFinishLegally(pos[0], pos[1], nx, ny))
				return d;
			if (!game.aiMoveLegal(pos[0], pos[1], nx, ny))
				continue;
			final int value = reach.turnsToFinish(nx, ny, nvx, nvy);
			if (value < bestValue) {
				bestValue = value;
				best = d;
			}
		}
		return best;
	}

	/** Finish precedence mirrors the main candidate scan: a velocity-range-valid
	 * crossing wins before ordinary geometry or body legality is considered. */
	private Direction immediateFinishMove(final int[] pos, final int[] vel) {
		for (final Direction d : DIRECTIONS) {
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
				continue;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
			if (game.crossesFinishLegally(pos[0], pos[1], nx, ny))
				return d;
		}
		return null;
	}

	/** A safe move of mine (alive, non-crashing, not self-sealable) that leaves
	 *  rival {@code ri} with zero legal moves -- forcing its crash this turn --
	 *  or null if none exists. */
	private Direction findForcedCrashMove(final int[] pos, final int[] vel, final int ri, final int playerNum) {
		for (final Direction d : DIRECTIONS) {
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
				continue;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
			if (game.crossesFinishLegally(pos[0], pos[1], nx, ny))
				continue;
			if (!game.aiMoveLegal(pos[0], pos[1], nx, ny))
				continue;
			if (game.isCrashingPlayer(nx, ny, playerNum))
				continue;
			if (!reach.isAlive(nx, ny, nvx, nvy))
				continue;
			if (sealable(nx, ny, nvx, nvy, playerNum))
				continue;
			if (rivalEscapes(ri, nx, ny, playerNum) == 0)
				return d;
		}
		return null;
	}

	/** Full physical opponent states cannot be packed into five velocity bits:
	 *  a legal human reply may accelerate beyond the AI planning cap. */
	static record EndgameState(int mx, int my, int mvx, int mvy,
			int rx, int ry, int rvx, int rvy, int depth, boolean rivalTurn) {}

	private java.util.HashMap<EndgameState, Boolean> egMemo;
	private int									egNodes;

	/** Speed round 2, patch endgame (exact): the solver's memo as a primitive table
	 *  (E2) and each car state's crossing, legality and alive verdicts as lazily
	 *  filled bit masks (R4). Both live for one solve: the memo object a solve
	 *  starts with is the generation token (egSync opens a new generation whenever
	 *  egMemo holds another object), so no entry outlives a solve, a query or a
	 *  test's reset of egMemo. A memo key outside the packed domain stays in
	 *  egMemo; a car state outside the mask domain asks the game directly. Within
	 *  a solve the table answers every lookup as egMemo would (each key is stored
	 *  at most once, nothing is dropped, the packing is injective), and a mask bit
	 *  is the predicate's value on its edge: aiGridLegal is in the mask key and
	 *  nothing in the search writes it or the geometry and maps. Memory: E2 grows
	 *  to at most 2^17 slots (2 MiB; at most AI1_EG_NODES + 1 stores per solve at
	 *  load <= 1/2) and is reused; R4 is a fixed 2^14 slots (320 KiB).
	 *  -Dai.perf.noEndgameTable=true sends every node to egMemo and the direct
	 *  calls. Under PERF_CHECK egMemo and the direct calls stay the authority: the
	 *  table and the masks are compared at every lookup and a difference prints a
	 *  PERF-AWARE ENDGAME MISMATCH line. */
	private static final boolean PERF_NO_EG_TABLE = Boolean.getBoolean("ai.perf.noEndgameTable");
	/** The egMemo object the current generation belongs to (a sentinel before the first). */
	private Object egOwner = new Object();
	/** The current generation, >= 1 once a node has run: a zero stamp is an empty slot. */
	private int egGeneration;
	/** E2: open addressing with linear probing. Slot s holds the key (egKeyA[s], egKeyB[s])
	 *  while egStamp[s] >>> 1 is the current generation; the stamp's bit 0 is the
	 *  verdict. egSize counts this generation's entries; egMask is the capacity - 1. */
	private long[] egKeyA;
	private int[] egKeyB, egStamp;
	private int egSize, egMask;
	/** R4: 2^EGM_BITS direct-mapped slots, each a car state's key, its mask word and the
	 *  generation that wrote it. A mask word holds, per predicate (offset EGM_CROSS,
	 *  EGM_LEGAL or EGM_ALIVE), nine known bits and, nine bits above them, nine
	 *  verdict bits; bit = the move's Direction ordinal. */
	private static final int EGM_BITS = 14, EGM_CROSS = 0, EGM_LEGAL = 18, EGM_ALIVE = 36;
	private long[] egmKey, egmVal;
	private int[] egmStamp;

	/** Opens a new generation when egMemo holds another object than the last node
	 *  saw: every search allocates a fresh one, tests assign their own. */
	private void egSync() {
		if (egMemo == egOwner)
			return;
		if (egmKey == null && !PERF_NO_EG_TABLE) {
			final long[] keys = new long[1 << EGM_BITS], words = new long[1 << EGM_BITS];
			final int[] stamps = new int[1 << EGM_BITS];
			egmKey = keys;
			egmVal = words;
			egmStamp = stamps;
		}
		egOwner = egMemo;
		egSize = 0;
		if (++egGeneration >= 1 << 30) {	// the E2 stamp is generation << 1 | verdict
			egGeneration = 1;
			if (egStamp != null)
				java.util.Arrays.fill(egStamp, 0);
			if (egmStamp != null)
				java.util.Arrays.fill(egmStamp, 0);
		}
	}

	/** E2's domain, a function of the key alone: cells 0..4095, my velocity within
	 *  +-12 (the AI cap), the rival's within 16 bits, depth 0..31. */
	private static boolean egInTable(final int mx, final int my, final int mvx, final int mvy,
			final int rx, final int ry, final int rvx, final int rvy, final int depth) {
		return !PERF_NO_EG_TABLE && (mx | my | rx | ry) >>> 12 == 0 && depth >>> 5 == 0
				&& mvx >= -12 && mvx <= 12 && mvy >= -12 && mvy <= 12
				&& (rvx + 32768 | rvy + 32768) >>> 16 == 0;
	}

	/** E2 key, first word (with egPackB injective on egInTable's domain). */
	private static long egPackA(final int mx, final int my, final int mvx, final int mvy,
			final int rx, final int ry, final int depth, final boolean rivalTurn) {
		return mx | (long) my << 12 | (long) rx << 24 | (long) ry << 36 | (long) (mvx + 12) << 48
				| (long) (mvy + 12) << 53 | (long) depth << 58 | (rivalTurn ? Long.MIN_VALUE : 0L);
	}

	/** E2 key, second word: the rival's velocity as two 16-bit fields. */
	private static int egPackB(final int rvx, final int rvy) {
		return (rvx & 0xFFFF) << 16 | (rvy & 0xFFFF);
	}

	/** E2 hash: the splitmix64 finalizer of keyA ^ keyB * golden ratio. */
	private static int egHash(final long a, final int b) {
		long h = a ^ (b & 0xFFFFFFFFL) * 0x9E3779B97F4A7C15L;
		h = (h ^ h >>> 30) * 0xBF58476D1CE4E5B9L;
		h = (h ^ h >>> 27) * 0x94D049BB133111EBL;
		return (int) (h ^ h >>> 31);
	}

	/** E2 lookup: 1 or 0 for a stored win or loss, -1 for an absent key. */
	private int egFind(final long a, final int b) {
		if (egKeyA == null)
			return -1;
		for (int s = egHash(a, b) & egMask;; s = s + 1 & egMask) {
			final int stamp = egStamp[s];
			if (stamp >>> 1 != egGeneration)
				return -1;		// an empty slot ends the probe: nothing is removed
			if (egKeyA[s] == a && egKeyB[s] == b)
				return stamp & 1;
		}
	}

	/** E2 store. It probes afresh (the recursion since the lookup may have grown the
	 *  table) and doubles the table before the load would pass one half. */
	private void egPut(final long a, final int b, final boolean win) {
		if (egKeyA == null)
			egRehash(1 << 12);
		else if ((egSize + 1) * 2 > egKeyA.length)
			egRehash(egKeyA.length << 1);
		final int stamp = egGeneration << 1 | (win ? 1 : 0);
		int s = egHash(a, b) & egMask;
		for (; egStamp[s] >>> 1 == egGeneration; s = s + 1 & egMask)
			if (egKeyA[s] == a && egKeyB[s] == b) {
				egStamp[s] = stamp;		// a stored key takes the new verdict, as a map's put does
				return;
			}
		egKeyA[s] = a;
		egKeyB[s] = b;
		egStamp[s] = stamp;
		egSize++;
	}

	/** E2: new arrays of the given capacity holding this generation's entries. */
	private void egRehash(final int capacity) {
		final long[] keysA = new long[capacity];
		final int[] keysB = new int[capacity], stamps = new int[capacity];
		final int mask = capacity - 1;
		if (egKeyA != null)
			for (int i = 0; i < egKeyA.length; i++)
				if (egStamp[i] >>> 1 == egGeneration) {
					int s = egHash(egKeyA[i], egKeyB[i]) & mask;
					while (stamps[s] != 0)
						s = s + 1 & mask;
					keysA[s] = egKeyA[i];
					keysB[s] = egKeyB[i];
					stamps[s] = egStamp[i];
				}
		egKeyA = keysA;
		egKeyB = keysB;
		egStamp = stamps;
		egMask = mask;
	}

	/** R4 key of a car state, with the grid flag the legality verdicts read; -1
	 *  outside the packed domain (cells 0..65535, velocities -1024..1023). */
	private long egmKeyOf(final int x, final int y, final int vx, final int vy) {
		if (PERF_NO_EG_TABLE || (x | y) >>> 16 != 0 || (vx + 1024 | vy + 1024) >>> 11 != 0)
			return -1L;
		return x | (long) y << 16 | (long) (vx + 1024) << 32 | (long) (vy + 1024) << 43
				| (game.aiGridLegal ? 1L << 54 : 0L);
	}

	/** R4 slot of a key, -1 for none. */
	private static int egmSlot(final long key) {
		return key < 0 ? -1 : (int) (key * 0x9E3779B97F4A7C15L >>> 64 - EGM_BITS);
	}

	/** The mask word the slot holds for key in this generation, else 0: nothing known. */
	private long egmLoad(final int slot, final long key) {
		return slot >= 0 && egmStamp[slot] == egGeneration && egmKey[slot] == key ? egmVal[slot] : 0L;
	}

	/** R4: the mask word with predicate kind known for move b of the car state at
	 *  (x, y) whose move lands on (nx, ny) with velocity (nvx, nvy). Asks the game,
	 *  records the verdict and rewrites the slot (a state another node parked there
	 *  meanwhile only loses its bits). Called for an unknown bit, and under
	 *  PERF_CHECK for every bit: a known verdict that differs from the game's is
	 *  reported and replaced by the game's. */
	private long egmAsk(final long mask, final int kind, final int b, final int slot, final long key,
			final int x, final int y, final int nx, final int ny, final int nvx, final int nvy) {
		final boolean direct = kind == EGM_CROSS ? game.crossesFinishLegally(x, y, nx, ny)
				: kind == EGM_LEGAL ? game.aiMoveLegal(x, y, nx, ny) : reach.isAlive(nx, ny, nvx, nvy);
		final long known = 1L << kind + b, verdict = known << 9;
		if ((mask & known) != 0) {
			final boolean cached = (mask & verdict) != 0;
			if (cached == direct)
				return mask;
			egmReport(kind, x, y, nx, ny, cached, direct);
		}
		final long next = direct ? mask | known | verdict : (mask | known) & ~verdict;
		if (slot >= 0) {
			egmKey[slot] = key;
			egmVal[slot] = next;
			egmStamp[slot] = egGeneration;
		}
		return next;
	}

	/** PERF_CHECK: a mask bit that differs from the game's verdict. */
	private static void egmReport(final int kind, final int x, final int y, final int nx, final int ny,
			final boolean cached, final boolean direct) {
		System.err.println("PERF-AWARE ENDGAME MISMATCH mask edge=(" + x + "," + y + ")->(" + nx + "," + ny
				+ ") kind=" + (kind == EGM_CROSS ? "cross" : kind == EGM_LEGAL ? "legal" : "alive")
				+ " cached=" + cached + " direct=" + direct);
	}

	/** PERF_CHECK: the table must answer a packed key as egMemo does. */
	private void egCheckMemo(final EndgameState key, final Boolean map, final long a, final int b) {
		final int table = egFind(a, b), want = map == null ? -1 : map ? 1 : 0;
		if (table != want)
			System.err.println("PERF-AWARE ENDGAME MISMATCH memo key=(" + key.mx() + "," + key.my() + ","
					+ key.mvx() + "," + key.mvy() + "," + key.rx() + "," + key.ry() + "," + key.rvx() + ","
					+ key.rvy() + "," + key.depth() + "," + (key.rivalTurn() ? "rival" : "my") + ") table="
					+ egVerdictName(table) + " map=" + egVerdictName(want));
	}

	private static String egVerdictName(final int verdict) {
		return verdict < 0 ? "none" : verdict == 1 ? "true" : "false";
	}

	/** Lever 5 (round 43, shared champion): 1v1 exact endgame solver. When the sole
	 *  live rival and I are both within {@link #AI1_EG_ETA} turns of the
	 *  finish, run a boolean paranoid minimax over the joint state (strict
	 *  me/rival alternation -- exact for two live movers regardless of index
	 *  order; landing-cell blocking, the campaign's board convention) to
	 *  {@link #AI1_EG_DEPTH} rounds. Returns the FASTEST move with a
	 *  guaranteed win (I cross first, or the rival is forced to crash while
	 *  my state stays alive) or null. A blown node budget claims nothing. */
	private Direction endgameSolve(final int[] pos, final int[] vel, final int playerNum) {
		final int ri = decisiveRival(playerNum);
		// The minimax key has no progress ledger. It is sound only when
		// BOTH racers owe just their final S/F crossing; being near the next
		// gate is not being near victory when the exact potential is absent.
		if (ri < 0 || lapAware || frameLapAware[ri] || game.raceTurnLimitReached())
			return null;
		final int myT = ttf(pos[0], pos[1], vel[0], vel[1]);
		final int[] rp = game.players[ri].getPosition(), rv = game.players[ri].getVelocity();
		final int rT = ttfFor(ri, rp[0], rp[1], rv[0], rv[1]);
		if (myT > AI1_EG_ETA || rT > AI1_EG_ETA)
			return null;
		// perf (upmemo C3, exact): past the guards the search is a function of the root and
		// the race world, so a root met again -- mostly the top-level solve an upgraded
		// forecast move already made -- replays its result (egResultFind).
		final int egKnown = egResultFind(playerNum, ri, pos, vel, rp, rv);
		if (egKnown != RaceAiMoveMemo.MISS && !PERF_CHECK)
			return RaceAiMoveMemo.move(egKnown);
		final Direction solved = endgameSearch(pos, vel, rp, rv);
		egResultRecord(egKnown, playerNum, solved);
		return solved;
	}

	/** endgameSolve's search past its guards (split out unchanged for upmemo C3): a fresh
	 *  memo and node count, the mover's moves in Direction order, the fastest proven win;
	 *  null when none is proven or the node budget blows. */
	private Direction endgameSearch(final int[] pos, final int[] vel, final int[] rp, final int[] rv) {
		egMemo = new java.util.HashMap<>();
		egNodes = 0;
		Direction best = null;
		int bestT = Integer.MAX_VALUE;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
				continue;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
			if (game.crossesFinishLegally(pos[0], pos[1], nx, ny))
				return d;		// immediate finish: the fastest win there is
			if (!game.aiMoveLegal(pos[0], pos[1], nx, ny))
				continue;
			if (nx == rp[0] && ny == rp[1])
				continue;
			if (!reach.isAlive(nx, ny, nvx, nvy))
				continue;
			final int t = ttf(nx, ny, nvx, nvy);
			if (best != null && t >= bestT)
				continue;		// only a strictly faster win can improve
			if (egRival(nx, ny, nvx, nvy, rp[0], rp[1], rv[0], rv[1], AI1_EG_DEPTH * 2 - 1)) {
				best = d;
				bestT = t;
			}
			if (egNodes > AI1_EG_NODES)
				return null;	// budget blown mid-search: results untrusted
		}
		return best;
	}

	/** Rival ply: TRUE iff my win survives EVERY legal rival reply (worst
	 *  case; suicidal blocking lines included -- only geometry and my body
	 *  restrict it). A boxed rival crashes: my win iff my state is alive.
	 *  Speed round 2 (exact): the memo is the E2 table for a key in its domain
	 *  (egMemo otherwise), and the rival state's crossing and legality verdicts
	 *  come from its R4 mask, each asked of the game where this loop asks it, at
	 *  most once per solve while its slot keeps the state; the tests and breaks
	 *  keep their order. */
	private boolean egRival(final int mx, final int my, final int mvx, final int mvy,
			final int rx, final int ry, final int rvx, final int rvy, final int depth) {
		egNodes++;
		// The referee retires the mover before accepting another acceleration.
		// Projected depth fixes the clock relative to this search's root.
		if (endgameTimedOut(depth))
			return true;
		if (depth <= 0)
			return false;		// horizon: no guarantee
		egSync();
		final boolean inTable = egInTable(mx, my, mvx, mvy, rx, ry, rvx, rvy, depth);
		final long keyA = inTable ? egPackA(mx, my, mvx, mvy, rx, ry, depth, true) : 0L;
		final int keyB = inTable ? egPackB(rvx, rvy) : 0;
		EndgameState key = null;
		if (!inTable || PERF_CHECK) {
			key = new EndgameState(mx, my, mvx, mvy, rx, ry, rvx, rvy, depth, true);
			final Boolean memo = egMemo.get(key);
			if (inTable)
				egCheckMemo(key, memo, keyA, keyB);
			if (memo != null)
				return memo;
		} else {
			final int memo = egFind(keyA, keyB);
			if (memo >= 0)
				return memo == 1;
		}
		final long stateKey = egmKeyOf(rx, ry, rvx, rvy);
		final int slot = egmSlot(stateKey);
		long mask = egmLoad(slot, stateKey);
		boolean anyMove = false;
		boolean win = true;
		for (final Direction d : DIRECTIONS) {
			if (egNodes > AI1_EG_NODES) {
				win = false;	// budget: conservative, claim nothing
				break;
			}
			// Opponents are constrained by physics, never by our search cap.
			final int nvx = rvx + d.dx, nvy = rvy + d.dy;
			final int nx = rx + nvx, ny = ry + nvy, b = d.ordinal();
			if (PERF_CHECK || (mask & 1L << EGM_CROSS + b) == 0)
				mask = egmAsk(mask, EGM_CROSS, b, slot, stateKey, rx, ry, nx, ny, nvx, nvy);
			if ((mask & 1L << EGM_CROSS + 9 + b) != 0) {
				win = false;	// rival crosses first
				anyMove = true;
				break;
			}
			if (PERF_CHECK || (mask & 1L << EGM_LEGAL + b) == 0)
				mask = egmAsk(mask, EGM_LEGAL, b, slot, stateKey, rx, ry, nx, ny, nvx, nvy);
			if ((mask & 1L << EGM_LEGAL + 9 + b) == 0)
				continue;
			if (nx == mx && ny == my)
				continue;
			anyMove = true;
			if (!egMy(mx, my, mvx, mvy, nx, ny, nvx, nvy, depth - 1)) {
				win = false;
				break;
			}
		}
		if (!anyMove)
			win = reach.isAlive(mx, my, mvx, mvy);
		if (key != null)
			egMemo.put(key, win);
		if (inTable)
			egPut(keyA, keyB, win);
		return win;
	}

	/** My ply: TRUE iff some alive (or finishing) move of mine keeps the
	 *  guaranteed win alive. Speed round 2 (exact): the memo as in egRival; my
	 *  state's R4 mask answers the crossing, legality and alive-landing tests. */
	private boolean egMy(final int mx, final int my, final int mvx, final int mvy,
			final int rx, final int ry, final int rvx, final int rvy, final int depth) {
		egNodes++;
		if (endgameTimedOut(depth) || depth <= 0)
			return false;
		egSync();
		final boolean inTable = egInTable(mx, my, mvx, mvy, rx, ry, rvx, rvy, depth);
		final long keyA = inTable ? egPackA(mx, my, mvx, mvy, rx, ry, depth, false) : 0L;
		final int keyB = inTable ? egPackB(rvx, rvy) : 0;
		EndgameState key = null;
		if (!inTable || PERF_CHECK) {
			key = new EndgameState(mx, my, mvx, mvy, rx, ry, rvx, rvy, depth, false);
			final Boolean memo = egMemo.get(key);
			if (inTable)
				egCheckMemo(key, memo, keyA, keyB);
			if (memo != null)
				return memo;
		} else {
			final int memo = egFind(keyA, keyB);
			if (memo >= 0)
				return memo == 1;
		}
		final long stateKey = egmKeyOf(mx, my, mvx, mvy);
		final int slot = egmSlot(stateKey);
		long mask = egmLoad(slot, stateKey);
		boolean win = false;
		for (final Direction d : DIRECTIONS) {
			if (egNodes > AI1_EG_NODES)
				break;
			final int nvx = mvx + d.dx, nvy = mvy + d.dy;
			if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
				continue;
			final int nx = mx + nvx, ny = my + nvy, b = d.ordinal();
			if (PERF_CHECK || (mask & 1L << EGM_CROSS + b) == 0)
				mask = egmAsk(mask, EGM_CROSS, b, slot, stateKey, mx, my, nx, ny, nvx, nvy);
			if ((mask & 1L << EGM_CROSS + 9 + b) != 0) {
				win = true;
				break;
			}
			if (PERF_CHECK || (mask & 1L << EGM_LEGAL + b) == 0)
				mask = egmAsk(mask, EGM_LEGAL, b, slot, stateKey, mx, my, nx, ny, nvx, nvy);
			if ((mask & 1L << EGM_LEGAL + 9 + b) == 0)
				continue;
			if (nx == rx && ny == ry)
				continue;
			if (PERF_CHECK || (mask & 1L << EGM_ALIVE + b) == 0)
				mask = egmAsk(mask, EGM_ALIVE, b, slot, stateKey, mx, my, nx, ny, nvx, nvy);
			if ((mask & 1L << EGM_ALIVE + 9 + b) == 0)
				continue;
			if (egRival(nx, ny, nvx, nvy, rx, ry, rvx, rvy, depth - 1)) {
				win = true;
				break;
			}
		}
		if (key != null)
			egMemo.put(key, win);
		if (inTable)
			egPut(keyA, keyB, win);
		return win;
	}

	/** Root is our move at depth 2*AI1_EG_DEPTH. Retired roster slots
	 *  consume no turns; the original roster still sets the timeout limit. */
	private boolean endgameTimedOut(final int depth) {
		return game.lapGates != null && (long) game.turnCount() + 2L * AI1_EG_DEPTH - depth
				> (long) game.totalLaps * 750 * game.players.length;
	}

	/** TRUE iff state (x,y,vx,vy) is SEALABLE: opponents can jointly occupy
	 *  every escape (geometry-legal alive successor) with DISTINCT cars whose
	 *  landings are geometry-legal for them (worst-case physics, matching via
	 *  Kuhn). A finishing escape is never sealable. */
	private boolean sealable(final int x, final int y, final int vx, final int vy, final int playerNum) {
		int escapeCount = 0;
		// perf_aisearch (exact): the velocity range and aiMoveLegal from succMask.
		final int sm = succMask(x, y, vx, vy);
		for (final Direction direction : DIRECTIONS) {
			final int nvx = vx + direction.dx, nvy = vy + direction.dy;
			if ((sm & 1 << 16 + direction.ordinal()) == 0)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			// perf_aisearch (exact): the same AND, the frame and landing tests first
			// (lap-aware with a checkpoint owed no crossing counts).
			if ((!lapAware || lapGate == 0 && reach.shedableLanding(nx, ny, nvx, nvy))
					&& game.crossesFinishLegally(x, y, nx, ny))
				return false;
			if ((sm & 1 << direction.ordinal()) == 0)
				continue;
			if (!reach.isAlive(nx, ny, nvx, nvy))
				continue;
			sealEscapes[escapeCount * 2] = nx;
			sealEscapes[escapeCount * 2 + 1] = ny;
			escapeCount++;
		}
		if (escapeCount == 0)
			return true;
		java.util.Arrays.fill(sealCover, 0, escapeCount, 0);
		int opponentCount = 0;
		for (final Player opponent : game.players) {
			if (opponent.getNumber() == playerNum || opponent.isFinished())
				continue;
			final int bit = 1 << opponentCount;
			opponentCount++;
			final int[] position = opponent.getPosition();
			final int[] velocity = opponent.getVelocity();
			final int cx = position[0] + velocity[0], cy = position[1] + velocity[1];
			for (int escape = 0; escape < escapeCount; escape++) {
				final int ex = sealEscapes[escape * 2];
				final int ey = sealEscapes[escape * 2 + 1];
				if (Math.abs(ex - cx) <= 1 && Math.abs(ey - cy) <= 1
						&& game.aiMoveLegal(position[0], position[1], ex, ey))
					sealCover[escape] |= bit;
			}
		}
		return hasDistinctCover(sealCover, escapeCount, opponentCount, sealMatch);
	}

	/** Whether every requested cell can be assigned a different opponent from
	 *  its bitmask. Package-private for regression tests of the 9-player case. */
	static boolean hasDistinctCover(final int[] cover, final int opponentCount) {
		if (opponentCount < 0 || opponentCount > Integer.SIZE)
			throw new IllegalArgumentException("opponentCount out of range: " + opponentCount);
		return hasDistinctCover(cover, cover.length, opponentCount, new int[opponentCount]);
	}

	private static boolean hasDistinctCover(final int[] cover, final int escapeCount,
			final int opponentCount, final int[] matchOpponent) {
		if (escapeCount > opponentCount)
			return false;
		java.util.Arrays.fill(matchOpponent, 0, opponentCount, -1);
		for (int escape = 0; escape < escapeCount; escape++) {
			if (!sealAugment(escape, cover, matchOpponent, opponentCount, 0))
				return false;
		}
		return true;
	}

	private static boolean sealAugment(final int escape, final int[] cover, final int[] matchOpponent,
			final int opponentCount, final int usedMask) {
		for (int opponent = 0; opponent < opponentCount; opponent++) {
			final int bit = 1 << opponent;
			if ((cover[escape] & bit) == 0 || (usedMask & bit) != 0)
				continue;
			if (matchOpponent[opponent] < 0
					|| sealAugment(matchOpponent[opponent], cover, matchOpponent, opponentCount, usedMask | bit)) {
				matchOpponent[opponent] = escape;
				return true;
			}
		}
		return false;
	}

	/** Generic N-ply escape headroom: max over alive moves (dodging predicted
	 *  traffic per ply) with the leaf ply scored as the alive-fraction. */
	private double fmRec(final int x, final int y, final int vx, final int vy,
			final MobilitySearch search, final int ply) {
		final long memoKey = mobilityMemoKey(x, y, vx, vy, ply);
		final double cached = fmMemoGet(memoKey, search.epoch);
		if (cached == cached)
			return cached;
		final long[] b = search.blocked[ply - 1];
		final int bc = search.blockedCount[ply - 1];
		final long[] direct = search.blockedBits[ply - 1];
		// perf_aisearch (exact): a crossing counts here when it is legal and
		// (!lapAware || lapGate == 0 && shedable landing) -- never lap-aware with a
		// checkpoint owed -- so only !lapAware or lapGate == 0 asks for one, and
		// the side-effect-free tests run cheapest first.
		final boolean crossFrame = !lapAware || lapGate == 0;
		// perf_aisearch (exact): reach.isAlive at every in-range landing from one
		// probe of the state's alive plane (aliveMask).
		final int aliveSucc = aliveMask(x, y, vx, vy);
		if (ply == search.depth) {
			int cnt = 0;
			for (final Direction d : DIRECTIONS) {
				final int nvx = vx + d.dx, nvy = vy + d.dy;
				if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
					continue;
				final int nx = x + nvx, ny = y + nvy;
				// Counted: a crossing that counts, or a free alive landing -- one OR,
				// the free alive landing asked first.
				if ((aliveSucc & 1 << d.ordinal()) != 0
						&& !blockedContains(b, bc, direct, search.gridW, search.gridH, nx, ny)
						|| crossFrame && (!lapAware || reach.shedableLanding(nx, ny, nvx, nvy))
								&& game.crossesFinishLegally(x, y, nx, ny))
					cnt++;
			}
			final double result = cnt / 9.0;
			fmMemoPut(memoKey, search.epoch, result);
			return result;
		}
		// Every value lies in [0, 1]: the node is 1.0 when a crossing counts or a
		// continuation reaches 1.0, else the best continuation, whatever the order
		// of the scan. The continuations are searched first; the crossings are
		// asked only when none of them reached 1.0. (The memo holds exact values
		// under unique keys, so the order changes only what it caches.)
		double best = 0.0;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
				continue;
			if ((aliveSucc & 1 << d.ordinal()) == 0)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (blockedContains(b, bc, direct, search.gridW, search.gridH, nx, ny))
				continue;
			final double v = fmRec(nx, ny, nvx, nvy, search, ply + 1);
			if (v > best) {
				best = v;
				if (best >= 1.0) {
					fmMemoPut(memoKey, search.epoch, 1.0);
					return 1.0;
				}
			}
		}
		if (crossFrame)
			for (final Direction d : DIRECTIONS) {
				final int nvx = vx + d.dx, nvy = vy + d.dy;
				if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
					continue;
				final int nx = x + nvx, ny = y + nvy;
				if ((!lapAware || reach.shedableLanding(nx, ny, nvx, nvy))
						&& game.crossesFinishLegally(x, y, nx, ny)) {
					fmMemoPut(memoKey, search.epoch, 1.0);
					return 1.0;
				}
			}
		fmMemoPut(memoKey, search.epoch, best);
		return best;
	}

	/** perf_aisearch: log2 of the aliveMask table's slots. */
	private static final int ALIVE_MASK_BITS = 18;
	/** perf_aisearch: the aliveMask table (direct-mapped, entry = key << 32 | mask)
	 *  and the alive map and dimensions it was filled against. */
	private long[] aliveMaskTab;
	private BitSet aliveMaskAlive;
	private int aliveMaskW = -1, aliveMaskH = -1, aliveMaskVmax = -1, aliveMaskSpan = -1;

	/** perf_aisearch: bit d set when Direction d's velocity from (vx, vy) is in the
	 *  AI range and reach.isAlive holds at its landing -- what fmRec reads for every
	 *  successor. A function of the state, the alive map and its dimensions alone,
	 *  kept per state under its alive index (unique on the map's domain, stored
	 *  whole); the table empties itself when the map or a dimension changes. */
	private int aliveMask(final int x, final int y, final int vx, final int vy) {
		final Reachability r = reach;
		if (r.aliveStates == null || x < 0 || y < 0 || x >= r.aliveW || y >= r.aliveH
				|| r.velocityOutOfRange(vx, vy) || r.aliveSpan != 2 * r.aliveVMAX + 1)
			return aliveMaskCompute(x, y, vx, vy);
		final int key = r.aliveIdx(x, y, vx, vy);
		if (key < 0)
			return aliveMaskCompute(x, y, vx, vy);
		if (aliveMaskTab == null || aliveMaskAlive != r.aliveStates || aliveMaskW != r.aliveW
				|| aliveMaskH != r.aliveH || aliveMaskVmax != r.aliveVMAX || aliveMaskSpan != r.aliveSpan) {
			if (aliveMaskTab == null)
				aliveMaskTab = new long[1 << ALIVE_MASK_BITS];
			java.util.Arrays.fill(aliveMaskTab, -1L);
			aliveMaskAlive = r.aliveStates;
			aliveMaskW = r.aliveW;
			aliveMaskH = r.aliveH;
			aliveMaskVmax = r.aliveVMAX;
			aliveMaskSpan = r.aliveSpan;
		}
		final int slot = key * 0x9E3779B1 >>> 32 - ALIVE_MASK_BITS;
		final long entry = aliveMaskTab[slot];
		if ((int) (entry >>> 32) == key)
			return (int) entry;
		final int mask = aliveMaskCompute(x, y, vx, vy);
		aliveMaskTab[slot] = (long) key << 32 | mask;
		return mask;
	}

	/** perf_aisearch: aliveMask computed. */
	private int aliveMaskCompute(final int x, final int y, final int vx, final int vy) {
		int mask = 0;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (!RaceGame.aiVelocityOutOfRange(nvx, nvy) && reach.isAlive(x + nvx, y + nvy, nvx, nvy))
				mask |= 1 << d.ordinal();
		}
		return mask;
	}

	/** One immutable opponent projection plus a transposition epoch shared by
	 *  every candidate root in one real turn. Candidate roots overlap heavily;
	 *  rebuilding the projection for each root repeated the same search. The
	 *  memo itself is the pooled primitive table on RaceAi (round 130): a hit
	 *  needs this search's epoch AND the key, so concurrent nested searches
	 *  never cross-hit and evictions only recompute. Blocked cells are tiny
	 *  per-ply arrays (<= 3 per opponent) -- linear scan, no boxing. */
	private static final class MobilitySearch {
		int depth;
		final long[][] blocked;
		final int[] blockedCount;
		final long[][] blockedBits;
		final int[][] touchedWords;
		final int[] touchedCount;
		final int gridW;
		final int gridH;
		int epoch;

		MobilitySearch(final int depth, final int players, final int gridW,
				final int gridH) {
			this.gridW = gridW;
			this.gridH = gridH;
			blocked = new long[depth][3 * players];
			blockedCount = new int[depth];
			final int words = (gridW * gridH + Long.SIZE - 1) >>> 6;
			blockedBits = new long[depth][words];
			touchedWords = new int[depth][3 * players];
			touchedCount = new int[depth];
		}

		void reset(final int newDepth, final int newEpoch) {
			for (int ply = 0; ply < blockedBits.length; ply++) {
				for (int i = 0; i < touchedCount[ply]; i++)
					blockedBits[ply][touchedWords[ply][i]] = 0L;
				touchedCount[ply] = 0;
				blockedCount[ply] = 0;
			}
			depth = newDepth;
			epoch = newEpoch;
		}

		void indexBlockedCells() {
			for (int ply = 0; ply < depth; ply++) {
				final long[] bits = blockedBits[ply];
				for (int i = 0; i < blockedCount[ply]; i++) {
					final long cell = blocked[ply][i];
					final int x = (int) (cell >> 32), y = (int) cell;
					if (x < 0 || y < 0 || x >= gridW || y >= gridH)
						continue;
					final int index = x * gridH + y;
					final int word = index >>> 6;
					if (bits[word] == 0L)
						touchedWords[ply][touchedCount[ply]++] = word;
					bits[word] |= 1L << (index & 63);
				}
			}
		}
	}

	/** Round 130: pooled open-addressing transposition table for {@link #fmRec}
	 *  (long keys, double values, epoch validity). Replaces the per-turn boxed
	 *  HashMap that dominated the mobility recursion's self time (JFR: getNode
	 *  plus per-turn resize churn). Probe chains are capped; past the cap a
	 *  store is skipped -- correctness never depends on a store landing. */
	private static final int FM_MEMO_BITS = 15;
	private static final int FM_MEMO_PROBE_CAP = 32;
	private final long[] fmMemoKeys = new long[1 << FM_MEMO_BITS];
	private final double[] fmMemoVals = new double[1 << FM_MEMO_BITS];
	private final int[] fmMemoEpochs = new int[1 << FM_MEMO_BITS];
	private int fmMemoEpoch;

	private static int fmMemoSlot(final long key) {
		return (int) (key * 0x9E3779B97F4A7C15L >>> 64 - FM_MEMO_BITS);
	}

	/** NaN = miss (stored values live in [0, 1]). */
	private double fmMemoGet(final long key, final int epoch) {
		int slot = fmMemoSlot(key);
		for (int probe = 0; probe < FM_MEMO_PROBE_CAP && fmMemoEpochs[slot] == epoch; probe++) {
			if (fmMemoKeys[slot] == key)
				return fmMemoVals[slot];
			slot = slot + 1 & (1 << FM_MEMO_BITS) - 1;
		}
		return Double.NaN;
	}

	private void fmMemoPut(final long key, final int epoch, final double value) {
		int slot = fmMemoSlot(key);
		for (int probe = 0; probe < FM_MEMO_PROBE_CAP; probe++) {
			if (fmMemoEpochs[slot] != epoch || fmMemoKeys[slot] == key) {
				fmMemoKeys[slot] = key;
				fmMemoVals[slot] = value;
				fmMemoEpochs[slot] = epoch;
				return;
			}
			slot = slot + 1 & (1 << FM_MEMO_BITS) - 1;
		}
	}

	static boolean blockedContains(final long[] cells, final int count,
			final long[] direct, final int gridW, final int gridH,
			final int x, final int y) {
		if (x >= 0 && y >= 0 && x < gridW && y < gridH) {
			final int index = x * gridH + y;
			return (direct[index >>> 6] & 1L << (index & 63)) != 0;
		}
		final long cell = ((long) x << 32) | (y & 0xffffffffL);
		for (int i = 0; i < count; i++)
			if (cells[i] == cell)
				return true;
		return false;
	}

	/** Build an N-ply opponent world once per AI turn. Opponents advance N
	 *  greedy steps, blocking their top-3 min-turns cells at each ply. */
	private MobilitySearch mobilitySearch(final int subjectNum, final boolean avoidOcc, final int depth) {
		refreshLiveOccupancy();
		final boolean nested = inScorerSim || trueConfirmDepth != 0 || simDepth != 0;
		MobilitySearch search = nested ? nestedMobilityWorkspace : outerMobilityWorkspace;
		final int gridW = game.gameCols + 1, gridH = game.gameRows + 1;
		if (search == null || search.blocked.length != depth
				|| search.blocked[0].length != 3 * game.players.length
				|| search.gridW != gridW || search.gridH != gridH) {
			search = new MobilitySearch(depth, game.players.length, gridW, gridH);
			if (nested)
				nestedMobilityWorkspace = search;
			else
				outerMobilityWorkspace = search;
		}
		search.reset(depth, ++fmMemoEpoch);
		final long[][] blocked = search.blocked;
		final int[] blockedCount = search.blockedCount;
		for (final Player opponent : game.players) {
			if (opponent.getNumber() == subjectNum || opponent.isFinished())
				continue;
			final int[] position = opponent.getPosition();
			final int[] velocity = opponent.getVelocity();
			int x = position[0], y = position[1], vx = velocity[0], vy = velocity[1];
			for (int k = 0; k < depth; k++) {
				final int nc = greedyStepBlockTop3(x, y, vx, vy, avoidOcc, blocked[k],
						blockedCount[k], mobilityMove);
				if (nc < 0)
					break;
				blockedCount[k] = nc;
				x = mobilityMove[0];
				y = mobilityMove[1];
				vx = mobilityMove[2];
				vy = mobilityMove[3];
			}
		}
		search.indexBlockedCells();
		return search;
	}

	/** N-ply escape headroom in a per-turn opponent world (see {@link #fmRec}). */
	private double futureMobility(final int x, final int y, final int vx, final int vy,
			final MobilitySearch search) {
		if (reach.turnsArr == null)
			return 1.0;
		return fmRec(x, y, vx, vy, search, 1);
	}

	/** Collision-free key for one mobility-search state. Reachability already
	 *  assigns every in-domain (position, velocity) a unique non-negative int;
	 *  the high word adds the ply. The blocked world is implicit in the memo's
	 *  per-turn lifetime. */
	private long mobilityMemoKey(final int x, final int y, final int vx, final int vy, final int ply) {
		return ((long) ply << 32) | (reach.aliveIdx(x, y, vx, vy) & 0xffffffffL);
	}

	/** Best greedy step; blocks the rival's up-to-3 lowest-turns cells by
	 *  appending to the ply's cell array (duplicates fine -- the reader is a
	 *  linear scan). Returns the new count, or -1 when no step exists. */
	private int greedyStepBlockTop3(final int x, final int y, final int vx, final int vy,
			final boolean avoidOcc, final long[] block, final int blockCount, final int[] out) {
		// perf_aisearch (exact): the scan kept, among the moves whose velocity is in
		// reach's range and whose landing is on the map, has finite turns and holds
		// no live body, the three with the fewest turns by strict < (equal turns in
		// Direction order). That is the stable turns order of those moves without
		// the body test (greedyOrder, a function of the state and the turns map)
		// with the occupied landings dropped, cut at three: the same cells in the
		// same order, the same first move.
		final long order = greedyOrder(x, y, vx, vy);
		int count = blockCount, taken = 0;
		for (int i = 0; i < DIRECTIONS.length && taken < 3; i++) {
			final int ordinal = (int) (order >>> 4 * i) & 0xF;
			if (ordinal == 0xF)
				break;
			final Direction direction = DIRECTIONS[ordinal];
			final int nvx = vx + direction.dx, nvy = vy + direction.dy;
			final int nx = x + nvx, ny = y + nvy;
			if (avoidOcc && cellOccupiedByLive(nx, ny, x, y))
				continue;
			if (taken++ == 0)
				writeMove(out, nx, ny, nvx, nvy);
			block[count++] = ((long) nx << 32) | (ny & 0xffffffffL);
		}
		return taken == 0 ? -1 : count;
	}

	/** perf_aisearch: log2 of the greedyOrder table's slots. */
	private static final int GREEDY_ORDER_BITS = 16;
	/** perf_aisearch: greedyOrder keys (alive indexes) stay below this; an empty
	 *  entry's key bits equal it. */
	private static final int GREEDY_ORDER_KEY_LIMIT = (1 << 28) - 1;
	/** perf_aisearch: the greedyOrder table (direct-mapped, entry = key << 36 |
	 *  order) and the map and dimensions it was filled against. */
	private long[] greedyOrderTab;
	private int[] greedyOrderTurns;
	private int greedyOrderAliveW = -1, greedyOrderAliveH = -1, greedyOrderVmax = -1,
			greedyOrderSpan = -1;
	private final int[] greedyOrderTurnsScratch = new int[DIRECTIONS.length];
	private final int[] greedyOrderOrdinalScratch = new int[DIRECTIONS.length];

	/** perf_aisearch: the moves of (x, y, vx, vy) whose velocity is in reach's
	 *  range and whose landing is on the map with finite turns, sorted stably by
	 *  those turns (equal turns keep Direction order) and packed by packOrder. A
	 *  function of the state, the turns map and the map's dimensions alone, kept
	 *  per state under its alive index (unique on the map's domain, checked
	 *  whole); the table empties itself when the map or a dimension changes. */
	private long greedyOrder(final int x, final int y, final int vx, final int vy) {
		final Reachability r = reach;
		if (x < 0 || y < 0 || x >= r.aliveW || y >= r.aliveH || r.velocityOutOfRange(vx, vy)
				|| r.aliveSpan != 2 * r.aliveVMAX + 1)
			return greedyOrderCompute(x, y, vx, vy);
		final int key = r.aliveIdx(x, y, vx, vy);
		if (key < 0 || key >= GREEDY_ORDER_KEY_LIMIT)
			return greedyOrderCompute(x, y, vx, vy);
		if (greedyOrderTab == null || greedyOrderTurns != r.turnsArr || greedyOrderAliveW != r.aliveW
				|| greedyOrderAliveH != r.aliveH || greedyOrderVmax != r.aliveVMAX
				|| greedyOrderSpan != r.aliveSpan) {
			if (greedyOrderTab == null)
				greedyOrderTab = new long[1 << GREEDY_ORDER_BITS];
			java.util.Arrays.fill(greedyOrderTab, -1L);
			greedyOrderTurns = r.turnsArr;
			greedyOrderAliveW = r.aliveW;
			greedyOrderAliveH = r.aliveH;
			greedyOrderVmax = r.aliveVMAX;
			greedyOrderSpan = r.aliveSpan;
		}
		final int slot = key * 0x9E3779B1 >>> 32 - GREEDY_ORDER_BITS;
		final long entry = greedyOrderTab[slot];
		if ((int) (entry >>> 36) == key)
			return entry & ORDER_NONE;
		final long order = greedyOrderCompute(x, y, vx, vy);
		greedyOrderTab[slot] = (long) key << 36 | order;
		return order;
	}

	/** perf_aisearch: greedyOrder computed -- the original scan's first three tests,
	 *  then an insertion sort that moves an entry only past strictly larger turns. */
	private long greedyOrderCompute(final int x, final int y, final int vx, final int vy) {
		final int[] turnsBy = greedyOrderTurnsScratch, ordinals = greedyOrderOrdinalScratch;
		int n = 0;
		for (final Direction direction : DIRECTIONS) {
			final int nvx = vx + direction.dx, nvy = vy + direction.dy;
			if (reach.velocityOutOfRange(nvx, nvy))
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (nx < 0 || ny < 0 || nx >= reach.aliveW || ny >= reach.aliveH)
				continue;
			final int turns = reach.turnsArr[reach.aliveIdx(nx, ny, nvx, nvy)];
			if (turns == Integer.MAX_VALUE)
				continue;
			int i = n++;
			while (i > 0 && turnsBy[i - 1] > turns) {
				turnsBy[i] = turnsBy[i - 1];
				ordinals[i] = ordinals[i - 1];
				i--;
			}
			turnsBy[i] = turns;
			ordinals[i] = direction.ordinal();
		}
		return packOrder(ordinals, n);
	}

	/** True iff the ALIVE state (x,y,vx,vy) has at least two one-step
	 *  continuations that are geometry-legal and alive (a legal forward crossing
	 *  counts): genuinely open road, not a knife-edge single-file thread. The
	 *  precomputed roomy map answers every alive state (Reachability.sweepRoomy);
	 *  the recursive fallback and the depth-1 map had no caller (review,
	 *  2026-09-28). */
	private boolean isRoomy(final int x, final int y, final int vx, final int vy) {
		// Round 222: the body once carried a lap-aware crossing rule no reachable
		// state ever ran (the map answered first); raced as frame-specific maps it
		// was inert, so the map's rule is the rule. Without maps every state is
		// alive (Reachability.isAlive) and every alive state roomy.
		final BitSet roomy = reach.roomy0;
		return roomy == null || roomy.get(reach.aliveIdx(x, y, vx, vy));
	}

}
