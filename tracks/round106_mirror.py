#!/usr/bin/env python3
"""Mirror the proven Round 106 AI1 gates into the AI2 copy."""
from pathlib import Path

path = Path('src/tr/logic/RaceAi.java')
source = path.read_text()
old_open = '''\t\t\t\t\t\tchosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\ttrue, funnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS, true);
'''
new_open = '''\t\t\t\t\t\tfinal boolean openingPackConfirm = denseSlowPack
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
assert source.count(old_open) == 1
source = source.replace(old_open, new_open, 1)
old_veto = '''\t\t\t\t\t\t\t\t\t\tif (game.crossesFinish(pos[0], pos[1], ax, ay)
\t\t\t\t\t\t\t\t\t\t\t\t|| simOutcome(ax, ay, avx, avy, playerNum, AI1_DEEP_HORIZON,
\t\t\t\t\t\t\t\t\t\t\t\t\t\ttrue, true, true, true) >= 0) {
'''
new_veto = '''\t\t\t\t\t\t\t\t\t\tboolean falseAliveTarget = false;
\t\t\t\t\t\t\t\t\t\tif (poTByDir[chosen.ordinal()] == poTByDir[smomAlt.ordinal()]
\t\t\t\t\t\t\t\t\t\t\t\t&& Math.max(Math.abs(djvx), Math.abs(djvy))
\t\t\t\t\t\t\t\t\t\t\t\t\t\t== Math.max(Math.abs(avx), Math.abs(avy))
\t\t\t\t\t\t\t\t\t\t\t\t&& trapByDir[chosen.ordinal()] >= AI1_TRAP_L1
\t\t\t\t\t\t\t\t\t\t\t\t&& liveRivalsRemaining(playerNum) >= AI1_PRIVATE_FIELD_MIN_RIVALS
\t\t\t\t\t\t\t\t\t\t\t\t&& kindHomogeneousRoster(playerNum)
\t\t\t\t\t\t\t\t\t\t\t\t&& trueConfirmDepth < AI1_TRUE_CONFIRM_MAXDEPTH) {
\t\t\t\t\t\t\t\t\t\t\ttrueConfirmDepth++;
\t\t\t\t\t\t\t\t\t\t\ttry {
\t\t\t\t\t\t\t\t\t\t\t\tfinal int confirmCap = Math.max(AI1_SCORER_MAXRIVALS,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tAI1_DEEP_CERT_RIVALS);
\t\t\t\t\t\t\t\t\t\t\t\tfinal boolean chosenTrueAlive = simOutcome(dcx, dcy, djvx, djvy,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tplayerNum, AI1_DEEP_HORIZON, true, true, true, true,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tfalse, true, confirmCap, null, null, null) >= 0;
\t\t\t\t\t\t\t\t\t\t\t\tfinal boolean altTrueAlive = simOutcome(ax, ay, avx, avy, playerNum,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tAI1_DEEP_HORIZON, true, true, true, true, false, true,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tconfirmCap, null, null, null) >= 0;
\t\t\t\t\t\t\t\t\t\t\t\tfalseAliveTarget = chosenTrueAlive && !altTrueAlive;
\t\t\t\t\t\t\t\t\t\t\t} finally {
\t\t\t\t\t\t\t\t\t\t\t\ttrueConfirmDepth--;
\t\t\t\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t\t\t\tif (!falseAliveTarget && (game.crossesFinish(pos[0], pos[1], ax, ay)
\t\t\t\t\t\t\t\t\t\t\t\t|| simOutcome(ax, ay, avx, avy, playerNum, AI1_DEEP_HORIZON,
\t\t\t\t\t\t\t\t\t\t\t\t\t\ttrue, true, true, true) >= 0)) {
'''
assert source.count(old_veto) == 1
path.write_text(source.replace(old_veto, new_veto, 1))
