#!/usr/bin/env python3
"""Materialize Round 121's per-rival Pareto acceleration certificate.

The promoted field-acceleration rule compares the mover and aggregate rival
cost. That is intentionally strict, but a short aggregate can hide one modeled
rival getting worse while another improves. This AI1-only experiment adds an
optional per-rival cost vector to the existing scorer rollout, then screens a
broader one-turn acceleration class only when:

* the 12-round scorer world strictly improves the mover;
* aggregate rival cost strictly improves;
* every modeled rival is individually no worse;
* the landing is zero-trap, zero-uncertainty and unsealable; and
* all existing downstream seal and danger vetoes still run.

The promoted guardedFieldPaceOverride retains priority and AI2 remains frozen.
No track, seed, coordinate, player or direction identity is encoded.
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
    "\tprivate final long[] rolloutFieldCost = new long[1];\n",
    "\tprivate final long[] rolloutFieldCost = new long[1];\n"
    "\tprivate long[] paretoChosenFieldCost;\n"
    "\tprivate long[] paretoCandidateFieldCost;\n",
    "per-rival storage",
)

replace_once(
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_SIX_AHEAD_ROUNDS\t= 8;"
    "\t// round 117: synchronized six-ahead formations retain the established proof depth\n",
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_SIX_AHEAD_ROUNDS\t= 8;"
    "\t// round 117: synchronized six-ahead formations retain the established proof depth\n"
    "\tprivate final static int\t\tAI1_PARETO_VECTOR_MIN_SPEED2_GAIN\t= 4;\n"
    "\tprivate final static int\t\tAI1_PARETO_VECTOR_MIN_AHEAD\t= 1;\n"
    "\tprivate final static int\t\tAI1_PARETO_VECTOR_MAX_AHEAD\t= 7;\n"
    "\tprivate final static int\t\tAI1_PARETO_VECTOR_MAX_TTF\t= 90;\n"
    "\tprivate final static int\t\tAI1_PARETO_VECTOR_ROUNDS\t= 12;\n"
    "\tprivate final static int\t\tAI1_PARETO_VECTOR_SCORER_CAP\t= 7;\n",
    "pareto constants",
)

replace_once(
    "\t\t\tchosen = guardedFieldPaceOverride(pos, vel, playerNum, chosen,\n"
    "\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n",
    "\t\t\tfinal Direction fieldIncumbent = chosen;\n"
    "\t\t\tchosen = guardedFieldPaceOverride(pos, vel, playerNum, fieldIncumbent,\n"
    "\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n"
    "\t\t\tif (chosen == fieldIncumbent)\n"
    "\t\t\t\tchosen = paretoVectorFieldPaceOverride(pos, vel, playerNum, fieldIncumbent,\n"
    "\t\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n",
    "AI1 call",
)

helper_anchor = "\n\t/** Round 117 candidate-formation proof: a previously moved rival is\n"
helper = r'''
	private long[] paretoFieldCostVector(final boolean candidate) {
		final int required = game.players.length + 1;
		if (candidate) {
			if (paretoCandidateFieldCost == null || paretoCandidateFieldCost.length != required)
				paretoCandidateFieldCost = new long[required];
			return paretoCandidateFieldCost;
		}
		if (paretoChosenFieldCost == null || paretoChosenFieldCost.length != required)
			paretoChosenFieldCost = new long[required];
		return paretoChosenFieldCost;
	}

	private boolean fieldVectorNoWorse(final long[] candidate, final long[] chosen,
			final int playerNum) {
		for (int i = 0; i < game.players.length; i++) {
			if (game.players[i].getNumber() == playerNum)
				continue;
			if (candidate[i + 1] > chosen[i + 1])
				return false;
		}
		return true;
	}

	/** Round 121 experiment: broaden one-turn acceleration only when a longer
	 * scorer rollout gives a strict mover and aggregate-field gain plus an
	 * individual no-regression certificate for every rival. The promoted field
	 * rule runs first; this method sees only its unchanged incumbents. */
	private Direction paretoVectorFieldPaceOverride(final int[] pos, final int[] vel,
			final int playerNum, final Direction chosen, final double[] trapByDir,
			final double[] uncByDir, final int[] turnsByDir) {
		if (moverKind(playerNum) != Player.Kind.AI1 || chosen == Direction.NONE
				|| !kindHomogeneousRoster(playerNum))
			return chosen;
		final int chosenT = turnsByDir[chosen.ordinal()];
		if (chosenT == Integer.MAX_VALUE
				|| chosenT < AI1_FINISH_HOMOGENEOUS_TTF + 2
				|| chosenT > AI1_PARETO_VECTOR_MAX_TTF)
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
				|| rivalsAhead < AI1_PARETO_VECTOR_MIN_AHEAD
				|| rivalsAhead > AI1_PARETO_VECTOR_MAX_AHEAD
				|| aheadProgress <= 0L)
			return chosen;

		final int chosenVx = vel[0] + chosen.dx, chosenVy = vel[1] + chosen.dy;
		final int chosenX = pos[0] + chosenVx, chosenY = pos[1] + chosenVy;
		final int chosenSpeed2 = speedSquared(chosenVx, chosenVy);
		final long[] chosenVector = paretoFieldCostVector(false);
		final long[] candidateVector = paretoFieldCostVector(true);
		int chosenFinal = Integer.MIN_VALUE;
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
			if (speed2 - chosenSpeed2 < AI1_PARETO_VECTOR_MIN_SPEED2_GAIN)
				continue;
			if (turns <= AI1_FINISH_EXTENDED_TTF && speed2 < AI1_DJS_SPD2)
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
						playerNum, AI1_PARETO_VECTOR_ROUNDS,
						AI1_PARETO_VECTOR_SCORER_CAP, chosenVector);
				if (chosenFinal < 0 || chosenVector[0] >= ROLLOUT_FAILURE_COST)
					return chosen;
			}
			final int candidateFinal = scorerFieldOutcome(nx, ny, nvx, nvy,
					playerNum, AI1_PARETO_VECTOR_ROUNDS,
					AI1_PARETO_VECTOR_SCORER_CAP, candidateVector);
			if (candidateFinal < 0 || candidateFinal >= chosenFinal
					|| candidateVector[0] >= chosenVector[0]
					|| !fieldVectorNoWorse(candidateVector, chosenVector, playerNum))
				continue;
			if (best == null || candidateFinal < bestFinal
					|| candidateFinal == bestFinal && candidateVector[0] < bestField) {
				best = d;
				bestFinal = candidateFinal;
				bestField = candidateVector[0];
			}
		}
		if (best != null && AI_DEBUG_DJS)
			System.err.println("AIDBG PARETO-VECTOR p=" + playerNum + " pos=("
					+ pos[0] + "," + pos[1] + ") " + chosen + " -> " + best
					+ " ttf " + chosenT + " -> " + turnsByDir[best.ordinal()]
					+ " ahead=" + rivalsAhead + " progress=" + aheadProgress
					+ " self " + chosenFinal + " -> " + bestFinal
					+ " field " + chosenVector[0] + " -> " + bestField);
		return best != null ? best : chosen;
	}

'''
replace_once(helper_anchor, "\n" + helper + helper_anchor, "pareto helper insertion")

replace_once(
    "\t\tif (outFieldCost != null)\n"
    "\t\t\toutFieldCost[0] = 0L;\n",
    "\t\tif (outFieldCost != null)\n"
    "\t\t\tjava.util.Arrays.fill(outFieldCost, 0L);\n",
    "field vector reset",
)

replace_once(
    "\t\t\t\tif (!moved) {\n"
    "\t\t\t\t\tif (i == myIdx)\n"
    "\t\t\t\t\t\treturn -1;\n"
    "\t\t\t\t\talive[i] = false;\n"
    "\t\t\t\t\tif (outFieldCost != null)\n"
    "\t\t\t\t\t\tfailedRivalCost += ROLLOUT_FAILURE_COST;\n"
    "\t\t\t\t\tcontinue;\n"
    "\t\t\t\t}\n",
    "\t\t\t\tif (!moved) {\n"
    "\t\t\t\t\tif (i == myIdx)\n"
    "\t\t\t\t\t\treturn -1;\n"
    "\t\t\t\t\talive[i] = false;\n"
    "\t\t\t\t\tif (outFieldCost != null) {\n"
    "\t\t\t\t\t\tfailedRivalCost += ROLLOUT_FAILURE_COST;\n"
    "\t\t\t\t\t\tif (outFieldCost.length > i + 1)\n"
    "\t\t\t\t\t\t\toutFieldCost[i + 1] = ROLLOUT_FAILURE_COST;\n"
    "\t\t\t\t\t}\n"
    "\t\t\t\t\tcontinue;\n"
    "\t\t\t\t}\n",
    "failed rival vector cost",
)

replace_once(
    "\t\t\t\tfinal int turns = reach.turnsToFinish(px[i], py[i], vx[i], vy[i]);\n"
    "\t\t\t\tfieldCost += turns == Integer.MAX_VALUE ? ROLLOUT_FAILURE_COST : turns;\n",
    "\t\t\t\tfinal int turns = reach.turnsToFinish(px[i], py[i], vx[i], vy[i]);\n"
    "\t\t\t\tfinal long rivalCost = turns == Integer.MAX_VALUE\n"
    "\t\t\t\t\t\t? ROLLOUT_FAILURE_COST : turns;\n"
    "\t\t\t\tfieldCost += rivalCost;\n"
    "\t\t\t\tif (outFieldCost.length > i + 1)\n"
    "\t\t\t\t\toutFieldCost[i + 1] = rivalCost;\n",
    "live rival vector cost",
)

assert source.count("private Direction paretoVectorFieldPaceOverride(") == 1
assert source.count("chosen = paretoVectorFieldPaceOverride(") == 1
assert source.count("AIDBG PARETO-VECTOR") == 1
assert source.count("private Direction optimalMoveAI2") == 1
PATH.write_text(source)
print("materialized Round 121 per-rival Pareto acceleration proof")
