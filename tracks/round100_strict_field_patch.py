#!/usr/bin/env python3
"""Apply an AI1-only strict field-comparative pace candidate."""
from pathlib import Path
import sys

mode = int(sys.argv[1])
if mode not in (1, 2, 3):
    raise SystemExit("mode must be 1, 2, or 3")

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()

old_latch = "\tprivate static boolean\t\t\tinTrueRivalConfirm;"
new_latch = "\tprivate boolean\t\t\t\tinTrueRivalConfirm;"
assert source.count(old_latch) == 1
source = source.replace(old_latch, new_latch, 1)

call = """\t\t\tchosen = stagedPaceOverride(pos, vel, playerNum, chosen, scoreByDir, scoreNSByDir,\n\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n"""
new_call = call + (
    "\t\t\tchosen = strictFieldPaceOverride(pos, vel, playerNum, chosen, trapByDir, "
    f"uncByDir, poTByDir, {mode});\n"
)
assert source.count(call) == 2
source = source.replace(call, new_call, 1)

anchor = "\tprivate Direction privatePaceOverride(final int[] pos, final int[] vel, final int playerNum,\n"
helper = """\t/** Round 100 candidate: admit a one-turn map gain only when the same\n\t * eight-round scorer field proves strict mover and aggregate-field gains. */\n\tprivate Direction strictFieldPaceOverride(final int[] pos, final int[] vel, final int playerNum,\n\t\t\tfinal Direction chosen, final double[] trapByDir, final double[] uncByDir,\n\t\t\tfinal int[] turnsByDir, final int mode) {\n\t\tfinal int chosenT = turnsByDir[chosen.ordinal()];\n\t\tif (chosenT == Integer.MAX_VALUE || chosenT < AI1_FINISH_HOMOGENEOUS_TTF + 2\n\t\t\t\t|| !kindHomogeneousRoster(playerNum)\n\t\t\t\t|| liveRivalsRemaining(playerNum) < AI1_PRIVATE_FIELD_MIN_RIVALS)\n\t\t\treturn chosen;\n\t\tfinal int chosenVx = vel[0] + chosen.dx, chosenVy = vel[1] + chosen.dy;\n\t\tfinal int chosenX = pos[0] + chosenVx, chosenY = pos[1] + chosenVy;\n\t\tint chosenFinal = Integer.MIN_VALUE;\n\t\tlong chosenField = Long.MAX_VALUE;\n\t\tDirection best = null;\n\t\tint bestFinal = Integer.MAX_VALUE;\n\t\tlong bestField = Long.MAX_VALUE;\n\t\tfor (final Direction d : DIRECTIONS) {\n\t\t\tif (d == chosen || d == Direction.NONE || turnsByDir[d.ordinal()] + 1 != chosenT)\n\t\t\t\tcontinue;\n\t\t\tfinal double trap = trapByDir[d.ordinal()];\n\t\t\tfinal double unc = uncByDir[d.ordinal()];\n\t\t\tif (mode == 1 && (trap != 0.0 || unc != 0.0))\n\t\t\t\tcontinue;\n\t\t\tif (mode == 2 && (trap > AI1_TRAP_L2 || unc != 0.0))\n\t\t\t\tcontinue;\n\t\t\tif (mode == 3 && (trap > trapByDir[chosen.ordinal()]\n\t\t\t\t\t|| unc > uncByDir[chosen.ordinal()]))\n\t\t\t\tcontinue;\n\t\t\tfinal int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;\n\t\t\tfinal int nx = pos[0] + nvx, ny = pos[1] + nvy;\n\t\t\tif (sealable(nx, ny, nvx, nvy, playerNum))\n\t\t\t\tcontinue;\n\t\t\tif (chosenFinal == Integer.MIN_VALUE) {\n\t\t\t\tchosenFinal = scorerFieldOutcome(chosenX, chosenY, chosenVx, chosenVy, playerNum,\n\t\t\t\t\t\tAI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);\n\t\t\t\tchosenField = rolloutFieldCost[0];\n\t\t\t\tif (chosenFinal < 0)\n\t\t\t\t\treturn chosen;\n\t\t\t}\n\t\t\tfinal int candidateFinal = scorerFieldOutcome(nx, ny, nvx, nvy, playerNum,\n\t\t\t\t\tAI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);\n\t\t\tfinal long candidateField = rolloutFieldCost[0];\n\t\t\tif (candidateFinal < 0 || candidateFinal >= chosenFinal || candidateField >= chosenField)\n\t\t\t\tcontinue;\n\t\t\tif (best == null || candidateFinal < bestFinal\n\t\t\t\t\t|| candidateFinal == bestFinal && candidateField < bestField) {\n\t\t\t\tbest = d;\n\t\t\t\tbestFinal = candidateFinal;\n\t\t\t\tbestField = candidateField;\n\t\t\t}\n\t\t}\n\t\tif (best != null)\n\t\t\tSystem.err.println("AIDBG STRICT-FIELD mode=" + mode + " p=" + playerNum\n\t\t\t\t\t+ " pos=(" + pos[0] + "," + pos[1] + ") " + chosen + " -> " + best\n\t\t\t\t\t+ " ttf " + chosenT + " -> " + turnsByDir[best.ordinal()]\n\t\t\t\t\t+ " self " + chosenFinal + " -> " + bestFinal\n\t\t\t\t\t+ " field " + chosenField + " -> " + bestField);\n\t\treturn best != null ? best : chosen;\n\t}\n\n"""
assert source.count(anchor) == 1
source = source.replace(anchor, helper + anchor, 1)
path.write_text(source)
