#!/usr/bin/env python3
"""Materialize Round 117's synchronized exact-six-ahead acceleration.

Round 106 deliberately capped its forward-pack rule at five rivals ahead. The
unfinished pace sweep exposed one real sixth-place gain and two Coil field
redistributions from the same local move. Board reconstruction supplies a
structural separator without adding rollout depth: only the good seed has a
previously moved rival adjacent to the proposed landing and already carrying
the candidate's exact velocity. That is a synchronized formation rather than a
lone back-marker acceleration.

Every promoted rule remains unchanged. AI1 alone may enter the established
high-energy (speed-squared gain >=16) eight-round field certificate with exactly
six rivals ahead when that synchronized candidate-velocity peer exists. AI2
remains frozen.
"""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global source
    count = source.count(old)
    assert count == 1, (label, count)
    source = source.replace(old, new, 1)


helper_anchor = (
    "\n\t/** Round 106: recover a one-turn acceleration only in a bounded forward\n"
)
helper = r'''

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
'''
replace_once(helper_anchor, helper + helper_anchor, "candidate peer helper")

replace_once(
    "\t\tif (liveRivals < AI1_PRIVATE_FIELD_MIN_RIVALS\n"
    "\t\t\t\t|| rivalsAhead < AI1_FIELD_ACCEL_MIN_AHEAD\n"
    "\t\t\t\t|| rivalsAhead > AI1_FIELD_ACCEL_MAX_AHEAD || aheadProgress <= 0L)\n"
    "\t\t\treturn chosen;\n\n"
    "\t\tfinal int chosenVx = vel[0] + chosen.dx, chosenVy = vel[1] + chosen.dy;\n"
    "\t\tfinal int chosenX = pos[0] + chosenVx, chosenY = pos[1] + chosenVy;\n"
    "\t\tfinal int chosenSpeed2 = speedSquared(chosenVx, chosenVy);\n"
    "\t\tfinal boolean frontierMover = moverKind(playerNum) == Player.Kind.AI1;\n",
    "\t\tfinal boolean frontierMover = moverKind(playerNum) == Player.Kind.AI1;\n"
    "\t\tfinal boolean sixAheadFrontier = frontierMover\n"
    "\t\t\t\t&& rivalsAhead == AI1_FIELD_ACCEL_MAX_AHEAD + 1;\n"
    "\t\tif (liveRivals < AI1_PRIVATE_FIELD_MIN_RIVALS\n"
    "\t\t\t\t|| rivalsAhead < AI1_FIELD_ACCEL_MIN_AHEAD\n"
    "\t\t\t\t|| rivalsAhead > AI1_FIELD_ACCEL_MAX_AHEAD && !sixAheadFrontier\n"
    "\t\t\t\t|| aheadProgress <= 0L)\n"
    "\t\t\treturn chosen;\n\n"
    "\t\tfinal int chosenVx = vel[0] + chosen.dx, chosenVy = vel[1] + chosen.dy;\n"
    "\t\tfinal int chosenX = pos[0] + chosenVx, chosenY = pos[1] + chosenVy;\n"
    "\t\tfinal int chosenSpeed2 = speedSquared(chosenVx, chosenVy);\n",
    "six-ahead admission",
)

replace_once(
    "\t\t\tif (speed2Gain < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN\n"
    "\t\t\t\t\t&& !frontierModerateGain)\n"
    "\t\t\t\tcontinue;\n",
    "\t\t\tif (speed2Gain < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN\n"
    "\t\t\t\t\t&& !frontierModerateGain)\n"
    "\t\t\t\tcontinue;\n"
    "\t\t\t// The new six-ahead class is the established high-energy arm only;\n"
    "\t\t\t// Round 115's moderate 9..15 frontier remains capped at five ahead.\n"
    "\t\t\tif (sixAheadFrontier && speed2Gain < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN)\n"
    "\t\t\t\tcontinue;\n",
    "six-ahead energy floor",
)

replace_once(
    "\t\t\tfinal int nx = pos[0] + nvx, ny = pos[1] + nvy;\n"
    "\t\t\tfinal int candidateInf = Math.max(Math.abs(nvx), Math.abs(nvy));\n",
    "\t\t\tfinal int nx = pos[0] + nvx, ny = pos[1] + nvy;\n"
    "\t\t\tif (sixAheadFrontier && !hasAdjacentPriorCandidateVelocityPeer(\n"
    "\t\t\t\t\tnx, ny, nvx, nvy, playerNum))\n"
    "\t\t\t\tcontinue;\n"
    "\t\t\tfinal int candidateInf = Math.max(Math.abs(nvx), Math.abs(nvy));\n",
    "synchronized peer gate",
)

replace_once(
    "\t * aggregate-field gains. Round 115 leaves the promoted gain>=16 rule intact;\n",
    "\t * aggregate-field gains. Round 117 admits an exact-six-ahead high-energy\n"
    "\t * formation only with an adjacent prior candidate-velocity peer. Round 115\n"
    "\t * leaves the promoted gain>=16 rule otherwise intact;\n",
    "method documentation",
)

assert source.count("hasAdjacentPriorCandidateVelocityPeer") == 2
assert source.count("sixAheadFrontier") == 4
path.write_text(source)
print("materialized Round 117 synchronized exact-six-ahead acceleration")
