#!/usr/bin/env python3
"""Materialize Round 124's phase-consistent trap-L2 acceleration.

The old broad trap-L2 field-acceleration experiment contained one Pareto pace
gain and eight bad races. Diagnostics show a clean structural split. The gain
occurs for the second mover of the round at TTF 33; every nearby same-corner
counterexample fires after at least two rivals have already updated, while the
other counterexamples are farther than TTF 45.

Round 124 therefore lets the existing strict field certificate consider a
positive L1/L2 candidate only for AI1, only when at most one racer has already
moved in the current round, only through TTF 45, and only in the established
two-to-five-ahead class. The high-energy gain>=16, zero uncertainty,
unsealable landing, eight-round strict mover/field improvement and downstream
danger checks are unchanged. AI2 remains frozen.
"""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()

old_doc = (
    "\t * formation only with an adjacent prior candidate-velocity peer. Round 115\n"
    "\t * leaves the promoted gain>=16 rule otherwise intact;\n"
    "\t * AI1 alone may test gains 9..15 inside TTF 45 from an incumbent below the\n"
    "\t * speed-7 danger threshold, never from a scorer coast. */\n"
)
new_doc = (
    "\t * formation only with an adjacent prior candidate-velocity peer. Round 124\n"
    "\t * additionally admits a positive L1/L2 candidate only for the first two\n"
    "\t * movers of an AI1 round inside TTF 45; the partial-round counterexamples\n"
    "\t * remain excluded. Round 115's moderate zero-trap frontier is unchanged. */\n"
)
assert source.count(old_doc) == 1, source.count(old_doc)
source = source.replace(old_doc, new_doc, 1)

old_frontier = (
    "\t\tfinal boolean sixAheadFrontier = frontierMover\n"
    "\t\t\t\t&& rivalsAhead == AI1_FIELD_ACCEL_MAX_AHEAD + 1;\n"
)
new_frontier = (
    "\t\tfinal boolean sixAheadFrontier = frontierMover\n"
    "\t\t\t\t&& rivalsAhead == AI1_FIELD_ACCEL_MAX_AHEAD + 1;\n"
    "\t\tfinal boolean earlyRoundTrapFrontier = frontierMover\n"
    "\t\t\t\t&& game.subgamestate <= 1\n"
    "\t\t\t\t&& chosenT <= AI1_FIELD_ACCEL_FRONTIER_LOW_GAIN_MAX_TTF\n"
    "\t\t\t\t&& rivalsAhead <= AI1_FIELD_ACCEL_MAX_AHEAD;\n"
)
assert source.count(old_frontier) == 1, source.count(old_frontier)
source = source.replace(old_frontier, new_frontier, 1)

old_loop = (
    "\t\t\tfinal int turns = turnsByDir[d.ordinal()];\n"
    "\t\t\tif (d == chosen || d == Direction.NONE || turns == Integer.MAX_VALUE\n"
    "\t\t\t\t\t|| turns + 1 != chosenT || trapByDir[d.ordinal()] != 0.0\n"
    "\t\t\t\t\t|| uncByDir[d.ordinal()] != 0.0)\n"
    "\t\t\t\tcontinue;\n"
)
new_loop = (
    "\t\t\tfinal int turns = turnsByDir[d.ordinal()];\n"
    "\t\t\tfinal double candidateTrap = trapByDir[d.ordinal()];\n"
    "\t\t\tfinal boolean frontierTrapCandidate = earlyRoundTrapFrontier\n"
    "\t\t\t\t\t&& candidateTrap > 0.0 && candidateTrap <= AI1_TRAP_L2;\n"
    "\t\t\tif (d == chosen || d == Direction.NONE || turns == Integer.MAX_VALUE\n"
    "\t\t\t\t\t|| turns + 1 != chosenT\n"
    "\t\t\t\t\t|| candidateTrap != 0.0 && !frontierTrapCandidate\n"
    "\t\t\t\t\t|| uncByDir[d.ordinal()] != 0.0)\n"
    "\t\t\t\tcontinue;\n"
)
assert source.count(old_loop) == 1, source.count(old_loop)
source = source.replace(old_loop, new_loop, 1)

assert source.count("earlyRoundTrapFrontier") == 2
assert source.count("frontierTrapCandidate") == 2
assert source.count("game.subgamestate <= 1") == 1
assert source.count("private Direction optimalMoveAI2") == 1
path.write_text(source)
print("materialized Round 124 early-round trap-L2 acceleration")
