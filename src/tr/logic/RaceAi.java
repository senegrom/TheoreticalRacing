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

	RaceAi(final RaceGame game) {
		this.game = game;
		this.reach = game.reach;
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
	/** Forensic gates: -Dai.debug.player=N per-turn pick dump for that player;
	 *  -Dai.debug.djs DJS-death events for ALL players. Both off by default. */
	private final static int		AI_DEBUG_PLAYER	= Integer.getInteger("ai.debug.player", -1);
	private final static boolean	AI_DEBUG_DJS	= Boolean.getBoolean("ai.debug.djs");
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
				final Direction sd = findForcedCrashMove(pos, vel, ri, playerNum, false);
				if (sd != null)
					return sd;
			}
		}
		// Endgame solver (round 43, lever 5, AI1 only): 1v1 exact paranoid
		// minimax near the finish. Acts ONLY on proven wins (I finish first or
		// the rival is forced to crash under its best defense) -- the deep
		// generalization of the 1-ply seal above; unproven values fall through
		// to the normal scorer (insurance-premium law: no paranoid defense).
		if (sealRivals == 1) {
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

		final double[] trapByDir = new double[Direction.values().length];
		Direction best = null;
		double bestScore = Double.MAX_VALUE;
		Direction bestLegal = null;
		double bestLegalScore = Double.MAX_VALUE;
		Direction fallback = Direction.NONE;
		double fallbackScore = Double.MAX_VALUE;

		for (final Direction d : Direction.values()) {
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
			final int[][][] worlds = simulateTwoRounds(playerNum, newX, newY);
			final int[][] world = worlds[0];
			final double[] deepCounted = searchMinTurnsCountedSoft3(newX, newY, newVx, newVy, AI1_DEEP_LOOKAHEAD, 0,
					predictedSteps, playerNum, worlds[0], worlds[1], reach.distAt(pos[0], pos[1]));
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
					: d2SafeCount == 1 ? AI1_TRAP_L1
							: d2SafeCount == 2 ? AI1_TRAP_L2
									: 0.0;
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
				if (roomySucc <= 1 && countNearbyOpponents(new int[]{newX, newY }, playerNum, AI1_PACK_R2) >= 2)
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
			if (poT < poBestT) {
				final double poRoom = futureMobility4(newX, newY, newVx, newVy, playerNum, true);
				final int poSpd = Math.max(Math.abs(newVx), Math.abs(newVy));
				if (poRoom >= AI1_PO_ROOM_HI || (poRoom >= AI1_PO_ROOM_MID && poSpd <= AI1_PO_SPD_MAX)
						|| (sealRivals <= AI1_SPARSE_RIVALS && poRoom >= AI1_PACE_FLOOR
							&& !sealable(newX, newY, newVx, newVy, playerNum, false))) {
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
		Direction chosen = (poDir != null && poBestT < poScorerT) ? poDir : best;
		if (chosen != null) {
			// r50 sealGuard v2: exact worst-case box check (distinct-opponent
			// matching, legality-checked covers). If the chosen landing is
			// sealable, take the FASTEST unsealable alternative instead.
			final int cvx = vel[0] + chosen.dx, cvy = vel[1] + chosen.dy;
			final int cx = pos[0] + cvx, cy = pos[1] + cvy;
			if (!game.crossesFinish(pos[0], pos[1], cx, cy) && sealable(cx, cy, cvx, cvy, playerNum, false)) {
				int bestT = Integer.MAX_VALUE;
				Direction safest = null;
				for (final Direction d : Direction.values()) {
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
					if (sealable(nx, ny, nvx, nvy, playerNum, false))
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
			if (trapByDir[chosen.ordinal()] >= 0.5)
				chosen = dangerJointSearch(pos, vel, playerNum, chosen);
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
		for (final Direction d : Direction.values()) {
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

	/** Step every live opponent one move in ACTUAL turn order, conditioned on
	 *  my candidate landing: game.players numbered after me take their round-r move
	 *  (they see my landing and all earlier sim moves), then game.players numbered
	 *  before me take their round-r+1 move. Movers use the greedy policy
	 *  against the updating occupancy; a mover with no legal unoccupied move
	 *  stays put. Returns occupancy[i] = player (i+1)'s simulated cell when I
	 *  make my next move (null for me and finished game.players).
	 *  <p>
	 *  Velocity note: every mover steps once from its CURRENT velocity, and
	 *  that is timing-exact for BOTH classes -- later movers' current state is
	 *  pre-round-r (their round-r move is the one simulated), while earlier
	 *  movers already moved this round, so their current velocity is
	 *  post-round-r and one step from it IS their round-r+1 move. Only the
	 *  policy (greedy min-turns instead of each opponent's real scorer) is
	 *  approximate; the sequencing and mutual exclusion are exact. */
	private int[][] simulateRound(final int playerNum, final int candX, final int candY) {
		final int[][] occ = new int[game.players.length][];
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			occ[p.getNumber() - 1] = p.getPosition();
		}
		final int[][] blocked = occ.clone();           // shallow: shares position refs
		blocked[playerNum - 1] = new int[]{candX, candY }; // my landing blocks
		// later movers (round r), then earlier movers (round r+1), each once
		for (int pass = 0; pass < 2; pass++) {
			for (final Player p : game.players) {
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
					if (Math.abs(nvx) <= RaceGame.AI_MAX_SPEED && Math.abs(nvy) <= RaceGame.AI_MAX_SPEED
							&& game.isMoveLegalGeometryCached(cur[0], cur[1], cur[0] + nvx, cur[1] + nvy)
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
		final int[][] occ = new int[game.players.length][];
		final int[][] simVel = new int[game.players.length][];
		for (final Player p : game.players) {
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
	 *  turn order (game.players numbered after me first, then game.players numbered
	 *  before me), updating {@code occ}/{@code simVel}/{@code blocked} in
	 *  place. Mirrors {@link #simulateRound}'s loop exactly; the only addition
	 *  is recording the step a legal mover already took into {@code simVel}
	 *  (a stay-put mover keeps its old velocity). */
	private void simulateRoundPass(final int playerNum, final int[][] occ, final int[][] simVel, final int[][] blocked) {
		for (int pass = 0; pass < 2; pass++) {
			for (final Player p : game.players) {
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
					if (Math.abs(nvx) <= RaceGame.AI_MAX_SPEED && Math.abs(nvy) <= RaceGame.AI_MAX_SPEED
							&& game.isMoveLegalGeometryCached(cur[0], cur[1], cur[0] + nvx, cur[1] + nvy)
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
		for (final Direction d : Direction.values()) {
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
		for (final Direction d : Direction.values()) {
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
		for (final Direction d : Direction.values()) {
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
		final int[][][] result = new int[Math.max(1, steps)][][];
		for (int k = 0; k < result.length; k++)
			result[k] = new int[game.players.length][];
		for (final Player p : game.players) {
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
				if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
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


	/** Greedy min-turnsToFinish move for a car at (x,y) vel (cvx,cvy) over a
	 *  DETACHED array board (alive cars at px/py). Returns {nx,ny,nvx,nvy} for the
	 *  best legal, non-crashing, alive move, or null if boxed. Used by simOutcome. */
	private int[] greedyMoveOverState(final int x, final int y, final int cvx, final int cvy, final int self,
			final int[] px, final int[] py, final boolean[] alive) {
		int bestT = Integer.MAX_VALUE;
		int[] best = null;
		for (final Direction d : Direction.values()) {
			final int nvx = cvx + d.dx, nvy = cvy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny))
				return new int[]{nx, ny, nvx, nvy };
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
			if (occ)
				continue;
			if (!reach.isAlive(nx, ny, nvx, nvy))
				continue;
			final int tt = reach.turnsToFinish(nx, ny, nvx, nvy);
			if (tt < bestT) {
				bestT = tt;
				best = new int[]{nx, ny, nvx, nvy };
			}
		}
		return best;
	}

	/** Roll the joint game forward from MY candidate landing over a DETACHED
	 *  board copy: every car plays greedy min-turnsToFinish; move-order aware
	 *  (the first simulated round covers only the players who still move after
	 *  me this round). Returns my turnsToFinish after {@code rounds} full
	 *  rounds, or -1 if I end up boxed (no legal alive move at one of my
	 *  slots). No mutation of live players[] -- deterministic, cannot
	 *  livelock. AI1 only (round 40 danger joint search). */
	private int simOutcome(final int myX, final int myY, final int myVx, final int myVy,
			final int playerNum, final int rounds) {
		final int n = game.players.length;
		final int[] px = new int[n], py = new int[n], vx = new int[n], vy = new int[n];
		final boolean[] alive = new boolean[n];
		int myIdx = 0;
		for (int i = 0; i < n; i++) {
			final Player p = game.players[i];
			final int[] pp = p.getPosition(), pv = p.getVelocity();
			px[i] = pp[0];
			py[i] = pp[1];
			vx[i] = pv[0];
			vy[i] = pv[1];
			alive[i] = !p.isFinished();
			if (p.getNumber() == playerNum)
				myIdx = i;
		}
		px[myIdx] = myX;
		py[myIdx] = myY;
		vx[myIdx] = myVx;
		vy[myIdx] = myVy;
		for (int r = 0; r < rounds; r++) {
			// First simulated round: only players after me in this real round's
			// move order still move before my next slot.
			final int from = r == 0 ? game.subgamestate + 1 : 0;
			for (int i = from; i < n; i++) {
				if (!alive[i] || i == myIdx && r == 0)
					continue;
				final int[] mv = greedyMoveOverState(px[i], py[i], vx[i], vy[i], i, px, py, alive);
				if (mv == null) {
					if (i == myIdx)
						return -1;
					alive[i] = false;
					continue;
				}
				px[i] = mv[0];
				py[i] = mv[1];
				vx[i] = mv[2];
				vy[i] = mv[3];
			}
		}
		return reach.turnsToFinish(px[myIdx], py[myIdx], vx[myIdx], vy[myIdx]);
	}

	/** Danger joint search (round 40, AI1 only): if the chosen landing DIES in
	 *  the joint rollout, switch to the surviving candidate with the best
	 *  sim-final turnsToFinish; keep the chosen move in every other case. */
	private Direction dangerJointSearch(final int[] pos, final int[] vel, final int playerNum,
			final Direction chosen) {
		final int cvx = vel[0] + chosen.dx, cvy = vel[1] + chosen.dy;
		final int cx = pos[0] + cvx, cy = pos[1] + cvy;
		if (game.crossesFinish(pos[0], pos[1], cx, cy))
			return chosen;
		if (simOutcome(cx, cy, cvx, cvy, playerNum, AI1_DJS_ROUNDS) >= 0)
			return chosen;
		final boolean dbg = AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum;
		if (dbg)
			System.err.println("AIDBG DJS p=" + playerNum + " pos=(" + pos[0] + "," + pos[1] + ") vel=(" + vel[0]
					+ "," + vel[1] + ") chosen=" + chosen + " DIES in-sim");
		Direction best = null;
		int bestT = Integer.MAX_VALUE;
		for (final Direction d : Direction.values()) {
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
			final int t = simOutcome(nx, ny, nvx, nvy, playerNum, AI1_DJS_ROUNDS);
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
				final Direction sd = findForcedCrashMove(pos, vel, ri, playerNum, false);
				if (sd != null)
					return sd;
			}
		}
		// Endgame solver (round 43, PROMOTED round 44): 1v1 exact paranoid
		// minimax near the finish -- acts ONLY on proven wins; unproven values
		// fall through to the normal scorer. See endgameSolve.
		if (sealRivals == 1) {
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

		final double[] trapByDir = new double[Direction.values().length];
		Direction best = null;
		double bestScore = Double.MAX_VALUE;
		Direction bestLegal = null;
		double bestLegalScore = Double.MAX_VALUE;
		Direction fallback = Direction.NONE;
		double fallbackScore = Double.MAX_VALUE;

		for (final Direction d : Direction.values()) {
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
			final int[][][] worlds = simulateTwoRounds(playerNum, newX, newY);
			final int[][] world = worlds[0];
			final double[] deepCounted = searchMinTurnsCountedSoft3(newX, newY, newVx, newVy, AI1_DEEP_LOOKAHEAD, 0,
					predictedSteps, playerNum, worlds[0], worlds[1], reach.distAt(pos[0], pos[1]));
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
				if (roomySucc <= 1 && countNearbyOpponents(new int[]{newX, newY }, playerNum, 36) >= 2)
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
			if (poT < poBestT) {
				final double poRoom = futureMobility4(newX, newY, newVx, newVy, playerNum, true);
				final int poSpd = Math.max(Math.abs(newVx), Math.abs(newVy));
				if (poRoom >= 0.88 || (poRoom >= 0.78 && poSpd <= 4)
						|| (sealRivals <= AI1_SPARSE_RIVALS && poRoom >= AI1_PACE_FLOOR
							&& !sealable(newX, newY, newVx, newVy, playerNum, false))) {
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
		Direction chosen = (poDir != null && poBestT < poScorerT) ? poDir : best;
		if (chosen != null) {
			// r50 sealGuard v2: exact worst-case box check (distinct-opponent
			// matching, legality-checked covers). If the chosen landing is
			// sealable, take the FASTEST unsealable alternative instead.
			final int cvx = vel[0] + chosen.dx, cvy = vel[1] + chosen.dy;
			final int cx = pos[0] + cvx, cy = pos[1] + cvy;
			if (!game.crossesFinish(pos[0], pos[1], cx, cy) && sealable(cx, cy, cvx, cvy, playerNum, false)) {
				int bestT = Integer.MAX_VALUE;
				Direction safest = null;
				for (final Direction d : Direction.values()) {
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
					if (sealable(nx, ny, nvx, nvy, playerNum, false))
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
			// Danger joint search (round 40, PROMOTED): survival-only override
			// in flagged states -- see dangerJointSearch.
			if (AI_DEBUG_PLAYER == playerNum)
				System.err.println("AIDBG turn p=" + playerNum + " pos=(" + pos[0] + "," + pos[1] + ") vel=("
						+ vel[0] + "," + vel[1] + ") chosen=" + chosen + " trap=" + trapByDir[chosen.ordinal()]);
			if (trapByDir[chosen.ordinal()] >= 0.5)
				chosen = dangerJointSearch(pos, vel, playerNum, chosen);
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

	/** Count live opponents within squared distance r2 of (pos). */
	private int countNearbyOpponents(final int[] pos, final int playerNum, final int r2) {
		int count = 0;
		for (final Player p : game.players) {
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
		for (final Direction d : Direction.values()) {
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
		for (final Direction d : Direction.values()) {
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
		for (final Direction d : Direction.values()) {
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
	private Direction findForcedCrashMove(final int[] pos, final int[] vel, final int ri, final int playerNum,
			final boolean selfByIndex) {
		for (final Direction d : Direction.values()) {
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
			if (sealable(nx, ny, nvx, nvy, playerNum, selfByIndex))
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
		for (final Direction d : Direction.values()) {
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
		final Long key = egKey(mx, my, mvx, mvy, rx, ry, rvx, rvy, depth, true);
		final Boolean memo = egMemo.get(key);
		if (memo != null)
			return memo;
		boolean anyMove = false;
		boolean win = true;
		for (final Direction d : Direction.values()) {
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
		final Long key = egKey(mx, my, mvx, mvy, rx, ry, rvx, rvy, depth, false);
		final Boolean memo = egMemo.get(key);
		if (memo != null)
			return memo;
		boolean win = false;
		for (final Direction d : Direction.values()) {
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

	/** Pack a joint endgame state into a memo key: 8b coords, 5b velocity
	 *  offsets (+12), 5b depth, 1b turn = 58 bits. */
	private Long egKey(final int mx, final int my, final int mvx, final int mvy,
			final int rx, final int ry, final int rvx, final int rvy, final int depth, final boolean rivalTurn) {
		long k = mx;
		k = k << 8 | my;
		k = k << 5 | mvx + 12;
		k = k << 5 | mvy + 12;
		k = k << 8 | rx;
		k = k << 8 | ry;
		k = k << 5 | rvx + 12;
		k = k << 5 | rvy + 12;
		k = k << 5 | depth;
		k = k << 1 | (rivalTurn ? 1 : 0);
		return k;
	}

	/** TRUE iff state (x,y,vx,vy) is SEALABLE: opponents can jointly occupy
	 *  every escape (geometry-legal alive successor) with DISTINCT cars whose
	 *  landings are geometry-legal for them (worst-case physics, matching via
	 *  Kuhn). A finishing escape is never sealable. */
	private boolean sealable(final int x, final int y, final int vx, final int vy, final int playerNum,
			final boolean selfByIndex) {
		final java.util.List<int[]> esc = new java.util.ArrayList<>();
		for (final Direction d : Direction.values()) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny))
				return false;
			if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			if (!reach.isAlive(nx, ny, nvx, nvy))
				continue;
			esc.add(new int[]{nx, ny });
		}
		if (esc.isEmpty())
			return true; // already dead-ended
		final int ne = esc.size();
		if (ne > 7)
			return false; // more escapes than opponents
		// cover[e] = bitmask of opponents that can legally land on escape e
		final int[] cover = new int[ne];
		int oi = 0;
		for (int i = 0; i < game.players.length; i++) {
			// selfByIndex=true preserves the champion's off-by-one (index-vs-number:
			// self included as a phantom cover, rival number playerNum+1 ignored);
			// false is the fix (round 42, AI1). Flip on promotion.
			if ((selfByIndex ? i == playerNum : game.players[i].getNumber() == playerNum)
					|| game.players[i].isFinished())
				continue;
			final int bit = 1 << oi;
			oi++;
			final int[] op = game.players[i].getPosition();
			final int[] ov = game.players[i].getVelocity();
			final int cx = op[0] + ov[0], cy = op[1] + ov[1];
			for (int e = 0; e < ne; e++) {
				if (Math.abs(esc.get(e)[0] - cx) <= 1 && Math.abs(esc.get(e)[1] - cy) <= 1
						&& game.isMoveLegalGeometryCached(op[0], op[1], esc.get(e)[0], esc.get(e)[1]))
					cover[e] |= bit;
			}
		}
		// Kuhn's matching: every escape needs a DISTINCT opponent
		final int[] matchOpp = new int[8];
		java.util.Arrays.fill(matchOpp, -1);
		for (int e = 0; e < ne; e++) {
			if (!sealAugment(e, cover, matchOpp, new boolean[8]))
				return false; // this escape cannot get a distinct cover
		}
		return true;
	}

	private boolean sealAugment(final int e, final int[] cover, final int[] matchOpp, final boolean[] used) {
		for (int o = 0; o < 8; o++) {
			if ((cover[e] & (1 << o)) == 0 || used[o])
				continue;
			used[o] = true;
			if (matchOpp[o] < 0 || sealAugment(matchOpp[o], cover, matchOpp, used)) {
				matchOpp[o] = e;
				return true;
			}
		}
		return false;
	}

	/** Generic N-ply escape headroom: max over alive moves (dodging predicted
	 *  traffic per ply) with the leaf ply scored as the alive-fraction. */
	private double fmRec(final int x, final int y, final int vx, final int vy,
			final java.util.List<java.util.HashSet<Long>> blocked, final int ply, final int depth) {
		final java.util.HashSet<Long> b = blocked.get(ply - 1);
		if (ply == depth) {
			int cnt = 0;
			for (final Direction d : Direction.values()) {
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
			return cnt / 9.0;
		}
		double best = 0.0;
		for (final Direction d : Direction.values()) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (Math.abs(nvx) > RaceGame.AI_MAX_SPEED || Math.abs(nvy) > RaceGame.AI_MAX_SPEED)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny))
				return 1.0;
			if (b.contains(((long) nx << 32) | (ny & 0xffffffffL)))
				continue;
			if (!reach.isAlive(nx, ny, nvx, nvy))
				continue;
			final double v = fmRec(nx, ny, nvx, nvy, blocked, ply + 1, depth);
			if (v > best) {
				best = v;
				if (best >= 1.0)
					return 1.0;
			}
		}
		return best;
	}

	/** 4-ply escape headroom (see fmRec); opponents advance 4 greedy steps,
	 *  blocking their top-3 min-turns cells each ply (robust to prediction error). */
	private double futureMobility4(final int x, final int y, final int vx, final int vy,
			final int subjectNum, final boolean avoidOcc) {
		if (reach.turnsArr == null)
			return 1.0;
		final java.util.List<java.util.HashSet<Long>> blocked = new java.util.ArrayList<>();
		for (int k = 0; k < 4; k++)
			blocked.add(new java.util.HashSet<>());
		for (int i = 0; i < game.players.length; i++) {
			if (i == subjectNum || game.players[i].isFinished())
				continue;
			final int[] p = game.players[i].getPosition();
			int[] cur = new int[]{p[0], p[1], game.players[i].getVelocity()[0], game.players[i].getVelocity()[1] };
			for (int k = 0; k < 4; k++) {
				cur = greedyStepBlockTop3(cur[0], cur[1], cur[2], cur[3], avoidOcc, blocked.get(k));
				if (cur == null)
					break;
			}
		}
		return fmRec(x, y, vx, vy, blocked, 1, 4);
	}

	/** Best greedy step; blocks the rival's up-to-3 lowest-turns cells. */
	private int[] greedyStepBlockTop3(final int x, final int y, final int vx, final int vy,
			final boolean avoidOcc, final java.util.HashSet<Long> block) {
		int t1 = Integer.MAX_VALUE, t2 = Integer.MAX_VALUE, t3 = Integer.MAX_VALUE;
		int[] c1 = null, c2 = null, c3 = null;
		for (final Direction d : Direction.values()) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (Math.abs(nvx) > reach.aliveVMAX || Math.abs(nvy) > reach.aliveVMAX)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (nx < 0 || ny < 0 || nx >= reach.aliveW || ny >= reach.aliveH)
				continue;
			if (avoidOcc && cellOccupiedByLive(nx, ny, x, y))
				continue;
			final int t = reach.turnsArr[reach.aliveIdx(nx, ny, nvx, nvy)];
			if (t >= Integer.MAX_VALUE)
				continue;
			if (t < t1) {
				t3 = t2; c3 = c2;
				t2 = t1; c2 = c1;
				t1 = t; c1 = new int[]{nx, ny, nvx, nvy };
			} else if (t < t2) {
				t3 = t2; c3 = c2;
				t2 = t; c2 = new int[]{nx, ny, nvx, nvy };
			} else if (t < t3) {
				t3 = t; c3 = new int[]{nx, ny, nvx, nvy };
			}
		}
		if (c1 == null)
			return null;
		block.add(((long) c1[0] << 32) | (c1[1] & 0xffffffffL));
		if (c2 != null)
			block.add(((long) c2[0] << 32) | (c2[1] & 0xffffffffL));
		if (c3 != null)
			block.add(((long) c3[0] << 32) | (c3[1] & 0xffffffffL));
		return c1;
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
		for (final Direction d : Direction.values()) {
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
		for (final Direction d : Direction.values()) {
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
