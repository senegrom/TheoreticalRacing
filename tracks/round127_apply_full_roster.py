#!/usr/bin/env python3
"""Give Round 127 one explicit all-rival faithful rollout mode.

The ordinary true-rival confirms intentionally model only nearby rivals.  A
large scorer cap does not bypass that radius: it merely permits more members
inside it.  Zandvoort seed 195 is a different class; the offline oracle proves
that the distant members of the compressed field are part of the round-10/11
failure.  Integer.MAX_VALUE is therefore reserved as a local sentinel meaning
"put every live rival in the unsuppressed scorer set".  No existing call uses
that value, so all prior confirmation semantics remain byte-for-byte intact.
"""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()

old_membership = '''\t\tif (scorerRivals) {
\t\t\t// Round 102: for TRUE-RIVAL confirms only, the membership radius
\t\t\t// scales with MY speed -- monza s80 commits at spd-inf 10 toward a
\t\t\t// braking car 11 cells downstream; a fixed Chebyshev-10 net can
\t\t\t// never contain the rivals a fast landing reaches within the
\t\t\t// horizon. Suppressed worlds keep the pinned radius (a global
\t\t\t// change slowed the round-96 coil finish frontier by four moves).
\t\t\tfinal int spdInf = Math.max(Math.abs(myVx), Math.abs(myVy));
\t\t\tfinal int scorerNear = trueRivals ? Math.max(AI1_SCORER_NEAR, 2 * spdInf)
\t\t\t\t\t: AI1_SCORER_NEAR;
\t\t\tfor (int k = 0; k < scorerCap; k++) {
'''
new_membership = '''\t\tif (scorerRivals) {
\t\t\t// Round 102: for TRUE-RIVAL confirms only, the membership radius
\t\t\t// scales with MY speed -- monza s80 commits at spd-inf 10 toward a
\t\t\t// braking car 11 cells downstream; a fixed Chebyshev-10 net can
\t\t\t// never contain the rivals a fast landing reaches within the
\t\t\t// horizon. Suppressed worlds keep the pinned radius (a global
\t\t\t// change slowed the round-96 coil finish frontier by four moves).
\t\t\t// Round 127 reserves Integer.MAX_VALUE for the single dense-corridor
\t\t\t// certificate that must reproduce the all-frontier oracle. Existing
\t\t\t// bounded confirms retain both their cap and their measured radius.
\t\t\tfinal boolean fullScorerRoster = trueRivals && scorerCap == Integer.MAX_VALUE;
\t\t\tfinal int effectiveScorerCap = fullScorerRoster
\t\t\t\t\t? game.players.length - 1 : scorerCap;
\t\t\tfinal int spdInf = Math.max(Math.abs(myVx), Math.abs(myVy));
\t\t\tfinal int scorerNear = fullScorerRoster ? Integer.MAX_VALUE
\t\t\t\t\t: trueRivals ? Math.max(AI1_SCORER_NEAR, 2 * spdInf)
\t\t\t\t\t: AI1_SCORER_NEAR;
\t\t\tfor (int k = 0; k < effectiveScorerCap; k++) {
'''
assert source.count(old_membership) == 1, source.count(old_membership)
source = source.replace(old_membership, new_membership, 1)

old_cap = '''\t\t\t\t\t\t\tfinal int confirmCap = Math.max(AI1_DEEP_CERT_RIVALS, liveRivals);'''
new_cap = '''\t\t\t\t\t\t\tfinal int confirmCap = Integer.MAX_VALUE;'''
assert source.count(old_cap) == 1, source.count(old_cap)
source = source.replace(old_cap, new_cap, 1)

assert source.count("fullScorerRoster") == 3
assert source.count("effectiveScorerCap") == 2
assert source.count("final int confirmCap = Integer.MAX_VALUE;") == 1
path.write_text(source)
print("materialized Round 127 all-rival faithful rollout sentinel")
