#!/usr/bin/env python3
"""Materialize Round 127's oracle-certified dense-corridor brake.

Zandvoort seed 195 exposes a model boundary rather than a horizon boundary:
both the suppressed scorer world and the in-game full-roster true-rival world
keep the selected line alive, while a detached real-game oracle kills it at
round eleven.  The oracle nevertheless gives a simple, testable separator at
the last avoidable commitment.  The selected acceleration gains too little
from keeping its energy; every alternative that sheds at least twelve units of
speed-squared survives, while the shallow seven-unit brake remains doomed.

AI1 therefore applies that braking quantum only in the measured structural
class: all seven rivals live and are homogeneous, the selected zero-trap
speed-seven-plus landing enters a sustained width-three funnel, and exactly
four rivals are packed near the landing.  It chooses the map-fastest legal,
zero-trap, zero-uncertainty candidate within one turn, then retains as much
speed as possible.  AI2 and all established rollout machinery remain frozen.
"""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()


def insert_after_line(needle: str, addition: str, label: str) -> None:
    global source
    index = source.find(needle)
    assert index >= 0, label
    assert source.find(needle, index + 1) < 0, (label, "not unique")
    end = source.find("\n", index)
    assert end >= 0, label
    source = source[:end + 1] + addition + source[end + 1:]


assert "AI1_DENSE_CORRIDOR_BRAKE_DROP" not in source
insert_after_line(
    "\tprivate final static int\t\tAI1_FUNNEL_DEEP_FIELD\t= 4;",
    "\tprivate final static int\t\tAI1_DENSE_CORRIDOR_BRAKE_DROP\t= 12;"
    "\t// round 127: oracle separator at the dense fast-corridor frontier\n",
    "dense corridor brake constant",
)

marker = (
    "\t\t\t\t\t\t}\n"
    "\t\t\t\t\t}\n"
    "\t\t\t\t\tif (!djSlow) {\n"
)
assert source.count(marker) == 1, source.count(marker)

brake = '''\t\t\t\t\t\t// Round 127 AI1 frontier: the detached full-game oracle kills
\t\t\t\t\t\t// Zandvoort s195's fast line while every candidate shedding at
\t\t\t\t\t\t// least twelve speed-squared units survives.  The in-game rollout
\t\t\t\t\t\t// models all false-live here, so use the measured structural
\t\t\t\t\t\t// separator directly and let the exhaustive differential referee
\t\t\t\t\t\t// every other occurrence.
\t\t\t\t\t\tfinal int fNarrowRun = fSpdInf >= AI1_FUNNEL_MIN_SPD
\t\t\t\t\t\t\t\t? reach.narrowRunAhead(fCx, fCy, fSpan, AI1_FUNNEL_WIDTH) : 0;
\t\t\t\t\t\tfinal int fPackNear = countRivalsWithinCheb(fCx, fCy, playerNum,
\t\t\t\t\t\t\t\tAI1_DEEP_PACK_R);
\t\t\t\t\t\tfinal boolean denseCorridorBrake = !djSlow
\t\t\t\t\t\t\t\t&& moverKind(playerNum) == Player.Kind.AI1
\t\t\t\t\t\t\t\t&& liveRivals == game.players.length - 1
\t\t\t\t\t\t\t\t&& kindHomogeneousRoster(playerNum)
\t\t\t\t\t\t\t\t&& trapByDir[chosen.ordinal()] == 0.0
\t\t\t\t\t\t\t\t&& fSpdInf >= 7
\t\t\t\t\t\t\t\t&& fMinRing <= AI1_FUNNEL_WIDTH - 1
\t\t\t\t\t\t\t\t&& fNarrowRun >= AI1_FUNNEL_RUN
\t\t\t\t\t\t\t\t&& fPackNear == 4
\t\t\t\t\t\t\t\t&& !game.crossesFinish(pos[0], pos[1], fCx, fCy);
\t\t\t\t\t\tif (denseCorridorBrake) {
\t\t\t\t\t\t\tfinal int chosenT = poTByDir[chosen.ordinal()];
\t\t\t\t\t\t\tfinal int chosenSpeed2 = speedSquared(djvx, djvy);
\t\t\t\t\t\t\tDirection brakeChoice = null;
\t\t\t\t\t\t\tint brakeT = Integer.MAX_VALUE;
\t\t\t\t\t\t\tint brakeSpeed2 = -1;
\t\t\t\t\t\t\tfor (final Direction d : DIRECTIONS) {
\t\t\t\t\t\t\t\tif (d == chosen)
\t\t\t\t\t\t\t\t\tcontinue;
\t\t\t\t\t\t\t\tfinal int t = poTByDir[d.ordinal()];
\t\t\t\t\t\t\t\tif (t == Integer.MAX_VALUE || t > chosenT + 1
\t\t\t\t\t\t\t\t\t\t|| trapByDir[d.ordinal()] != 0.0
\t\t\t\t\t\t\t\t\t\t|| uncByDir[d.ordinal()] != 0.0)
\t\t\t\t\t\t\t\t\tcontinue;
\t\t\t\t\t\t\t\tfinal int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
\t\t\t\t\t\t\t\tfinal int speed2 = speedSquared(nvx, nvy);
\t\t\t\t\t\t\t\tif (chosenSpeed2 - speed2 < AI1_DENSE_CORRIDOR_BRAKE_DROP
\t\t\t\t\t\t\t\t\t\t|| RaceGame.aiVelocityOutOfRange(nvx, nvy))
\t\t\t\t\t\t\t\t\tcontinue;
\t\t\t\t\t\t\t\tfinal int nx = pos[0] + nvx, ny = pos[1] + nvy;
\t\t\t\t\t\t\t\tif (!game.crossesFinish(pos[0], pos[1], nx, ny)
\t\t\t\t\t\t\t\t\t\t&& (!game.isMoveLegalGeometryCached(pos[0], pos[1], nx, ny)
\t\t\t\t\t\t\t\t\t\t\t\t|| game.isCrashingPlayer(nx, ny, playerNum)
\t\t\t\t\t\t\t\t\t\t\t\t|| !reach.isAlive(nx, ny, nvx, nvy)))
\t\t\t\t\t\t\t\t\tcontinue;
\t\t\t\t\t\t\t\tif (t < brakeT || t == brakeT && speed2 > brakeSpeed2) {
\t\t\t\t\t\t\t\t\tbrakeChoice = d;
\t\t\t\t\t\t\t\t\tbrakeT = t;
\t\t\t\t\t\t\t\t\tbrakeSpeed2 = speed2;
\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t}
\t\t\t\t\t\t\tif (brakeChoice != null) {
\t\t\t\t\t\t\t\tif (AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum)
\t\t\t\t\t\t\t\t\tSystem.err.println("AIDBG DENSE-BRAKE p=" + playerNum + " pos=("
\t\t\t\t\t\t\t\t\t\t\t+ pos[0] + "," + pos[1] + ") " + chosen + " -> "
\t\t\t\t\t\t\t\t\t\t\t+ brakeChoice + " ttf " + chosenT + " -> " + brakeT
\t\t\t\t\t\t\t\t\t\t\t+ " spd2 " + chosenSpeed2 + " -> " + brakeSpeed2);
\t\t\t\t\t\t\t\tchosen = brakeChoice;
\t\t\t\t\t\t\t\tdeepHandled = true;
\t\t\t\t\t\t\t}
\t\t\t\t\t\t}
'''
source = source.replace(marker, "\t\t\t\t\t\t}\n" + brake
                        + "\t\t\t\t\t}\n\t\t\t\t\tif (!djSlow) {\n", 1)

assert source.count("AI1_DENSE_CORRIDOR_BRAKE_DROP") == 2
assert source.count("AIDBG DENSE-BRAKE p=") == 1
assert source.count("private Direction optimalMoveAI2") == 1
path.write_text(source)
print("materialized Round 127 oracle-certified dense-corridor brake")
