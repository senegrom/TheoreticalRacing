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

dense = r'''						// Round 127 AI1 frontier: the sparse fast-funnel arm stops at
						// four live rivals because its eight-round proxy false-killed
						// dense Le Mans traffic. Zandvoort s195 is the complementary
						// class: seven live homogeneous rivals, a width-three sustained
						// funnel, and a speed-7+ choice that dies only at round 11 while
						// lower-energy map-near alternatives survive. Pay for a direct
						// 12-round scorer-field certificate only on that narrow geometry;
						// accept only a braking target within one map turn.
						final int fNarrowRun = fSpdInf >= AI1_FUNNEL_MIN_SPD
								? reach.narrowRunAhead(fCx, fCy, fSpan, AI1_FUNNEL_WIDTH) : 0;
						final boolean denseFastFunnel = !djSlow
								&& moverKind(playerNum) == Player.Kind.AI1
								&& liveRivals >= AI1_PRIVATE_FIELD_MIN_RIVALS
								&& kindHomogeneousRoster(playerNum)
								&& fMinRing <= AI1_FUNNEL_WIDTH - 1
								&& fSpdInf > fMinRing && fNarrowRun >= AI1_FUNNEL_RUN
								&& countRivalsWithinCheb(fCx, fCy, playerNum,
										AI1_DEEP_PACK_R) >= AI1_DEEP_PACK
								&& !game.crossesFinish(pos[0], pos[1], fCx, fCy);
						if (denseFastFunnel) {
							if (AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum)
								System.err.println("AIDBG DENSE-FUNNEL p=" + playerNum + " pos=("
										+ pos[0] + "," + pos[1] + ") chosen=" + chosen
										+ " minRing=" + fMinRing + " run=" + fNarrowRun
										+ " rivals=" + liveRivals + " -> scorer12");
							final Direction denseChoice = dangerJointSearch(pos, vel, playerNum,
									chosen, true, true, true, true,
									AI1_DENSE_FAST_FUNNEL_ROUNDS, AI1_DEEP_CERT_RIVALS, true);
							if (denseChoice != chosen) {
								final int denseVx = vel[0] + denseChoice.dx;
								final int denseVy = vel[1] + denseChoice.dy;
								final int denseT = poTByDir[denseChoice.ordinal()];
								final int chosenT = poTByDir[chosen.ordinal()];
								if (denseT <= chosenT + 1
										&& speedSquared(denseVx, denseVy) < speedSquared(djvx, djvy)) {
									if (AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum)
										System.err.println("AIDBG DENSE-FUNNEL SWITCH " + chosen + " -> "
												+ denseChoice + " ttf " + chosenT + " -> " + denseT);
									chosen = denseChoice;
									deepHandled = true;
								} else if (AI_DEBUG_DJS || AI_DEBUG_PLAYER == playerNum) {
									System.err.println("AIDBG DENSE-FUNNEL reject target " + denseChoice
											+ " ttf=" + denseT + " spd2="
											+ speedSquared(denseVx, denseVy));
								}
						}
'''
source = source.replace(marker, "\t\t\t\t\t\t}\n" + dense
                        + "\t\t\t\t\t}\n\t\t\t\t\tif (!djSlow) {\n", 1)

assert source.count("AI1_DENSE_FAST_FUNNEL_ROUNDS") == 2
assert source.count("AIDBG DENSE-FUNNEL p=") == 1
assert source.count("private Direction optimalMoveAI2") == 1
path.write_text(source)
print("materialized Round 127 dense fast-funnel certificate")
