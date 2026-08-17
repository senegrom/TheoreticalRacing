#!/usr/bin/env python3
"""Apply Round 106 instance-state and homogeneous opening-pack changes."""
from pathlib import Path

race = Path('src/tr/logic/RaceAi.java')
source = race.read_text()
for old, new in (
    ('\tprivate static int\t\t\t\ttrueConfirmDepth;',
     '\tprivate int\t\t\t\t\ttrueConfirmDepth;'),
    ('\tstatic volatile boolean\t\t\tsimTrace;',
     '\tvolatile boolean\t\t\t\tsimTrace;'),
):
    assert source.count(old) == 1
    source = source.replace(old, new, 1)

anchor = ('\tprivate final static int\t\tAI1_SLOW_PACK_SPD2_SMALL\t= 12;'
          '\t// round 71 (promoted): speed floor for the small-field gate '
          '(start-grid moves stay below it)\n')
assert source.count(anchor) == 1
source = source.replace(
    anchor,
    anchor + ('\tprivate final static int\t\tAI1_OPENING_PACK_MAX_HISTORY\t= 4;'
              '\t// round 106: homogeneous start-funnel confirmation through the '
              'fourth personal move\n'),
    1,
)
old = '''\t\t\t\t\t\tchosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\ttrue, funnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS, true);
'''
new = '''\t\t\t\t\t\tfinal boolean openingPackConfirm = denseSlowPack
\t\t\t\t\t\t\t\t&& kindHomogeneousRoster(playerNum)
\t\t\t\t\t\t\t\t&& game.players[game.subgamestate].getHistory().size()
\t\t\t\t\t\t\t\t\t\t<= AI1_OPENING_PACK_MAX_HISTORY;
\t\t\t\t\t\tchosen = openingPackConfirm
\t\t\t\t\t\t\t\t? dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\t\t\ttrue, AI1_DJS_SLOW_ROUNDS, AI1_SCORER_MAXRIVALS, true,
\t\t\t\t\t\t\t\t\t\ttrue, true, true)
\t\t\t\t\t\t\t\t: dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\t\t\ttrue, funnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS, true);
'''
assert source.count(old) == 2
source = source.replace(old, new, 1)
race.write_text(source)

game = Path('src/tr/logic/RaceGame.java')
source = game.read_text()
assert source.count('RaceAi.simTrace = true;') == 1
assert source.count('RaceAi.simTrace = false;') == 1
source = source.replace('RaceAi.simTrace = true;', 'ai.simTrace = true;', 1)
source = source.replace('RaceAi.simTrace = false;', 'ai.simTrace = false;', 1)
game.write_text(source)
