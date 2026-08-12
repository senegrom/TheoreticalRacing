package tr.logic;

import java.util.BitSet;

/**
 * The vector-racing AI extracted from {@link RaceGame}: move selection for both
 * variants (AI1 = frontier we improve, AI2 = frozen AI2.9 standard), opponent
 * prediction, box-seal detection, brake-proof pace discipline and the N-ply
 * escape-headroom search. Reads the reachability maps and its host's
 * legality/geometry predicates through back-refs; returns the chosen move.
 */
final class RaceAi {
	private final RaceGame game;
	private final Reachability reach;
	/** Cached because the compiler-generated values() method clones on every call. */
	private static final Direction[] DIRECTIONS = Direction.values();
	/** Scratch storage is instance-owned: one RaceAi drives one single-threaded game. */
	private TwoRoundWorkspace twoRoundWorkspace;
	private PredictionWorkspace predictionWorkspace;
	private RolloutWorkspace rolloutWorkspace;
	private final int[] sealEscapes = new int[DIRECTIONS.length * 2];
	private final int[] sealCover = new int[DIRECTIONS.length];
	private final int[] sealMatch = new int[Integer.SIZE];
	private final int[] mobilityMove = new int[4];
	/** Outer candidate scores stay live while scorer-rival rollouts invoke a
	 *  recursion-guarded nested scorer, so those two levels need disjoint rows. */
	private final CandidateWorkspace outerCandidates = new CandidateWorkspace();
	private final CandidateWorkspace nestedCandidates = new CandidateWorkspace();

	private static final class CandidateWorkspace {
		final double[] trapByDirection = new double[DIRECTIONS.length];
		final double[] scoreWithoutSpread = new double[DIRECTIONS.length];
		final int[] turnsByDirection = new int[DIRECTIONS.length];
		final double[] scoreByDirection = new double[DIRECTIONS.length];
		final double[] uncertaintyByDirection = new double[DIRECTIONS.length];

		void reset() {
			java.util.Arrays.fill(trapByDirection, 0.0);
			java.util.Arrays.fill(scoreWithoutSpread, Double.MAX_VALUE);
			java.util.Arrays.fill(turnsByDirection, Integer.MAX_VALUE);
			java.util.Arrays.fill(scoreByDirection, Double.MAX_VALUE);
			java.util.Arrays.fill(uncertaintyByDirection, 0.0);
		}
	}

	private static final class TwoRoundWorkspace {
		final int[][] current;
		final int[][] world1;
		final int[][] blocked;
		final int[][] simulatedVelocity;
		final int[][] round1Position;
		final int[][] round2Position;
		final int[][] round1Velocity;
		final int[][] round2Velocity;
		final int[] candidatePosition = new int[2];

		TwoRoundWorkspace(final int players) {
			current = new int[players][];
			world1 = new int[players][];
			blocked = new int[players][];
			simulatedVelocity = new int[players][];
			round1Position = new int[players][2];
			round2Position = new int[players][2];
			round1Velocity = new int[players][2];
			round2Velocity = new int[players][2];
		}
	}

	private static final class PredictionWorkspace {
		final int[][][] result;
		final int[][][] cells;

		PredictionWorkspace(final int steps, final int players) {
			result = new int[steps][players][];
			cells = new int[steps][players][2];
		}
	}

	private static final class ScorerWorkspace {
		final int[][] originalPosition;
		final int[][] originalVelocity;
		final int[][] simulatedPosition;
		final int[][] simulatedVelocity;
		final int[] finishedPlace;

		ScorerWorkspace(final int players) {
			originalPosition = new int[players][];
			originalVelocity = new int[players][];
			simulatedPosition = new int[players][2];
			simulatedVelocity = new int[players][2];
			finishedPlace = new int[players];
		}
	}

	private static final class RolloutWorkspace {
		final int[] px;
		final int[] py;
		final int[] vx;
		final int[] vy;
		final boolean[] alive;
		final boolean[] scorerSet;
		final int[] move = new int[4];
		final int[] finalTier = new int[1];
		final ScorerWorkspace scorer;

		RolloutWorkspace(final int players) {
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
	}

	private CandidateWorkspace candidateWorkspace() {
		final CandidateWorkspace workspace = IN_SCORER_SIM ? nestedCandidates : outerCandidates;
		workspace.reset();
		return workspace;
	}

	/** Dispatches to AI1 or AI2. AI2 is now the FROZEN STANDARD (the AI2.9
	 *  zero-conflict champion: AI2.8 + conflict penalty zeroed); AI1 is forked
	 *  from it and is the one we improve from here. */
	Direction computeAiMove() {
		reach.ensureReachabilityReady();
		final Player p = game.players[game.subgamestate];
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
	private Direction pureMinTurnsMove(final int x, final int y, final int vx, final int vy,
			final int playerNum) {
		Direction best = null;
		int bestTurns = Integer.MAX_VALUE;
		Direction bestLegal = null;
		double bestLegalScore = Double.MAX_VALUE;
		Direction fallback = Direction.NONE;
		double fallbackScore = Double.MAX_VALUE;
		for (final Direction d : DIRECTIONS) {
			final int newVx = vx + d.dx;
			final int newVy = vy + d.dy;
			if (Math.abs(newVx) > RaceGame.AI_MAX_SPEED || Math.abs(newVy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int newX = x + newVx;
			final int newY = y + newVy;
			if (game.crossesFinish(x, y, newX, newY))
				return d;
			final double sc = reach.scorePos(newX, newY, newVx, newVy);
			if (!game.isMoveLegalGeometryCached(x, y, newX, newY)) {
				if (sc < fallbackScore) {
					fallbackScore = sc;
					fallback = d;
				}
				continue;
			}
			if (game.isCrashingPlayer(newX, newY, playerNum))
				continue;
			if (sc < bestLegalScore) {
				bestLegalScore = sc;
				bestLegal = d;
			}
			final int turns = reach.turnsToFinish(newX, newY, newVx, newVy);
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

	/** Explicit search depth for the soft depth-2 search
	 *  ({@link #searchMinTurnsCountedSoft3}) -- my next TWO moves are searched
	 *  explicitly, each ply priced against its own simulated opponent round
	 *  (world1 at stepIdx 0, world2 at stepIdx 1) before the opponent-blind
	 *  map takes over. */
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
	private final static int		AI1_SEAL_MAXRIVALS	= 3;	// endgame seal fires when <= this many rivals remain
	private final static double	AI1_PACE_FLOOR	= 0.60;	// min poRoom to take an unsealable faster move (sparse field only)
	private final static int		AI1_SPARSE_RIVALS	= 3;
	private final static int		AI1_DJS_ROUNDS	= 3;	// danger joint search: rollout depth in rounds	// aggressive pace floor applies only when <= this many rivals remain
	private final static int		AI1_DJS_SPD2	= 49;	// round 55 (AI1): DJS also fires at landing speed^2 >= this -- the ancestral speed-7-10 corner-entry class keeps the trap ladder at 0 until every alternative is dead, so the trap gate alone triggers too late
	private final static int		AI1_DJS_SLOW_ROUNDS	= 5;	// round 59: rollout horizon for slow-class fires (landing spd^2 < AI1_DJS_SPD2) -- the slow queue dooms commit 3-5 rounds out (lemans-s4 start funnel, oracle-measured)
	private final static int		AI1_DJS_SLOW_L1_ROUNDS	= 6;	// round 70 frontier: L1 slow traps get one extra round; interlagos 4-car s3/s4 dies exactly beyond the 5-round verdict
	private final static int		AI1_SCORER_NEAR	= 10;	// round 59: Chebyshev radius for real-scorer rivals in slow-class rollouts
	private final static int		AI1_SCORER_MAXRIVALS	= 3;	// round 59: at most this many nearest real-scorer rivals per rollout (cost bound; the box formers are always adjacent)
	private final static int		AI1_TRAP_SOLO_R	= 16;	// round 61: trap relief radius -- L1/L2 threads are only dangerous if a rival can contest them; no live rival within this Chebyshev range of the landing = the map's own certification suffices (max per-axis closure is |v|+1 <= 13 per round)
	private final static int		AI1_DEEP_HORIZON	= 8;	// round 65: rollout horizon for pack-gated deep escalations -- the hairpin-s10 doom commits 7 rounds out (oracle: three candidates FINISH @r6 while the chosen dies @r7)
	private final static int		AI1_DEEP_PACK	= 3;	// round 65: escalate only with >= this many rivals within AI1_DEEP_PACK_R of the landing (the doom class lives in packs; solo tunnels excluded)
	private final static int		AI1_DEEP_PACK_R	= 10;	// round 65: Chebyshev pack radius for the deep escalation gate
	private final static int		AI1_SLOW_PACK		= 7;	// round 67: rare dense slow-pack scorer trigger
	private final static int		AI1_SLOW_PACK_R	= 10;
	private final static int		AI1_SLOW_PACK_SPD2	= 16;
	private final static int		AI1_SLOW_PACK_MIN	= 3;	// round 71 (promoted): small-field generalization of the dense-pack gate -- the monaco-4car s9 funnel doom (m27, spd^2=13, 3 rivals all within Cheb 10) is smom-blind and non-fragile but scorer-rival-visible @r2
	private final static int		AI1_SLOW_PACK_SPD2_SMALL	= 12;	// round 71 (promoted): speed floor for the small-field gate (start-grid moves stay below it)
	private final static int		AI1_DEEP_CERT_RIVALS	= 6;	// round 73: scorer-rival cap for the ahead-pack corridor certification -- the interlagos-s10 m103 killers are ranks 4-6 by landing distance, beyond the round-59 nearest-3 set
	private final static int		AI1_FINISH_CERT_TTF	= 15;	// round 75 (promoted): bounded near-finish sprint; candidate must finish at its empty-map optimum in two independent joint models
	private final static int		AI1_MOBILITY_DEPTH	= 4;	// frontier; projection/cache shared per turn
	private final static int		AI2_MOBILITY_DEPTH	= 4;	// frozen standard
	/** Forensic gates: -Dai.debug.player=N per-turn pick dump for that player;
	 *  -Dai.debug.djs DJS-death events for ALL players. Both off by default. */
	private final static int		AI_DEBUG_PLAYER	= Integer.getInteger("ai.debug.player", -1);
	private final static boolean	AI_DEBUG_DJS	= Boolean.getBoolean("ai.debug.djs");
	private final static boolean	AI_DEBUG_COMP	= Boolean.getBoolean("ai.debug.comp");
	/** Round 59: true while a rival's rollout move is computed by the REAL
	 *  scorer (scorerMoveOverState) -- suppresses the recursive machinery
	 *  (endgame solver, certified tie-break override, DJS) inside that call.
	 *  Single-threaded AI turn; cleared in a finally. */
	private static boolean			IN_SCORER_SIM	= false;
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
	private final static double	AI1_VACATE_V	= 3;		// rival speed >= this: predicted cell nulled (transiting)
	private final static double	AI1_TRAP_L1		= 2.0;	// trap ladder: 1 safe successor
	private final static double	AI1_TRAP_L2		= 0.5;	// trap ladder: 2 safe successors

	/**
	 * AI1 (EXPERIMENTAL FRONTIER): forked verbatim from the AI2.9 standard.
	 * Identical to {@link #optimalMoveAI2} at fork time; improvements are
	 * applied here while AI2 stays frozen as the reference.
	 */
	private Direction optimalMoveAI1(final int[] pos, final int[] vel, final int playerNum) {
		// Endgame seal (frontier, per "force the last rival to crash = win"): with
		// few rivals left, if a SAFE move of mine leaves the decisive rival with no
		// legal move (a forced crash), take it. Only a rival that moves after me this
		// round (ri > subgamestate) can be forced; gated on my own safety so I never
		// trap myself to trap them.
		final int sealRivals = liveRivalsRemaining(playerNum);
		if (sealRivals >= 1 && sealRivals <= AI1_SEAL_MAXRIVALS) {
			final int ri = decisiveRival(playerNum);
			if (ri > game.subgamestate && rivalEscapes(ri, -1, -1, playerNum) >= 1) {
				final Direction sd = findForcedCrashMove(pos, vel, ri, playerNum);
				if (sd != null)
					return sd;
			}
		}
		// Endgame solver (round 43, lever 5, AI1 only): 1v1 exact paranoid
		// minimax near the finish. Acts ONLY on proven wins (I finish first or
		// the rival is forced to crash under its best defense) -- the deep
		// generalization of the 1-ply seal above; unproven values fall through
		// to the normal scorer (insurance-premium law: no paranoid defense).
		if (sealRivals == 1 && !IN_SCORER_SIM) {
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
		final int[][][] predictedSteps = predictedOpponentSteps(playerNum, 1);
		// Vacated-cell awareness: a fast-moving opponent (|v| >= 3) will have
		// moved through/off its predicted cell by the time I could occupy it --
		// blocking those cells causes phantom detours. Null out transiting
		// opponents' predictions; only slow/parked rivals stay blocked.
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pv = p.getVelocity();
			if (Math.hypot(pv[0], pv[1]) >= AI1_VACATE_V)
				predictedSteps[0][p.getNumber() - 1] = null;
		}
		final int[][] predicted = predictedSteps[0];
		// In-traffic ply-2 foresight RESTORED (fore2): the v4/v5 pack gate that
		// disabled the ply-2 price whenever any rival sat within squared
		// distance 36 is GONE -- the round-2 world (worlds[1]) is now priced on
		// every move. Ahead-rivals only: only bodies of rivals currently AHEAD
		// of me on track are priced (see occupiedByAheadRival +
		// searchMinTurnsCountedSoft3 below); a chaser's body is not priced,
		// since ceding a line two rounds out to a car behind me trades race
		// position for nothing. The queue brakes (queueBox, cornerEntry) now
		// guard the corridors the old gate was protecting.

		final CandidateWorkspace candidateWorkspace = candidateWorkspace();
		final double[] trapByDir = candidateWorkspace.trapByDirection;
		// round 49 arm C: non-spread score and raw map ttf per candidate, for the
		// certified pace tie-break after the loop.
		final double[] scoreNSByDir = candidateWorkspace.scoreWithoutSpread;
		final int[] poTByDir = candidateWorkspace.turnsByDirection;
		// round 62: full score and unc per candidate, for the certified UNC
		// override after the loop.
		final double[] scoreByDir = candidateWorkspace.scoreByDirection;
		final double[] uncByDir = candidateWorkspace.uncertaintyByDirection;
		MobilitySearch paceMobility = null;
		Direction best = null;
		double bestScore = Double.MAX_VALUE;
		Direction bestLegal = null;
		double bestLegalScore = Double.MAX_VALUE;
		Direction fallback = Direction.NONE;
		double fallbackScore = Double.MAX_VALUE;

		for (final Direction d : DIRECTIONS) {
			final int newVx = vel[0] + d.dx;
			final int newVy = vel[1] + d.dy;
			if (Math.abs(newVx) > RaceGame.AI_MAX_SPEED || Math.abs(newVy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int newX = pos[0] + newVx;
			final int newY = pos[1] + newVy;
			if (game.crossesFinish(pos[0], pos[1], newX, newY))
				return d;
			final double sc = reach.scorePos(newX, newY, newVx, newVy);
			if (!game.isMoveLegalGeometryCached(pos[0], pos[1], newX, newY)) {
				if (sc < fallbackScore) {
					fallbackScore = sc;
					fallback = d;
				}
				continue;
			}
			if (game.isCrashingPlayer(newX, newY, playerNum))
				continue;
			if (sc < bestLegalScore) {
				bestLegalScore = sc;
				bestLegal = d;
			}
			final int ownTurns = reach.turnsToFinish(newX, newY, newVx, newVy);
			if (ownTurns == Integer.MAX_VALUE)
				continue;

			// TWO-ROUND SOFT WORLD-STEP (the experiment): simulate TWO whole
			// rounds in actual turn order, conditioned on THIS candidate
			// landing. worlds[0] answers the round-r+1 questions (safe
			// successors, ply-1 pricing) exactly as before; worlds[1] gives the
			// bodies' cells when I make my round-r+2 move, pricing the second
			// explicit search ply -- ALWAYS on now (fore2, no pack gate), but
			// ahead-rivals only: searchMinTurnsCountedSoft3 prices the ply-2
			// landing only when the round-2 body belongs to a rival currently
			// AHEAD of me on track (myDist = distAt of my CURRENT cell); a
			// chaser's body is left unpriced (ceding a line two rounds out to
			// a car behind me trades race position for nothing).
			final TwoRoundWorkspace worlds = simulateTwoRounds(playerNum, newX, newY);
			final int[][] world = worlds.world1;
			final double[] deepCounted = searchMinTurnsCountedSoft3(newX, newY, newVx, newVy, AI1_DEEP_LOOKAHEAD, 0,
					predictedSteps, playerNum, worlds.world1, worlds.current, reach.distAt(pos[0], pos[1]));
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
			double trapPenalty = d2SafeCount == 0 ? 50.0
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
			trapByDir[d.ordinal()] = trapPenalty;
			final double speed = Math.hypot(newVx, newVy);
			// Per-state certified budget with a legacy floor: the map-certified
			// minimal target T (>= 2 independent blind braking descents reach
			// |v| <= T from this candidate state) governs above the floor; the
			// floor preserves the zero-penalty regime at low speed.
			final int widthBudget = Math.max(5, reach.certBudget(newX, newY, newVx, newVy)) + d2SafeCount;
			final double overSpeed = Math.max(0.0, speed - widthBudget);
			double speedCap = overSpeed * overSpeed * 0.4;
			double uncertified = 0.0;
			if (speed > AI1_BRAKE_SPEED) {
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
						uncertified = (speed - AI1_BRAKE_SPEED) * (proofs == 0 ? 2.5 : 1.0);
				}
			}
			// Pack-gated knife-edge corner-entry brake: price roomy-successor
			// scarcity when a pack is packed at a corner entry (>= 2 rivals
			// within squared distance 36 and <= 1 roomy escape) -- fires where
			// the converging-opponent surcharge reads false. The pack gate
			// spares the lone fast knife-edge that is the racing line on tight
			// circuits, so only genuine corner-entry traffic jams brake.
			double cornerEntry = 0.0;
			if (speed > AI1_BRAKE_SPEED) {
				final int roomySucc = countRoomySuccessors(newX, newY, newVx, newVy, playerNum);
				if (roomySucc <= 1 && countNearbyOpponents(newX, newY, playerNum, AI1_PACK_R2) >= 2)
					cornerEntry = (speed - AI1_BRAKE_SPEED) * (roomySucc == 0 ? 3.0 : 1.5);
			}
			// v5.1 queue-compression corner guard (zandvoort forensic, AI1
			// only): the corner-entry brake above is opponent-BLIND in its
			// escape count, the brake proofs ignore transiting (|v| >= 3)
			// rivals, and the round-sims behind d2SafeCount and the ply-2
			// price assume a hairpin queue keeps flowing -- so a fast coast
			// whose timed margin is already thin (d2SafeCount <= 2) while
			// >= 2 SLOWER rivals sit within squared distance 36 at-or-ahead
			// of the landing (compression, not a chase) is one round from
			// being boxed: on zandvoort both alive continuations of
			// (43,66)v(-4,3) were bodily occupied by the compressed queue
			// when the victim arrived, after the coast had beaten the
			// covered brake by 0.278. Price the coast like the survivable
			// knife-edge corner entry ((speed-4) * 1.5) so the brake wins.
			double queueBox = 0.0;
			if (speed > AI1_BRAKE_SPEED && cornerEntry == 0.0) {
				if (d2SafeCount <= 2 && countSlowerRivalsAhead(newX, newY, speed, playerNum) >= 2)
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
			final double conflict = cellOccupiedByPrediction(newX, newY, predicted) ? 0.0 : 0.0; // AI2.9: conflict penalty ZEROED (auto-tuner v2) -- +3.0 was redundant soft caution atop the hard isCrashingPlayer check; removing it is faster (63.81 vs 64.10) AND a landslide h2h win (3.926 vs 5.074), crash-free everywhere
			final double spread = opponentSpreadPenalty(newX, newY, playerNum);
			// Racing-line momentum tie-break: among moves of otherwise-equal cost,
			// prefer the one carrying more usable speed.
			final double momentum = AI2_MOMENTUM_TIEBREAK * speed;
			// Plateau-width robustness tie-break: prefer candidates whose best
			// follow-up is achievable many ways over knife-edge lines.
			final double robustness = AI2_PLATEAU_TIEBREAK * Math.min((int) deepCounted[1], 5);
			final double score = costToFinish + trapPenalty + speedCap + uncertified + cornerEntry + queueBox + conflict + spread - momentum - robustness;
			final int poT = reach.turnsArr != null && reach.isAlive(newX, newY, newVx, newVy)
					? reach.turnsArr[reach.aliveIdx(newX, newY, newVx, newVy)] : Integer.MAX_VALUE;
			if (AI_DEBUG_COMP)
				System.err.println("R49C p=" + playerNum + " pos=(" + pos[0] + "," + pos[1] + ") vel=("
						+ vel[0] + "," + vel[1] + ") d=" + d + " land=(" + newX + "," + newY + ") ttf=" + poT
						+ " score=" + score + " cost=" + costToFinish + " trap=" + trapPenalty
						+ " cap=" + speedCap + " unc=" + uncertified + " ce=" + cornerEntry
						+ " qb=" + queueBox + " spread=" + spread + " mom=" + momentum
						+ " rob=" + robustness);
			scoreNSByDir[d.ordinal()] = score - spread;
			poTByDir[d.ordinal()] = poT;
			scoreByDir[d.ordinal()] = score;
			uncByDir[d.ordinal()] = uncertified;
			if (poT < poBestT) {
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
		if (best != null && !IN_SCORER_SIM) {
			final double bestNS = scoreNSByDir[best.ordinal()];
			int fastT = poTByDir[best.ordinal()];
			Direction fast = null;
			for (final Direction d : DIRECTIONS) {
				if (d == best || poTByDir[d.ordinal()] >= fastT)
					continue;
				if (scoreNSByDir[d.ordinal()] > bestNS + 1e-9)
					continue;
				// round 75 (AI1): admit trap-L2 faster lines under a STRONGER
				// proof -- the round-58 arm required trap 0 and certified with
				// smom-3, the world the r73/r74 counterexamples proved blind at
				// pack sites; the widened scorer-rival certificate replaces it.
				if (trapByDir[d.ordinal()] > AI1_TRAP_L2)
					continue;
				final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
				final int nx = pos[0] + nvx, ny = pos[1] + nvy;
				if (sealable(nx, ny, nvx, nvy, playerNum))
					continue;
				if (simOutcome(nx, ny, nvx, nvy, playerNum, AI1_DJS_ROUNDS, true, true, true, true,
						AI1_DEEP_CERT_RIVALS, null) < 0)
					continue;
				fast = d;
				fastT = poTByDir[d.ordinal()];
			}
			if (fast != null)
				best = fast;
		}
		// round 62 (AI1): certified UNC override. The counterfactual on the
		// r61 equilibrium still attributes the largest recoverable pool to
		// `uncertified` (monaco s1: 50 ttf, deep search agreeing 48/48), and
		// rounds 49-53 proved the surcharge is load-bearing insurance that
		// must NOT be cut by predicate alone. Pay it everywhere EXCEPT where
		// a strictly faster line wins the unc-free comparison AND passes the
		// strongest proof owned: zero trap, not sealable, and survival in the
		// round-59 scorer-rival world (the proof round 52 lacked). Solo flips
		// have empty scorer sets, so their proofs cost nothing.
		if (best != null && !IN_SCORER_SIM) {
			final double bestNU = scoreByDir[best.ordinal()] - uncByDir[best.ordinal()];
			int fastT = poTByDir[best.ordinal()];
			Direction fast = null;
			for (final Direction d : DIRECTIONS) {
				if (d == best || poTByDir[d.ordinal()] >= fastT)
					continue;
				if (uncByDir[d.ordinal()] <= 0.0 || scoreByDir[d.ordinal()] == Double.MAX_VALUE)
					continue;
				if (scoreByDir[d.ordinal()] - uncByDir[d.ordinal()] > bestNU + 1e-9)
					continue;
				if (trapByDir[d.ordinal()] != 0.0)
					continue;
				final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
				final int nx = pos[0] + nvx, ny = pos[1] + nvy;
				if (sealable(nx, ny, nvx, nvy, playerNum))
					continue;
				if (simOutcome(nx, ny, nvx, nvy, playerNum, AI1_DJS_SLOW_ROUNDS, true, true, true, true) < 0)
					continue;
				fast = d;
				fastT = poTByDir[d.ordinal()];
			}
			if (fast != null)
				best = fast;
		}
		Direction chosen = (poDir != null && poBestT < poScorerT) ? poDir : best;
		if (chosen != null) {
			// r50 sealGuard v2: exact worst-case box check (distinct-opponent
			// matching, legality-checked covers). If the chosen landing is
			// sealable, take the FASTEST unsealable alternative instead.
			final int cvx = vel[0] + chosen.dx, cvy = vel[1] + chosen.dy;
			final int cx = pos[0] + cvx, cy = pos[1] + cvy;
			if (!game.crossesFinish(pos[0], pos[1], cx, cy) && sealable(cx, cy, cvx, cvy, playerNum)) {
				// Round 72 (AI1): a worst-case seal warning must not force the
				// scorer into a strictly narrower local trap. Nurburgring 8-car
				// seed 19 exposed the incoherence: the scorer's tier-L2 N was
				// oracle-alive, while the old fastest-unsealable guard replaced it
				// with tier-L1 E, which died. Keep the guard's anti-seal purpose,
				// but require a trap-monotone escape.
				final double chosenTrap = trapByDir[chosen.ordinal()];
				int bestT = Integer.MAX_VALUE;
				Direction safest = null;
				for (final Direction d : DIRECTIONS) {
					final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
					if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
						continue;
					final int nx = pos[0] + nvx, ny = pos[1] + nvy;
					if (game.crossesFinish(pos[0], pos[1], nx, ny)) {
						safest = d;
						bestT = -1;
						break;
					}
					if (!game.isMoveLegalGeometryCached(pos[0], pos[1], nx, ny))
						continue;
					if (game.isCrashingPlayer(nx, ny, playerNum))
						continue;
					if (!reach.isAlive(nx, ny, nvx, nvy))
						continue;
					if (trapByDir[d.ordinal()] > chosenTrap)
						continue;
					if (sealable(nx, ny, nvx, nvy, playerNum))
						continue;
					final int tt = reach.turnsArr != null ? reach.turnsArr[reach.aliveIdx(nx, ny, nvx, nvy)] : 0;
					if (tt < bestT) {
						bestT = tt;
						safest = d;
					}
				}
				if (safest != null)
					chosen = safest;
			}
			// Round 75 (PROMOTED): a bounded, proof-gated finish sprint. Local trap and
			// uncertainty terms can spend a whole turn protecting a line even when
			// a faster candidate is already close enough to certify all the way to
			// the flag. Monaco s16 m789 is the minimal example: S has map ttf=15
			// and finishes in 15 rounds, while narrow SW has ttf=14 and finishes in
			// exactly 14; every other move dies. Accept a strictly-faster candidate
			// only if BOTH the score-shaped-rival and scorer-rival joint worlds reach
			// the finish at the empty-map lower bound (ttf+1 simulation rounds; the
			// first partial round contains only players after me). The normal DJS
			// still runs afterwards, retaining its independent survival veto.
			if (!IN_SCORER_SIM) {
				int sprintT = poTByDir[chosen.ordinal()];
				Direction sprint = null;
				for (final Direction d : DIRECTIONS) {
					final int t = poTByDir[d.ordinal()];
					if (d == chosen || t >= sprintT || t > AI1_FINISH_CERT_TTF
							|| trapByDir[d.ordinal()] > AI1_TRAP_L1)
						continue;
					final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
					final int nx = pos[0] + nvx, ny = pos[1] + nvy;
					final int rounds = t + 1;
					if (simOutcome(nx, ny, nvx, nvy, playerNum, rounds, true, true, true, false) != 0)
						continue;
					if (simOutcome(nx, ny, nvx, nvy, playerNum, rounds, true, true, true, true,
							AI1_DEEP_CERT_RIVALS, null) != 0)
						continue;
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
			// Danger joint search (round 40): in flagged states (the landing's
			// trap ladder >= 0.5, i.e. <= 2 safe successors) roll the joint game
			// 3 rounds forward on a detached greedy board. STRICTLY asymmetric:
			// only override when the pick provably dies in-sim and an alternative
			// survives -- a surviving pick is always kept (fs1's false-alarm
			// evasion crashes came from warning-based re-picks; survival-only
			// switching cannot fire on a line that was actually fine).
			if (AI_DEBUG_PLAYER == playerNum)
				System.err.println("AIDBG turn p=" + playerNum + " pos=(" + pos[0] + "," + pos[1] + ") vel=("
						+ vel[0] + "," + vel[1] + ") chosen=" + chosen + " trap=" + trapByDir[chosen.ordinal()]);
			// round 45 (AI1): sim fidelity only -- finished cars vanish from the
			// sim board (the real game removes them; ghosts caused phantom
			// blockage verdicts). The always-on trigger arm was REJECTED by the
			// ancestral screen: 6 DJS switches/race (vs 0-1) -> false-death
			// model errors perturbed the field into new doom pockets
			// (hungaroring guard 1->5). The trap gate is not just a cost gate;
			// it bounds exposure to sim model error.
			// round 55 (AI1): retry a wider trigger UNDER exact-self fidelity
			// (round 51 fixed the false-death class that sank the round-45 arm):
			// also fire at high landing speed, where the ancestral crash shapes
			// live but the trap ladder still reads 0. Survival-only asymmetry
			// unchanged -- extra fires can only override provably dying picks.
			// Landing velocity recomputed: the sealGuard may have swapped chosen.
			final int djvx = vel[0] + chosen.dx, djvy = vel[1] + chosen.dy;
			// round 59 (AI1): slow-class fires (landing below the wide-trigger
			// speed) use the real-scorer near-rival world and a 5-round
			// horizon -- the six residual champion crashes are ALL slow queue
			// dooms committing 3-5 rounds out, where every cheap proxy drifts
			// (oracle-proven at hungaroring-(64,115) and the lemans-s4
			// funnel). Fast fires keep the proven smom world at 3 rounds.
			final boolean djSlow = djvx * djvx + djvy * djvy < AI1_DJS_SPD2;
			if (!IN_SCORER_SIM) {
				if (trapByDir[chosen.ordinal()] >= 0.5 || !djSlow) {
					final int dangerRounds = djSlow && trapByDir[chosen.ordinal()] >= AI1_TRAP_L1
							? AI1_DJS_SLOW_L1_ROUNDS
							: djSlow ? AI1_DJS_SLOW_ROUNDS : AI1_DJS_ROUNDS;
					// round 65 (AI1): pack-gated DEEP escalation for fast fires.
					// The 5-7-round doom class (hairpin s10: three candidates
					// FINISH @r6 while the chosen dies @r7) is invisible to the
					// 3-round world. With >= AI1_DEEP_PACK rivals within
					// Chebyshev AI1_DEEP_PACK_R of the landing, run the cheap
					// smom pre-screen at the deep horizon and escalate to the
					// scorer-rival world on a dead-or-FRAGILE (final tier <= 1)
					// verdict; the scorer-rival re-verdict gates any switch.
					boolean deepHandled = false;
					if (!djSlow) {
						final int dcx = pos[0] + djvx, dcy = pos[1] + djvy;
						int packNear = 0;
						for (final Player pp : game.players) {
							if (pp.getNumber() == playerNum || pp.isFinished())
								continue;
							final int[] ppos = pp.getPosition();
							if (Math.abs(ppos[0] - dcx) <= AI1_DEEP_PACK_R
									&& Math.abs(ppos[1] - dcy) <= AI1_DEEP_PACK_R)
								packNear++;
						}
						if (packNear >= AI1_DEEP_PACK && !game.crossesFinish(pos[0], pos[1], dcx, dcy)) {
							final int[] ft = rolloutWorkspace().finalTier;
							ft[0] = 3;
							final int dv = simOutcome(dcx, dcy, djvx, djvy, playerNum, AI1_DEEP_HORIZON,
									true, true, true, false, AI1_SCORER_MAXRIVALS, ft);
							if (dv < 0 || ft[0] <= 1) {
								if (AI_DEBUG_DJS)
									System.err.println("AIDBG DEEP p=" + playerNum + " pos=(" + pos[0] + ","
											+ pos[1] + ") chosen=" + chosen + " smom8 "
											+ (dv < 0 ? "dies" : "fragile") + " -> scorer rollout");
								Direction deepChoice = chosen;
								if (dv < 0 && trapByDir[chosen.ordinal()] >= AI1_TRAP_L2) {
									// Cross-model certificate: the topology-shaped smom world proves
									// a locally narrow pick dies and proposes a survivor; accept that
									// survivor only if the scorer-rival world independently keeps it
									// alive. The local trap gate excludes open-line false deaths.
									final Direction smomAlt = dangerJointSearch(pos, vel, playerNum, chosen,
											true, true, true, false, AI1_DEEP_HORIZON);
									if (smomAlt != chosen) {
										final int avx = vel[0] + smomAlt.dx, avy = vel[1] + smomAlt.dy;
										final int ax = pos[0] + avx, ay = pos[1] + avy;
										if (game.crossesFinish(pos[0], pos[1], ax, ay)
												|| simOutcome(ax, ay, avx, avy, playerNum, AI1_DEEP_HORIZON,
														true, true, true, true) >= 0) {
											deepChoice = smomAlt;
											if (AI_DEBUG_DJS)
												System.err.println("AIDBG DEEP p=" + playerNum
														+ " cross-model SWITCH " + chosen + " -> " + smomAlt);
										}
									}
								}
								if (deepChoice == chosen)
									deepChoice = dangerJointSearch(pos, vel, playerNum, chosen, true, true,
											true, true, AI1_DEEP_HORIZON);
								chosen = deepChoice;
								deepHandled = true;
							} else {
								// round 73 (AI1): the smom-8 pre-screen is blind to
								// CONVERGENCE dooms -- interlagos s10 m103 reads alive
								// tier-3 while faithful rivals kill @r2: the killers
								// (ranks 4-6 by landing distance) brake INTO my
								// shedding corridor, so drifting AND static rival
								// models both vacate the kill. With >= AI1_DEEP_PACK
								// rivals AHEAD of the landing (positive dot with the
								// landing velocity), certify the chosen in the
								// scorer-rival world at the widened cap (the nearest-3
								// set here is exactly the harmless rear queue).
								// Survival-only switch as everywhere.
								int aheadNear = 0;
								for (final Player pp : game.players) {
									if (pp.getNumber() == playerNum || pp.isFinished())
										continue;
									final int[] ppos = pp.getPosition();
									if (Math.abs(ppos[0] - dcx) <= AI1_DEEP_PACK_R
											&& Math.abs(ppos[1] - dcy) <= AI1_DEEP_PACK_R
											&& (ppos[0] - dcx) * djvx + (ppos[1] - dcy) * djvy > 0)
										aheadNear++;
								}
								// Round 74 (AI1): a fast whole-field queue can converge
								// from the SIDE/REAR, so the ahead-only Round 73 gate misses
								// it. Zigzag s22 m72 has all seven rivals within Cheb 10,
								// only one ahead, and three rival bodies already occupying
								// the mover's neutral 3x3 landing grid: smom-8 reads the chosen
								// alive/tier-3 while scorer rivals prove it dead @r2 and keep
								// two equal-ttf escapes alive. Certify only that rare shape,
								// and only when a near-equal low-trap escape is on the table.
								boolean closeEscape = false;
								final int chosenT = poTByDir[chosen.ordinal()];
								for (final Direction d : DIRECTIONS) {
									if (d != chosen && poTByDir[d.ordinal()] <= chosenT + 1
											&& trapByDir[d.ordinal()] <= AI1_TRAP_L2) {
										closeEscape = true;
										break;
									}
								}
								final int landingBodies = countRivalsWithinCheb(pos[0] + vel[0],
										pos[1] + vel[1], playerNum, 1);
								final boolean compressedRearQueue = packNear == sealRivals
										&& sealRivals >= AI1_SLOW_PACK && aheadNear <= 1
										&& landingBodies >= 2 && closeEscape;
								if (aheadNear >= AI1_DEEP_PACK || compressedRearQueue) {
									if (AI_DEBUG_DJS)
										System.err.println("AIDBG " + (compressedRearQueue ? "QUEUE" : "CORR")
												+ " p=" + playerNum + " pos=(" + pos[0] + "," + pos[1]
												+ ") chosen=" + chosen + " ahead=" + aheadNear
												+ " bodies=" + landingBodies
												+ " -> certified scorer check");
									chosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
											true, AI1_DJS_ROUNDS, AI1_DEEP_CERT_RIVALS);
									deepHandled = true;
								}
							}
						}
					}
					if (!deepHandled)
						chosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
								djSlow, dangerRounds);
				} else {
					// round 60 (AI1): trap-0 slow moves get a CHEAP smom smoke
					// test -- the vacate-optimistic ladder reads roomy at the
					// zigzag-s4 doom entry (m102: count 0 in reality, death 4
					// rounds out, smom sees it) so nothing fired there. A smom
					// death ESCALATES to the faithful scorer-rival rollout,
					// which re-verdicts the chosen and gates any switch -- smom
					// false alarms are filtered before they can perturb.
					final int scvx = vel[0] + chosen.dx, scvy = vel[1] + chosen.dy;
					final int scx = pos[0] + scvx, scy = pos[1] + scvy;
					final int slowSpd2 = scvx * scvx + scvy * scvy;
					boolean closeEscape = false;
					final int chosenT = poTByDir[chosen.ordinal()];
					for (final Direction d : DIRECTIONS) {
						if (d != chosen && poTByDir[d.ordinal()] <= chosenT + 1
								&& trapByDir[d.ordinal()] <= AI1_TRAP_L2) {
							closeEscape = true;
							break;
						}
					}
					final int slowPack = countRivalsWithinCheb(scx, scy, playerNum, AI1_SLOW_PACK_R);
					// round 71 (AI1): the dense-pack gate generalized to SMALL
					// fields -- the monaco-4car s9 funnel doom (entry m27,
					// spd^2=13, all 3 rivals within Chebyshev 10, survivors N/SE)
					// is smom-blind AND non-fragile (tier 3) yet scorer-rival
					// visible @r2; only the trigger was missing. Whole live
					// field packed + close escape, with a lower speed floor for
					// fields below the 8-car pack size (start grids stay below
					// spd^2=12).
					final boolean packAll = slowPack == sealRivals && closeEscape;
					final boolean denseSlowPack = packAll && (sealRivals >= AI1_SLOW_PACK
							? slowSpd2 >= AI1_SLOW_PACK_SPD2
							: sealRivals >= AI1_SLOW_PACK_MIN && slowSpd2 >= AI1_SLOW_PACK_SPD2_SMALL);
					final boolean smokeDies = !game.crossesFinish(pos[0], pos[1], scx, scy)
							&& simOutcome(scx, scy, scvx, scvy, playerNum, AI1_DJS_SLOW_ROUNDS,
									true, true, true, false) < 0;
					if (denseSlowPack || smokeDies) {
						if (AI_DEBUG_DJS)
							System.err.println("AIDBG ESC p=" + playerNum + " pos=(" + pos[0] + ","
									+ pos[1] + ") chosen=" + chosen + (denseSlowPack ? " dense-pack" : " smom-dies")
									+ " -> scorer rollout");
						chosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
								true, AI1_DJS_SLOW_ROUNDS);
					}
				}
			}
			return chosen;
		}
		if (bestLegal != null)
			return bestLegal;
		return fallback;
	}

	/**
	 * AI1 v5.1 queue-compression support (zandvoort forensic, round 21): count
	 * live rivals within squared distance 36 of the candidate landing (x,y)
	 * that are at-or-ahead of it in track progress and genuinely SLOWER than
	 * the landing speed. Ahead-ness reuses {@link #hasConvergingOpponentAhead}
	 * semantics exactly (same-progress slack +3, |diff| <= 15 wall exclusion);
	 * slower reuses its 1.0 speed margin. Two or more such rivals directly in
	 * front of a fast landing are a compressing corner queue -- traffic that
	 * will NOT have flowed on by the time I arrive, whatever the greedy
	 * round-sims claim.
	 */
	private int countSlowerRivalsAhead(final int x, final int y, final double mySpeed, final int playerNum) {
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
			if (dx * dx + dy * dy > 36)
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
			if (Math.hypot(pv[0], pv[1]) <= 2.5)
				count++;
		}
		return count;
	}

	/** AI1 frontier only (queueBox v3 long-range trigger): count STALLED
	 *  rivals (|v| <= 2.5, the {@link #countSlowerRivalsAhead} threshold)
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
			if (dx * dx + dy * dy > reachSq)
				continue;
			final int oDist = reach.distAt(pp[0], pp[1]);
			if (oDist == Integer.MAX_VALUE || myDist - oDist > reachCells + 3 || oDist > myDist + 3)
				continue; // behind me, or across a wall: no compression
			final int[] pv = p.getVelocity();
			if (Math.hypot(pv[0], pv[1]) <= 2.5)
				count++;
		}
		return count;
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
		for (final Direction d : DIRECTIONS) {
			final int newVx = vel[0] + d.dx;
			final int newVy = vel[1] + d.dy;
			if (Math.abs(newVx) > RaceGame.AI_MAX_SPEED || Math.abs(newVy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int newX = pos[0] + newVx;
			final int newY = pos[1] + newVy;
			if (game.crossesFinish(pos[0], pos[1], newX, newY))
				return d;
			final double sc = reach.scorePos(newX, newY, newVx, newVy);
			if (!game.isMoveLegalGeometryCached(pos[0], pos[1], newX, newY)) {
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
			final int turns = reach.turnsToFinish(newX, newY, newVx, newVy);
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

	/** Reusable two-round opponent projection. The reference arrays and every
	 *  generated coordinate/velocity pair are retained across candidate moves;
	 *  each pass only rewrites primitive values and swaps row references. */
	private TwoRoundWorkspace twoRoundWorkspace() {
		final int players = game.players.length;
		if (twoRoundWorkspace == null || twoRoundWorkspace.current.length != players)
			twoRoundWorkspace = new TwoRoundWorkspace(players);
		return twoRoundWorkspace;
	}

	/** Simulate two complete opponent rounds in actual turn order, conditioned
	 *  on my candidate landing. {@code world1} contains the cells for my next
	 *  move and {@code current} the cells for the move after that. */
	private TwoRoundWorkspace simulateTwoRounds(final int playerNum, final int candX, final int candY) {
		final TwoRoundWorkspace workspace = twoRoundWorkspace();
		final int[][] current = workspace.current;
		final int[][] simulatedVelocity = workspace.simulatedVelocity;
		java.util.Arrays.fill(current, null);
		java.util.Arrays.fill(workspace.world1, null);
		java.util.Arrays.fill(simulatedVelocity, null);
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int idx = p.getNumber() - 1;
			current[idx] = p.getPosition();
			simulatedVelocity[idx] = p.getVelocity();
		}
		System.arraycopy(current, 0, workspace.blocked, 0, current.length);
		workspace.candidatePosition[0] = candX;
		workspace.candidatePosition[1] = candY;
		workspace.blocked[playerNum - 1] = workspace.candidatePosition;
		simulateRoundPass(playerNum, current, simulatedVelocity, workspace.blocked,
				workspace.round1Position, workspace.round1Velocity);
		current[playerNum - 1] = null;
		System.arraycopy(current, 0, workspace.world1, 0, current.length);
		workspace.blocked[playerNum - 1] = null;
		simulateRoundPass(playerNum, current, simulatedVelocity, workspace.blocked,
				workspace.round2Position, workspace.round2Velocity);
		current[playerNum - 1] = null;
		return workspace;
	}

	/** One two-pass opponent round. A mover always receives a fresh logical
	 *  position row, but that row is caller-owned and reused on the next root;
	 *  a velocity row is replaced only when the move is legal, matching the
	 *  original stay-put semantics exactly. */
	private void simulateRoundPass(final int playerNum, final int[][] occupancy,
			final int[][] simulatedVelocity, final int[][] blocked,
			final int[][] nextPosition, final int[][] nextVelocity) {
		for (int pass = 0; pass < 2; pass++) {
			for (final Player p : game.players) {
				final boolean later = p.getNumber() > playerNum;
				if (p.getNumber() == playerNum || p.isFinished() || (pass == 0 ? !later : later))
					continue;
				final int idx = p.getNumber() - 1;
				final int[] current = occupancy[idx];
				blocked[idx] = null;
				final int[] velocity = simulatedVelocity[idx];
				final Direction direction = pureMinTurnsMoveSim(current, velocity, blocked);
				int nx = current[0];
				int ny = current[1];
				if (direction != null) {
					final int nvx = velocity[0] + direction.dx;
					final int nvy = velocity[1] + direction.dy;
					if (Math.abs(nvx) <= RaceGame.AI_MAX_SPEED && Math.abs(nvy) <= RaceGame.AI_MAX_SPEED
							&& game.isMoveLegalGeometryCached(current[0], current[1], current[0] + nvx, current[1] + nvy)
							&& !cellOccupiedByPrediction(current[0] + nvx, current[1] + nvy, blocked)) {
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
				blocked[idx] = positionOut;
			}
		}
	}

	/** Is cell (x,y) occupied in the simulated occupancy by a rival currently
	 *  strictly AHEAD of me on track ({@code myDist} from {@link #distAt})?
	 *  Chaser bodies are deliberately not priced: a detour ceded two rounds out
	 *  to a car behind me surrenders race position for nothing. */
	private boolean occupiedByAheadRival(final int x, final int y, final int[][] occupancy, final int myDist) {
		for (int i = 0; i < occupancy.length; i++) {
			final int[] cell = occupancy[i];
			if (cell != null && cell[0] == x && cell[1] == y) {
				final int[] rivalPos = game.players[i].getPosition();
				return reach.distAt(rivalPos[0], rivalPos[1]) < myDist;
			}
		}
		return false;
	}

	/** The champion's soft-priced depth-2 search (both AI bodies). Each of my
	 *  next TWO moves is searched explicitly: a {@code stepIdx == 0} landing on a
	 *  round-1 sim body is priced (+3.0, the conflict weight) rather than
	 *  hard-skipped, and a {@code stepIdx == 1} landing is priced only when the
	 *  round-2 body ({@code occupancy2}) belongs to a rival currently AHEAD of me
	 *  on track ({@code myDist} = distAt of my CURRENT cell), via
	 *  {@link #occupiedByAheadRival} instead of {@link #cellOccupiedByPrediction}.
	 *  A chaser's body is left unpriced; {@code myDist} threads unchanged through
	 *  the recursion. Geometry stays hard; a finish crossing escapes pricing. */
	private double searchMinTurnsSoft3(final int x, final int y, final int vx, final int vy, final int levels, final int stepIdx,
			final int[][][] predictedSteps, final int playerNum, final int[][] occupancy, final int[][] occupancy2,
			final int myDist) {
		if (levels == 0) {
			final int t = reach.turnsToFinish(x, y, vx, vy);
			return t == Integer.MAX_VALUE ? Double.MAX_VALUE : t;
		}
		double best = Double.MAX_VALUE;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny))
				return 1;
			if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			double price = 0.0;
			if (stepIdx == 0) {
				if (cellOccupiedByPrediction(nx, ny, occupancy))
					price = 3.0;
			} else {
				if (stepIdx < predictedSteps.length && cellOccupiedByPrediction(nx, ny, predictedSteps[stepIdx]))
					continue;
				if (stepIdx == 1 && occupancy2 != null && occupiedByAheadRival(nx, ny, occupancy2, myDist))
					price = AI1_PLY2_PRICE;
			}
			final double sub = searchMinTurnsSoft3(nx, ny, nvx, nvy, levels - 1, stepIdx + 1, predictedSteps, playerNum,
					occupancy, occupancy2, myDist);
			if (sub == Double.MAX_VALUE)
				continue;
			if (1.0 + price + sub < best)
				best = 1.0 + price + sub;
		}
		return best;
	}

	/** Plateau-counting twin of {@link #searchMinTurnsSoft3} (both AI bodies):
	 *  same ahead-only ply-2 pricing (at {@code stepIdx == 1} only bodies of
	 *  rivals AHEAD of me are priced), recursing into
	 *  {@link #searchMinTurnsSoft3}, and additionally reporting the plateau
	 *  width (how many follow-ups achieve the minimum) for the robustness
	 *  tie-break. {@code myDist} is threaded from the caller (distAt of my
	 *  CURRENT cell). Prices stay exact small constants, so the plateau compare
	 *  remains an exact {@code ==}. */
	private double[] searchMinTurnsCountedSoft3(final int x, final int y, final int vx, final int vy, final int levels,
			final int stepIdx, final int[][][] predictedSteps, final int playerNum, final int[][] occupancy,
			final int[][] occupancy2, final int myDist) {
		double best = Double.MAX_VALUE;
		int countAtMin = 0;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny))
				return new double[]{1, 9 };
			if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			double price = 0.0;
			if (stepIdx == 0) {
				if (cellOccupiedByPrediction(nx, ny, occupancy))
					price = 3.0;
			} else {
				if (stepIdx < predictedSteps.length && cellOccupiedByPrediction(nx, ny, predictedSteps[stepIdx]))
					continue;
				if (stepIdx == 1 && occupancy2 != null && occupiedByAheadRival(nx, ny, occupancy2, myDist))
					price = AI1_PLY2_PRICE;
			}
			final double sub = searchMinTurnsSoft3(nx, ny, nvx, nvy, levels - 1, stepIdx + 1, predictedSteps, playerNum,
					occupancy, occupancy2, myDist);
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
	private int countFutureSafeSuccessorsTimed(final int x, final int y, final int vx, final int vy, final int playerNum,
			final int[][] occupancy) {
		int count = 0;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx;
			final int nvy = vy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = x + nvx;
			final int ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny))
				return 9;
			if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			if (cellOccupiedByPrediction(nx, ny, occupancy))
				continue;
			if (reach.isAlive(nx, ny, nvx, nvy))
				count++;
		}
		return count;
	}

	/**
	 * Project each live opponent forward {@code steps} of their own moves using
	 * the pure min-turns policy. {@code result[k][opponentIdx]} is that
	 * opponent's position after {@code k+1} moves (null if it can't be
	 * projected that far).
	 */
	private int[][][] predictedOpponentSteps(final int myPlayerNum, final int steps) {
		final int projectionSteps = Math.max(1, steps);
		if (predictionWorkspace == null || predictionWorkspace.result.length != projectionSteps
				|| predictionWorkspace.result[0].length != game.players.length)
			predictionWorkspace = new PredictionWorkspace(projectionSteps, game.players.length);
		for (final int[][] step : predictionWorkspace.result)
			java.util.Arrays.fill(step, null);
		for (final Player player : game.players) {
			if (player.getNumber() == myPlayerNum || player.isFinished())
				continue;
			int px = player.getPosition()[0], py = player.getPosition()[1];
			int pvx = player.getVelocity()[0], pvy = player.getVelocity()[1];
			final int playerIndex = player.getNumber() - 1;
			for (int step = 0; step < steps; step++) {
				final Direction direction = pureMinTurnsMove(px, py, pvx, pvy, player.getNumber());
				if (direction == null)
					break;
				final int nvx = pvx + direction.dx;
				final int nvy = pvy + direction.dy;
				if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
					break;
				px += nvx;
				py += nvy;
				pvx = nvx;
				pvy = nvy;
				final int[] cell = predictionWorkspace.cells[step][playerIndex];
				cell[0] = px;
				cell[1] = py;
				predictionWorkspace.result[step][playerIndex] = cell;
			}
		}
		return predictionWorkspace.result;
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
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny))
				return writeMove(out, nx, ny, nvx, nvy);
			if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			boolean occupied = false;
			for (int j = 0; j < px.length; j++) {
				if (j == self || !alive[j])
					continue;
				if (px[j] == nx && py[j] == ny) {
					occupied = true;
					break;
				}
			}
			if (occupied || !reach.isAlive(nx, ny, nvx, nvy))
				continue;
			final int turns = reach.turnsToFinish(nx, ny, nvx, nvy);
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
		for (final Direction d : DIRECTIONS) {
			final int nvx = cvx + d.dx, nvy = cvy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny))
				return 3;
			if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			boolean occ = false;
			for (int j = 0; j < px.length; j++) {
				if (j == self || !alive[j])
					continue;
				if (px[j] == nx && py[j] == ny) {
					occ = true;
					break;
				}
			}
			if (occ || !reach.isAlive(nx, ny, nvx, nvy))
				continue;
			if (++count >= 3)
				return 3;
		}
		return count;
	}

	/** Round 51 (AI1 only): MY move inside the joint rollout. The real me is the
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
		for (final Direction d : DIRECTIONS) {
			final int nvx = cvx + d.dx, nvy = cvy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny))
				return writeMove(out, nx, ny, nvx, nvy);
			if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			boolean occupied = false;
			for (int j = 0; j < px.length; j++) {
				if (j == self || !alive[j])
					continue;
				if (px[j] == nx && py[j] == ny) {
					occupied = true;
					break;
				}
			}
			if (occupied || !reach.isAlive(nx, ny, nvx, nvy))
				continue;
			final int tier = safeSuccessorsOverState(nx, ny, nvx, nvy, self, px, py, alive);
			final int turns = reach.turnsToFinish(nx, ny, nvx, nvy);
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
		for (final Direction d : DIRECTIONS) {
			final int nvx = cvx + d.dx, nvy = cvy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny))
				return writeMove(out, nx, ny, nvx, nvy);
			if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			boolean occupied = false;
			for (int j = 0; j < px.length; j++) {
				if (j == self || !alive[j])
					continue;
				if (px[j] == nx && py[j] == ny) {
					occupied = true;
					break;
				}
			}
			if (occupied || !reach.isAlive(nx, ny, nvx, nvy))
				continue;
			final int tier = safeSuccessorsOverState(nx, ny, nvx, nvy, self, px, py, alive);
			final double trap = tier == 0 ? 50.0 : tier == 1 ? AI1_TRAP_L1 : tier == 2 ? AI1_TRAP_L2 : 0.0;
			final double score = reach.turnsToFinish(nx, ny, nvx, nvy) + trap;
			// Momentum tie-break (policy matrix "smom"): among score-equal
			// candidates the real scorer HOLDS SPEED down the racing line
			// (deep cost + momentum), so prefer the faster landing. This is
			// what reproduces the silverstone box; the trap term reproduces
			// the hungaroring corridor claim -- smom matches the real-scorer
			// reference on all four site/candidate cells of the matrix.
			final int spd2 = nvx * nvx + nvy * nvy;
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
	 *  recursive machinery suppressed (IN_SCORER_SIM), restores everything
	 *  in a finally. Writes the landing to {@code out} and returns true, or
	 *  returns false when the scorer is boxed or would enter a body/dead state. */
	private boolean scorerMoveOverState(final int i, final int[] px, final int[] py,
			final int[] vx, final int[] vy, final boolean[] alive, final int[] out,
			final ScorerWorkspace workspace) {
		final int n = game.players.length;
		final int ss = game.subgamestate;
		final boolean previousScorerSim = IN_SCORER_SIM;
		for (int j = 0; j < n; j++) {
			final Player player = game.players[j];
			workspace.originalPosition[j] = player.getPosition();
			workspace.originalVelocity[j] = player.getVelocity();
			workspace.finishedPlace[j] = player.getFinishedPlace();
		}
		final Direction direction;
		try {
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
			}
			game.subgamestate = i;
			IN_SCORER_SIM = true;
			direction = computeAiMove();
		} finally {
			IN_SCORER_SIM = previousScorerSim;
			for (int j = 0; j < n; j++) {
				final Player player = game.players[j];
				player.setPosition(workspace.originalPosition[j]);
				player.setVelocity(workspace.originalVelocity[j]);
				player.setFinishedPlace(workspace.finishedPlace[j]);
			}
			game.subgamestate = ss;
		}
		if (direction == null)
			return false;
		final int nvx = vx[i] + direction.dx, nvy = vy[i] + direction.dy;
		if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
			return false;
		final int nx = px[i] + nvx, ny = py[i] + nvy;
		if (game.crossesFinish(px[i], py[i], nx, ny))
			return writeMove(out, nx, ny, nvx, nvy);
		if (!game.isMoveLegalGeometryCached(px[i], py[i], nx, ny))
			return false;
		for (int j = 0; j < n; j++)
			if (j != i && alive[j] && px[j] == nx && py[j] == ny)
				return false;
		if (!reach.isAlive(nx, ny, nvx, nvy))
			return false;
		return writeMove(out, nx, ny, nvx, nvy);
	}

	private RolloutWorkspace rolloutWorkspace() {
		final int players = game.players.length;
		if (rolloutWorkspace == null || rolloutWorkspace.px.length != players)
			rolloutWorkspace = new RolloutWorkspace(players);
		return rolloutWorkspace;
	}

	/** Roll the joint game forward from MY candidate landing over a DETACHED
	 *  board copy: every car plays greedy min-turnsToFinish; move-order aware
	 *  (the first simulated round covers only the players who still move after
	 *  me this round). Returns my turnsToFinish after {@code rounds} full
	 *  rounds, or -1 if I end up boxed (no legal alive move at one of my
	 *  slots). No mutation of live players[] -- deterministic, cannot
	 *  livelock. AI1 only (round 40 danger joint search). */
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
		final RolloutWorkspace workspace = rolloutWorkspace();
		final int[] px = workspace.px;
		final int[] py = workspace.py;
		final int[] vx = workspace.vx;
		final int[] vy = workspace.vy;
		final boolean[] alive = workspace.alive;
		final boolean[] scorerSet = workspace.scorerSet;
		final int[] move = workspace.move;
		java.util.Arrays.fill(scorerSet, false);
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
			if (player.getNumber() == playerNum)
				myIdx = i;
		}
		px[myIdx] = myX;
		py[myIdx] = myY;
		vx[myIdx] = myVx;
		vy[myIdx] = myVy;
		// Round 59: slow-class fires roll the nearest rivals with their REAL
		// scorer (recursion-guarded); the rest keep the smom proxy.
		// Membership is fixed at rollout start: the nearest
		// AI1_SCORER_MAXRIVALS within Chebyshev AI1_SCORER_NEAR.
		if (scorerRivals) {
			for (int k = 0; k < scorerCap; k++) {
				int nearest = -1, nearestD = AI1_SCORER_NEAR + 1;
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
		for (int round = 0; round < rounds; round++) {
			// First simulated round: only players after me in this real round's
			// move order still move before my next slot.
			final int from = round == 0 ? game.subgamestate + 1 : 0;
			for (int i = from; i < game.players.length; i++) {
				if (!alive[i] || i == myIdx && round == 0)
					continue;
				// Round 51: my car follows the trap-aware policy. Round 57:
				// rivals use the score-shaped ttf + trap proxy; selected close
				// rivals instead use their recursion-guarded real scorer.
				final boolean moved;
				if (i == myIdx)
					moved = exactSelf
							? selfMoveOverState(px[i], py[i], vx[i], vy[i], i, px, py, alive, move)
							: greedyMoveOverState(px[i], py[i], vx[i], vy[i], i, px, py, alive, move);
				else if (scorerSet[i])
					moved = scorerMoveOverState(i, px, py, vx, vy, alive, move, workspace.scorer);
				else if (exactRivals)
					moved = rivalMoveOverState(px[i], py[i], vx[i], vy[i], i, px, py, alive, move);
				else
					moved = greedyMoveOverState(px[i], py[i], vx[i], vy[i], i, px, py, alive, move);
				if (simFinishVanish && moved && game.crossesFinish(px[i], py[i], move[0], move[1])) {
					if (i == myIdx) {
						if (outFinalTier != null)
							outFinalTier[0] = 3;
						return 0;
					}
					alive[i] = false;
					continue;
				}
				if (!moved) {
					if (i == myIdx)
						return -1;
					alive[i] = false;
					continue;
				}
				px[i] = move[0];
				py[i] = move[1];
				vx[i] = move[2];
				vy[i] = move[3];
			}
		}
		// Round 65: a surviving-but-fragile final (tier <= 1) is the
		// escalation signal for the 5-7-round doom class.
		if (outFinalTier != null)
			outFinalTier[0] = safeSuccessorsOverState(px[myIdx], py[myIdx], vx[myIdx], vy[myIdx],
					myIdx, px, py, alive);
		return reach.turnsToFinish(px[myIdx], py[myIdx], vx[myIdx], vy[myIdx]);
	}

	/** Danger joint search (round 40, AI1 only): if the chosen landing DIES in
	 *  the joint rollout, switch to the surviving candidate with the best
	 *  sim-final turnsToFinish; keep the chosen move in every other case. */
	private Direction dangerJointSearch(final int[] pos, final int[] vel, final int playerNum,
			final Direction chosen, final boolean simFinishVanish, final boolean exactSelf,
			final boolean exactRivals, final boolean scorerRivals, final int rounds) {
		return dangerJointSearch(pos, vel, playerNum, chosen, simFinishVanish, exactSelf,
				exactRivals, scorerRivals, rounds, AI1_SCORER_MAXRIVALS);
	}

	private Direction dangerJointSearch(final int[] pos, final int[] vel, final int playerNum,
			final Direction chosen, final boolean simFinishVanish, final boolean exactSelf,
			final boolean exactRivals, final boolean scorerRivals, final int rounds, final int scorerCap) {
		final int cvx = vel[0] + chosen.dx, cvy = vel[1] + chosen.dy;
		final int cx = pos[0] + cvx, cy = pos[1] + cvy;
		if (game.crossesFinish(pos[0], pos[1], cx, cy))
			return chosen;
		if (simOutcome(cx, cy, cvx, cvy, playerNum, rounds, simFinishVanish, exactSelf, exactRivals, scorerRivals,
				scorerCap, null) >= 0)
			return chosen;
		final boolean dbg = AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum;
		if (dbg)
			System.err.println("AIDBG DJS p=" + playerNum + " pos=(" + pos[0] + "," + pos[1] + ") vel=(" + vel[0]
					+ "," + vel[1] + ") chosen=" + chosen + " DIES in-sim");
		Direction best = null;
		int bestT = Integer.MAX_VALUE;
		for (final Direction d : DIRECTIONS) {
			if (d == chosen)
				continue;
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
			if (game.crossesFinish(pos[0], pos[1], nx, ny))
				return d;
			if (!game.isMoveLegalGeometryCached(pos[0], pos[1], nx, ny))
				continue;
			if (game.isCrashingPlayer(nx, ny, playerNum))
				continue;
			if (!reach.isAlive(nx, ny, nvx, nvy))
				continue;
			final int t = simOutcome(nx, ny, nvx, nvy, playerNum, rounds, simFinishVanish, exactSelf, exactRivals,
					scorerRivals, scorerCap, null);
			if (dbg)
				System.err.println("AIDBG DJS  alt " + d + " land=(" + nx + "," + ny + ") simT="
						+ (t < 0 ? "DIES" : String.valueOf(t)));
			if (t >= 0 && t < bestT) {
				bestT = t;
				best = d;
			}
		}
		if (dbg)
			System.err.println("AIDBG DJS  -> " + (best != null ? "SWITCH " + best + " simT=" + bestT
					: "KEEP " + chosen + " (no survivor)"));
		return best != null ? best : chosen;
	}

	/**
	 * AI2 (FROZEN STANDARD): the AI2.9 zero-conflict champion — the AI2.8
	 * pace-ceiling base (queue-sensing + always-on ahead-rival ply-2 foresight)
	 * with the predicted-cell conflict penalty ZEROED. That +3.0 was redundant
	 * soft caution atop the hard isCrashingPlayer collision check, so removing
	 * it takes more direct lines and claims contested cells a conflict&gt;0 field
	 * yields. Found by the mixed-field auto-tuner (v2) — invisible to same-AI
	 * hand-tuning. Gates: pace f=154 c=0 mv=63.81 vs AI2.8's 64.10 (FIRST
	 * sub-64.10, fastest zero-crash ever); h2h LANDSLIDE 3.926 vs 5.074 c=0
	 * (biggest margin of the campaign); --slow 80.05 vs 80.24. all-conflict0 is
	 * crash-free on all 22 (the hard check prevents real collisions among
	 * equally-aggressive cars); it wins by aggressive line-claiming that can
	 * squeeze a differently-behaving opponent into a wall (~1/59 mixed races) —
	 * a FEATURE in a racing game, per the user. Don't change AI2 — it's the
	 * yardstick; AI1 is the experimental copy being improved.
	 */
	private Direction optimalMoveAI2(final int[] pos, final int[] vel, final int playerNum) {
		// Endgame seal (per "force the last rival to crash = win"): with
		// few rivals left, if a SAFE move of mine leaves the decisive rival with no
		// legal move (a forced crash), take it. Only a rival that moves after me this
		// round (ri > subgamestate) can be forced; gated on my own safety so I never
		// trap myself to trap them.
		final int sealRivals = liveRivalsRemaining(playerNum);
		if (sealRivals >= 1 && sealRivals <= AI1_SEAL_MAXRIVALS) {
			final int ri = decisiveRival(playerNum);
			if (ri > game.subgamestate && rivalEscapes(ri, -1, -1, playerNum) >= 1) {
				final Direction sd = findForcedCrashMove(pos, vel, ri, playerNum);
				if (sd != null)
					return sd;
			}
		}
		// Endgame solver (round 43, PROMOTED round 44): 1v1 exact paranoid
		// minimax near the finish -- acts ONLY on proven wins; unproven values
		// fall through to the normal scorer. See endgameSolve.
		if (sealRivals == 1 && !IN_SCORER_SIM) {
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
		final int[][][] predictedSteps = predictedOpponentSteps(playerNum, 1);
		// Vacated-cell awareness: a fast-moving opponent (|v| >= 3) will have
		// moved through/off its predicted cell by the time I could occupy it --
		// blocking those cells causes phantom detours. Null out transiting
		// opponents' predictions; only slow/parked rivals stay blocked.
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pv = p.getVelocity();
			if (Math.hypot(pv[0], pv[1]) >= 3)
				predictedSteps[0][p.getNumber() - 1] = null;
		}
		final int[][] predicted = predictedSteps[0];
		// In-traffic ply-2 foresight RESTORED (fore2): the v4/v5 pack gate that
		// disabled the ply-2 price whenever any rival sat within squared
		// distance 36 is GONE -- the round-2 world (worlds[1]) is now priced on
		// every move. Ahead-rivals only: only bodies of rivals currently AHEAD
		// of me on track are priced (see occupiedByAheadRival +
		// searchMinTurnsCountedSoft3 below); a chaser's body is not priced,
		// since ceding a line two rounds out to a car behind me trades race
		// position for nothing. The queue brakes (queueBox, cornerEntry) now
		// guard the corridors the old gate was protecting.

		final CandidateWorkspace candidateWorkspace = candidateWorkspace();
		final double[] trapByDir = candidateWorkspace.trapByDirection;
		// round 49 arm C: non-spread score and raw map ttf per candidate, for the
		// certified pace tie-break after the loop.
		final double[] scoreNSByDir = candidateWorkspace.scoreWithoutSpread;
		final int[] poTByDir = candidateWorkspace.turnsByDirection;
		// round 63 (PROMOTED round 62): score and unc per candidate for the
		// certified UNC override -- see the AI1 body.
		final double[] scoreByDir = candidateWorkspace.scoreByDirection;
		final double[] uncByDir = candidateWorkspace.uncertaintyByDirection;
		MobilitySearch paceMobility = null;
		Direction best = null;
		double bestScore = Double.MAX_VALUE;
		Direction bestLegal = null;
		double bestLegalScore = Double.MAX_VALUE;
		Direction fallback = Direction.NONE;
		double fallbackScore = Double.MAX_VALUE;

		for (final Direction d : DIRECTIONS) {
			final int newVx = vel[0] + d.dx;
			final int newVy = vel[1] + d.dy;
			if (Math.abs(newVx) > RaceGame.AI_MAX_SPEED || Math.abs(newVy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int newX = pos[0] + newVx;
			final int newY = pos[1] + newVy;
			if (game.crossesFinish(pos[0], pos[1], newX, newY))
				return d;
			final double sc = reach.scorePos(newX, newY, newVx, newVy);
			if (!game.isMoveLegalGeometryCached(pos[0], pos[1], newX, newY)) {
				if (sc < fallbackScore) {
					fallbackScore = sc;
					fallback = d;
				}
				continue;
			}
			if (game.isCrashingPlayer(newX, newY, playerNum))
				continue;
			if (sc < bestLegalScore) {
				bestLegalScore = sc;
				bestLegal = d;
			}
			final int ownTurns = reach.turnsToFinish(newX, newY, newVx, newVy);
			if (ownTurns == Integer.MAX_VALUE)
				continue;

			// TWO-ROUND SOFT WORLD-STEP (the experiment): simulate TWO whole
			// rounds in actual turn order, conditioned on THIS candidate
			// landing. worlds[0] answers the round-r+1 questions (safe
			// successors, ply-1 pricing) exactly as before; worlds[1] gives the
			// bodies' cells when I make my round-r+2 move, pricing the second
			// explicit search ply -- ALWAYS on now (fore2, no pack gate), but
			// ahead-rivals only: searchMinTurnsCountedSoft3 prices the ply-2
			// landing only when the round-2 body belongs to a rival currently
			// AHEAD of me on track (myDist = distAt of my CURRENT cell); a
			// chaser's body is left unpriced (ceding a line two rounds out to
			// a car behind me trades race position for nothing).
			final TwoRoundWorkspace worlds = simulateTwoRounds(playerNum, newX, newY);
			final int[][] world = worlds.world1;
			final double[] deepCounted = searchMinTurnsCountedSoft3(newX, newY, newVx, newVy, AI1_DEEP_LOOKAHEAD, 0,
					predictedSteps, playerNum, worlds.world1, worlds.current, reach.distAt(pos[0], pos[1]));
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
			double trapPenalty = d2SafeCount == 0 ? 50.0
					: d2SafeCount == 1 ? 2.0
							: d2SafeCount == 2 ? 0.5
									: 0.0;
			// round 63 (PROMOTED round 61): rival-conditional trap relief -- a
			// 1-2-wide certified thread is uncontestable with no live rival
			// within AI1_TRAP_SOLO_R of the landing; the map's certification
			// suffices solo. 0-safe stays 50. See the AI1 body.
			if (trapPenalty > 0.0 && d2SafeCount > 0 && !rivalWithinCheb(newX, newY, playerNum, AI1_TRAP_SOLO_R))
				trapPenalty = 0.0;
			trapByDir[d.ordinal()] = trapPenalty;
			final double speed = Math.hypot(newVx, newVy);
			// Per-state certified budget with a legacy floor: the map-certified
			// minimal target T (>= 2 independent blind braking descents reach
			// |v| <= T from this candidate state) governs above the floor; the
			// floor preserves the zero-penalty regime at low speed.
			final int widthBudget = Math.max(5, reach.certBudget(newX, newY, newVx, newVy)) + d2SafeCount;
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
				if (roomySucc <= 1 && countNearbyOpponents(newX, newY, playerNum, 36) >= 2)
					cornerEntry = (speed - 4.0) * (roomySucc == 0 ? 3.0 : 1.5);
			}
			// v5.1 queue-compression corner guard (zandvoort forensic, AI1
			// only): the corner-entry brake above is opponent-BLIND in its
			// escape count, the brake proofs ignore transiting (|v| >= 3)
			// rivals, and the round-sims behind d2SafeCount and the ply-2
			// price assume a hairpin queue keeps flowing -- so a fast coast
			// whose timed margin is already thin (d2SafeCount <= 2) while
			// >= 2 SLOWER rivals sit within squared distance 36 at-or-ahead
			// of the landing (compression, not a chase) is one round from
			// being boxed: on zandvoort both alive continuations of
			// (43,66)v(-4,3) were bodily occupied by the compressed queue
			// when the victim arrived, after the coast had beaten the
			// covered brake by 0.278. Price the coast like the survivable
			// knife-edge corner entry ((speed-4) * 1.5) so the brake wins.
			double queueBox = 0.0;
			if (speed > 4.0 && cornerEntry == 0.0) {
				if (d2SafeCount <= 2 && countSlowerRivalsAhead(newX, newY, speed, playerNum) >= 2)
					queueBox = (speed - 4.0) * 1.5;
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
						queueBox = (speed - 4.0) * 1.5;
				}
			}
			final double conflict = cellOccupiedByPrediction(newX, newY, predicted) ? 0.0 : 0.0; // AI2.9: conflict penalty ZEROED (auto-tuner v2) -- +3.0 was redundant soft caution atop the hard isCrashingPlayer check; removing it is faster (63.81 vs 64.10) AND a landslide h2h win (3.926 vs 5.074), crash-free everywhere
			final double spread = opponentSpreadPenalty(newX, newY, playerNum);
			// Racing-line momentum tie-break: among moves of otherwise-equal cost,
			// prefer the one carrying more usable speed.
			final double momentum = AI2_MOMENTUM_TIEBREAK * speed;
			// Plateau-width robustness tie-break: prefer candidates whose best
			// follow-up is achievable many ways over knife-edge lines.
			final double robustness = AI2_PLATEAU_TIEBREAK * Math.min((int) deepCounted[1], 5);
			final double score = costToFinish + trapPenalty + speedCap + uncertified + cornerEntry + queueBox + conflict + spread - momentum - robustness;
			final int poT = reach.turnsArr != null && reach.isAlive(newX, newY, newVx, newVy)
					? reach.turnsArr[reach.aliveIdx(newX, newY, newVx, newVy)] : Integer.MAX_VALUE;
			scoreNSByDir[d.ordinal()] = score - spread;
			poTByDir[d.ordinal()] = poT;
			scoreByDir[d.ordinal()] = score;
			uncByDir[d.ordinal()] = uncertified;
			if (poT < poBestT) {
				if (paceMobility == null)
					paceMobility = mobilitySearch(playerNum, true, AI2_MOBILITY_DEPTH);
				final double poRoom = futureMobility(newX, newY, newVx, newVy, paceMobility);
				final int poSpd = Math.max(Math.abs(newVx), Math.abs(newVy));
				if (poRoom >= 0.88 || (poRoom >= 0.78 && poSpd <= 4)
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
		// Certified pace tie-break (rounds 48-53, PROMOTED round 54): mirror of
		// the AI1 frontier mechanism -- see optimalMoveAI1 for the derivation.
		// Override `spread` toward a strictly faster line only when CERTIFIED:
		// weakly better on every non-spread term (spread is the sole reason it
		// lost), zero trap penalty, not sealable, and it survives the
		// exact-self joint rollout. An uncertified faster line is never taken.
		if (best != null && !IN_SCORER_SIM) {
			final double bestNS = scoreNSByDir[best.ordinal()];
			int fastT = poTByDir[best.ordinal()];
			Direction fast = null;
			for (final Direction d : DIRECTIONS) {
				if (d == best || poTByDir[d.ordinal()] >= fastT)
					continue;
				if (scoreNSByDir[d.ordinal()] > bestNS + 1e-9)
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
			if (fast != null)
				best = fast;
		}
		// round 63 (PROMOTED round 62): certified UNC override -- pay the
		// surcharge everywhere except where a strictly faster line wins the
		// unc-free comparison AND passes zero trap + !sealable + survival in
		// the scorer-rival world. See the AI1 body for the derivation.
		if (best != null && !IN_SCORER_SIM) {
			final double bestNU = scoreByDir[best.ordinal()] - uncByDir[best.ordinal()];
			int fastT = poTByDir[best.ordinal()];
			Direction fast = null;
			for (final Direction d : DIRECTIONS) {
				if (d == best || poTByDir[d.ordinal()] >= fastT)
					continue;
				if (uncByDir[d.ordinal()] <= 0.0 || scoreByDir[d.ordinal()] == Double.MAX_VALUE)
					continue;
				if (scoreByDir[d.ordinal()] - uncByDir[d.ordinal()] > bestNU + 1e-9)
					continue;
				if (trapByDir[d.ordinal()] != 0.0)
					continue;
				final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
				final int nx = pos[0] + nvx, ny = pos[1] + nvy;
				if (sealable(nx, ny, nvx, nvy, playerNum))
					continue;
				if (simOutcome(nx, ny, nvx, nvy, playerNum, AI1_DJS_SLOW_ROUNDS, true, true, true, true) < 0)
					continue;
				fast = d;
				fastT = poTByDir[d.ordinal()];
			}
			if (fast != null)
				best = fast;
		}
		Direction chosen = (poDir != null && poBestT < poScorerT) ? poDir : best;
		if (chosen != null) {
			// r50 sealGuard v2: exact worst-case box check (distinct-opponent
			// matching, legality-checked covers). If the chosen landing is
			// sealable, take the FASTEST unsealable alternative instead.
			final int cvx = vel[0] + chosen.dx, cvy = vel[1] + chosen.dy;
			final int cx = pos[0] + cvx, cy = pos[1] + cvy;
			if (!game.crossesFinish(pos[0], pos[1], cx, cy) && sealable(cx, cy, cvx, cvy, playerNum)) {
				// Round 72 (PROMOTED): a worst-case seal warning must not force
				// the scorer into a strictly narrower local trap. See the AI1
				// body for the Nurburgring seed-19 derivation.
				final double chosenTrap = trapByDir[chosen.ordinal()];
				int bestT = Integer.MAX_VALUE;
				Direction safest = null;
				for (final Direction d : DIRECTIONS) {
					final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
					if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
						continue;
					final int nx = pos[0] + nvx, ny = pos[1] + nvy;
					if (game.crossesFinish(pos[0], pos[1], nx, ny)) {
						safest = d;
						bestT = -1;
						break;
					}
					if (!game.isMoveLegalGeometryCached(pos[0], pos[1], nx, ny))
						continue;
					if (game.isCrashingPlayer(nx, ny, playerNum))
						continue;
					if (!reach.isAlive(nx, ny, nvx, nvy))
						continue;
					if (trapByDir[d.ordinal()] > chosenTrap)
						continue;
					if (sealable(nx, ny, nvx, nvy, playerNum))
						continue;
					final int tt = reach.turnsArr != null ? reach.turnsArr[reach.aliveIdx(nx, ny, nvx, nvy)] : 0;
					if (tt < bestT) {
						bestT = tt;
						safest = d;
					}
				}
				if (safest != null)
					chosen = safest;
			}
			// Round 75 (PROMOTED): bounded near-finish pace recovery. A
			// strictly-faster low-trap candidate may replace the scorer choice
			// only when both independent joint models finish at the empty-map
			// lower bound. See the AI1 body for the Monaco seed-16 derivation.
			if (!IN_SCORER_SIM) {
				int sprintT = poTByDir[chosen.ordinal()];
				Direction sprint = null;
				for (final Direction d : DIRECTIONS) {
					final int t = poTByDir[d.ordinal()];
					if (d == chosen || t >= sprintT || t > AI1_FINISH_CERT_TTF
							|| trapByDir[d.ordinal()] > AI1_TRAP_L1)
						continue;
					final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
					final int nx = pos[0] + nvx, ny = pos[1] + nvy;
					final int rounds = t + 1;
					if (simOutcome(nx, ny, nvx, nvy, playerNum, rounds, true, true, true, false) != 0)
						continue;
					if (simOutcome(nx, ny, nvx, nvy, playerNum, rounds, true, true, true, true,
							AI1_DEEP_CERT_RIVALS, null) != 0)
						continue;
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
			// Danger joint search (round 40, PROMOTED): survival-only override
			// in flagged states -- see dangerJointSearch.
			if (AI_DEBUG_PLAYER == playerNum)
				System.err.println("AIDBG turn p=" + playerNum + " pos=(" + pos[0] + "," + pos[1] + ") vel=("
						+ vel[0] + "," + vel[1] + ") chosen=" + chosen + " trap=" + trapByDir[chosen.ordinal()]);
			// round 58 (PROMOTED): wide speed trigger (rounds 55) + smom rival
			// sim (round 57) -- matches AI1; see the frontier body for the
			// oracle derivation. Landing velocity recomputed: the sealGuard may
			// have swapped chosen.
			final int djvx = vel[0] + chosen.dx, djvy = vel[1] + chosen.dy;
			// round 63 (PROMOTED rounds 59+60): slow-class fires use the
			// real-scorer near-rival world at the 5-round horizon; trap-0 slow
			// moves get the smom smoke test that escalates to the scorer
			// rollout on a death verdict. Fast fires keep smom at 3 rounds.
			// round 66 (PROMOTED round 65): fast fires WITH a pack (>= 3 rivals
			// within Chebyshev 10 of the landing) run the deep smom pre-screen
			// and escalate to the scorer-rival world at horizon 8 on a
			// dead-or-fragile verdict -- the 5-7-round doom class.
			// round 68: trap-0 slow moves also escalate for the rare all-field
			// dense-pack shape. Round 69 (PROMOTED): a locally narrow fast pick
			// that smom proves dead may take a smom survivor only when the
			// independent scorer-rival world also certifies it alive.
			// Round 70 (PROMOTED): slow L1 traps extend the scorer-rival verdict
			// from five to six rounds, covering the interlagos four-car queue doom.
			// See the AI1 body for the oracle derivations.
			final boolean djSlow = djvx * djvx + djvy * djvy < AI1_DJS_SPD2;
			if (!IN_SCORER_SIM) {
				if (trapByDir[chosen.ordinal()] >= 0.5 || !djSlow) {
					final int dangerRounds = djSlow && trapByDir[chosen.ordinal()] >= AI1_TRAP_L1
							? AI1_DJS_SLOW_L1_ROUNDS
							: djSlow ? AI1_DJS_SLOW_ROUNDS : AI1_DJS_ROUNDS;
					boolean deepHandled = false;
					if (!djSlow) {
						final int dcx = pos[0] + djvx, dcy = pos[1] + djvy;
						int packNear = 0;
						for (final Player pp : game.players) {
							if (pp.getNumber() == playerNum || pp.isFinished())
								continue;
							final int[] ppos = pp.getPosition();
							if (Math.abs(ppos[0] - dcx) <= AI1_DEEP_PACK_R
									&& Math.abs(ppos[1] - dcy) <= AI1_DEEP_PACK_R)
								packNear++;
						}
						if (packNear >= AI1_DEEP_PACK && !game.crossesFinish(pos[0], pos[1], dcx, dcy)) {
							final int[] ft = rolloutWorkspace().finalTier;
							ft[0] = 3;
							final int dv = simOutcome(dcx, dcy, djvx, djvy, playerNum, AI1_DEEP_HORIZON,
									true, true, true, false, AI1_SCORER_MAXRIVALS, ft);
							if (dv < 0 || ft[0] <= 1) {
								if (AI_DEBUG_DJS)
									System.err.println("AIDBG DEEP p=" + playerNum + " pos=(" + pos[0] + ","
											+ pos[1] + ") chosen=" + chosen + " smom8 "
											+ (dv < 0 ? "dies" : "fragile") + " -> scorer rollout");
								Direction deepChoice = chosen;
								if (dv < 0 && trapByDir[chosen.ordinal()] >= AI1_TRAP_L2) {
									final Direction smomAlt = dangerJointSearch(pos, vel, playerNum, chosen,
											true, true, true, false, AI1_DEEP_HORIZON);
									if (smomAlt != chosen) {
										final int avx = vel[0] + smomAlt.dx, avy = vel[1] + smomAlt.dy;
										final int ax = pos[0] + avx, ay = pos[1] + avy;
										if (game.crossesFinish(pos[0], pos[1], ax, ay)
												|| simOutcome(ax, ay, avx, avy, playerNum, AI1_DEEP_HORIZON,
														true, true, true, true) >= 0) {
											deepChoice = smomAlt;
											if (AI_DEBUG_DJS)
												System.err.println("AIDBG DEEP p=" + playerNum
														+ " cross-model SWITCH " + chosen + " -> " + smomAlt);
										}
									}
								}
								if (deepChoice == chosen)
									deepChoice = dangerJointSearch(pos, vel, playerNum, chosen, true, true,
											true, true, AI1_DEEP_HORIZON);
								chosen = deepChoice;
								deepHandled = true;
							} else {
								// Round 74 (PROMOTED): certified convergence check. The
								// ahead-pack branch covers the Round 73 Interlagos case;
								// the compressed-rear-queue branch covers Zigzag s22 m72.
								int aheadNear = 0;
								for (final Player pp : game.players) {
									if (pp.getNumber() == playerNum || pp.isFinished())
										continue;
									final int[] ppos = pp.getPosition();
									if (Math.abs(ppos[0] - dcx) <= AI1_DEEP_PACK_R
											&& Math.abs(ppos[1] - dcy) <= AI1_DEEP_PACK_R
											&& (ppos[0] - dcx) * djvx + (ppos[1] - dcy) * djvy > 0)
										aheadNear++;
								}
								boolean closeEscape = false;
								final int chosenT = poTByDir[chosen.ordinal()];
								for (final Direction d : DIRECTIONS) {
									if (d != chosen && poTByDir[d.ordinal()] <= chosenT + 1
											&& trapByDir[d.ordinal()] <= AI1_TRAP_L2) {
										closeEscape = true;
										break;
									}
								}
								final int landingBodies = countRivalsWithinCheb(pos[0] + vel[0],
										pos[1] + vel[1], playerNum, 1);
								final boolean compressedRearQueue = packNear == sealRivals
										&& sealRivals >= AI1_SLOW_PACK && aheadNear <= 1
										&& landingBodies >= 2 && closeEscape;
								if (aheadNear >= AI1_DEEP_PACK || compressedRearQueue) {
									if (AI_DEBUG_DJS)
										System.err.println("AIDBG " + (compressedRearQueue ? "QUEUE" : "CORR")
												+ " p=" + playerNum + " pos=(" + pos[0] + "," + pos[1]
												+ ") chosen=" + chosen + " ahead=" + aheadNear
												+ " bodies=" + landingBodies
												+ " -> certified scorer check");
									chosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
											true, AI1_DJS_ROUNDS, AI1_DEEP_CERT_RIVALS);
									deepHandled = true;
								}
							}
						}
					}
					if (!deepHandled)
						chosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
								djSlow, dangerRounds);
				} else {
					// round 68 (PROMOTED round 67): the dense slow-pack escape
					// proof -- with the whole live field packed within Chebyshev
					// AI1_SLOW_PACK_R and a near-equal low-trap alternative on
					// the table, the scorer-rival rollout arbitrates even when
					// the smom smoke test reads alive (the lemans-s4 funnel).
					final int scvx = vel[0] + chosen.dx, scvy = vel[1] + chosen.dy;
					final int scx = pos[0] + scvx, scy = pos[1] + scvy;
					final int slowSpd2 = scvx * scvx + scvy * scvy;
					boolean closeEscape = false;
					final int chosenT = poTByDir[chosen.ordinal()];
					for (final Direction d : DIRECTIONS) {
						if (d != chosen && poTByDir[d.ordinal()] <= chosenT + 1
								&& trapByDir[d.ordinal()] <= AI1_TRAP_L2) {
							closeEscape = true;
							break;
						}
					}
					final int slowPack = countRivalsWithinCheb(scx, scy, playerNum, AI1_SLOW_PACK_R);
					// Round 71 (PROMOTED): generalise the dense-pack trigger to
					// four-car fields with a lower speed floor. Whole-field packing
					// and a near-equal low-trap escape keep the extra scorer rollout
					// narrowly tied to the Monaco seed-9 funnel class.
					final boolean packAll = slowPack == sealRivals && closeEscape;
					final boolean denseSlowPack = packAll && (sealRivals >= AI1_SLOW_PACK
							? slowSpd2 >= AI1_SLOW_PACK_SPD2
							: sealRivals >= AI1_SLOW_PACK_MIN && slowSpd2 >= AI1_SLOW_PACK_SPD2_SMALL);
					final boolean smokeDies = !game.crossesFinish(pos[0], pos[1], scx, scy)
							&& simOutcome(scx, scy, scvx, scvy, playerNum, AI1_DJS_SLOW_ROUNDS,
									true, true, true, false) < 0;
					if (denseSlowPack || smokeDies) {
						if (AI_DEBUG_DJS)
							System.err.println("AIDBG ESC p=" + playerNum + " pos=(" + pos[0] + ","
									+ pos[1] + ") chosen=" + chosen + (denseSlowPack ? " dense-pack" : " smom-dies")
									+ " -> scorer rollout");
						chosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
								true, AI1_DJS_SLOW_ROUNDS);
					}
				}
			}
			return chosen;
		}
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
		final int myDist = reach.distAt(x, y);
		if (myDist == Integer.MAX_VALUE)
			return true; // off-map: be conservative
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			final int dx = x - pp[0];
			final int dy = y - pp[1];
			if (dx * dx + dy * dy > 144)
				continue;
			final int oDist = reach.distAt(pp[0], pp[1]);
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

	/** Tiny penalty for ending up close to other live game.players, breaks lateral ties. */
	private double opponentSpreadPenalty(final int x, final int y, final int playerNum) {
		double penalty = 0;
		for (final Player p : game.players) {
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
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx;
			final int nvy = vy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = x + nvx;
			final int ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny))
				return 9;
			if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			if (game.isCrashingPlayer(nx, ny, playerNum))
				continue;
			if (cellOccupiedByPrediction(nx, ny, predicted))
				continue;
			if (reach.isAlive(nx, ny, nvx, nvy))
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
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx;
			final int nvy = vy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = x + nvx;
			final int ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny))
				return 9;
			if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			if (reach.isAlive(nx, ny, nvx, nvy) && isRoomy(nx, ny, nvx, nvy, 0))
				count++;
		}
		return count;
	}

	/** True iff a live player other than the one at (sx,sy) occupies (nx,ny). */
	private boolean cellOccupiedByLive(final int nx, final int ny, final int sx, final int sy) {
		for (final Player p : game.players) {
			if (p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			if (pp[0] == nx && pp[1] == ny && !(pp[0] == sx && pp[1] == sy))
				return true;
		}
		return false;
	}

	/** Number of rivals still racing (not finished, not crashed). */
	private int liveRivalsRemaining(final int playerNum) {
		int n = 0;
		for (final Player p : game.players)
			if (p.getNumber() != playerNum && !p.isFinished())
				n++;
		return n;
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
		int n = 0;
		for (final Direction d : DIRECTIONS) {
			final int nvx = rv[0] + d.dx, nvy = rv[1] + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = rp[0] + nvx, ny = rp[1] + nvy;
			if (game.crossesFinish(rp[0], rp[1], nx, ny))
				return 99;
			if (!game.isMoveLegalGeometryCached(rp[0], rp[1], nx, ny))
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

	/** A safe move of mine (alive, non-crashing, not self-sealable) that leaves
	 *  rival {@code ri} with zero legal moves -- forcing its crash this turn --
	 *  or null if none exists. */
	private Direction findForcedCrashMove(final int[] pos, final int[] vel, final int ri, final int playerNum) {
		for (final Direction d : DIRECTIONS) {
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
			if (game.crossesFinish(pos[0], pos[1], nx, ny))
				continue;
			if (!game.isMoveLegalGeometryCached(pos[0], pos[1], nx, ny))
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

	private java.util.HashMap<Long, Boolean>	egMemo;
	private int									egNodes;

	/** Lever 5 (round 43, AI1 only): 1v1 exact endgame solver. When the sole
	 *  live rival and I are both within {@link #AI1_EG_ETA} turns of the
	 *  finish, run a boolean paranoid minimax over the joint state (strict
	 *  me/rival alternation -- exact for two live movers regardless of index
	 *  order; landing-cell blocking, the campaign's board convention) to
	 *  {@link #AI1_EG_DEPTH} rounds. Returns the FASTEST move with a
	 *  guaranteed win (I cross first, or the rival is forced to crash while
	 *  my state stays alive) or null. A blown node budget claims nothing. */
	private Direction endgameSolve(final int[] pos, final int[] vel, final int playerNum) {
		final int ri = decisiveRival(playerNum);
		if (ri < 0)
			return null;
		final int myT = reach.turnsToFinish(pos[0], pos[1], vel[0], vel[1]);
		final int[] rp = game.players[ri].getPosition(), rv = game.players[ri].getVelocity();
		final int rT = reach.turnsToFinish(rp[0], rp[1], rv[0], rv[1]);
		if (myT > AI1_EG_ETA || rT > AI1_EG_ETA)
			return null;
		egMemo = new java.util.HashMap<>();
		egNodes = 0;
		Direction best = null;
		int bestT = Integer.MAX_VALUE;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
			if (game.crossesFinish(pos[0], pos[1], nx, ny))
				return d;		// immediate finish: the fastest win there is
			if (!game.isMoveLegalGeometryCached(pos[0], pos[1], nx, ny))
				continue;
			if (nx == rp[0] && ny == rp[1])
				continue;
			if (!reach.isAlive(nx, ny, nvx, nvy))
				continue;
			final int t = reach.turnsToFinish(nx, ny, nvx, nvy);
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
	 *  restrict it). A boxed rival crashes: my win iff my state is alive. */
	private boolean egRival(final int mx, final int my, final int mvx, final int mvy,
			final int rx, final int ry, final int rvx, final int rvy, final int depth) {
		egNodes++;
		if (depth <= 0)
			return false;		// horizon: no guarantee
		final long key = endgameMemoKey(mx, my, mvx, mvy, rx, ry, rvx, rvy, depth, true);
		final Boolean memo = egMemo.get(key);
		if (memo != null)
			return memo;
		boolean anyMove = false;
		boolean win = true;
		for (final Direction d : DIRECTIONS) {
			if (egNodes > AI1_EG_NODES) {
				win = false;	// budget: conservative, claim nothing
				break;
			}
			final int nvx = rvx + d.dx, nvy = rvy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = rx + nvx, ny = ry + nvy;
			if (game.crossesFinish(rx, ry, nx, ny)) {
				win = false;	// rival crosses first
				anyMove = true;
				break;
			}
			if (!game.isMoveLegalGeometryCached(rx, ry, nx, ny))
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
		egMemo.put(key, win);
		return win;
	}

	/** My ply: TRUE iff some alive (or finishing) move of mine keeps the
	 *  guaranteed win alive. */
	private boolean egMy(final int mx, final int my, final int mvx, final int mvy,
			final int rx, final int ry, final int rvx, final int rvy, final int depth) {
		egNodes++;
		if (depth <= 0)
			return false;
		final long key = endgameMemoKey(mx, my, mvx, mvy, rx, ry, rvx, rvy, depth, false);
		final Boolean memo = egMemo.get(key);
		if (memo != null)
			return memo;
		boolean win = false;
		for (final Direction d : DIRECTIONS) {
			if (egNodes > AI1_EG_NODES)
				break;
			final int nvx = mvx + d.dx, nvy = mvy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = mx + nvx, ny = my + nvy;
			if (game.crossesFinish(mx, my, nx, ny)) {
				win = true;
				break;
			}
			if (!game.isMoveLegalGeometryCached(mx, my, nx, ny))
				continue;
			if (nx == rx && ny == ry)
				continue;
			if (!reach.isAlive(nx, ny, nvx, nvy))
				continue;
			if (egRival(nx, ny, nvx, nvy, rx, ry, rvx, rvy, depth - 1)) {
				win = true;
				break;
			}
		}
		egMemo.put(key, win);
		return win;
	}

	/** Pack a joint endgame state into a collision-free memo key for every
	 *  supported grid coordinate: 9b coordinates, 5b velocity offsets (+12),
	 *  5b depth and 1b turn = 62 bits. */
	static long endgameMemoKey(final int mx, final int my, final int mvx, final int mvy,
			final int rx, final int ry, final int rvx, final int rvy, final int depth, final boolean rivalTurn) {
		long k = mx & 0x1FFL;
		k = k << 9 | my & 0x1FFL;
		k = k << 5 | mvx + 12 & 0x1FL;
		k = k << 5 | mvy + 12 & 0x1FL;
		k = k << 9 | rx & 0x1FFL;
		k = k << 9 | ry & 0x1FFL;
		k = k << 5 | rvx + 12 & 0x1FL;
		k = k << 5 | rvy + 12 & 0x1FL;
		k = k << 5 | depth & 0x1FL;
		k = k << 1 | (rivalTurn ? 1 : 0);
		return k;
	}

	/** TRUE iff state (x,y,vx,vy) is SEALABLE: opponents can jointly occupy
	 *  every escape (geometry-legal alive successor) with DISTINCT cars whose
	 *  landings are geometry-legal for them (worst-case physics, matching via
	 *  Kuhn). A finishing escape is never sealable. */
	private boolean sealable(final int x, final int y, final int vx, final int vy, final int playerNum) {
		int escapeCount = 0;
		for (final Direction direction : DIRECTIONS) {
			final int nvx = vx + direction.dx, nvy = vy + direction.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny))
				return false;
			if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
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
						&& game.isMoveLegalGeometryCached(position[0], position[1], ex, ey))
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
		final Double cached = search.memo.get(memoKey);
		if (cached != null)
			return cached;
		final java.util.HashSet<Long> b = search.blocked.get(ply - 1);
		if (ply == search.depth) {
			int cnt = 0;
			for (final Direction d : DIRECTIONS) {
				final int nvx = vx + d.dx, nvy = vy + d.dy;
				if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
					continue;
				final int nx = x + nvx, ny = y + nvy;
				if (game.crossesFinish(x, y, nx, ny)) {
					cnt++;
					continue;
				}
				if (b.contains(((long) nx << 32) | (ny & 0xffffffffL)))
					continue;
				if (reach.isAlive(nx, ny, nvx, nvy))
					cnt++;
			}
			final double result = cnt / 9.0;
			search.memo.put(memoKey, result);
			return result;
		}
		double best = 0.0;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny)) {
				search.memo.put(memoKey, 1.0);
				return 1.0;
			}
			if (b.contains(((long) nx << 32) | (ny & 0xffffffffL)))
				continue;
			if (!reach.isAlive(nx, ny, nvx, nvy))
				continue;
			final double v = fmRec(nx, ny, nvx, nvy, search, ply + 1);
			if (v > best) {
				best = v;
				if (best >= 1.0) {
					search.memo.put(memoKey, 1.0);
					return 1.0;
				}
			}
		}
		search.memo.put(memoKey, best);
		return best;
	}

	/** One immutable opponent projection plus a transposition table shared by
	 *  every candidate root in one real turn. Candidate roots overlap heavily;
	 *  rebuilding both structures for each root repeated the same search. */
	private static final class MobilitySearch {
		final int depth;
		final java.util.List<java.util.HashSet<Long>> blocked;
		final java.util.HashMap<Long, Double> memo = new java.util.HashMap<>();

		MobilitySearch(final int depth, final java.util.List<java.util.HashSet<Long>> blocked) {
			this.depth = depth;
			this.blocked = blocked;
		}
	}

	/** Build an N-ply opponent world once per AI turn. Opponents advance N
	 *  greedy steps, blocking their top-3 min-turns cells at each ply. */
	private MobilitySearch mobilitySearch(final int subjectNum, final boolean avoidOcc, final int depth) {
		final java.util.List<java.util.HashSet<Long>> blocked = new java.util.ArrayList<>();
		for (int k = 0; k < depth; k++)
			blocked.add(new java.util.HashSet<>());
		for (final Player opponent : game.players) {
			if (opponent.getNumber() == subjectNum || opponent.isFinished())
				continue;
			final int[] position = opponent.getPosition();
			final int[] velocity = opponent.getVelocity();
			int x = position[0], y = position[1], vx = velocity[0], vy = velocity[1];
			for (int k = 0; k < depth; k++) {
				if (!greedyStepBlockTop3(x, y, vx, vy, avoidOcc, blocked.get(k), mobilityMove))
					break;
				x = mobilityMove[0];
				y = mobilityMove[1];
				vx = mobilityMove[2];
				vy = mobilityMove[3];
			}
		}
		return new MobilitySearch(depth, blocked);
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

	/** Best greedy step; blocks the rival's up-to-3 lowest-turns cells. */
	private boolean greedyStepBlockTop3(final int x, final int y, final int vx, final int vy,
			final boolean avoidOcc, final java.util.HashSet<Long> block, final int[] out) {
		int t1 = Integer.MAX_VALUE, t2 = Integer.MAX_VALUE, t3 = Integer.MAX_VALUE;
		int x1 = 0, y1 = 0, vx1 = 0, vy1 = 0;
		int x2 = 0, y2 = 0, x3 = 0, y3 = 0;
		for (final Direction direction : DIRECTIONS) {
			final int nvx = vx + direction.dx, nvy = vy + direction.dy;
			if (Math.abs(nvx) > reach.aliveVMAX || Math.abs(nvy) > reach.aliveVMAX)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (nx < 0 || ny < 0 || nx >= reach.aliveW || ny >= reach.aliveH)
				continue;
			if (avoidOcc && cellOccupiedByLive(nx, ny, x, y))
				continue;
			final int turns = reach.turnsArr[reach.aliveIdx(nx, ny, nvx, nvy)];
			if (turns == Integer.MAX_VALUE)
				continue;
			if (turns < t1) {
				t3 = t2;
				x3 = x2;
				y3 = y2;
				t2 = t1;
				x2 = x1;
				y2 = y1;
				t1 = turns;
				x1 = nx;
				y1 = ny;
				vx1 = nvx;
				vy1 = nvy;
			} else if (turns < t2) {
				t3 = t2;
				x3 = x2;
				y3 = y2;
				t2 = turns;
				x2 = nx;
				y2 = ny;
			} else if (turns < t3) {
				t3 = turns;
				x3 = nx;
				y3 = ny;
			}
		}
		if (t1 == Integer.MAX_VALUE)
			return false;
		block.add(((long) x1 << 32) | (y1 & 0xffffffffL));
		if (t2 != Integer.MAX_VALUE)
			block.add(((long) x2 << 32) | (y2 & 0xffffffffL));
		if (t3 != Integer.MAX_VALUE)
			block.add(((long) x3 << 32) | (y3 & 0xffffffffL));
		return writeMove(out, x1, y1, vx1, vy1);
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
		for (final Direction bd : DIRECTIONS) {
			final int bvx = vx + bd.dx;
			final int bvy = vy + bd.dy;
			if (Math.abs(bvx) > RaceGame.AI_MAX_SPEED || Math.abs(bvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final double bSpeed = Math.hypot(bvx, bvy);
			if (bSpeed > speed)
				continue; // braking cone only
			final int bx = x + bvx;
			final int by = y + bvy;
			if (!game.isMoveLegalGeometryCached(x, y, bx, by))
				continue;
			if (!reach.isAlive(bx, by, bvx, bvy))
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
			final byte[] shedMap = requireRoomy ? reach.minShed2Roomy : reach.minShed2;
			final boolean shed;
			if (shedMap != null && targetSpeed >= 0 && targetSpeed == Math.rint(targetSpeed) && targetSpeed * targetSpeed < 255.0)
				shed = (shedMap[reach.aliveIdx(bx, by, bvx, bvy)] & 0xFF) <= targetSpeed * targetSpeed;
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
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx;
			final int nvy = vy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			if (Math.hypot(nvx, nvy) > speed)
				continue; // braking cone only
			final int nx = x + nvx;
			final int ny = y + nvy;
			if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			if (!reach.isAlive(nx, ny, nvx, nvy))
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
		// (always ready in practice: reach.ensureReachabilityReady() runs before any
		// AI move). States outside the precomputed space fall through to the
		// recursive body, which handles them exactly as before (its in-range
		// sub-calls hit the maps).
		final BitSet roomyMap = depth == 0 ? reach.roomy0 : depth == 1 ? reach.roomy1 : null;
		if (roomyMap != null && Math.abs(vx) <= reach.aliveVMAX && Math.abs(vy) <= reach.aliveVMAX && x >= 0 && y >= 0 && x < reach.aliveW
				&& y < reach.aliveH)
			return roomyMap.get(reach.aliveIdx(x, y, vx, vy));
		int count = 0;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx;
			final int nvy = vy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = x + nvx;
			final int ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny)) {
				count++;
			} else {
				if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
					continue;
				if (!reach.isAlive(nx, ny, nvx, nvy))
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

}
