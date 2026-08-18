#!/usr/bin/env python3
"""Materialize the Round 116 high-speed moderate-acceleration experiment.

Round 115 safely admitted speed-squared gains 9..15 only below the speed-7
threshold. This experiment leaves every promoted decision untouched and tests
only the excluded high-speed, near-range class with a longer 12-round scorer-
field proof. The existing trap, uncertainty, funnel, seal and downstream
danger vetoes remain authoritative. AI2 stays the frozen control.
"""
from pathlib import Path

PATH = Path("src/tr/logic/RaceAi.java")
source = PATH.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global source
    count = source.count(old)
    assert count == 1, (label, count)
    source = source.replace(old, new, 1)


replace_once(
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_FRONTIER_LOW_GAIN_MAX_TTF\t= 45;"
    "\t// round 115: short-range boundary for speed2 gains 9..15\n",
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_FRONTIER_LOW_GAIN_MAX_TTF\t= 45;"
    "\t// round 115: short-range boundary for speed2 gains 9..15\n"
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_HIGH_SPEED_PROOF_ROUNDS\t= 12;"
    "\t// round 116: longer proof for the excluded high-speed near-range class\n",
    "proof constant",
)

replace_once(
    "\t\t\tchosen = guardedFieldPaceOverride(pos, vel, playerNum, chosen,\n"
    "\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n",
    "\t\t\tfinal Direction fieldIncumbent = chosen;\n"
    "\t\t\tchosen = guardedFieldPaceOverride(pos, vel, playerNum, fieldIncumbent,\n"
    "\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n"
    "\t\t\tif (chosen == fieldIncumbent)\n"
    "\t\t\t\tchosen = highSpeedFieldPaceOverride(pos, vel, playerNum, fieldIncumbent,\n"
    "\t\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n",
    "AI1 call",
)

helper_anchor = (
    "\t/** Round 106: recover a one-turn acceleration only in a bounded forward\n"
)
helper = r'''	/** Round 116 experiment: recover a moderate one-turn acceleration outside
	 * Round 115's low-speed box only when a twelve-round scorer-field world
	 * proves strict mover and aggregate-field progress. The current Round 106/
	 * 115 decision retains priority, so this method can only affect the excluded
	 * high-speed, TTF<=45, speed-squared-gain 9..15 class. */
	private Direction highSpeedFieldPaceOverride(final int[] pos, final int[] vel,
			final int playerNum, final Direction chosen, final double[] trapByDir,
			final double[] uncByDir, final int[] turnsByDir) {
		if (moverKind(playerNum) != Player.Kind.AI1 || chosen == Direction.NONE
				|| !kindHomogeneousRoster(playerNum))
			return chosen;
		final int chosenT = turnsByDir[chosen.ordinal()];
		if (chosenT == Integer.MAX_VALUE
				|| chosenT < AI1_FINISH_HOMOGENEOUS_TTF + 2
				|| chosenT > AI1_FIELD_ACCEL_FRONTIER_LOW_GAIN_MAX_TTF)
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
				|| rivalsAhead > AI1_FIELD_ACCEL_MAX_AHEAD
				|| aheadProgress <= 0L)
			return chosen;

		final int chosenVx = vel[0] + chosen.dx, chosenVy = vel[1] + chosen.dy;
		final int chosenX = pos[0] + chosenVx, chosenY = pos[1] + chosenVy;
		final int chosenSpeed2 = speedSquared(chosenVx, chosenVy);
		if (chosenSpeed2 < AI1_DJS_SPD2)
			return chosen;

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
			final int speed2 = speedSquared(nvx, nvy);
			final int speed2Gain = speed2 - chosenSpeed2;
			if (speed2Gain < AI1_FIELD_ACCEL_FRONTIER_MIN_SPEED2_GAIN
					|| speed2Gain >= AI1_FIELD_ACCEL_MIN_SPEED2_GAIN)
				continue;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
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
				chosenFinal = scorerFieldOutcome(chosenX, chosenY, chosenVx, chosenVy,
						playerNum, AI1_FIELD_ACCEL_HIGH_SPEED_PROOF_ROUNDS,
						AI1_DEEP_CERT_RIVALS, rolloutFieldCost);
				chosenField = rolloutFieldCost[0];
				if (chosenFinal < 0 || chosenField >= ROLLOUT_FAILURE_COST)
					return chosen;
			}
			final int candidateFinal = scorerFieldOutcome(nx, ny, nvx, nvy,
					playerNum, AI1_FIELD_ACCEL_HIGH_SPEED_PROOF_ROUNDS,
					AI1_DEEP_CERT_RIVALS, rolloutFieldCost);
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
			System.err.println("AIDBG FIELD-H12 p=" + playerNum + " pos=("
					+ pos[0] + "," + pos[1] + ") " + chosen + " -> " + best
					+ " ttf " + chosenT + " -> " + turnsByDir[best.ordinal()]
					+ " ahead=" + rivalsAhead + " progress=" + aheadProgress
					+ " self " + chosenFinal + " -> " + bestFinal
					+ " field " + chosenField + " -> " + bestField);
		return best != null ? best : chosen;
	}

'''
replace_once(helper_anchor, helper + helper_anchor, "helper insertion")

assert source.count("private Direction highSpeedFieldPaceOverride(") == 1
assert source.count("chosen = highSpeedFieldPaceOverride(") == 1
assert source.count("AIDBG FIELD-H12") == 1
PATH.write_text(source)
print("materialized Round 116 high-speed 12-round field proof")
