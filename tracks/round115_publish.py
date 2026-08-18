#!/usr/bin/env python3
"""Generate Round 115's permanent regression pin and campaign notes."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import textwrap

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402


def measure() -> dict[str, dict[int, tuple[int, int, list[int]]]]:
    measured: dict[str, dict[int, tuple[int, int, list[int]]]] = {"AI1": {}, "AI2": {}}
    with tempfile.TemporaryDirectory(prefix="round115-publish-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind, seeds in (("AI1", (1, 38, 106)), ("AI2", (1, 38, 106))):
            bench_ai.set_all_to(kind)
            for seed in seeds:
                result = bench_ai.run_track("coil", timeout=1200, seed=seed)
                if result is None:
                    raise SystemExit(f"Round 115 measurement failed: {kind} Coil seed {seed}")
                measured[kind][seed] = result
    return measured


def validate(measured: dict[str, dict[int, tuple[int, int, list[int]]]]) -> None:
    for seed in (1, 38):
        ai1 = measured["AI1"][seed]
        ai2 = measured["AI2"][seed]
        if ai1[0] != ai2[0] or ai1[1] != ai2[1]:
            raise SystemExit(f"Round 115 changed safety on Coil seed {seed}: {ai1}, {ai2}")
        if len(ai1[2]) != len(ai2[2]) or any(a > b for a, b in zip(ai1[2], ai2[2])):
            raise SystemExit(f"Round 115 is not individually non-worsening on Coil seed {seed}: {ai1}, {ai2}")
        if sum(ai1[2]) >= sum(ai2[2]):
            raise SystemExit(f"Round 115 lost its pace gain on Coil seed {seed}: {ai1}, {ai2}")
    if measured["AI1"][106] != measured["AI2"][106]:
        raise SystemExit(f"Round 115 coast control changed: {measured}")


def write_regression(measured: dict[str, dict[int, tuple[int, int, list[int]]]]) -> None:
    source = f'''#!/usr/bin/env python3
"""Pin Round 115's AI1-only low-energy field acceleration."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

EXPECTED = {measured!r}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {{"AI1": {{}}, "AI2": {{}}}}
    with tempfile.TemporaryDirectory(prefix="round115-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for seed in (1, 38, 106):
                actual[kind][seed] = bench_ai.run_track("coil", timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-115 regression: {{actual}}, expected {{EXPECTED}}")
    for seed in (1, 38):
        ai1, ai2 = actual["AI1"][seed], actual["AI2"][seed]
        if ai1[0:2] != ai2[0:2] or any(a > b for a, b in zip(ai1[2], ai2[2])):
            raise SystemExit(f"Round-115 Pareto contract lost on seed {{seed}}: {{ai1}}, {{ai2}}")
        if sum(ai1[2]) >= sum(ai2[2]):
            raise SystemExit(f"Round-115 pace gain lost on seed {{seed}}: {{ai1}}, {{ai2}}")
    if actual["AI1"][106] != actual["AI2"][106]:
        raise SystemExit(f"Round-115 coast control changed: {{actual}}")
    print("AI1GraduatedFieldAccelRegression: OK (Coil seeds 1/38 faster; seed 106 and AI2 frozen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    Path("tests/ai1_graduated_field_accel_regression.py").write_text(source)


def update_notes(summary: dict[str, object], measured: dict[str, dict[int, tuple[int, int, list[int]]]]) -> None:
    counts = summary["counts"]
    assert isinstance(counts, dict)
    section = f"""## Round 115: low-energy graduated field acceleration

Round 106 required a speed-squared gain of at least 16 before its eight-round
scorer-field certificate could recover a one-map-turn acceleration. Unfinished
Round 111-114 branches showed that lowering the floor to 9 exposes real pace,
but also found two distinct overreach classes: long-range Spa changes and a
high-energy Silverstone redistribution. The promoted frontier therefore keeps
the gain>=16 rule unchanged and admits gains 9..15 only for AI1, only through
TTF 45, only when the incumbent speed-squared is below 49, and never when the
scorer deliberately coasts. The existing trap, uncertainty, funnel, seal,
strict-self and strict-aggregate-field proofs remain mandatory. AI2 stays the
frozen Round-110 yardstick.

The exact {summary['pairs']}-pair differential recorded
{counts.get('pareto_faster', 0)} Pareto-faster race(s),
{counts.get('safety_gain', 0)} safety gain(s), and zero slower races, safety
regressions or field redistributions. Net finisher moves changed by
{summary['net_moves']}. Coil seed 1 improves from
{sum(measured['AI2'][1][2])} to {sum(measured['AI1'][1][2])} moves and Coil
seed 38 from {sum(measured['AI2'][38][2])} to
{sum(measured['AI1'][38][2])}, with the same finishers, order and no individual
slowdown. Coil seed 106 remains exact, as do the Spa and Silverstone
counterexample pins.

"""
    development = Path("AI_DEVELOPMENT.md")
    text = development.read_text()
    heading = "## Round 115: low-energy graduated field acceleration\n"
    if heading not in text:
        anchor = "## Highest-value next directions\n"
        development.write_text(text.replace(anchor, section + anchor, 1) if anchor in text else text + "\n" + section)

    campaign = Path("racing-memory.md")
    marker = "ROUND 115 (low-energy graduated field acceleration):"
    campaign_text = campaign.read_text()
    if marker not in campaign_text:
        note = textwrap.dedent(
            f"""

            {marker} The Round-106 field certificate now admits AI1-only
            speed2 gains 9..15 through TTF 45 when the incumbent speed2 is below
            49 and the scorer is not coasting. This retains the Coil seed-1 and
            seed-38 Pareto gains while excluding the long-range Spa and
            high-energy Silverstone counterexamples. Exact gate:
            {summary['pairs']} pairs, {counts.get('pareto_faster', 0)}
            Pareto-faster, {counts.get('safety_gain', 0)} safety gain(s), zero
            slower/safety-regression/redistribution outcomes, net
            {summary['net_moves']} finisher moves. AI2 remains frozen.
            """
        )
        campaign.write_text(campaign_text.rstrip() + note)


def main() -> int:
    summary = json.loads(Path("round115-full-summary.json").read_text())
    bad = sum(summary["counts"].get(key, 0) for key in ("slower", "safety_regression", "redistribution"))
    if summary.get("pairs") != 3500 or bad or summary["counts"].get("pareto_faster", 0) < 1:
        raise SystemExit(f"invalid Round-115 promotion summary: {summary}")
    measured = measure()
    validate(measured)
    write_regression(measured)
    update_notes(summary, measured)
    print(json.dumps(measured, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
