#!/usr/bin/env python3
"""Enable the rejected broad ESC-call corridor confirm in AI1 only.

This is diagnostic, not a promotion candidate. It proves that the corridor
confirm catches Hungaroring seed 144 and exposes the exact heterogeneous-field
counterexample that made the Round 105 experiment too broad.
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
new = """\t\t\t\t\t\t// Round 109 diagnostic: turn on thread audit, true confirmation and
\t\t\t\t\t\t// the corridor leg at the ESC call. This intentionally recreates
\t\t\t\t\t\t// the rejected Round 105 experiment so its mixed-field boundary can
\t\t\t\t\t\t// be measured rather than guessed.
\t\t\t\t\t\tchosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\ttrue, funnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS,
\t\t\t\t\t\t\t\ttrue, true, true);
"""
assert head.count(old) == 1, head.count(old)
assert "Round 109 diagnostic" not in source
head = head.replace(old, new, 1)
assert head.count("Round 109 diagnostic") == 1
path.write_text(head + tail)
print("materialized AI1 broad ESC corridor confirm diagnostic")
