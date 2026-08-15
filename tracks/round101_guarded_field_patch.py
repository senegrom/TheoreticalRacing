#!/usr/bin/env python3
"""Apply the AI1-only Round 101 guarded field acceleration candidate."""
from pathlib import Path

path = Path('src/tr/logic/RaceAi.java')
source = path.read_text()

old_latch = '\tprivate static boolean\t\t\tinTrueRivalConfirm;'
new_latch = '\tprivate boolean\t\t\t\tinTrueRivalConfirm;'
assert source.count(old_latch) == 1
source = source.replace(old_latch, new_latch, 1)

const_anchor = '\tprivate final static int\t\tAI1_STAGED_MAX_SPEED2_GAIN\t= 9;\t// at most one |v|=4->5 axis of extra energy vs the scorer\n'
consts = const_anchor + (
    '\tprivate final static int\t\tAI1_FIELD_ACCEL_MIN_SPEED2_GAIN\t= 16;\t// round 101: only decisive one-turn accelerations survived the counterexample screen\n'
    '\tprivate final static int\t\tAI1_FIELD_ACCEL_MIN_AHEAD\t= 2;\t// require a forward pack, not an isolated or trailing-car re-rank\n'
    '\tprivate final static int\t\tAI1_FIELD_ACCEL_MAX_AHEAD\t= 5;\t// six-ahead full-tail cases exposed the Coil regression\n'
)
assert source.count(const_anchor) == 1
source = source.replace(const_anchor, consts, 1)

call = '''\t\t\tchosen = stagedPaceOverride(pos, vel, playerNum, chosen, scoreByDir, scoreNSByDir,\n\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n'''
new_call = call + '''\t\t\tchosen = guardedFieldPaceOverride(pos, vel, playerNum, chosen,\n\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n'''
assert source.count(call) == 2
source = source.replace(call, new_call, 1)

anchor = '\tprivate Direction privatePaceOverride(final int[] pos, final int[] vel, final int playerNum,\n'
helper = '''\t/** Round 101: recover a one-turn acceleration only in a bounded forward\n\t * pack when the same eight-round scorer world proves strict mover and\n\t * aggregate-field gains. The incumbent field must be finite; marginal\n\t * energy changes, six-ahead tail cases, and switchback false-ahead geometry\n\t * retain the champion line. */\n\tprivate Direction guardedFieldPaceOverride(final int[] pos, final int[] vel,\n\t\t\tfinal int playerNum, final Direction chosen, final double[] trapByDir,\n\t\t\tfinal double[] uncByDir, final int[] turnsByDir) {\n\t\tfinal int chosenT = turnsByDir[chosen.ordinal()];\n\t\tif (chosenT == Integer.MAX_VALUE || chosenT < AI1_FINISH_HOMOGENEOUS_TTF + 2\n\t\t\t\t|| !kindHomogeneousRoster(playerNum))\n\t\t\treturn chosen;\n\t\tint liveRivals = 0, rivalsAhead = 0;\n\t\tlong aheadProgress = 0L;\n\t\tfinal boolean stagedLaunch = useTrackDistanceForStagedLaunch(vel[0], vel[1],\n\t\t\t\tgame.startZoneA.contains(pos[0], pos[1]));\n\t\tfinal int moverProgress = reach.distAt(pos[0], pos[1]);\n\t\tfor (final Player rival : game.players) {\n\t\t\tif (rival.getNumber() == playerNum || rival.isFinished())\n\t\t\t\tcontinue;\n\t\t\tliveRivals++;\n\t\t\tfinal int[] rivalPos = rival.getPosition();\n\t\t\tfinal int rivalProgress = reach.distAt(rivalPos[0], rivalPos[1]);\n\t\t\tfinal boolean ahead = stagedLaunch\n\t\t\t\t\t? isStrictlyAheadByTrackDistance(moverProgress, rivalProgress)\n\t\t\t\t\t: ((long) rivalPos[0] - pos[0]) * vel[0]\n\t\t\t\t\t\t\t+ ((long) rivalPos[1] - pos[1]) * vel[1] > 0L;\n\t\t\tif (ahead) {\n\t\t\t\trivalsAhead++;\n\t\t\t\tif (moverProgress != Integer.MAX_VALUE && rivalProgress != Integer.MAX_VALUE)\n\t\t\t\t\taheadProgress += (long) moverProgress - rivalProgress;\n\t\t\t}\n\t\t}\n\t\tif (liveRivals < AI1_PRIVATE_FIELD_MIN_RIVALS\n\t\t\t\t|| rivalsAhead < AI1_FIELD_ACCEL_MIN_AHEAD\n\t\t\t\t|| rivalsAhead > AI1_FIELD_ACCEL_MAX_AHEAD || aheadProgress <= 0L)\n\t\t\treturn chosen;\n\n\t\tfinal int chosenVx = vel[0] + chosen.dx, chosenVy = vel[1] + chosen.dy;\n\t\tfinal int chosenX = pos[0] + chosenVx, chosenY = pos[1] + chosenVy;\n\t\tfinal int chosenSpeed2 = speedSquared(chosenVx, chosenVy);\n\t\tint chosenFinal = Integer.MIN_VALUE;\n\t\tlong chosenField = Long.MAX_VALUE;\n\t\tDirection best = null;\n\t\tint bestFinal = Integer.MAX_VALUE;\n\t\tlong bestField = Long.MAX_VALUE;\n\t\tfor (final Direction d : DIRECTIONS) {\n\t\t\tfinal int turns = turnsByDir[d.ordinal()];\n\t\t\tif (d == chosen || d == Direction.NONE || turns == Integer.MAX_VALUE\n\t\t\t\t\t|| turns + 1 != chosenT || trapByDir[d.ordinal()] != 0.0\n\t\t\t\t\t|| uncByDir[d.ordinal()] != 0.0)\n\t\t\t\tcontinue;\n\t\t\tfinal int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;\n\t\t\tif (speedSquared(nvx, nvy) - chosenSpeed2 < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN)\n\t\t\t\tcontinue;\n\t\t\tfinal int nx = pos[0] + nvx, ny = pos[1] + nvy;\n\t\t\tif (sealable(nx, ny, nvx, nvy, playerNum))\n\t\t\t\tcontinue;\n\t\t\tif (chosenFinal == Integer.MIN_VALUE) {\n\t\t\t\tchosenFinal = scorerFieldOutcome(chosenX, chosenY, chosenVx, chosenVy, playerNum,\n\t\t\t\t\t\tAI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);\n\t\t\t\tchosenField = rolloutFieldCost[0];\n\t\t\t\tif (chosenFinal < 0 || chosenField >= ROLLOUT_FAILURE_COST)\n\t\t\t\t\treturn chosen;\n\t\t\t}\n\t\t\tfinal int candidateFinal = scorerFieldOutcome(nx, ny, nvx, nvy, playerNum,\n\t\t\t\t\tAI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);\n\t\t\tfinal long candidateField = rolloutFieldCost[0];\n\t\t\tif (candidateFinal < 0 || candidateFinal >= chosenFinal\n\t\t\t\t\t|| candidateField >= chosenField)\n\t\t\t\tcontinue;\n\t\t\tif (best == null || candidateFinal < bestFinal\n\t\t\t\t\t|| candidateFinal == bestFinal && candidateField < bestField) {\n\t\t\t\tbest = d;\n\t\t\t\tbestFinal = candidateFinal;\n\t\t\t\tbestField = candidateField;\n\t\t\t}\n\t\t}\n\t\tif (best != null && AI_DEBUG_DJS)\n\t\t\tSystem.err.println("AIDBG FIELD-ACCEL p=" + playerNum + " pos=(" + pos[0]\n\t\t\t\t\t+ "," + pos[1] + ") " + chosen + " -> " + best + " ttf " + chosenT\n\t\t\t\t\t+ " -> " + turnsByDir[best.ordinal()] + " ahead=" + rivalsAhead\n\t\t\t\t\t+ " progress=" + aheadProgress + " self " + chosenFinal + " -> "\n\t\t\t\t\t+ bestFinal + " field " + chosenField + " -> " + bestField);\n\t\treturn best != null ? best : chosen;\n\t}\n\n'''
assert source.count(anchor) == 1
source = source.replace(anchor, helper + anchor, 1)
path.write_text(source)
