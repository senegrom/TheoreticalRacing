#!/usr/bin/env python3
"""Apply the AI1-only Round 103 six-rival true-confirmation candidate."""
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

path.write_text(source, encoding="utf-8")
