#!/usr/bin/env python3
"""Materialize Round 108's AI1-only equal-speed false-target veto.

Round 105's remaining Zandvoort seed-115 crash occurs after the danger ladder
switches from the selected line to an equal-speed alternative.  The topology
rollout calls both lines alive, but the existing full-fidelity rival model says
that the selected line survives and the switch target dies.  Before taking an
equal-speed switch in a large homogeneous field, compare those two lines with
the faithful rival model and veto only that false-target transition.

The AI2 copy is deliberately untouched: it remains the frozen control.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceAi.java")
source = race.read_text()

# Include the AI1-only "frontier" comment in the anchor.  AI2 has the same
# control flow but its following comment says only "Round 95", so this anchor
# both proves the policy boundary and prevents an accidental champion edit.
ai1_old = """\t\t\t\t\t\t\t\t\t\tif (game.crossesFinish(pos[0], pos[1], ax, ay)
\t\t\t\t\t\t\t\t\t\t\t\t|| simOutcome(ax, ay, avx, avy, playerNum, AI1_DEEP_HORIZON,
\t\t\t\t\t\t\t\t\t\t\t\t\t\ttrue, true, true, true) >= 0) {
\t\t\t\t\t\t\t\t\t\t\t// Round 95 frontier: the topology-shaped model can false-kill a
"""

ai1_new = """\t\t\t\t\t\t\t\t\t\tboolean falseAliveTarget = false;
\t\t\t\t\t\t\t\t\t\t// Round 108 AI1 frontier: an equal-speed topology switch can
\t\t\t\t\t\t\t\t\t\t// leave a faithful-rival-alive line for a faithful-rival-dead one.
\t\t\t\t\t\t\t\t\t\t// Reuse the existing bounded true-confirm model only for that
\t\t\t\t\t\t\t\t\t\t// narrow transition; every ordinary ladder decision is unchanged.
\t\t\t\t\t\t\t\t\t\tif (poTByDir[chosen.ordinal()] == poTByDir[smomAlt.ordinal()]
\t\t\t\t\t\t\t\t\t\t\t\t&& Math.max(Math.abs(djvx), Math.abs(djvy))
\t\t\t\t\t\t\t\t\t\t\t\t\t\t== Math.max(Math.abs(avx), Math.abs(avy))
\t\t\t\t\t\t\t\t\t\t\t\t&& trapByDir[chosen.ordinal()] >= AI1_TRAP_L1
\t\t\t\t\t\t\t\t\t\t\t\t&& liveRivalsRemaining(playerNum) >= AI1_PRIVATE_FIELD_MIN_RIVALS
\t\t\t\t\t\t\t\t\t\t\t\t&& kindHomogeneousRoster(playerNum)
\t\t\t\t\t\t\t\t\t\t\t\t&& trueConfirmDepth < AI1_TRUE_CONFIRM_MAXDEPTH) {
\t\t\t\t\t\t\t\t\t\t\ttrueConfirmDepth++;
\t\t\t\t\t\t\t\t\t\t\ttry {
\t\t\t\t\t\t\t\t\t\t\t\tfinal int confirmCap = Math.max(AI1_SCORER_MAXRIVALS,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tAI1_DEEP_CERT_RIVALS);
\t\t\t\t\t\t\t\t\t\t\t\tfinal boolean chosenTrueAlive = simOutcome(dcx, dcy, djvx, djvy,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tplayerNum, AI1_DEEP_HORIZON, true, true, true, true,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tfalse, true, confirmCap, null, null, null) >= 0;
\t\t\t\t\t\t\t\t\t\t\t\tfinal boolean altTrueAlive = simOutcome(ax, ay, avx, avy, playerNum,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tAI1_DEEP_HORIZON, true, true, true, true, false, true,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tconfirmCap, null, null, null) >= 0;
\t\t\t\t\t\t\t\t\t\t\t\tfalseAliveTarget = chosenTrueAlive && !altTrueAlive;
\t\t\t\t\t\t\t\t\t\t\t} finally {
\t\t\t\t\t\t\t\t\t\t\t\ttrueConfirmDepth--;
\t\t\t\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t\t\t\tif (!falseAliveTarget && (game.crossesFinish(pos[0], pos[1], ax, ay)
\t\t\t\t\t\t\t\t\t\t\t\t|| simOutcome(ax, ay, avx, avy, playerNum, AI1_DEEP_HORIZON,
\t\t\t\t\t\t\t\t\t\t\t\t\t\ttrue, true, true, true) >= 0)) {
\t\t\t\t\t\t\t\t\t\t\t// Round 95 frontier: the topology-shaped model can false-kill a
"""

assert source.count(ai1_old) == 1, source.count(ai1_old)
assert "// Round 108 AI1 frontier:" not in source
source = source.replace(ai1_old, ai1_new, 1)
assert source.count(ai1_old) == 0
assert source.count("// Round 108 AI1 frontier:") == 1
# The frozen AI2 branch must retain its original corresponding condition.
assert source.count("// Round 95: the topology-shaped model can false-kill a genuinely") == 1
race.write_text(source)
