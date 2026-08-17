#!/usr/bin/env python3
"""Materialize the guarded Round 106 forward-pack pace improvement.

Revives the strongest unfinished Round 104 acceleration idea on the current
Round 105 AI1, but narrows it to medium-range race states (map TTF <= 90).
AI2 remains frozen as the champion yardstick.
"""
from pathlib import Path

P = Path("src/tr/logic/RaceAi.java")
s = P.read_text()

const_anchor = "\tprivate final static int\t\tAI1_STAGED_MAX_SPEED2_GAIN\t= 9;\t// at most one |v|=4->5 axis of extra energy vs the scorer\n"
constants = const_anchor + (
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_MIN_SPEED2_GAIN\t= 16;\t// round 106: decisive one-turn energy gain\n"
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_MIN_AHEAD\t= 2;\t// require a real forward pack\n"
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_MAX_AHEAD\t= 5;\t// bounded proof excludes full-tail six-ahead cases\n"
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_MAX_TTF\t= 90;\t// keep the 8-round proof in the medium-range race phase\n"
)
assert s.count(const_anchor) == 1
assert "AI1_FIELD_ACCEL_MIN_SPEED2_GAIN" not in s
s = s.replace(const_anchor, constants, 1)

call = """\t\t\tchosen = stagedPaceOverride(pos, vel, playerNum, chosen, scoreByDir, scoreNSByDir,\n\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n"""
field_call = call + """\t\t\tchosen = guardedFieldPaceOverride(pos, vel, playerNum, chosen,\n\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n"""
assert s.count(call) == 2
# AI1 only; AI2 is intentionally frozen.
s = s.replace(call, field_call, 1)

helper_anchor = "\tprivate Direction privatePaceOverride(final int[] pos, final int[] vel, final int playerNum,\n"
assert s.count(helper_anchor) == 1
helper = r'''	/** Round 106: recover a one-turn acceleration only in a bounded forward
	 * pack when the same eight-round scorer world proves strict mover and
	 * aggregate-field gains. The TTF cap prevents long-range rollout optimism. */
	private Direction guardedFieldPaceOverride(final int[] pos, final int[] vel,
			final int playerNum, final Direction chosen, final double[] trapByDir,
			final double[] uncByDir, final int[] turnsByDir) {
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
		if (liveRivals < AI1_PRIVATE_FIELD_MIN_RIVALS
				|| rivalsAhead < AI1_FIELD_ACCEL_MIN_AHEAD
				|| rivalsAhead > AI1_FIELD_ACCEL_MAX_AHEAD || aheadProgress <= 0L)
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
			final int speed2 = speedSquared(nvx, nvy);
			if (speed2 - chosenSpeed2 < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN)
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
s = s.replace(helper_anchor, helper + helper_anchor, 1)
assert s.count("guardedFieldPaceOverride(pos, vel, playerNum, chosen") == 1
P.write_text(s)
print("materialized guarded AI1 forward-pack accelerator")
