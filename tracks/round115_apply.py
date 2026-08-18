#!/usr/bin/env python3
"""Materialize Round 115's AI1-only graduated field acceleration.

The promoted Round-106 certificate remains unchanged for every speed-squared
gain of at least 16. AI1 alone may also test moderate gains 9..15, but only
inside TTF 45, from an incumbent below the existing speed-7 danger threshold,
and never by replacing a deliberate scorer coast. The same 8-round
scorer-field proof still has to show strict mover and aggregate-field
improvement. AI2 remains the frozen Round-110 yardstick through delegation.
"""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()

# Round 109/110 promotion made AI2 delegate to the champion body. Keep that
# delegation byte-for-byte unchanged and isolate this experiment by mover kind.
ai2 = """\tprivate Direction optimalMoveAI2(final int[] pos, final int[] vel, final int playerNum) {
\t\treturn optimalMoveAI1(pos, vel, playerNum);
\t}
"""
assert source.count(ai2) == 1

constant_anchor = (
    "\tprivate final static int\t\tAI1_FIELD_ACCEL_MAX_TTF\t= 90;"
    "\t// keep the 8-round proof in the medium-range race phase\n"
)
assert source.count(constant_anchor) == 1
assert "AI1_FIELD_ACCEL_FRONTIER_MIN_SPEED2_GAIN" not in source
source = source.replace(
    constant_anchor,
    constant_anchor
    + "\tprivate final static int\t\tAI1_FIELD_ACCEL_FRONTIER_MIN_SPEED2_GAIN\t= 9;"
      "\t// round 115 frontier: moderate acceleration floor for AI1 only\n"
    + "\tprivate final static int\t\tAI1_FIELD_ACCEL_FRONTIER_LOW_GAIN_MAX_TTF\t= 45;"
      "\t// round 115: short-range boundary for speed2 gains 9..15\n",
    1,
)

javadoc = """\t/** Round 106: recover a one-turn acceleration only in a bounded forward
\t * pack when the same eight-round scorer world proves strict mover and
\t * aggregate-field gains. The TTF cap prevents long-range rollout optimism. */
"""
replacement_javadoc = """\t/** Round 106: recover a one-turn acceleration only in a bounded forward
\t * pack when the same eight-round scorer world proves strict mover and
\t * aggregate-field gains. Round 115 leaves the promoted gain>=16 rule intact;
\t * AI1 alone may test gains 9..15 inside TTF 45 from an incumbent below the
\t * speed-7 danger threshold, never from a scorer coast. */
"""
assert source.count(javadoc) == 1
source = source.replace(javadoc, replacement_javadoc, 1)

chosen_anchor = (
    "\t\tfinal int chosenSpeed2 = speedSquared(chosenVx, chosenVy);\n"
    "\t\tint chosenFinal = Integer.MIN_VALUE;\n"
)
chosen_replacement = (
    "\t\tfinal int chosenSpeed2 = speedSquared(chosenVx, chosenVy);\n"
    "\t\tfinal boolean frontierMover = moverKind(playerNum) == Player.Kind.AI1;\n"
    "\t\tint chosenFinal = Integer.MIN_VALUE;\n"
)
assert source.count(chosen_anchor) == 1
source = source.replace(chosen_anchor, chosen_replacement, 1)

speed_anchor = (
    "\t\t\tfinal int speed2 = speedSquared(nvx, nvy);\n"
    "\t\t\tif (speed2 - chosenSpeed2 < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN)\n"
    "\t\t\t\tcontinue;\n"
)
speed_replacement = (
    "\t\t\tfinal int speed2 = speedSquared(nvx, nvy);\n"
    "\t\t\tfinal int speed2Gain = speed2 - chosenSpeed2;\n"
    "\t\t\tfinal boolean frontierModerateGain = frontierMover\n"
    "\t\t\t\t\t&& chosen != Direction.NONE\n"
    "\t\t\t\t\t&& chosenSpeed2 < AI1_DJS_SPD2\n"
    "\t\t\t\t\t&& chosenT <= AI1_FIELD_ACCEL_FRONTIER_LOW_GAIN_MAX_TTF\n"
    "\t\t\t\t\t&& speed2Gain >= AI1_FIELD_ACCEL_FRONTIER_MIN_SPEED2_GAIN;\n"
    "\t\t\tif (speed2Gain < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN\n"
    "\t\t\t\t\t&& !frontierModerateGain)\n"
    "\t\t\t\tcontinue;\n"
)
assert source.count(speed_anchor) == 1
source = source.replace(speed_anchor, speed_replacement, 1)

assert source.count(ai2) == 1
assert source.count("frontierModerateGain") == 2
assert source.count("AI1_FIELD_ACCEL_FRONTIER_LOW_GAIN_MAX_TTF") == 2
assert source.count("chosenSpeed2 < AI1_DJS_SPD2") == 1
path.write_text(source)
print("materialized Round 115 AI1-only low-energy graduated field acceleration")
