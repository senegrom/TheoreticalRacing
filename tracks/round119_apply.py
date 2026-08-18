#!/usr/bin/env python3
"""Materialize Round 119's synchronized six-ahead moderate acceleration.

Round 117 admits exactly six rivals ahead only for a synchronized formation:
a previously moved rival must be adjacent to the candidate landing and already
carry the candidate velocity.  It unnecessarily retained the old speed-squared
16 floor even inside Round 115's short-range moderate-gain proof window.

This experiment allows gains 9..15 in that same synchronized six-ahead class,
while retaining every existing guard: AI1-only, non-coasting incumbent,
chosen speed below the speed-seven danger threshold, TTF <=45, one map-turn
improvement, zero trap/uncertainty, unsealable landing, eight-round strict mover
and aggregate-field improvement, and all downstream danger machinery.  AI2 is
untouched.
"""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()

old_doc = (
    "\t * aggregate-field gains. Round 117 admits an exact-six-ahead high-energy\n"
    "\t * formation only with an adjacent prior candidate-velocity peer. Round 115\n"
    "\t * leaves the promoted gain>=16 rule otherwise intact;\n"
    "\t * AI1 alone may test gains 9..15 inside TTF 45 from an incumbent below the\n"
    "\t * speed-7 danger threshold, never from a scorer coast. */\n"
)
new_doc = (
    "\t * aggregate-field gains. Round 119 extends Round 117's synchronized\n"
    "\t * exact-six-ahead formation into Round 115's moderate gain 9..15 band;\n"
    "\t * the adjacent prior candidate-velocity peer, TTF-45, low incumbent speed,\n"
    "\t * non-coast and strict field proof remain mandatory. */\n"
)
assert source.count(old_doc) == 1, source.count(old_doc)
source = source.replace(old_doc, new_doc, 1)

old_block = (
    "\t\t\t// The new six-ahead class is the established high-energy arm only;\n"
    "\t\t\t// Round 115's moderate 9..15 frontier remains capped at five ahead.\n"
    "\t\t\tif (sixAheadFrontier && speed2Gain < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN)\n"
    "\t\t\t\tcontinue;\n"
)
new_block = (
    "\t\t\t// Round 119: the synchronized six-ahead formation may use the same\n"
    "\t\t\t// short-range moderate-gain certificate as the two-to-five-ahead arm.\n"
    "\t\t\t// frontierModerateGain already enforces AI1, non-coast, chosen speed\n"
    "\t\t\t// below 7, TTF <=45 and speed-squared gain >=9.\n"
)
assert source.count(old_block) == 1, source.count(old_block)
source = source.replace(old_block, new_block, 1)

assert source.count("Round 119: the synchronized six-ahead formation") == 1
assert source.count("hasAdjacentPriorCandidateVelocityPeer(") == 2
assert source.count("private Direction optimalMoveAI2") == 1
path.write_text(source)
print("materialized Round 119 synchronized six-ahead moderate acceleration")
