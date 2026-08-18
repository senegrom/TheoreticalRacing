#!/usr/bin/env python3
"""Materialize Round 127's dense fast-funnel twelve-round certificate.

Zandvoort seed 195 exposes a clean threshold discontinuity.  At move 70 the
static sustained-funnel signal fires, but the established eight-round proof
ends alive.  One mover turn later the landing crosses the speed-7 threshold;
the chosen acceleration then dies at faithful round 11 while several braking
alternatives survive through round 18, yet the existing fast-funnel arm is
restricted to sparse fields because its eight-round model false-killed dense
Le Mans traffic.

This experiment leaves the sparse arm unchanged.  AI1 alone may run a deeper
12-round scorer-field certificate in a large homogeneous field only when the
landing is fast, packed, and enters a sustained width-three-or-narrower funnel.
A switch is accepted only to a lower-energy candidate no more than one map turn
slower.  AI2 remains the frozen control.
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
    "\t// round 127: dense fast-funnel chosen/target certificate\n",
    "dense funnel constant",
)

marker = (
    "\t\t\t\t\t\t}\n"
    "\t\t\t\t\t}\n"
    "\t\t\t\t\tif (!djSlow) {\n"
)
assert source.count(marker) == 1, source.count(marker)

dense = '''\t\t\t\t\t\t// Round 127 AI1 frontier: the sparse fast-funnel arm stops at
\t\t\t\t\t\t// four live rivals because its eight-round proxy false-killed
\t\t\t\t\t\t// dense Le Mans traffic. Zandvoort s195 is the complementary
\t\t\t\t\t\t// class: seven live homogeneous rivals, a width-three sustained
\t\t\t\t\t\t// funnel, and a speed-7+ choice that dies only at round 11 while
\t\t\t\t\t\t// lower-energy map-near alternatives survive. Pay for a direct
\t\t\t\t\t\t// 12-round scorer-field certificate only on that narrow geometry;
\t\t\t\t\t\t// accept only a braking target within one map turn.
\t\t\t\t\t\tfinal int fNarrowRun = fSpdInf >= AI1_FUNNEL_MIN_SPD
\t\t\t\t\t\t\t\t? reach.narrowRunAhead(fCx, fCy, fSpan, AI1_FUNNEL_WIDTH) : 0;
\t\t\t\t\t\tfinal int fPackNear = countRivalsWithinCheb(fCx, fCy, playerNum,
\t\t\t\t\t\t\t\tAI1_DEEP_PACK_R);
\t\t\t\t\t\tfinal boolean fHomogeneous = kindHomogeneousRoster(playerNum);
\t\t\t\t\t\tfinal boolean fCrossesFinish = game.crossesFinish(pos[0], pos[1], fCx, fCy);
\t\t\t\t\t\tif (AI_DEBUG_PLAYER == playerNum)
\t\t\t\t\t\t\tSystem.err.println("AIDBG DENSE-CHECK p=" + playerNum + " pos=("
\t\t\t\t\t\t\t\t\t+ pos[0] + "," + pos[1] + ") chosen=" + chosen
\t\t\t\t\t\t\t\t\t+ " slow=" + djSlow + " spdInf=" + fSpdInf
\t\t\t\t\t\t\t\t\t+ " minRing=" + fMinRing + " run=" + fNarrowRun
\t\t\t\t\t\t\t\t\t+ " pack=" + fPackNear + " live=" + liveRivals
\t\t\t\t\t\t\t\t\t+ " homogeneous=" + fHomogeneous
\t\t\t\t\t\t\t\t\t+ " finish=" + fCrossesFinish);
\t\t\t\t\t\tfinal boolean denseFastFunnel = !djSlow
\t\t\t\t\t\t\t\t&& moverKind(playerNum) == Player.Kind.AI1
\t\t\t\t\t\t\t\t&& liveRivals >= AI1_PRIVATE_FIELD_MIN_RIVALS
\t\t\t\t\t\t\t\t&& fHomogeneous
\t\t\t\t\t\t\t\t&& fMinRing <= AI1_FUNNEL_WIDTH - 1
\t\t\t\t\t\t\t\t&& fSpdInf > fMinRing && fNarrowRun >= AI1_FUNNEL_RUN
\t\t\t\t\t\t\t\t&& fPackNear >= AI1_DEEP_PACK
\t\t\t\t\t\t\t\t&& !fCrossesFinish;
\t\t\t\t\t\tif (denseFastFunnel) {
\t\t\t\t\t\t\tif (AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum)
\t\t\t\t\t\t\t\tSystem.err.println("AIDBG DENSE-FUNNEL p=" + playerNum + " pos=("
\t\t\t\t\t\t\t\t\t\t+ pos[0] + "," + pos[1] + ") chosen=" + chosen
\t\t\t\t\t\t\t\t\t\t+ " minRing=" + fMinRing + " run=" + fNarrowRun
\t\t\t\t\t\t\t\t\t\t+ " rivals=" + liveRivals + " -> scorer12");
\t\t\t\t\t\t\tfinal Direction denseChoice = dangerJointSearch(pos, vel, playerNum,
\t\t\t\t\t\t\t\t\tchosen, true, true, true, true,
\t\t\t\t\t\t\t\t\tAI1_DENSE_FAST_FUNNEL_ROUNDS, AI1_DEEP_CERT_RIVALS, true);
\t\t\t\t\t\t\tif (denseChoice != chosen) {
\t\t\t\t\t\t\t\tfinal int denseVx = vel[0] + denseChoice.dx;
\t\t\t\t\t\t\t\tfinal int denseVy = vel[1] + denseChoice.dy;
\t\t\t\t\t\t\t\tfinal int denseT = poTByDir[denseChoice.ordinal()];
\t\t\t\t\t\t\t\tfinal int chosenT = poTByDir[chosen.ordinal()];
\t\t\t\t\t\t\t\tif (denseT <= chosenT + 1
\t\t\t\t\t\t\t\t\t\t&& speedSquared(denseVx, denseVy) < speedSquared(djvx, djvy)) {
\t\t\t\t\t\t\t\t\tif (AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum)
\t\t\t\t\t\t\t\t\t\tSystem.err.println("AIDBG DENSE-FUNNEL SWITCH " + chosen + " -> "
\t\t\t\t\t\t\t\t\t\t\t\t+ denseChoice + " ttf " + chosenT + " -> " + denseT);
\t\t\t\t\t\t\t\t\tchosen = denseChoice;
\t\t\t\t\t\t\t\t\tdeepHandled = true;
\t\t\t\t\t\t\t\t} else if (AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum) {
\t\t\t\t\t\t\t\t\tSystem.err.println("AIDBG DENSE-FUNNEL reject target " + denseChoice
\t\t\t\t\t\t\t\t\t\t\t+ " ttf=" + denseT + " spd2="
\t\t\t\t\t\t\t\t\t\t\t+ speedSquared(denseVx, denseVy));
\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t}
\t\t\t\t\t\t}
'''
source = source.replace(marker, "\t\t\t\t\t\t}\n" + dense
                        + "\t\t\t\t\t}\n\t\t\t\t\tif (!djSlow) {\n", 1)

assert source.count("AI1_DENSE_FAST_FUNNEL_ROUNDS") == 2
assert source.count("AIDBG DENSE-CHECK p=") == 1
assert source.count("AIDBG DENSE-FUNNEL p=") == 1
assert source.count("private Direction optimalMoveAI2") == 1
path.write_text(source)
print("materialized Round 127 dense fast-funnel certificate")
