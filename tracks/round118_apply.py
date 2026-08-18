#!/usr/bin/env python3
"""Materialize a broad AI1-only exact-seven-ahead acceleration census.

Round 117 proved one synchronized six-ahead formation. This experiment opens
only the next cardinality: exactly seven live rivals ahead of the mover. It
keeps the established high-energy floor, eight-round strict mover/aggregate
field proof, funnel check, seal veto and downstream danger machinery. No track,
seed, coordinate, player or direction identity is encoded. AI2 remains frozen.

This is deliberately a census candidate, not a promotion candidate: the exact
differential determines whether the class contains clean gains and which
structural separators are needed.
"""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global source
    count = source.count(old)
    assert count == 1, (label, count)
    source = source.replace(old, new, 1)


replace_once(
    "\t\tfinal boolean sixAheadFrontier = frontierMover\n"
    "\t\t\t\t&& rivalsAhead == AI1_FIELD_ACCEL_MAX_AHEAD + 1;\n"
    "\t\tif (liveRivals < AI1_PRIVATE_FIELD_MIN_RIVALS\n"
    "\t\t\t\t|| rivalsAhead < AI1_FIELD_ACCEL_MIN_AHEAD\n"
    "\t\t\t\t|| rivalsAhead > AI1_FIELD_ACCEL_MAX_AHEAD && !sixAheadFrontier\n"
    "\t\t\t\t|| aheadProgress <= 0L)\n",
    "\t\tfinal boolean sixAheadFrontier = frontierMover\n"
    "\t\t\t\t&& rivalsAhead == AI1_FIELD_ACCEL_MAX_AHEAD + 1;\n"
    "\t\tfinal boolean sevenAheadFrontier = frontierMover\n"
    "\t\t\t\t&& rivalsAhead == AI1_FIELD_ACCEL_MAX_AHEAD + 2;\n"
    "\t\tif (liveRivals < AI1_PRIVATE_FIELD_MIN_RIVALS\n"
    "\t\t\t\t|| rivalsAhead < AI1_FIELD_ACCEL_MIN_AHEAD\n"
    "\t\t\t\t|| rivalsAhead > AI1_FIELD_ACCEL_MAX_AHEAD\n"
    "\t\t\t\t\t\t&& !sixAheadFrontier && !sevenAheadFrontier\n"
    "\t\t\t\t|| aheadProgress <= 0L)\n",
    "seven-ahead admission",
)

replace_once(
    "\t\tfinal int fieldProofRounds = sixAheadFrontier\n"
    "\t\t\t\t? AI1_FIELD_ACCEL_SIX_AHEAD_ROUNDS : AI1_STAGED_HORIZON;\n",
    "\t\tfinal int fieldProofRounds = sixAheadFrontier || sevenAheadFrontier\n"
    "\t\t\t\t? AI1_FIELD_ACCEL_SIX_AHEAD_ROUNDS : AI1_STAGED_HORIZON;\n",
    "seven-ahead proof depth",
)

replace_once(
    "\t\t\t// The new six-ahead class is the established high-energy arm only;\n"
    "\t\t\t// Round 115's moderate 9..15 frontier remains capped at five ahead.\n"
    "\t\t\tif (sixAheadFrontier && speed2Gain < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN)\n"
    "\t\t\t\tcontinue;\n",
    "\t\t\t// Pack-cardinality frontiers remain the established high-energy arm\n"
    "\t\t\t// only; Round 115's moderate 9..15 rule stays capped at five ahead.\n"
    "\t\t\tif ((sixAheadFrontier || sevenAheadFrontier)\n"
    "\t\t\t\t\t&& speed2Gain < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN)\n"
    "\t\t\t\tcontinue;\n",
    "seven-ahead energy floor",
)

replace_once(
    "\t * aggregate-field gains. Round 117 admits an exact-six-ahead high-energy\n"
    "\t * formation only with an adjacent prior candidate-velocity peer. Round 115\n",
    "\t * aggregate-field gains. Round 118 observes the exact-seven-ahead\n"
    "\t * high-energy class while Round 117 keeps its exact-six-ahead formation\n"
    "\t * gated by an adjacent prior candidate-velocity peer. Round 115\n",
    "method documentation",
)

assert source.count("sevenAheadFrontier") == 4
assert source.count("hasAdjacentPriorCandidateVelocityPeer") == 2
assert source.count("private Direction optimalMoveAI2") == 1
path.write_text(source)
print("materialized Round 118 broad exact-seven-ahead acceleration census")
