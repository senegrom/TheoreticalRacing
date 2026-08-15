#!/usr/bin/env python3
"""Apply the AI1-only Round 101 robust DJS pace-retention candidate."""
from pathlib import Path

path = Path('src/tr/logic/RaceAi.java')
source = path.read_text()

old_latch = '\tprivate static boolean\t\t\tinTrueRivalConfirm;'
new_latch = '\tprivate boolean\t\t\t\tinTrueRivalConfirm;'
assert source.count(old_latch) == 1
source = source.replace(old_latch, new_latch, 1)

old = '''\t\tif (dbg)\n\t\t\tSystem.err.println("AIDBG DJS  -> " + (best != null ? "SWITCH " + best + " simT=" + bestT\n\t\t\t\t\t: "KEEP " + chosen + " (no survivor)"));\n\t\treturn best != null ? best : chosen;\n'''
new = '''\t\tif (best != null && !inScorerSim && !inTrueRivalConfirm\n\t\t\t\t&& moverKind(playerNum) == Player.Kind.AI1 && chosen != Direction.NONE\n\t\t\t\t&& kindHomogeneousRoster(playerNum)\n\t\t\t\t&& liveRivalsRemaining(playerNum) >= AI1_PRIVATE_FIELD_MIN_RIVALS) {\n\t\t\tfinal int chosenMapT = reach.turnsToFinish(cx, cy, cvx, cvy);\n\t\t\tfinal int bvx = vel[0] + best.dx, bvy = vel[1] + best.dy;\n\t\t\tfinal int bx = pos[0] + bvx, by = pos[1] + bvy;\n\t\t\tfinal int bestMapT = reach.turnsToFinish(bx, by, bvx, bvy);\n\t\t\tif (chosenMapT != Integer.MAX_VALUE && bestMapT == chosenMapT + 1\n\t\t\t\t\t&& !sealable(cx, cy, cvx, cvy, playerNum)) {\n\t\t\t\tfinal int[] trueTier = new int[1];\n\t\t\t\tfinal int[] trueThread = new int[1];\n\t\t\t\tfinal int trueOutcome;\n\t\t\t\tinTrueRivalConfirm = true;\n\t\t\t\ttry {\n\t\t\t\t\ttrueOutcome = simOutcome(cx, cy, cvx, cvy, playerNum,\n\t\t\t\t\t\t\tAI1_TRUE_CONFIRM_ROUNDS, true, true, true, true, true,\n\t\t\t\t\t\t\tAI1_DEEP_CERT_RIVALS, trueTier, null, trueThread);\n\t\t\t\t} finally {\n\t\t\t\t\tinTrueRivalConfirm = false;\n\t\t\t\t}\n\t\t\t\tif (trueOutcome >= 0 && trueTier[0] >= 3 && trueThread[0] == 0) {\n\t\t\t\t\tfinal int chosenFinal = scorerFieldOutcome(cx, cy, cvx, cvy, playerNum,\n\t\t\t\t\t\t\tAI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);\n\t\t\t\t\tfinal long chosenField = rolloutFieldCost[0];\n\t\t\t\t\tfinal int bestFinal = scorerFieldOutcome(bx, by, bvx, bvy, playerNum,\n\t\t\t\t\t\t\tAI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);\n\t\t\t\t\tfinal long bestField = rolloutFieldCost[0];\n\t\t\t\t\tif (chosenFinal >= 0 && bestFinal >= 0 && chosenFinal < bestFinal\n\t\t\t\t\t\t\t&& chosenField < ROLLOUT_FAILURE_COST\n\t\t\t\t\t\t\t&& bestField < ROLLOUT_FAILURE_COST && chosenField < bestField) {\n\t\t\t\t\t\tif (dbg)\n\t\t\t\t\t\t\tSystem.err.println("AIDBG DJS-RETAIN p=" + playerNum + " pos=("\n\t\t\t\t\t\t\t\t\t+ pos[0] + "," + pos[1] + ") " + chosen + " t="\n\t\t\t\t\t\t\t\t\t+ chosenMapT + " over " + best + " t=" + bestMapT\n\t\t\t\t\t\t\t\t\t+ " self " + chosenFinal + "<" + bestFinal + " field "\n\t\t\t\t\t\t\t\t\t+ chosenField + "<" + bestField);\n\t\t\t\t\t\treturn chosen;\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\t\tif (dbg)\n\t\t\tSystem.err.println("AIDBG DJS  -> " + (best != null ? "SWITCH " + best + " simT=" + bestT\n\t\t\t\t\t: "KEEP " + chosen + " (no survivor)"));\n\t\treturn best != null ? best : chosen;\n'''
assert source.count(old) == 1
path.write_text(source.replace(old, new, 1))
