#!/usr/bin/env python3
"""Materialize Round 116's deeper proof for high-speed moderate acceleration.

Round 115 safely admits speed-squared gains 9..15 only below speed squared 49.
The abandoned broader rule found a high-speed Silverstone redistribution: its
8-round aggregate proof was too short. This experiment reopens that high-speed
slice, but compares chosen and candidate through a 12-round scorer-field world.
The promoted Round-115 low-speed slice and the established gain>=16 slice keep
their existing 8-round proof unchanged. AI2 remains the frozen control.
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
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_FRONTIER_HIGH_SPEED_ROUNDS\t= 12;"
    "\t// round 116: deeper proof for speed-7+ moderate gains\n",
    "high-speed horizon",
)

replace_once(
    "\t\t\tfinal boolean frontierModerateGain = frontierMover\n"
    "\t\t\t\t\t&& chosen != Direction.NONE\n"
    "\t\t\t\t\t&& chosenSpeed2 < AI1_DJS_SPD2\n"
    "\t\t\t\t\t&& chosenT <= AI1_FIELD_ACCEL_FRONTIER_LOW_GAIN_MAX_TTF\n"
    "\t\t\t\t\t&& speed2Gain >= AI1_FIELD_ACCEL_FRONTIER_MIN_SPEED2_GAIN;\n",
    "\t\t\tfinal boolean frontierModerateGain = frontierMover\n"
    "\t\t\t\t\t&& chosen != Direction.NONE\n"
    "\t\t\t\t\t&& chosenT <= AI1_FIELD_ACCEL_FRONTIER_LOW_GAIN_MAX_TTF\n"
    "\t\t\t\t\t&& speed2Gain >= AI1_FIELD_ACCEL_FRONTIER_MIN_SPEED2_GAIN\n"
    "\t\t\t\t\t&& speed2Gain < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN;\n"
    "\t\t\tfinal boolean highSpeedModerateGain = frontierModerateGain\n"
    "\t\t\t\t\t&& chosenSpeed2 >= AI1_DJS_SPD2;\n",
    "moderate admission",
)

replace_once(
    "\t\t\tif (chosenFinal == Integer.MIN_VALUE) {\n"
    "\t\t\t\tchosenFinal = scorerFieldOutcome(chosenX, chosenY, chosenVx, chosenVy, playerNum,\n"
    "\t\t\t\t\t\tAI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);\n"
    "\t\t\t\tchosenField = rolloutFieldCost[0];\n"
    "\t\t\t\tif (chosenFinal < 0 || chosenField >= ROLLOUT_FAILURE_COST)\n"
    "\t\t\t\t\treturn chosen;\n"
    "\t\t\t}\n"
    "\t\t\tfinal int candidateFinal = scorerFieldOutcome(nx, ny, nvx, nvy, playerNum,\n"
    "\t\t\t\t\tAI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);\n"
    "\t\t\tfinal long candidateField = rolloutFieldCost[0];\n"
    "\t\t\tif (candidateFinal < 0 || candidateFinal >= chosenFinal\n"
    "\t\t\t\t\t|| candidateField >= chosenField)\n"
    "\t\t\t\tcontinue;\n",
    "\t\t\tfinal int proofRounds = highSpeedModerateGain\n"
    "\t\t\t\t\t? AI1_FIELD_ACCEL_FRONTIER_HIGH_SPEED_ROUNDS : AI1_STAGED_HORIZON;\n"
    "\t\t\tfinal int comparedChosenFinal;\n"
    "\t\t\tfinal long comparedChosenField;\n"
    "\t\t\tif (proofRounds == AI1_STAGED_HORIZON) {\n"
    "\t\t\t\tif (chosenFinal == Integer.MIN_VALUE) {\n"
    "\t\t\t\t\tchosenFinal = scorerFieldOutcome(chosenX, chosenY, chosenVx, chosenVy, playerNum,\n"
    "\t\t\t\t\t\t\tAI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);\n"
    "\t\t\t\t\tchosenField = rolloutFieldCost[0];\n"
    "\t\t\t\t\tif (chosenFinal < 0 || chosenField >= ROLLOUT_FAILURE_COST)\n"
    "\t\t\t\t\t\treturn chosen;\n"
    "\t\t\t\t}\n"
    "\t\t\t\tcomparedChosenFinal = chosenFinal;\n"
    "\t\t\t\tcomparedChosenField = chosenField;\n"
    "\t\t\t} else {\n"
    "\t\t\t\tcomparedChosenFinal = scorerFieldOutcome(chosenX, chosenY, chosenVx, chosenVy,\n"
    "\t\t\t\t\t\tplayerNum, proofRounds, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);\n"
    "\t\t\t\tcomparedChosenField = rolloutFieldCost[0];\n"
    "\t\t\t\tif (comparedChosenFinal < 0 || comparedChosenField >= ROLLOUT_FAILURE_COST)\n"
    "\t\t\t\t\tcontinue;\n"
    "\t\t\t}\n"
    "\t\t\tfinal int candidateFinal = scorerFieldOutcome(nx, ny, nvx, nvy, playerNum,\n"
    "\t\t\t\t\tproofRounds, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);\n"
    "\t\t\tfinal long candidateField = rolloutFieldCost[0];\n"
    "\t\t\tif (candidateFinal < 0 || candidateFinal >= comparedChosenFinal\n"
    "\t\t\t\t\t|| candidateField >= comparedChosenField)\n"
    "\t\t\t\tcontinue;\n",
    "horizon-aware proof",
)

assert source.count("AI1_FIELD_ACCEL_FRONTIER_HIGH_SPEED_ROUNDS") == 2
assert source.count("highSpeedModerateGain") == 2
path.write_text(source)
print("materialized Round 116 deep high-speed acceleration candidate")
