#!/usr/bin/env python3
"""Materialize Round 126's AI1-only equal-speed false-target veto.

The remaining Zandvoort seed-115 crash is an equal-speed lane-choice failure:
the topology-shaped deep world abandons its chosen line for an alternative that
the bounded faithful-rival world kills, while that same faithful world keeps
the chosen line alive.  Before accepting only that narrow class of switch, run
the existing certification-cap true-rival model on both landings and veto the
transition when it would replace a true-alive chosen line with a true-dead
alternative.

The gate is AI1-only because AI2 delegates to the shared frontier body and must
remain the frozen control.  Every non-equal-speed switch and every ordinary
survival decision remains byte-for-byte unchanged.
"""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()

old = """\t\t\t\t\t\tfinal int avx = vel[0] + smomAlt.dx, avy = vel[1] + smomAlt.dy;
\t\t\t\t\t\tfinal int ax = pos[0] + avx, ay = pos[1] + avy;
\t\t\t\t\t\tif (game.crossesFinish(pos[0], pos[1], ax, ay)
\t\t\t\t\t\t\t\t|| simOutcome(ax, ay, avx, avy, playerNum, AI1_DEEP_HORIZON,
\t\t\t\t\t\t\t\t\t\ttrue, true, true, true) >= 0) {
\t\t\t\t\t\t\t// Round 95 frontier: the topology-shaped model can false-kill a
"""

new = """\t\t\t\t\t\tfinal int avx = vel[0] + smomAlt.dx, avy = vel[1] + smomAlt.dy;
\t\t\t\t\t\tfinal int ax = pos[0] + avx, ay = pos[1] + avy;
\t\t\t\t\t\tboolean falseAliveTarget = false;
\t\t\t\t\t\t// Round 126 AI1 frontier: an equal-speed topology switch can
\t\t\t\t\t\t// leave a faithful-rival-alive line for a faithful-rival-dead
\t\t\t\t\t\t// one.  Reuse the bounded true-confirm model only for that
\t\t\t\t\t\t// transition; all ordinary ladder decisions remain unchanged.
\t\t\t\t\t\tif (moverKind(playerNum) == Player.Kind.AI1
\t\t\t\t\t\t\t\t&& poTByDir[chosen.ordinal()] == poTByDir[smomAlt.ordinal()]
\t\t\t\t\t\t\t\t&& Math.max(Math.abs(djvx), Math.abs(djvy))
\t\t\t\t\t\t\t\t\t\t== Math.max(Math.abs(avx), Math.abs(avy))
\t\t\t\t\t\t\t\t&& trapByDir[chosen.ordinal()] >= AI1_TRAP_L1
\t\t\t\t\t\t\t\t&& liveRivalsRemaining(playerNum) >= AI1_PRIVATE_FIELD_MIN_RIVALS
\t\t\t\t\t\t\t\t&& kindHomogeneousRoster(playerNum)
\t\t\t\t\t\t\t\t&& trueConfirmDepth < AI1_TRUE_CONFIRM_MAXDEPTH) {
\t\t\t\t\t\t\ttrueConfirmDepth++;
\t\t\t\t\t\t\ttry {
\t\t\t\t\t\t\t\tfinal int confirmCap = Math.max(AI1_SCORER_MAXRIVALS,
\t\t\t\t\t\t\t\t\t\tAI1_DEEP_CERT_RIVALS);
\t\t\t\t\t\t\t\tfinal boolean chosenTrueAlive = simOutcome(dcx, dcy, djvx, djvy,
\t\t\t\t\t\t\t\t\t\tplayerNum, AI1_DEEP_HORIZON, true, true, true, true,
\t\t\t\t\t\t\t\t\t\tfalse, true, confirmCap, null, null, null) >= 0;
\t\t\t\t\t\t\t\tfinal boolean altTrueAlive = simOutcome(ax, ay, avx, avy, playerNum,
\t\t\t\t\t\t\t\t\t\tAI1_DEEP_HORIZON, true, true, true, true, false, true,
\t\t\t\t\t\t\t\t\t\tconfirmCap, null, null, null) >= 0;
\t\t\t\t\t\t\t\tfalseAliveTarget = chosenTrueAlive && !altTrueAlive;
\t\t\t\t\t\t\t\tif (AI_DEBUG_DJS && falseAliveTarget)
\t\t\t\t\t\t\t\t\tSystem.err.println("AIDBG EQUAL-VETO p=" + playerNum
\t\t\t\t\t\t\t\t\t\t\t+ " keep " + chosen + " over false target " + smomAlt);
\t\t\t\t\t\t\t} finally {
\t\t\t\t\t\t\t\ttrueConfirmDepth--;
\t\t\t\t\t\t\t}
\t\t\t\t\t\t}
\t\t\t\t\t\tif (!falseAliveTarget && (game.crossesFinish(pos[0], pos[1], ax, ay)
\t\t\t\t\t\t\t\t|| simOutcome(ax, ay, avx, avy, playerNum, AI1_DEEP_HORIZON,
\t\t\t\t\t\t\t\t\t\ttrue, true, true, true) >= 0)) {
\t\t\t\t\t\t\t// Round 95 frontier: the topology-shaped model can false-kill a
"""

assert source.count(old) == 1, source.count(old)
assert "Round 126 AI1 frontier" not in source
source = source.replace(old, new, 1)
assert source.count("Round 126 AI1 frontier") == 1
assert source.count("moverKind(playerNum) == Player.Kind.AI1") >= 2
assert source.count("private Direction optimalMoveAI2") == 1
path.write_text(source)
print("materialized Round 126 equal-speed false-target veto")
