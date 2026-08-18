#!/usr/bin/env python3
"""Materialize Round 117's exact-six-ahead acceleration certificate.

Round 106 deliberately capped its forward-pack rule at five rivals ahead. The
unfinished pace sweep exposed a real sixth-place gain, but the normal eight-
round proof also admitted two Coil field redistributions. The smallest horizon
that separates the three measured states is ten rounds: Coil seeds 5 and 22
lose their short-horizon certificate, while seed 86 remains strictly better.

This experiment therefore leaves every promoted rule unchanged and adds one
AI1-only class: exactly six rivals ahead, speed-squared gain at least 16, and a
strict ten-round mover plus aggregate-field improvement. AI2 remains frozen.
"""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()


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
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_SIX_AHEAD_ROUNDS\t= 10;"
    "\t// round 117: minimum horizon separating the sixth-place gain from two redistributions\n",
    "six-ahead horizon",
)

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
    "\t\tfinal int chosenSpeed2 = speedSquared(chosenVx, chosenVy);\n"
    "\t\tfinal int fieldProofRounds = sixAheadFrontier\n"
    "\t\t\t\t? AI1_FIELD_ACCEL_SIX_AHEAD_ROUNDS : AI1_STAGED_HORIZON;\n",
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
    "\t/** Round 106: recover a one-turn acceleration only in a bounded forward\n"
    "\t * pack when the same eight-round scorer world proves strict mover and\n",
    "\t/** Round 106: recover a one-turn acceleration only in a bounded forward\n"
    "\t * pack when the scorer world proves strict mover and\n",
    "method documentation",
)

# Only the guarded-field override may use the new horizon. Other scorer-field
# proofs intentionally retain their established depths, so edit inside a
# bounded method slice and assert the two expected calls there.
method_start = source.index("\tprivate Direction guardedFieldPaceOverride(")
method_end = source.index("\n\tprivate Direction privatePaceOverride(", method_start)
method = source[method_start:method_end]
old_horizon = "AI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost"
assert method.count(old_horizon) == 2, method.count(old_horizon)
method = method.replace(
    old_horizon,
    "fieldProofRounds, AI1_DEEP_CERT_RIVALS, rolloutFieldCost",
)
source = source[:method_start] + method + source[method_end:]

assert source.count("AI1_FIELD_ACCEL_SIX_AHEAD_ROUNDS") == 2
assert source.count("sixAheadFrontier") == 4
assert source.count("fieldProofRounds") == 3
path.write_text(source)
print("materialized Round 117 exact-six-ahead acceleration certificate")
