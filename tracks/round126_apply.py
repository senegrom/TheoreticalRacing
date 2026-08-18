#!/usr/bin/env python3
"""Materialize Round 126's AI1-only equal-speed false-target veto.

The remaining Zandvoort seed-115 crash is an equal-speed lane-choice failure:
the topology-shaped deep world abandons its chosen line for an alternative that
the bounded faithful-rival world kills, while that same faithful world keeps
the chosen line alive. Before accepting only that narrow class of switch, run
the existing certification-cap true-rival model on both landings and veto the
transition when it would replace a true-alive chosen line with a true-dead
alternative.

The gate is AI1-only because AI2 delegates to the shared frontier body and must
remain the frozen control. Every non-equal-speed switch and every ordinary
survival decision remains byte-for-byte unchanged.
"""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()
assert "Round 126 AI1 frontier" not in source

lines = source.splitlines(keepends=True)
avx_matches = [
    index for index, line in enumerate(lines)
    if line.lstrip().startswith(
        "final int avx = vel[0] + smomAlt.dx, avy = vel[1] + smomAlt.dy;")
]
assert len(avx_matches) == 1, avx_matches
avx_index = avx_matches[0]
indent = lines[avx_index][:-len(lines[avx_index].lstrip())]
assert lines[avx_index + 1].lstrip().startswith(
    "final int ax = pos[0] + avx, ay = pos[1] + avy;")
if_index = avx_index + 2
assert lines[if_index].lstrip().startswith(
    "if (game.crossesFinish(pos[0], pos[1], ax, ay)")
assert lines[if_index + 1].lstrip().startswith(
    "|| simOutcome(ax, ay, avx, avy, playerNum, AI1_DEEP_HORIZON,")
assert lines[if_index + 2].lstrip() == "true, true, true, true) >= 0) {\n"
assert lines[if_index + 3].lstrip().startswith(
    "// Round 95 frontier: the topology-shaped model can false-kill a")

block = [
    indent + "boolean falseAliveTarget = false;\n",
    indent + "// Round 126 AI1 frontier: an equal-speed topology switch can\n",
    indent + "// leave a faithful-rival-alive line for a faithful-rival-dead\n",
    indent + "// one. Reuse the bounded true-confirm model only for that\n",
    indent + "// transition; all ordinary ladder decisions remain unchanged.\n",
    indent + "if (moverKind(playerNum) == Player.Kind.AI1\n",
    indent + "\t\t&& poTByDir[chosen.ordinal()] == poTByDir[smomAlt.ordinal()]\n",
    indent + "\t\t&& Math.max(Math.abs(djvx), Math.abs(djvy))\n",
    indent + "\t\t\t\t== Math.max(Math.abs(avx), Math.abs(avy))\n",
    indent + "\t\t&& trapByDir[chosen.ordinal()] >= AI1_TRAP_L1\n",
    indent + "\t\t&& liveRivalsRemaining(playerNum) >= AI1_PRIVATE_FIELD_MIN_RIVALS\n",
    indent + "\t\t&& kindHomogeneousRoster(playerNum)\n",
    indent + "\t\t&& trueConfirmDepth < AI1_TRUE_CONFIRM_MAXDEPTH) {\n",
    indent + "\ttrueConfirmDepth++;\n",
    indent + "\ttry {\n",
    indent + "\t\tfinal int confirmCap = Math.max(AI1_SCORER_MAXRIVALS,\n",
    indent + "\t\t\t\tAI1_DEEP_CERT_RIVALS);\n",
    indent + "\t\tfinal boolean chosenTrueAlive = simOutcome(dcx, dcy, djvx, djvy,\n",
    indent + "\t\t\t\tplayerNum, AI1_DEEP_HORIZON, true, true, true, true,\n",
    indent + "\t\t\t\tfalse, true, confirmCap, null, null, null) >= 0;\n",
    indent + "\t\tfinal boolean altTrueAlive = simOutcome(ax, ay, avx, avy, playerNum,\n",
    indent + "\t\t\t\tAI1_DEEP_HORIZON, true, true, true, true, false, true,\n",
    indent + "\t\t\t\tconfirmCap, null, null, null) >= 0;\n",
    indent + "\t\tfalseAliveTarget = chosenTrueAlive && !altTrueAlive;\n",
    indent + "\t\tif (AI_DEBUG_DJS && falseAliveTarget)\n",
    indent + "\t\t\tSystem.err.println(\"AIDBG EQUAL-VETO p=\" + playerNum\n",
    indent + "\t\t\t\t\t+ \" keep \" + chosen + \" over false target \" + smomAlt);\n",
    indent + "\t} finally {\n",
    indent + "\t\ttrueConfirmDepth--;\n",
    indent + "\t}\n",
    indent + "}\n",
]
lines[if_index:if_index] = block
shifted_if = if_index + len(block)
lines[shifted_if] = indent + (
    "if (!falseAliveTarget && (game.crossesFinish(pos[0], pos[1], ax, ay)\n")
lines[shifted_if + 2] = indent + "\t\ttrue, true, true, true) >= 0)) {\n"

source = "".join(lines)
assert source.count("Round 126 AI1 frontier") == 1
assert source.count("AIDBG EQUAL-VETO") == 1
assert source.count("if (!falseAliveTarget && (game.crossesFinish") == 1
assert source.count("private Direction optimalMoveAI2") == 1
path.write_text(source)
print("materialized Round 126 equal-speed false-target veto")
