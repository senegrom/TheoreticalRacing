#!/usr/bin/env python3
"""Materialize Round 109's homogeneous-only ESC corridor confirmation.

The broad Round 105 experiment proved the ESC call can see the Hungaroring
seed-144 start-funnel doom, but applying it in heterogeneous fields perturbed a
mixed-safety pin. This candidate pays for the thread audit and true-rival
confirmation only while a large live roster is homogeneous with the mover.
AI2 remains the frozen control.
"""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()
boundary = source.index("\tprivate Direction optimalMoveAI2")
head, tail = source[:boundary], source[boundary:]

old = """\t\t\t\t\t\tchosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\ttrue, funnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS, true);
"""
new = """\t\t\t\t\t\t// Round 109: the ESC corridor confirmation is safe only as a
\t\t\t\t\t\t// homogeneous large-field certificate. The rejected broad arm
\t\t\t\t\t\t// changed a heterogeneous equilibrium; the Hungaroring-s144 target
\t\t\t\t\t\t// is an intact seven-rival same-policy start pack.
\t\t\t\t\t\tfinal boolean homogeneousEscConfirm = kindHomogeneousRoster(playerNum)
\t\t\t\t\t\t\t\t&& liveRivalsRemaining(playerNum) >= AI1_PRIVATE_FIELD_MIN_RIVALS;
\t\t\t\t\t\tchosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\ttrue, funnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS,
\t\t\t\t\t\t\t\ttrue, homogeneousEscConfirm, homogeneousEscConfirm,
\t\t\t\t\t\t\t\thomogeneousEscConfirm);
"""
assert head.count(old) == 1, head.count(old)
assert "homogeneousEscConfirm" not in source
head = head.replace(old, new, 1)
assert head.count("homogeneousEscConfirm") == 4
path.write_text(head + tail)
print("materialized homogeneous-only ESC true confirmation in AI1")
