#!/usr/bin/env python3
"""Materialize Round 127's bounded dense-corridor true-rival rescue.

Zandvoort seed 195 exposes a clean model boundary. At the last two avoidable
fast commitments, the existing eight-round suppressed-rival world keeps the
chosen line alive. The forensic oracle, which lets every car run the real
frontier, kills it in rounds ten or eleven while lower-energy alternatives
survive through round eighteen.

The candidate therefore pays for a twelve-round true-rival comparison only in
the measured structural class: AI1, all seven rivals still live and homogeneous,
a zero-trap speed-seven-plus landing, a sustained width-three funnel, and
exactly four rivals near the landing. It switches only after the chosen line is
proved dead, to a legal lower-energy survivor no more than one map turn slower.
AI2 and all existing sparse-funnel logic remain unchanged.
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


assert "AI1_DENSE_FAST_FUNNEL_ROUNDS" not in source
insert_after_line(
    "\tprivate final static int\t\tAI1_FUNNEL_DEEP_FIELD\t= 4;",
    "\tprivate final static int\t\tAI1_DENSE_FAST_FUNNEL_ROUNDS\t= 12;"
    "\t// round 127: bounded full-frontier dense-corridor proof\n",
    "dense funnel constant",
)

marker = (
    "\t\t\t\t\t\t}\n"
    "\t\t\t\t\t}\n"
    "\t\t\t\t\tif (!djSlow) {\n"
)
assert source.count(marker) == 1, source.count(marker)

dense = '''\t\t\t\t\t\t// Round 127 AI1 frontier: Zandvoort s195 is alive in every
\t\t\t\t\t\t// affordable suppressed-rival world but dies at faithful round
\t\t\t\t\t\t// ten or eleven once every nearby car keeps its real pace arms.
\t\t\t\t\t\t// Pay for that full-frontier model only in the measured rear-pack
\t\t\t\t\t\t// corridor class, then retain survival-only switching.
\t\t\t\t\t\tfinal int fNarrowRun = fSpdInf >= AI1_FUNNEL_MIN_SPD
\t\t\t\t\t\t\t\t? reach.narrowRunAhead(fCx, fCy, fSpan, AI1_FUNNEL_WIDTH) : 0;
\t\t\t\t\t\tfinal int fPackNear = countRivalsWithinCheb(fCx, fCy, playerNum,
\t\t\t\t\t\t\t\tAI1_DEEP_PACK_R);
\t\t\t\t\t\tfinal boolean fHomogeneous = kindHomogeneousRoster(playerNum);
\t\t\t\t\t\tfinal boolean fCrossesFinish = game.crossesFinish(pos[0], pos[1], fCx, fCy);
\t\t\t\t\t\tfinal boolean denseFastFunnel = !djSlow
\t\t\t\t\t\t\t\t&& moverKind(playerNum) == Player.Kind.AI1
\t\t\t\t\t\t\t\t&& liveRivals == game.players.length - 1
\t\t\t\t\t\t\t\t&& fHomogeneous
\t\t\t\t\t\t\t\t&& trapByDir[chosen.ordinal()] == 0.0
\t\t\t\t\t\t\t\t&& fSpdInf >= 7
\t\t\t\t\t\t\t\t&& fMinRing <= AI1_FUNNEL_WIDTH - 1
\t\t\t\t\t\t\t\t&& fNarrowRun >= AI1_FUNNEL_RUN
\t\t\t\t\t\t\t\t&& fPackNear == 4
\t\t\t\t\t\t\t\t&& !fCrossesFinish
\t\t\t\t\t\t\t\t&& trueConfirmDepth < AI1_TRUE_CONFIRM_MAXDEPTH;
\t\t\t\t\t\tif (AI_DEBUG_PLAYER == playerNum)
\t\t\t\t\t\t\tSystem.err.println("AIDBG DENSE-CHECK p=" + playerNum + " pos=("
\t\t\t\t\t\t\t\t\t+ pos[0] + "," + pos[1] + ") chosen=" + chosen
\t\t\t\t\t\t\t\t\t+ " slow=" + djSlow + " spdInf=" + fSpdInf
\t\t\t\t\t\t\t\t\t+ " minRing=" + fMinRing + " run=" + fNarrowRun
\t\t\t\t\t\t\t\t\t+ " pack=" + fPackNear + " live=" + liveRivals
\t\t\t\t\t\t\t\t\t+ " homogeneous=" + fHomogeneous
\t\t\t\t\t\t\t\t\t+ " armed=" + denseFastFunnel);
\t\t\t\t\t\tif (denseFastFunnel) {
\t\t\t\t\t\t\ttrueConfirmDepth++;
\t\t\t\t\t\t\ttry {
\t\t\t\t\t\t\t\tfinal int confirmCap = Math.max(AI1_DEEP_CERT_RIVALS, liveRivals);
\t\t\t\t\t\t\t\tfinal int chosenTrue = simOutcome(fCx, fCy, djvx, djvy, playerNum,
\t\t\t\t\t\t\t\t\t\tAI1_DENSE_FAST_FUNNEL_ROUNDS, true, true, true, true, true,
\t\t\t\t\t\t\t\t\t\ttrue, confirmCap, null, null, null);
\t\t\t\t\t\t\t\tif (AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum)
\t\t\t\t\t\t\t\t\tSystem.err.println("AIDBG DENSE-TRUE p=" + playerNum + " pos=("
\t\t\t\t\t\t\t\t\t\t\t+ pos[0] + "," + pos[1] + ") chosen=" + chosen
\t\t\t\t\t\t\t\t\t\t\t+ " verdict=" + chosenTrue + " cap=" + confirmCap);
\t\t\t\t\t\t\t\tif (chosenTrue < 0) {
\t\t\t\t\t\t\t\t\tfinal int chosenT = poTByDir[chosen.ordinal()];
\t\t\t\t\t\t\t\t\tfinal int chosenSpeed2 = speedSquared(djvx, djvy);
\t\t\t\t\t\t\t\t\tDirection survivor = null;
\t\t\t\t\t\t\t\t\tint survivorT = Integer.MAX_VALUE;
\t\t\t\t\t\t\t\t\tint survivorSpeed2 = Integer.MAX_VALUE;
\t\t\t\t\t\t\t\t\tfor (final Direction d : DIRECTIONS) {
\t\t\t\t\t\t\t\t\t\tif (d == chosen)
\t\t\t\t\t\t\t\t\t\t\tcontinue;
\t\t\t\t\t\t\t\t\t\tfinal int t = poTByDir[d.ordinal()];
\t\t\t\t\t\t\t\t\t\tif (t == Integer.MAX_VALUE || t > chosenT + 1)
\t\t\t\t\t\t\t\t\t\t\tcontinue;
\t\t\t\t\t\t\t\t\t\tfinal int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
\t\t\t\t\t\t\t\t\t\tfinal int speed2 = speedSquared(nvx, nvy);
\t\t\t\t\t\t\t\t\t\tif (speed2 >= chosenSpeed2 || RaceGame.aiVelocityOutOfRange(nvx, nvy))
\t\t\t\t\t\t\t\t\t\t\tcontinue;
\t\t\t\t\t\t\t\t\t\tfinal int nx = pos[0] + nvx, ny = pos[1] + nvy;
\t\t\t\t\t\t\t\t\t\tif (!game.crossesFinish(pos[0], pos[1], nx, ny)
\t\t\t\t\t\t\t\t\t\t\t\t&& (!game.isMoveLegalGeometryCached(pos[0], pos[1], nx, ny)
\t\t\t\t\t\t\t\t\t\t\t\t\t\t|| game.isCrashingPlayer(nx, ny, playerNum)
\t\t\t\t\t\t\t\t\t\t\t\t\t\t|| !reach.isAlive(nx, ny, nvx, nvy)))
\t\t\t\t\t\t\t\t\t\t\tcontinue;
\t\t\t\t\t\t\t\t\t\tfinal int candidateTrue = game.crossesFinish(pos[0], pos[1], nx, ny)
\t\t\t\t\t\t\t\t\t\t\t\t? 0 : simOutcome(nx, ny, nvx, nvy, playerNum,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tAI1_DENSE_FAST_FUNNEL_ROUNDS, true, true, true,
\t\t\t\t\t\t\t\t\t\t\t\t\t\ttrue, true, true, confirmCap, null, null, null);
\t\t\t\t\t\t\t\t\t\tif (AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum)
\t\t\t\t\t\t\t\t\t\t\tSystem.err.println("AIDBG DENSE-TRUE alt=" + d + " ttf=" + t
\t\t\t\t\t\t\t\t\t\t\t\t\t+ " spd2=" + speed2 + " verdict=" + candidateTrue);
\t\t\t\t\t\t\t\t\t\tif (candidateTrue >= 0 && (t < survivorT
\t\t\t\t\t\t\t\t\t\t\t\t|| t == survivorT && speed2 < survivorSpeed2)) {
\t\t\t\t\t\t\t\t\t\t\tsurvivor = d;
\t\t\t\t\t\t\t\t\t\t\tsurvivorT = t;
\t\t\t\t\t\t\t\t\t\t\tsurvivorSpeed2 = speed2;
\t\t\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t\t\tif (survivor != null) {
\t\t\t\t\t\t\t\t\t\tif (AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum)
\t\t\t\t\t\t\t\t\t\t\tSystem.err.println("AIDBG DENSE-TRUE SWITCH " + chosen + " -> "
\t\t\t\t\t\t\t\t\t\t\t\t\t+ survivor + " ttf " + chosenT + " -> " + survivorT);
\t\t\t\t\t\t\t\t\t\tchosen = survivor;
\t\t\t\t\t\t\t\t\t\tdeepHandled = true;
\t\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t} finally {
\t\t\t\t\t\t\t\ttrueConfirmDepth--;
\t\t\t\t\t\t\t}
\t\t\t\t\t\t}
'''
source = source.replace(marker, "\t\t\t\t\t\t}\n" + dense
                        + "\t\t\t\t\t}\n\t\t\t\t\tif (!djSlow) {\n", 1)

assert source.count("AI1_DENSE_FAST_FUNNEL_ROUNDS") == 4
assert source.count("AIDBG DENSE-TRUE p=") == 1
assert source.count("AIDBG DENSE-TRUE SWITCH") == 1
assert source.count("private Direction optimalMoveAI2") == 1
path.write_text(source)
print("materialized Round 127 dense true-rival corridor rescue")
