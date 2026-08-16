#!/usr/bin/env python3
"""Apply Round 103's six-rival true-confirmation rule to AI1 and AI2."""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text(encoding="utf-8")

old_latch = "\tprivate static boolean\t\t\tinTrueRivalConfirm;"
new_latch = "\tprivate boolean\t\t\t\tinTrueRivalConfirm;"
assert source.count(old_latch) == 1
source = source.replace(old_latch, new_latch, 1)

old_chosen = """\t\t\t\t\ttrueDead = simOutcome(cx, cy, cvx, cvy, playerNum, AI1_TRUE_CONFIRM_ROUNDS,
\t\t\t\t\t\t\tsimFinishVanish, exactSelf, exactRivals, true, scorerSelf, true,
\t\t\t\t\t\t\tscorerCap, null, null, null) < 0;"""
new_chosen = """\t\t\t\t\ttrueDead = simOutcome(cx, cy, cvx, cvy, playerNum, AI1_TRUE_CONFIRM_ROUNDS,
\t\t\t\t\t\t\tsimFinishVanish, exactSelf, exactRivals, true, scorerSelf, true,
\t\t\t\t\t\t\tAI1_DEEP_CERT_RIVALS, null, null, null) < 0;"""
assert source.count(old_chosen) == 1
source = source.replace(old_chosen, new_chosen, 1)

old_target = """\t\t\t\t\tsurvives = simOutcome(pos[0] + ncvx, pos[1] + ncvy, ncvx, ncvy, playerNum,
\t\t\t\t\t\t\tAI1_TRUE_CONFIRM_ROUNDS, simFinishVanish, exactSelf, exactRivals, true,
\t\t\t\t\t\t\tscorerSelf, true, scorerCap, null, null, null) >= 0;"""
new_target = """\t\t\t\t\tsurvives = simOutcome(pos[0] + ncvx, pos[1] + ncvy, ncvx, ncvy, playerNum,
\t\t\t\t\t\t\tAI1_TRUE_CONFIRM_ROUNDS, simFinishVanish, exactSelf, exactRivals, true,
\t\t\t\t\t\t\tscorerSelf, true, AI1_DEEP_CERT_RIVALS, null, null, null) >= 0;"""
assert source.count(old_target) == 1
source = source.replace(old_target, new_target, 1)

old_ai2 = """\t\t\t\t\t\t\t\tif (deepChoice == chosen)
\t\t\t\t\t\t\t\t\tdeepChoice = dangerJointSearch(pos, vel, playerNum, chosen, true, true,
\t\t\t\t\t\t\t\t\t\t\ttrue, true, AI1_DEEP_HORIZON);"""
new_ai2 = """\t\t\t\t\t\t\t\tif (deepChoice == chosen)
\t\t\t\t\t\t\t\t\tdeepChoice = dangerJointSearch(pos, vel, playerNum, chosen, true, true,
\t\t\t\t\t\t\t\t\t\t\ttrue, true, AI1_DEEP_HORIZON, AI1_SCORER_MAXRIVALS,
\t\t\t\t\t\t\t\t\t\t\tfalse, false, true);"""
assert source.count(old_ai2) == 1
source = source.replace(old_ai2, new_ai2, 1)

path.write_text(source, encoding="utf-8")
