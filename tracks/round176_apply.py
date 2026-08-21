#!/usr/bin/env python3
"""Materialize Round 176's narrow faithful-rival sprint confirmation.

Rand3 seed 1 exposed a finish-sprint false certificate.  At move 448 the
normal scorer selected NW, which the perfect rollout finishes in five rounds.
The Round-75 sprint override replaced it with map-faster N.  Both historical
proxy worlds reported a finish, but faithful rivals occupy N's only continuation
at true round five and the car crashes.  Confirm only that narrow class:
traffic-dependent L1 sprint candidates at map TTF >= 5.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceAi.java")
source = race.read_text()

old = "\tprivate final static int\t\tAI1_FINISH_CERT_TTF\t= 15;\t// round 75 (promoted): legacy mixed-field cap for the dual-model finish sprint\n"
new = old + (
    "\tprivate final static int\t\tAI1_FINISH_TRUE_CONFIRM_ROUNDS\t= 5;"
    "\t// round 176: faithful-rival veto for one-successor sprint lines\n"
)
assert source.count(old) == 1, source.count(old)
assert "AI1_FINISH_TRUE_CONFIRM_ROUNDS" not in source
source = source.replace(old, new, 1)

old = """\t\t\t\t\tif (simOutcome(nx, ny, nvx, nvy, playerNum, rounds, true, true, true, true,
\t\t\t\t\t\t\tAI1_DEEP_CERT_RIVALS, null) != 0)
\t\t\t\t\t\tcontinue;
\t\t\t\t\tif (extendedFrontier) {
"""
new = """\t\t\t\t\tif (simOutcome(nx, ny, nvx, nvy, playerNum, rounds, true, true, true, true,
\t\t\t\t\t\t\tAI1_DEEP_CERT_RIVALS, null) != 0)
\t\t\t\t\t\tcontinue;
\t\t\t\t\t// Round 176: a one-successor sprint can pass both proxy worlds
\t\t\t\t\t// while faithful rivals occupy its only continuation one round
\t\t\t\t\t// later. Confirm only that narrow, traffic-dependent class;
\t\t\t\t\t// wider sprint lines retain the established cheaper certificate.
\t\t\t\t\tif (t >= AI1_FINISH_TRUE_CONFIRM_ROUNDS
\t\t\t\t\t\t\t&& trapByDir[d.ordinal()] >= AI1_TRAP_L1
\t\t\t\t\t\t\t&& liveRivalsRemaining(playerNum) > 0) {
\t\t\t\t\t\tif (trueConfirmDepth >= AI1_TRUE_CONFIRM_MAXDEPTH)
\t\t\t\t\t\t\tcontinue;
\t\t\t\t\t\ttrueConfirmDepth++;
\t\t\t\t\t\ttry {
\t\t\t\t\t\t\tif (simOutcome(nx, ny, nvx, nvy, playerNum,
\t\t\t\t\t\t\t\t\tAI1_FINISH_TRUE_CONFIRM_ROUNDS, true, true, true, true,
\t\t\t\t\t\t\t\t\tfalse, true, AI1_DEEP_CERT_RIVALS, null, null, null) < 0)
\t\t\t\t\t\t\t\tcontinue;
\t\t\t\t\t\t} finally {
\t\t\t\t\t\t\ttrueConfirmDepth--;
\t\t\t\t\t\t}
\t\t\t\t\t}
\t\t\t\t\tif (extendedFrontier) {
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)
assert source.count("// Round 176: a one-successor sprint") == 1
assert source.count("AI1_FINISH_TRUE_CONFIRM_ROUNDS") == 3
race.write_text(source)
print("materialized Round 176 finish-sprint true confirmation")
