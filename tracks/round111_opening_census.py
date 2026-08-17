#!/usr/bin/env python3
"""Instrument every opening-pack true-confirm candidate in AI1.

Diagnostic only. It recreates the bounded opening-pack experiment and prints
all general state features before and after each actual switch, allowing the
Hungaroring seed-144 rescue to be separated from harmless-but-order-changing
opening decisions without naming a track, seed or coordinate in production.
"""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()

anchor = (
    "\tprivate final static int\t\tAI1_SLOW_PACK_SPD2_SMALL\t= 12;"
    "\t// round 71 (promoted): speed floor for the small-field gate "
    "(start-grid moves stay below it)\n"
)
assert source.count(anchor) == 1
assert "AI1_OPENING_PACK_MAX_HISTORY" not in source
source = source.replace(
    anchor,
    anchor
    + "\tprivate final static int\t\tAI1_OPENING_PACK_MAX_HISTORY\t= 4;"
      "\t// round 111 diagnostic opening window\n",
    1,
)

boundary = source.index("\tprivate Direction optimalMoveAI2")
head, tail = source[:boundary], source[boundary:]
old = """\t\t\t\t\t\tchosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\ttrue, funnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS, true);
"""
new = """\t\t\t\t\t\tfinal int openingHistory = game.players[game.subgamestate].getHistory().size();
\t\t\t\t\t\tfinal boolean openingPackConfirm = denseSlowPack
\t\t\t\t\t\t\t\t&& kindHomogeneousRoster(playerNum)
\t\t\t\t\t\t\t\t&& liveRivalsRemaining(playerNum) >= AI1_PRIVATE_FIELD_MIN_RIVALS
\t\t\t\t\t\t\t\t&& openingHistory <= AI1_OPENING_PACK_MAX_HISTORY;
\t\t\t\t\t\tfinal Direction openingBefore = chosen;
\t\t\t\t\t\tif (AI_DEBUG_DJS && openingPackConfirm)
\t\t\t\t\t\t\tSystem.err.println("AIDBG OPEN-CAND p=" + playerNum + " pos=(" + pos[0]
\t\t\t\t\t\t\t\t\t+ "," + pos[1] + ") vel=(" + vel[0] + "," + vel[1]
\t\t\t\t\t\t\t\t\t+ ") chosen=" + chosen + " landV=(" + scvx + "," + scvy
\t\t\t\t\t\t\t\t\t+ ") hist=" + openingHistory + " slowSpd2=" + slowSpd2
\t\t\t\t\t\t\t\t\t+ " spdInf=" + slowSpdInf + " ttf="
\t\t\t\t\t\t\t\t\t+ poTByDir[chosen.ordinal()] + " trap="
\t\t\t\t\t\t\t\t\t+ trapByDir[chosen.ordinal()] + " unc="
\t\t\t\t\t\t\t\t\t+ uncByDir[chosen.ordinal()] + " pack=" + slowPack + "/"
\t\t\t\t\t\t\t\t\t+ sealRivals + " ring=" + funnelMinRing + " smoke="
\t\t\t\t\t\t\t\t\t+ smokeDies + " start="
\t\t\t\t\t\t\t\t\t+ game.startZoneA.contains(pos[0], pos[1]));
\t\t\t\t\t\tchosen = openingPackConfirm
\t\t\t\t\t\t\t\t? dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\t\t\ttrue, AI1_DJS_SLOW_ROUNDS, AI1_SCORER_MAXRIVALS,
\t\t\t\t\t\t\t\t\t\ttrue, true, true, true)
\t\t\t\t\t\t\t\t: dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\t\t\ttrue, funnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS,
\t\t\t\t\t\t\t\t\t\ttrue);
\t\t\t\t\t\tif (AI_DEBUG_DJS && openingPackConfirm && chosen != openingBefore)
\t\t\t\t\t\t\tSystem.err.println("AIDBG OPEN-SWITCH p=" + playerNum + " pos=("
\t\t\t\t\t\t\t\t\t+ pos[0] + "," + pos[1] + ") vel=(" + vel[0] + ","
\t\t\t\t\t\t\t\t\t+ vel[1] + ") " + openingBefore + " -> " + chosen
\t\t\t\t\t\t\t\t\t+ " hist=" + openingHistory + " slowSpd2=" + slowSpd2
\t\t\t\t\t\t\t\t\t+ " ttf=" + poTByDir[openingBefore.ordinal()] + " trap="
\t\t\t\t\t\t\t\t\t+ trapByDir[openingBefore.ordinal()] + " unc="
\t\t\t\t\t\t\t\t\t+ uncByDir[openingBefore.ordinal()] + " pack=" + slowPack
\t\t\t\t\t\t\t\t\t+ "/" + sealRivals + " ring=" + funnelMinRing);
"""
assert head.count(old) == 1, head.count(old)
assert "AIDBG OPEN-CAND" not in source
head = head.replace(old, new, 1)
path.write_text(head + tail)
print("instrumented AI1 opening-pack confirmation census")
