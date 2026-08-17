#!/usr/bin/env python3
"""Materialize Round 112's far-opening true-rival confirmation in AI1.

The opening-pack census showed that the broad ESC confirmation had only two
bounded switches: the intended Hungaroring seed-144 rescue at map TTF 115 and
landing speed squared 18, and a Le Mans redistribution at TTF 58 / speed
squared 25.  This candidate admits only the far-opening speed-18 class in an
intact homogeneous pack through the mover's fourth personal move.  No track,
seed, coordinate, player number or absolute direction is encoded.  AI2 remains
the frozen control.
"""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()

constant_anchor = (
    "\tprivate final static int\t\tAI1_SLOW_PACK_SPD2_SMALL\t= 12;"
    "\t// round 71 (promoted): speed floor for the small-field gate "
    "(start-grid moves stay below it)\n"
)
assert source.count(constant_anchor) == 1
assert "AI1_FAR_OPENING_MIN_TTF" not in source
source = source.replace(
    constant_anchor,
    constant_anchor
    + "\tprivate final static int\t\tAI1_FAR_OPENING_MIN_TTF\t= 90;"
      "\t// round 112: exclude the mid-race ESC redistribution class\n"
    + "\tprivate final static int\t\tAI1_FAR_OPENING_SPEED2\t= 18;"
      "\t// measured two-axis |v|=2->3 start-funnel commitment\n"
    + "\tprivate final static int\t\tAI1_FAR_OPENING_MAX_HISTORY\t= 4;"
      "\t// confirmation through the fourth personal move only\n",
    1,
)

boundary = source.index("\tprivate Direction optimalMoveAI2")
head, tail = source[:boundary], source[boundary:]
old = """\t\t\t\t\t\tchosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\ttrue, funnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS, true);
"""
new = """\t\t\t\t\t\t// Round 112: the faithful-rival corridor confirm is admitted only
\t\t\t\t\t\t// for the far-opening speed-18 class isolated by the Round 111
\t\t\t\t\t\t// census.  The TTF and energy gates exclude the sole mid-race
\t\t\t\t\t\t// redistribution while keeping the Hungaroring-s144 proof.
\t\t\t\t\t\tfinal boolean farOpeningConfirm = denseSlowPack
\t\t\t\t\t\t\t\t&& kindHomogeneousRoster(playerNum)
\t\t\t\t\t\t\t\t&& liveRivalsRemaining(playerNum) >= AI1_PRIVATE_FIELD_MIN_RIVALS
\t\t\t\t\t\t\t\t&& game.players[game.subgamestate].getHistory().size()
\t\t\t\t\t\t\t\t\t\t<= AI1_FAR_OPENING_MAX_HISTORY
\t\t\t\t\t\t\t\t&& chosenT > AI1_FAR_OPENING_MIN_TTF
\t\t\t\t\t\t\t\t&& slowSpd2 == AI1_FAR_OPENING_SPEED2;
\t\t\t\t\t\tchosen = farOpeningConfirm
\t\t\t\t\t\t\t\t? dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\t\t\ttrue, AI1_DJS_SLOW_ROUNDS, AI1_SCORER_MAXRIVALS,
\t\t\t\t\t\t\t\t\t\ttrue, true, true, true)
\t\t\t\t\t\t\t\t: dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\t\t\ttrue, funnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS,
\t\t\t\t\t\t\t\t\t\ttrue);
"""
assert head.count(old) == 1, head.count(old)
assert "farOpeningConfirm" not in source
head = head.replace(old, new, 1)
source = head + tail
assert source.count("final boolean farOpeningConfirm") == 1
assert source.count("farOpeningConfirm") == 2
assert source.count("AI1_FAR_OPENING_MIN_TTF") == 2
assert source.count("private Direction optimalMoveAI2") == 1
path.write_text(source)
print("materialized Round 112 far-opening true-rival confirmation in AI1")
