#!/usr/bin/env python3
"""Extend only AI1's synchronized full-finish proof beyond map TTF 30.

The existing Round-96 admission contract remains unchanged: non-coasting,
exactly one map turn faster, exact L2, zero uncertainty, homogeneous starting
roster, at least five live rivals, adjacent same-velocity formation peer,
non-sealable landing, dual full-to-finish lower-bound proofs, strict eight-round
mover and aggregate-field improvement, and the independent downstream danger
veto.  This experiment changes only the upper TTF boundary for that contract.
"""
from __future__ import annotations

import argparse
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()

parser = argparse.ArgumentParser()
parser.add_argument("max_ttf", type=int, choices=(35, 40, 45))
args = parser.parse_args()

constant = (
    "\tprivate final static int\t\tAI1_FINISH_EXTENDED_TTF\t= 30;"
    "\t// round 96: one-turn, non-coasting homogeneous extension of the full finish proof\n"
)
assert source.count(constant) == 1
source = source.replace(
    constant,
    constant
    + f"\tprivate final static int\t\tAI1_FINISH_SYNC_FAR_TTF\t= {args.max_ttf};"
      "\t// round 112 experiment: same synchronized proof, farther from the flag\n",
    1,
)

boundary = source.index("\tprivate Direction optimalMoveAI2")
head, tail = source[:boundary], source[boundary:]
old = (
    "\t\t\t\t\tfinal boolean extendedFrontier = t > AI1_FINISH_HOMOGENEOUS_TTF\n"
    "\t\t\t\t\t\t\t&& t <= AI1_FINISH_EXTENDED_TTF && t + 1 == chosenT\n"
)
new = (
    "\t\t\t\t\tfinal boolean extendedFrontier = t > AI1_FINISH_HOMOGENEOUS_TTF\n"
    "\t\t\t\t\t\t\t&& t <= AI1_FINISH_SYNC_FAR_TTF && t + 1 == chosenT\n"
)
assert head.count(old) == 1, head.count(old)
head = head.replace(old, new, 1)
source = head + tail

marker = f"\t// Round 112 finish-frontier variant: synchronized proof through TTF {args.max_ttf}.\n"
anchor = "\tprivate final static int\t\tAI1_PRIVATE_BASE_HORIZON\t= 3;"
assert source.count(anchor) == 1
source = source.replace(anchor, marker + anchor, 1)

assert source.count("AI1_FINISH_SYNC_FAR_TTF") == 2
path.write_text(source)
print(f"materialized synchronized full-finish frontier through TTF {args.max_ttf}")
