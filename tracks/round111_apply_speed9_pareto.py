#!/usr/bin/env python3
"""Materialize the narrowed Round 111 speed-nine Pareto candidate.

Start from the per-rival proof experiment, then close the Spa seed-11
counterexample exactly at its general mechanism boundaries:

* the projected aggregate field must improve strictly, not merely tie;
* the forward pack remains bounded to the promoted two-to-five-ahead class;
* the proven 90-turn race phase is retained; and
* only the speed-squared admission threshold is relaxed, 16 -> 9.

The per-rival no-worse proof remains as an extra guard. AI2 and all downstream
seal/danger checks remain unchanged.
"""
from pathlib import Path
import runpy

runpy.run_path("tracks/round110_apply_pareto_field.py", run_name="__main__")

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()

replacements = (
    (
        "\tprivate final static int\t\tAI1_PARETO_FIELD_MIN_AHEAD\t= 1;\n",
        "\tprivate final static int\t\tAI1_PARETO_FIELD_MIN_AHEAD\t= 2;\n",
    ),
    (
        "\tprivate final static int\t\tAI1_PARETO_FIELD_MAX_AHEAD\t= 6;\n",
        "\tprivate final static int\t\tAI1_PARETO_FIELD_MAX_AHEAD\t= 5;\n",
    ),
    (
        "\tprivate final static int\t\tAI1_PARETO_FIELD_MAX_TTF\t= 120;\n",
        "\tprivate final static int\t\tAI1_PARETO_FIELD_MAX_TTF\t= 90;\n",
    ),
    (
        "\t\t\tif (candidateFinal < 0 || candidateFinal >= chosenFinal\n"
        "\t\t\t\t\t|| candidateVector[0] > chosenVector[0]\n",
        "\t\t\tif (candidateFinal < 0 || candidateFinal >= chosenFinal\n"
        "\t\t\t\t\t|| candidateVector[0] >= chosenVector[0]\n",
    ),
    (
        "\t/** Round 110 experiment: broaden the decisive-acceleration class only when\n",
        "\t/** Round 111: extend the decisive-acceleration class from speed2 gain 16\n"
        "\t * down to 9, while retaining strict aggregate progress and adding a\n"
        "\t * per-rival no-worse certificate.\n"
        "\t * Round 110 experiment: broaden the decisive-acceleration class only when\n",
    ),
)
for old, new in replacements:
    assert source.count(old) == 1, (old, source.count(old))
    source = source.replace(old, new, 1)

assert "AI1_PARETO_FIELD_MIN_SPEED2_GAIN\t= 9" in source
assert "AI1_PARETO_FIELD_MIN_AHEAD\t= 2" in source
assert "AI1_PARETO_FIELD_MAX_AHEAD\t= 5" in source
assert "AI1_PARETO_FIELD_MAX_TTF\t= 90" in source
path.write_text(source)
print("materialized narrowed Round 111 speed-nine Pareto candidate")
