#!/usr/bin/env python3
"""Apply the AI1-only Round 101 guarded-quorum acceleration candidate."""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()

old_latch = "\tprivate static boolean\t\t\tinTrueRivalConfirm;"
new_latch = "\tprivate boolean\t\t\t\tinTrueRivalConfirm;"
assert source.count(old_latch) == 1
source = source.replace(old_latch, new_latch, 1)

const_anchor = (
    "\tprivate final static int\t\tAI1_STAGED_MAX_SPEED2_GAIN\t= 9;"
    "\t// at most one |v|=4->5 axis of extra energy vs the scorer\n"
)
consts = const_anchor + (
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_MIN_TURNS\t= 29;"
    "\t// round 101: below this horizon the Spa counterexample outruns the finite rollout\n"
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_LONG_TURNS\t= 100;"
    "\t// a fixed eight-round proof is only a small slice of a three-digit tail\n"
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_MIN_SPEED2_GAIN\t= 16;"
    "\t// only decisive one-turn accelerations survived the counterexample screen\n"
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_MIN_AHEAD\t= 2;"
    "\t// require a forward pack, not an isolated or trailing-car re-rank\n"
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_MAX_AHEAD\t= 5;"
    "\t// six-ahead full-tail cases remain outside the bounded proof\n"
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_LONG_MIN_AHEAD\t= 5;"
    "\t// three-digit tails require the full bounded forward-pack quorum\n"
)
assert source.count(const_anchor) == 1
source = source.replace(const_anchor, consts, 1)

call = (
    "\t\t\tchosen = stagedPaceOverride(pos, vel, playerNum, chosen, scoreByDir, scoreNSByDir,\n"
    "\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n"
)
new_call = call + (
    "\t\t\tchosen = guardedFieldPaceOverride(pos, vel, playerNum, chosen,\n"
    "\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n"
)
assert source.count(call) == 2
source = source.replace(call, new_call, 1)

anchor = (
    "\tprivate Direction privatePaceOverride(final int[] pos, final int[] vel, final int playerNum,\n"
)
helper = r'''	/** Recover a one-turn acceleration only in a bounded forward pack when the
	 * same eight-round scorer world proves strict mover and aggregate-field
	 * gains. Near-finish lines and three-digit tails without the full forward
	 * quorum retain the incumbent because the finite rollout covers too little
	 * of their remaining race. */
	private Direction guardedFieldPaceOverride(final int[] pos, final int[] vel,
			final int playerNum, final Direction chosen, final double[] trapByDir,
			final double[] uncByDir, final int[] turnsByDir) {
		final int chosenT = turnsByDir[chosen.ordinal()];
		if (chosenT == Integer.MAX_VALUE || chosenT < AI1_FIELD_ACCEL_MIN_TURNS
				|| !kindHomogeneousRoster(playerNum))
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
		if (liveRivals < AI1_PRIVATE_FIELD_MIN_RIVALS
				|| rivalsAhead < AI1_FIELD_ACCEL_MIN_AHEAD
				|| rivalsAhead > AI1_FIELD_ACCEL_MAX_AHEAD || aheadProgress <= 0L
				|| chosenT >= AI1_FIELD_ACCEL_LONG_TURNS
						&& rivalsAhead < AI1_FIELD_ACCEL_LONG_MIN_AHEAD)
			return chosen;

		final int chosenVx = vel[0] + chosen.dx, chosenVy = vel[1] + chosen.dy;
		final int chosenX = pos[0] + chosenVx, chosenY = pos[1] + chosenVy;
		final int chosenSpeed2 = speedSquared(chosenVx, chosenVy);
		int chosenFinal = Integer.MIN_VALUE;
		long chosenField = Long.MAX_VALUE;
		Direction best = null;
		int bestFinal = Integer.MAX_VALUE;
		long bestField = Long.MAX_VALUE;
		for (final Direction d : DIRECTIONS) {
			final int turns = turnsByDir[d.ordinal()];
			if (d == chosen || d == Direction.NONE || turns == Integer.MAX_VALUE
					|| turns + 1 != chosenT || trapByDir[d.ordinal()] != 0.0
					|| uncByDir[d.ordinal()] != 0.0)
				continue;
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			if (speedSquared(nvx, nvy) - chosenSpeed2 < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN)
				continue;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
			if (sealable(nx, ny, nvx, nvy, playerNum))
				continue;
			if (chosenFinal == Integer.MIN_VALUE) {
				chosenFinal = scorerFieldOutcome(chosenX, chosenY, chosenVx, chosenVy, playerNum,
						AI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);
				chosenField = rolloutFieldCost[0];
				if (chosenFinal < 0 || chosenField >= ROLLOUT_FAILURE_COST)
					return chosen;
			}
			final int candidateFinal = scorerFieldOutcome(nx, ny, nvx, nvy, playerNum,
					AI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);
			final long candidateField = rolloutFieldCost[0];
			if (candidateFinal < 0 || candidateFinal >= chosenFinal
					|| candidateField >= chosenField)
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

'''
assert source.count(anchor) == 1
source = source.replace(anchor, helper + anchor, 1)
path.write_text(source)
