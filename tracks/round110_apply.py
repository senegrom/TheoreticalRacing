#!/usr/bin/env python3
"""Materialize the Round 110 dual-frontier AI1 candidate.

This rebases the strongest unfinished branch result onto the promoted Round 106
champion:

* an opening-pack true-rival confirmation rescues Hungaroring seed 144, but
  only in an intact homogeneous dense pack and through the fourth personal
  move; and
* an equal-speed false-target veto rescues Zandvoort seed 115.

The historical combined gate produced no slower, safety-regression or
redistribution outcomes; its summary failed only because four focused JSONs
were counted twice. AI2 remains the frozen control.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceAi.java")
source = race.read_text()

# Round 106 already promoted the instance-state correction needed by both
# bounded recursive confirmations. Fail closed on any older baseline.
assert source.count("\tprivate int\t\t\t\t\ttrueConfirmDepth;") == 1
assert source.count("\tprivate static int\t\t\t\ttrueConfirmDepth;") == 0
assert source.count("\tvolatile boolean\t\t\t\tsimTrace;") == 1
assert source.count("\tstatic volatile boolean\t\t\tsimTrace;") == 0
race_game = Path("src/tr/logic/RaceGame.java").read_text()
assert race_game.count("ai.simTrace") == 2
assert race_game.count("RaceAi.simTrace") == 0

# Round 110a: bounded opening-pack confirmation. The personal-history cap is
# track-independent and is the exact boundary already screened by the old
# combined branch.
constant_anchor = (
    "\tprivate final static int\t\tAI1_SLOW_PACK_SPD2_SMALL\t= 12;"
    "\t// round 71 (promoted): speed floor for the small-field gate "
    "(start-grid moves stay below it)\n"
)
assert source.count(constant_anchor) == 1
assert "AI1_OPENING_PACK_MAX_HISTORY" not in source
source = source.replace(
    constant_anchor,
    constant_anchor
    + "\tprivate final static int\t\tAI1_OPENING_PACK_MAX_HISTORY\t= 4;"
      "\t// round 110: true-rival confirmation through the fourth personal move\n",
    1,
)

boundary = source.index("\tprivate Direction optimalMoveAI2")
head, tail = source[:boundary], source[boundary:]
esc_old = """\t\t\t\t\t\tchosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\ttrue, funnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS, true);
"""
esc_new = """\t\t\t\t\t\t// Round 110 opening-pack frontier: the broad ESC corridor confirm
\t\t\t\t\t\t// is unnecessary. Pay for it only in a dense homogeneous roster
\t\t\t\t\t\t// through the mover's fourth personal move, the measured start-
\t\t\t\t\t\t// funnel class containing Hungaroring seed 144.
\t\t\t\t\t\tfinal boolean openingPackConfirm = denseSlowPack
\t\t\t\t\t\t\t\t&& kindHomogeneousRoster(playerNum)
\t\t\t\t\t\t\t\t&& liveRivalsRemaining(playerNum) >= AI1_PRIVATE_FIELD_MIN_RIVALS
\t\t\t\t\t\t\t\t&& game.players[game.subgamestate].getHistory().size()
\t\t\t\t\t\t\t\t\t\t<= AI1_OPENING_PACK_MAX_HISTORY;
\t\t\t\t\t\tchosen = openingPackConfirm
\t\t\t\t\t\t\t\t? dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\t\t\ttrue, AI1_DJS_SLOW_ROUNDS, AI1_SCORER_MAXRIVALS,
\t\t\t\t\t\t\t\t\t\ttrue, true, true, true)
\t\t\t\t\t\t\t\t: dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\t\t\ttrue, funnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS,
\t\t\t\t\t\t\t\t\t\ttrue);
"""
assert head.count(esc_old) == 1, head.count(esc_old)
head = head.replace(esc_old, esc_new, 1)
source = head + tail

# Round 110b: equal-speed topology targets get a faithful-rival comparison only
# when both lines have the same map pace and speed class in a large homogeneous
# roster. The selected line is retained only if it lives and the target dies.
equal_old = """\t\t\t\t\t\t\t\t\t\tif (game.crossesFinish(pos[0], pos[1], ax, ay)
\t\t\t\t\t\t\t\t\t\t\t\t|| simOutcome(ax, ay, avx, avy, playerNum, AI1_DEEP_HORIZON,
\t\t\t\t\t\t\t\t\t\t\t\t\t\ttrue, true, true, true) >= 0) {
\t\t\t\t\t\t\t\t\t\t\t// Round 95 frontier: the topology-shaped model can false-kill a
"""
equal_new = """\t\t\t\t\t\t\t\t\t\tboolean falseAliveTarget = false;
\t\t\t\t\t\t\t\t\t\t// Round 110 equal-speed frontier: do not abandon a faithful-
\t\t\t\t\t\t\t\t\t\t// rival-alive line for a faithful-rival-dead topology target.
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
assert source.count(equal_old) == 1, source.count(equal_old)
assert "Round 110 equal-speed frontier" not in source
source = source.replace(equal_old, equal_new, 1)

assert source.count("openingPackConfirm") == 3
assert source.count("Round 110 equal-speed frontier") == 1
assert source.count("// Round 95: the topology-shaped model can false-kill a genuinely") == 1
race.write_text(source)
print("materialized Round 110 opening-pack and equal-speed rescues in AI1")
