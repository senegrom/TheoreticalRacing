#!/usr/bin/env python3
"""Materialize one track-independent Round 109 pace-certificate variant.

The sweep changes only admission gates around the existing strict eight-round
scorer/field proof.  It never changes the proof itself, AI2, or downstream
seal/danger vetoes.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

RACE = Path("src/tr/logic/RaceAi.java")

VARIANTS: dict[str, dict[str, object]] = {
    "field_equal": {"field_nonworse": True},
    "speed9": {"min_speed2_gain": 9},
    "speed4": {"min_speed2_gain": 4},
    "ahead1": {"min_ahead": 1},
    "ahead6": {"max_ahead": 6},
    "ttf120": {"max_ttf": 120},
    "finish41": {"finish_speed2_floor": 41},
    "unc25": {"max_unc": "AI1_STAGED_UNC_MAX"},
    "trap_l2": {"max_trap": "AI1_TRAP_L2"},
    "speed9_field_equal": {"min_speed2_gain": 9, "field_nonworse": True},
    "speed9_ahead6": {"min_speed2_gain": 9, "max_ahead": 6},
    "speed9_ttf120": {"min_speed2_gain": 9, "max_ttf": 120},
    "speed9_unc25": {"min_speed2_gain": 9, "max_unc": "AI1_STAGED_UNC_MAX"},
    "speed9_finish41": {"min_speed2_gain": 9, "finish_speed2_floor": 41},
    "broad_strict": {
        "min_speed2_gain": 9,
        "min_ahead": 1,
        "max_ahead": 6,
        "max_ttf": 120,
        "field_nonworse": True,
    },
}


def replace_int_constant(source: str, name: str, value: int) -> str:
    pattern = re.compile(
        rf"^(\s*private final static int\s+{re.escape(name)}\s*=\s*)\d+(;.*)$",
        re.MULTILINE,
    )
    source, count = pattern.subn(rf"\g<1>{value}\2", source, count=1)
    assert count == 1, (name, count)
    return source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("variant", choices=sorted(VARIANTS))
    args = parser.parse_args()
    config = VARIANTS[args.variant]

    source = RACE.read_text()
    assert source.count("private Direction guardedFieldPaceOverride(") == 1
    assert source.count("chosen = guardedFieldPaceOverride(") == 1

    if "min_speed2_gain" in config:
        source = replace_int_constant(
            source, "AI1_FIELD_ACCEL_MIN_SPEED2_GAIN", int(config["min_speed2_gain"])
        )
    if "min_ahead" in config:
        source = replace_int_constant(
            source, "AI1_FIELD_ACCEL_MIN_AHEAD", int(config["min_ahead"])
        )
    if "max_ahead" in config:
        source = replace_int_constant(
            source, "AI1_FIELD_ACCEL_MAX_AHEAD", int(config["max_ahead"])
        )
    if "max_ttf" in config:
        source = replace_int_constant(
            source, "AI1_FIELD_ACCEL_MAX_TTF", int(config["max_ttf"])
        )

    max_trap = config.get("max_trap")
    max_unc = config.get("max_unc")
    if max_trap is not None or max_unc is not None:
        old = (
            "\t\t\tif (d == chosen || d == Direction.NONE || turns == Integer.MAX_VALUE\n"
            "\t\t\t\t\t|| turns + 1 != chosenT || trapByDir[d.ordinal()] != 0.0\n"
            "\t\t\t\t\t|| uncByDir[d.ordinal()] != 0.0)\n"
        )
        trap_clause = (
            f"trapByDir[d.ordinal()] > {max_trap}"
            if max_trap is not None
            else "trapByDir[d.ordinal()] != 0.0"
        )
        unc_clause = (
            f"uncByDir[d.ordinal()] > {max_unc}"
            if max_unc is not None
            else "uncByDir[d.ordinal()] != 0.0"
        )
        new = (
            "\t\t\tif (d == chosen || d == Direction.NONE || turns == Integer.MAX_VALUE\n"
            f"\t\t\t\t\t|| turns + 1 != chosenT || {trap_clause}\n"
            f"\t\t\t\t\t|| {unc_clause})\n"
        )
        assert source.count(old) == 1, source.count(old)
        source = source.replace(old, new, 1)

    if "finish_speed2_floor" in config:
        old = (
            "\t\t\tif (turns <= AI1_FINISH_EXTENDED_TTF && speed2 < AI1_DJS_SPD2)\n"
        )
        new = (
            "\t\t\tif (turns <= AI1_FINISH_EXTENDED_TTF && speed2 < "
            f"{int(config['finish_speed2_floor'])})\n"
        )
        assert source.count(old) == 1, source.count(old)
        source = source.replace(old, new, 1)

    if config.get("field_nonworse"):
        old = (
            "\t\t\tif (candidateFinal < 0 || candidateFinal >= chosenFinal\n"
            "\t\t\t\t\t|| candidateField >= chosenField)\n"
        )
        new = (
            "\t\t\tif (candidateFinal < 0 || candidateFinal >= chosenFinal\n"
            "\t\t\t\t\t|| candidateField > chosenField)\n"
        )
        assert source.count(old) == 1, source.count(old)
        source = source.replace(old, new, 1)

    marker = (
        "\t// Round 109 sweep variant: " + args.variant + " "
        + json.dumps(config, sort_keys=True) + "\n"
    )
    anchor = "\t/** Round 106: recover a one-turn acceleration only in a bounded forward\n"
    assert source.count(anchor) == 1
    source = source.replace(anchor, marker + anchor, 1)

    RACE.write_text(source)
    print(json.dumps({"variant": args.variant, "config": config}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
