#!/usr/bin/env python3
"""Apply Round 103's full-field true-confirmation fix to both race AIs."""
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

old_ai2 = """\t\t\t\t\t\t\t\tif (deepChoice == chosen)
\t\t\t\t\t\t\t\t\tdeepChoice = dangerJointSearch(pos, vel, playerNum, chosen, true, true,
\t\t\t\t\t\t\t\t\t\t\ttrue, true, AI1_DEEP_HORIZON);"""
new_ai2 = """\t\t\t\t\t\t\t\tif (deepChoice == chosen)
\t\t\t\t\t\t\t\t\tdeepChoice = dangerJointSearch(pos, vel, playerNum, chosen, true, true,
\t\t\t\t\t\t\t\t\t\t\ttrue, true, AI1_DEEP_HORIZON, AI1_SCORER_MAXRIVALS,
\t\t\t\t\t\t\t\t\t\t\tfalse, false, true);"""
assert source.count(old_ai2) == 1
source = source.replace(old_ai2, new_ai2, 1)

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

path.write_text(source, encoding="utf-8")
