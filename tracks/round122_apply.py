#!/usr/bin/env python3
"""Materialize Round 122's trap-bearing per-rival Pareto acceleration.

Reuse Round 121's vector-capable rollout, but narrow its experimental override
to the unpromoted Round-109 trap-L2 class: candidate trap is positive and at
most L2, uncertainty is zero, speed-squared gain is at least 16, two to five
rivals are ahead, and TTF is at most 90. Chosen/candidate are compared for 12
rounds with every rival individually no worse, strict mover improvement and
strict aggregate-field improvement. The promoted zero-trap rule runs first;
AI2 remains frozen.
"""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("round121_apply.py")), run_name="__main__")

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()

replacements = (
    (
        "\tprivate final static int\t\tAI1_PARETO_VECTOR_MIN_SPEED2_GAIN\t= 4;\n",
        "\tprivate final static int\t\tAI1_PARETO_VECTOR_MIN_SPEED2_GAIN\t= 16;\n",
    ),
    (
        "\tprivate final static int\t\tAI1_PARETO_VECTOR_MIN_AHEAD\t= 1;\n",
        "\tprivate final static int\t\tAI1_PARETO_VECTOR_MIN_AHEAD\t= 2;\n",
    ),
    (
        "\tprivate final static int\t\tAI1_PARETO_VECTOR_MAX_AHEAD\t= 7;\n",
        "\tprivate final static int\t\tAI1_PARETO_VECTOR_MAX_AHEAD\t= 5;\n",
    ),
)
for old, new in replacements:
    assert source.count(old) == 1, (old, source.count(old))
    source = source.replace(old, new, 1)

start = source.index("\tprivate Direction paretoVectorFieldPaceOverride(")
end = source.index("\n\t/** Round 117 candidate-formation proof:", start)
method = source[start:end]
old = (
    "\t\t\tif (d == chosen || d == Direction.NONE || turns == Integer.MAX_VALUE\n"
    "\t\t\t\t\t|| turns + 1 != chosenT || trapByDir[d.ordinal()] != 0.0\n"
    "\t\t\t\t\t|| uncByDir[d.ordinal()] != 0.0)\n"
)
new = (
    "\t\t\tif (d == chosen || d == Direction.NONE || turns == Integer.MAX_VALUE\n"
    "\t\t\t\t\t|| turns + 1 != chosenT || trapByDir[d.ordinal()] <= 0.0\n"
    "\t\t\t\t\t|| trapByDir[d.ordinal()] > AI1_TRAP_L2\n"
    "\t\t\t\t\t|| uncByDir[d.ordinal()] != 0.0)\n"
)
assert method.count(old) == 1, method.count(old)
method = method.replace(old, new, 1)
method = method.replace(
    "\t/** Round 121 experiment: broaden one-turn acceleration only when a longer\n",
    "\t/** Round 122 experiment: admit positive-trap L1/L2 acceleration only when a longer\n",
    1,
)
source = source[:start] + method + source[end:]

assert source.count("trapByDir[d.ordinal()] <= 0.0") == 1
assert source.count("trapByDir[d.ordinal()] > AI1_TRAP_L2") == 1
assert source.count("AIDBG PARETO-VECTOR") == 1
path.write_text(source)
print("materialized Round 122 trap-L2 per-rival Pareto acceleration")
