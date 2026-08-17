#!/usr/bin/env python3
"""Materialize a broader acceleration arm with a per-rival rollout proof.

Round 106 compares only the aggregate projected field cost.  That proof is
strong enough for its narrow admission gates, but an equal aggregate can hide
one simulated rival getting worse while another gets better.  This experiment
adds an optional per-rival cost vector to the existing scorer rollout and uses
it to admit a broader one-turn acceleration only when:

* the mover is strictly better after the same eight-round scorer rollout;
* every simulated rival is individually no worse;
* no rival fails, the candidate is unsealable, and the existing downstream
  seal and danger vetoes still run; and
* the rule remains track/seed/coordinate independent and AI1-only.
"""
from __future__ import annotations

from pathlib import Path

PATH = Path("src/tr/logic/RaceAi.java")
source = PATH.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global source
    count = source.count(old)
    assert count == 1, (label, count)
    source = source.replace(old, new, 1)


# Reusable output vectors.  Existing callers continue to pass the one-element
# aggregate scratch array and therefore remain byte-for-byte behaviourally
# unchanged.
replace_once(
    "\tprivate final long[] rolloutFieldCost = new long[1];\n",
    "\tprivate final long[] rolloutFieldCost = new long[1];\n"
    "\tprivate long[] paretoChosenFieldCost;\n"
    "\tprivate long[] paretoCandidateFieldCost;\n",
    "field-vector storage",
)

replace_once(
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_MAX_TTF\t= 90;"
    "\t// keep the 8-round proof in the medium-range race phase\n",
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_MAX_TTF\t= 90;"
    "\t// keep the 8-round proof in the medium-range race phase\n"
    "\tprivate final static int\t\tAI1_PARETO_FIELD_MIN_SPEED2_GAIN\t= 9;"
    "\t// round 110: broader acceleration requires per-rival monotonicity\n"
    "\tprivate final static int\t\tAI1_PARETO_FIELD_MIN_AHEAD\t= 1;\n"
    "\tprivate final static int\t\tAI1_PARETO_FIELD_MAX_AHEAD\t= 6;\n"
    "\tprivate final static int\t\tAI1_PARETO_FIELD_CORRIDOR_AHEAD\t= 5;\n"
    "\tprivate final static int\t\tAI1_PARETO_FIELD_MAX_TTF\t= 120;\n",
    "pareto constants",
)

# AI1 only.  AI2 remains the frozen comparator.
replace_once(
    "\t\t\tchosen = guardedFieldPaceOverride(pos, vel, playerNum, chosen,\n"
    "\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n",
    "\t\t\tchosen = guardedFieldPaceOverride(pos, vel, playerNum, chosen,\n"
    "\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n"
    "\t\t\tchosen = paretoFieldPaceOverride(pos, vel, playerNum, chosen,\n"
    "\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n",
    "AI1 pareto call",
)

helper_anchor = (
    "\tprivate Direction privatePaceOverride(final int[] pos, final int[] vel, final int playerNum,\n"
)
helper = r'''	private long[] paretoFieldCostVector(final boolean candidate) {
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

	/** Round 110 experiment: broaden the decisive-acceleration class only when
	 * the existing scorer rollout gives a strict mover gain and an individual
	 * no-regression certificate for every rival.  This complements rather than
	 * replaces Round 106, preserving every already-promoted acceleration. */
	private Direction paretoFieldPaceOverride(final int[] pos, final int[] vel,
			final int playerNum, final Direction chosen, final double[] trapByDir,
			final double[] uncByDir, final int[] turnsByDir) {
		final int chosenT = turnsByDir[chosen.ordinal()];
		if (chosenT == Integer.MAX_VALUE
				|| chosenT < AI1_FINISH_HOMOGENEOUS_TTF + 2
				|| chosenT > AI1_PARETO_FIELD_MAX_TTF
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
				|| rivalsAhead < AI1_PARETO_FIELD_MIN_AHEAD
				|| rivalsAhead > AI1_PARETO_FIELD_MAX_AHEAD
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
			if (speed2 - chosenSpeed2 < AI1_PARETO_FIELD_MIN_SPEED2_GAIN)
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
				if (rivalsAhead < AI1_PARETO_FIELD_CORRIDOR_AHEAD
						|| aheadProgress < (long) chosenSpan + candidateSpan)
					continue;
			}
			if (sealable(nx, ny, nvx, nvy, playerNum))
				continue;

			if (chosenFinal == Integer.MIN_VALUE) {
				chosenFinal = scorerFieldOutcome(chosenX, chosenY, chosenVx, chosenVy,
						playerNum, AI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, chosenVector);
				if (chosenFinal < 0 || chosenVector[0] >= ROLLOUT_FAILURE_COST)
					return chosen;
			}
			final int candidateFinal = scorerFieldOutcome(nx, ny, nvx, nvy,
					playerNum, AI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, candidateVector);
			if (candidateFinal < 0 || candidateFinal >= chosenFinal
					|| candidateVector[0] > chosenVector[0]
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
			System.err.println("AIDBG PARETO-FIELD p=" + playerNum + " pos=("
					+ pos[0] + "," + pos[1] + ") " + chosen + " -> " + best
					+ " ttf " + chosenT + " -> " + turnsByDir[best.ordinal()]
					+ " ahead=" + rivalsAhead + " progress=" + aheadProgress
					+ " self " + chosenFinal + " -> " + bestFinal
					+ " field " + chosenVector[0] + " -> " + bestField);
		return best != null ? best : chosen;
	}

'''
replace_once(helper_anchor, helper + helper_anchor, "pareto helper insertion")

# A one-element array keeps the legacy aggregate-only contract.  Larger arrays
# get aggregate cost at index 0 and the cost for player-array index i at i+1.
replace_once(
    "\t\tif (outFieldCost != null)\n"
    "\t\t\toutFieldCost[0] = 0L;\n",
    "\t\tif (outFieldCost != null)\n"
    "\t\t\tjava.util.Arrays.fill(outFieldCost, 0L);\n",
    "field-vector reset",
)

replace_once(
    "\t\t\t\t\tif (outFieldCost != null)\n"
    "\t\t\t\t\t\tfailedRivalCost += ROLLOUT_FAILURE_COST;\n",
    "\t\t\t\t\tif (outFieldCost != null) {\n"
    "\t\t\t\t\t\tfailedRivalCost += ROLLOUT_FAILURE_COST;\n"
    "\t\t\t\t\t\tif (outFieldCost.length > i + 1)\n"
    "\t\t\t\t\t\t\toutFieldCost[i + 1] = ROLLOUT_FAILURE_COST;\n"
    "\t\t\t\t\t}\n",
    "failed-rival vector cost",
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
    "live-rival vector cost",
)

assert source.count("private Direction paretoFieldPaceOverride(") == 1
assert source.count("chosen = paretoFieldPaceOverride(") == 1
assert source.count("AIDBG PARETO-FIELD") == 1
PATH.write_text(source)
print("materialized Round 110 per-rival Pareto acceleration proof")
