#!/usr/bin/env python3
"""Apply Round 103's full-field survival confirmation to both race AIs."""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text(encoding="utf-8")

old_latch = "\tprivate static boolean\t\t\tinTrueRivalConfirm;"
new_latch = "\tprivate boolean\t\t\t\tinTrueRivalConfirm;"
assert source.count(old_latch) == 1
source = source.replace(old_latch, new_latch, 1)

old_target = """\t\t\t\t\t\t\tAI1_TRUE_CONFIRM_ROUNDS, simFinishVanish, exactSelf, exactRivals, true,
\t\t\t\t\t\t\tscorerSelf, true, scorerCap, null, null, null) >= 0;"""
new_target = """\t\t\t\t\t\t\tAI1_TRUE_CONFIRM_ROUNDS, simFinishVanish, exactSelf, exactRivals, true,
\t\t\t\t\t\t\tscorerSelf, true, Math.max(scorerCap, AI1_DEEP_CERT_RIVALS),
\t\t\t\t\t\t\tnull, null, null) >= 0;"""
assert source.count(old_target) == 1
source = source.replace(old_target, new_target, 1)

comment_anchor = """\t\tif (trueDead && best != null) {
\t\t\t// Round 99: the cheap world proposed the switch target; make the
"""
comment_replacement = """\t\tif (trueDead && best != null) {
\t\t\t// Round 103: target confirmation uses at least the existing six-rival
\t\t\t// deep certificate. Zigzag seed 76 proved the nearest-three net can
\t\t\t// omit a box-forming rival and accept a false survivor. The wider net
\t\t\t// is paid only after a cheap-dead verdict has already proposed a switch.
\t\t\t// Round 99: the cheap world proposed the switch target; make the
"""
assert source.count(comment_anchor) == 1
source = source.replace(comment_anchor, comment_replacement, 1)

old_ai2 = """\t\t\t\t\t\t\t\tif (deepChoice == chosen)
\t\t\t\t\t\t\t\t\tdeepChoice = dangerJointSearch(pos, vel, playerNum, chosen, true, true,
\t\t\t\t\t\t\t\t\t\t\ttrue, true, AI1_DEEP_HORIZON);"""
new_ai2 = """\t\t\t\t\t\t\t\tif (deepChoice == chosen)
\t\t\t\t\t\t\t\t\tdeepChoice = dangerJointSearch(pos, vel, playerNum, chosen, true, true,
\t\t\t\t\t\t\t\t\t\t\ttrue, true, AI1_DEEP_HORIZON, AI1_SCORER_MAXRIVALS,
\t\t\t\t\t\t\t\t\t\t\tfalse, false, true);"""
assert source.count(old_ai2) == 1
source = source.replace(old_ai2, new_ai2, 1)

helper_anchor = """\t/** Danger joint search (round 40, AI1 only): if the chosen landing DIES in
"""
helper = """\t/** Rare full-policy survival check for dense homogeneous packs. Every
\t * selected rival runs its unsuppressed champion policy; nested confirms stay
\t * latched off. A surviving incumbent is never re-ranked. */
\tprivate Direction trueRivalSurvivalSearch(final int[] pos, final int[] vel,
\t\t\tfinal int playerNum, final Direction chosen, final int rounds, final int scorerCap) {
\t\tif (inTrueRivalConfirm)
\t\t\treturn chosen;
\t\tfinal int cvx = vel[0] + chosen.dx, cvy = vel[1] + chosen.dy;
\t\tfinal int cx = pos[0] + cvx, cy = pos[1] + cvy;
\t\tif (game.crossesFinish(pos[0], pos[1], cx, cy))
\t\t\treturn chosen;
\t\tfinal boolean previous = inTrueRivalConfirm;
\t\tinTrueRivalConfirm = true;
\t\ttry {
\t\t\tfinal int chosenT = simOutcome(cx, cy, cvx, cvy, playerNum, rounds,
\t\t\t\t\ttrue, true, true, true, false, true, scorerCap, null, null, null);
\t\t\tif (chosenT >= 0)
\t\t\t\treturn chosen;
\t\t\tDirection best = null;
\t\t\tint bestT = Integer.MAX_VALUE;
\t\t\tfor (final Direction d : DIRECTIONS) {
\t\t\t\tif (d == chosen)
\t\t\t\t\tcontinue;
\t\t\t\tfinal int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
\t\t\t\tif (RaceGame.aiVelocityOutOfRange(nvx, nvy))
\t\t\t\t\tcontinue;
\t\t\t\tfinal int nx = pos[0] + nvx, ny = pos[1] + nvy;
\t\t\t\tif (game.crossesFinish(pos[0], pos[1], nx, ny))
\t\t\t\t\treturn d;
\t\t\t\tif (!game.isMoveLegalGeometryCached(pos[0], pos[1], nx, ny)
\t\t\t\t\t\t|| game.isCrashingPlayer(nx, ny, playerNum)
\t\t\t\t\t\t|| !reach.isAlive(nx, ny, nvx, nvy))
\t\t\t\t\tcontinue;
\t\t\t\tfinal int t = simOutcome(nx, ny, nvx, nvy, playerNum, rounds,
\t\t\t\t\t\ttrue, true, true, true, false, true, scorerCap, null, null, null);
\t\t\t\tif (t >= 0 && t < bestT) {
\t\t\t\t\tbest = d;
\t\t\t\t\tbestT = t;
\t\t\t\t}
\t\t\t}
\t\t\tif (AI_DEBUG_DJS && best != null)
\t\t\t\tSystem.err.println("AIDBG TRUE-DEEP p=" + playerNum + " pos=(" + pos[0]
\t\t\t\t\t\t+ "," + pos[1] + ") " + chosen + " -> " + best + " t=" + bestT);
\t\t\treturn best != null ? best : chosen;
\t\t} finally {
\t\t\tinTrueRivalConfirm = previous;
\t\t}
\t}

"""
assert source.count(helper_anchor) == 1
source = source.replace(helper_anchor, helper + helper_anchor, 1)

fast_anchor = """\t\t\t\t\t\t// Deep (8-round) sim verdicts are trustworthy in SPARSE
\t\t\t\t\t\t// fields: the 4car lemans-s1 geometric doom is model-robust
"""
fast_gate = """\t\t\t\t\t\tfinal int funnelRun = fSpdInf >= AI1_FUNNEL_MIN_SPD
\t\t\t\t\t\t\t\t? reach.narrowRunAhead(fCx, fCy, fSpan, AI1_FUNNEL_WIDTH) : 0;
\t\t\t\t\t\tfinal boolean denseFunnel = liveRivals > AI1_FUNNEL_DEEP_FIELD
\t\t\t\t\t\t\t\t&& fMinRing <= AI1_FUNNEL_WIDTH && fSpdInf > fMinRing
\t\t\t\t\t\t\t\t&& funnelRun >= AI1_FUNNEL_RUN
\t\t\t\t\t\t\t\t&& trapByDir[chosen.ordinal()] == 0.0
\t\t\t\t\t\t\t\t&& kindHomogeneousRoster(playerNum)
\t\t\t\t\t\t\t\t&& countRivalsWithinCheb(fCx, fCy, playerNum, AI1_DEEP_PACK_R)
\t\t\t\t\t\t\t\t\t\t>= AI1_DEEP_CERT_RIVALS;
\t\t\t\t\t\tif (denseFunnel && !game.crossesFinish(pos[0], pos[1], fCx, fCy)) {
\t\t\t\t\t\t\tchosen = trueRivalSurvivalSearch(pos, vel, playerNum, chosen,
\t\t\t\t\t\t\t\t\tAI1_DEEP_HORIZON, AI1_DEEP_CERT_RIVALS);
\t\t\t\t\t\t\tdeepHandled = true;
\t\t\t\t\t\t}
"""
assert source.count(fast_anchor) == 2
source = source.replace(fast_anchor, fast_gate + fast_anchor)

slow_anchor = """\t\t\t\t\t\t\t\t\tchosen = dangerJointSearch(pos, vel, playerNum, chosen, true,
\t\t\t\t\t\t\t\t\t\t\tscorerRivals, exactRivals, simFinishVanish, slowRounds,
\t\t\t\t\t\t\t\t\t\t\tscorerCap, false, trapClass >= 2, false);
\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t\tdeepHandled = true;
"""
slow_replacement = """\t\t\t\t\t\t\t\t\tchosen = dangerJointSearch(pos, vel, playerNum, chosen, true,
\t\t\t\t\t\t\t\t\t\t\tscorerRivals, exactRivals, simFinishVanish, slowRounds,
\t\t\t\t\t\t\t\t\t\t\tscorerCap, false, trapClass >= 2, false);
\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t\tif (trapByDir[chosen.ordinal()] >= 0.5 && fSpdInf >= 4
\t\t\t\t\t\t\t\t\t\t&& kindHomogeneousRoster(playerNum)
\t\t\t\t\t\t\t\t\t\t&& countRivalsWithinCheb(cx, cy, playerNum, AI1_DEEP_PACK_R)
\t\t\t\t\t\t\t\t\t\t\t\t>= AI1_DEEP_CERT_RIVALS)
\t\t\t\t\t\t\t\t\tchosen = trueRivalSurvivalSearch(pos, vel, playerNum, chosen,
\t\t\t\t\t\t\t\t\t\t\tAI1_DJS_FAST_FRAGILE_ROUNDS, AI1_DEEP_CERT_RIVALS);
\t\t\t\t\t\t\t\tdeepHandled = true;
"""
assert source.count(slow_anchor) == 2
source = source.replace(slow_anchor, slow_replacement)

path.write_text(source, encoding="utf-8")
