#!/usr/bin/env python3
"""Materialize Round 104's proof-gated forward-pack acceleration.

The default mode changes AI1 only so current AI2 remains the exact control.
--mirror installs the already-proven call in AI2 after the differential passes.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


STAGED_CALL = (
    "\t\t\tchosen = stagedPaceOverride(pos, vel, playerNum, chosen, scoreByDir, scoreNSByDir,\n"
    "\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n"
)
FIELD_CALL = (
    "\t\t\tchosen = guardedFieldPaceOverride(pos, vel, playerNum, chosen,\n"
    "\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n"
)
METHOD_ANCHOR = (
    "\tprivate Direction privatePaceOverride(final int[] pos, final int[] vel, final int playerNum,\n"
)

HELPER = r'''	/** Round 104: recover a one-turn acceleration only in a bounded forward
	 * pack when independent eight- and ten-round scorer worlds both prove
	 * strict mover and aggregate-field gains. Marginal energy changes,
	 * six-ahead tails, close switchbacks and narrow braking funnels retain the
	 * champion line. */
	private Direction guardedFieldPaceOverride(final int[] pos, final int[] vel,
			final int playerNum, final Direction chosen, final double[] trapByDir,
			final double[] uncByDir, final int[] turnsByDir) {
		final int chosenT = turnsByDir[chosen.ordinal()];
		if (chosenT == Integer.MAX_VALUE || chosenT < AI1_FINISH_HOMOGENEOUS_TTF + 2
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
				|| rivalsAhead > AI1_FIELD_ACCEL_MAX_AHEAD || aheadProgress <= 0L)
			return chosen;

		final int chosenVx = vel[0] + chosen.dx, chosenVy = vel[1] + chosen.dy;
		final int chosenX = pos[0] + chosenVx, chosenY = pos[1] + chosenVy;
		final int chosenSpeed2 = speedSquared(chosenVx, chosenVy);
		int chosenFinal8 = Integer.MIN_VALUE;
		long chosenField8 = Long.MAX_VALUE;
		int chosenFinal10 = Integer.MIN_VALUE;
		long chosenField10 = Long.MAX_VALUE;
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
			if (chosenFinal8 == Integer.MIN_VALUE) {
				chosenFinal8 = scorerFieldOutcome(chosenX, chosenY, chosenVx, chosenVy,
						playerNum, AI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS,
						rolloutFieldCost);
				chosenField8 = rolloutFieldCost[0];
				if (chosenFinal8 < 0 || chosenField8 >= ROLLOUT_FAILURE_COST)
					return chosen;
			}
			final int candidateFinal8 = scorerFieldOutcome(nx, ny, nvx, nvy, playerNum,
					AI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);
			final long candidateField8 = rolloutFieldCost[0];
			if (candidateFinal8 < 0 || candidateFinal8 >= chosenFinal8
					|| candidateField8 >= chosenField8)
				continue;
			if (chosenFinal10 == Integer.MIN_VALUE) {
				chosenFinal10 = scorerFieldOutcome(chosenX, chosenY, chosenVx, chosenVy,
						playerNum, AI1_FIELD_ACCEL_CONFIRM_HORIZON,
						AI1_DEEP_CERT_RIVALS, rolloutFieldCost);
				chosenField10 = rolloutFieldCost[0];
				if (chosenFinal10 < 0 || chosenField10 >= ROLLOUT_FAILURE_COST)
					return chosen;
			}
			final int candidateFinal10 = scorerFieldOutcome(nx, ny, nvx, nvy, playerNum,
					AI1_FIELD_ACCEL_CONFIRM_HORIZON, AI1_DEEP_CERT_RIVALS,
					rolloutFieldCost);
			final long candidateField10 = rolloutFieldCost[0];
			if (candidateFinal10 < 0 || candidateFinal10 >= chosenFinal10
					|| candidateField10 >= chosenField10)
				continue;
			if (best == null || candidateFinal10 < bestFinal
					|| candidateFinal10 == bestFinal && candidateField10 < bestField) {
				best = d;
				bestFinal = candidateFinal10;
				bestField = candidateField10;
			}
		}
		if (best != null && AI_DEBUG_DJS)
			System.err.println("AIDBG FIELD-ACCEL p=" + playerNum + " pos=(" + pos[0]
					+ "," + pos[1] + ") " + chosen + " -> " + best + " ttf " + chosenT
					+ " -> " + turnsByDir[best.ordinal()] + " ahead=" + rivalsAhead
					+ " progress=" + aheadProgress + " confirm self " + chosenFinal10
					+ " -> " + bestFinal + " field " + chosenField10 + " -> " + bestField);
		return best != null ? best : chosen;
	}

'''


def isolate_mutable_state(root: Path) -> None:
    race = root / "src/tr/logic/RaceAi.java"
    source = race.read_text(encoding="utf-8")
    source, changed = re.subn(
        r"(?m)^(\tprivate )static (int\s+trueConfirmDepth\s*;)$",
        r"\1\2",
        source,
    )
    if changed not in (0, 1):
        raise RuntimeError(f"unexpected trueConfirmDepth declarations: {changed}")
    race.write_text(source, encoding="utf-8")

    game = root / "src/tr/logic/RaceGame.java"
    lines = game.read_text(encoding="utf-8").splitlines(keepends=True)
    trace_changes = 0
    for index, line in enumerate(lines):
        nearby = "".join(lines[max(0, index - 2): index + 3]).lower()
        if ("\tprivate static " in line and " final " not in line
                and "simtrace" in nearby):
            lines[index] = line.replace("\tprivate static ", "\tprivate ", 1)
            trace_changes += 1
    if trace_changes > 1:
        raise RuntimeError(f"unexpected mutable SIMTRACE fields: {trace_changes}")
    game.write_text("".join(lines), encoding="utf-8")


def install_policy(root: Path, mirror: bool) -> None:
    race = root / "src/tr/logic/RaceAi.java"
    source = race.read_text(encoding="utf-8")

    if "AI1_FIELD_ACCEL_CONFIRM_HORIZON" not in source:
        anchor = (
            "\tprivate final static int\t\tAI1_STAGED_MAX_SPEED2_GAIN\t= 9;"
            "\t// at most one |v|=4->5 axis of extra energy vs the scorer\n"
        )
        if source.count(anchor) != 1:
            raise RuntimeError("staged-energy anchor changed")
        constants = anchor + (
            "\tprivate final static int\t\tAI1_FIELD_ACCEL_MIN_SPEED2_GAIN\t= 16;"
            "\t// round 104: accept only decisive one-turn accelerations\n"
            "\tprivate final static int\t\tAI1_FIELD_ACCEL_MIN_AHEAD\t= 2;"
            "\t// require a real forward pack rather than an isolated re-rank\n"
            "\tprivate final static int\t\tAI1_FIELD_ACCEL_MAX_AHEAD\t= 5;"
            "\t// six-ahead full-tail cases remain outside the bounded proof\n"
            "\tprivate final static int\t\tAI1_FIELD_ACCEL_CONFIRM_HORIZON\t= 10;"
            "\t// confirm that the eight-round gain does not reverse late\n"
        )
        source = source.replace(anchor, constants, 1)

    if "private Direction guardedFieldPaceOverride" not in source:
        if source.count(METHOD_ANCHOR) != 1:
            raise RuntimeError("private-pace method anchor changed")
        source = source.replace(METHOD_ANCHOR, HELPER + METHOD_ANCHOR, 1)

    field_count = source.count(FIELD_CALL)
    if field_count == 0:
        if source.count(STAGED_CALL) != 2:
            raise RuntimeError("pace-call structure changed")
        source = source.replace(STAGED_CALL, STAGED_CALL + FIELD_CALL, 1)
        field_count = 1

    if mirror and field_count == 1:
        parts = source.split(STAGED_CALL)
        if len(parts) != 3:
            raise RuntimeError("cannot locate AI2 staged call")
        source = parts[0] + STAGED_CALL + parts[1] + STAGED_CALL + FIELD_CALL + parts[2]
        field_count = 2

    expected = 2 if mirror else 1
    if field_count != expected:
        raise RuntimeError(f"expected {expected} field calls, found {field_count}")
    race.write_text(source, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--mirror", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    isolate_mutable_state(root)
    install_policy(root, args.mirror)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Round 104 controller kick: latest-head gate
