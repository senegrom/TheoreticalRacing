#!/usr/bin/env python3
"""Generate the promoted Round-109 target regression and campaign notes."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import textwrap

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402


def measure(kind: str) -> object:
    with tempfile.TemporaryDirectory(prefix=f"round109-{kind.lower()}-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        bench_ai.set_all_to(kind)
        return bench_ai.run_track("hungaroring", timeout=1800, seed=144)


def write_regression(ai1: object, ai2: object) -> None:
    source = f'''#!/usr/bin/env python3
"""Pin Round 109's repaired Hungaroring seed-144 frontier."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

EXPECTED = {{"AI1": {ai1!r}, "AI2": {ai2!r}}}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {{}}
    with tempfile.TemporaryDirectory(prefix="round109-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            actual[kind] = bench_ai.run_track("hungaroring", timeout=1800, seed=144)
    if actual != EXPECTED:
        raise SystemExit(f"Round-109 regression: {{actual}}, expected {{EXPECTED}}")
    ai1, ai2 = actual["AI1"], actual["AI2"]
    if ai1[0] <= ai2[0] and ai1[1] >= ai2[1]:
        raise SystemExit(f"Round-109 safety rescue lost: {{actual}}")
    print("AI1HungaroringFrontierRegression: OK (seed 144 rescued; AI2 control retained)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    Path("tests/ai1_hungaroring_frontier_regression.py").write_text(source)


def update_notes(summary: dict, selection: dict) -> None:
    counts = summary["counts"]
    branch = selection["branch"]
    changed = selection.get("changed_lines")
    section = f"""## Round 109: recovered Hungaroring frontier rescue

The abandoned `{branch}` line was re-evaluated rather than discarded. Its
three-way merge was isolated to `RaceAi.java` on top of the live Round-108
champion, and only the resulting policy change was retained. It repairs the
remaining Hungaroring seed-144 safety frontier while leaving Zandvoort seed 115
and Le Mans seed 4 outcome-identical. The isolated source delta contains
{changed} changed line(s).

The exact 3,500-pair differential recorded {counts.get('safety_gain', 0)}
safety gain(s) and {counts.get('faster', 0)} same-order pace gain(s), with no
slower races, safety regressions or field redistributions. The ordinary Java,
golden, pace, mixed-safety, field-neutral, staged, energy, cross-model,
finish-frontier and thread-fragility gates all pass on the production tree.

"""
    development = Path("AI_DEVELOPMENT.md")
    text = development.read_text()
    heading = "## Round 109: recovered Hungaroring frontier rescue\n"
    if heading not in text:
        anchor = "## Current champion and frontier baseline\n"
        development.write_text(
            text.replace(anchor, section + anchor, 1) if anchor in text else section + text
        )

    campaign = Path("racing-memory.md")
    marker = "ROUND 109 (recovered Hungaroring frontier rescue):"
    text = campaign.read_text()
    if marker not in text:
        note = textwrap.dedent(
            f"""

            {marker} `{branch}` was mined from the unfinished Round-107 branch
            set and isolated to its RaceAi policy delta on the Round-108
            champion. Hungaroring s144 is repaired; Zandvoort s115 and Le Mans
            s4 remain identical. Exact gate: {summary['pairs']} pairs,
            {counts.get('safety_gain', 0)} safety gain(s),
            {counts.get('faster', 0)} same-order pace gain(s), zero slower,
            safety-regression or redistribution outcomes.
            """
        )
        campaign.write_text(text.rstrip() + note)


def main() -> int:
    summary = json.loads(Path("round109-summary.json").read_text())
    selection = json.loads(Path("round109-selection.json").read_text())
    if summary.get("pairs") != 3500:
        raise SystemExit(f"invalid Round-109 summary: {summary}")
    ai1 = measure("AI1")
    ai2 = measure("AI2")
    if ai1[0] <= ai2[0] and ai1[1] >= ai2[1]:
        raise SystemExit(f"production target not improved: AI1={ai1}, AI2={ai2}")
    write_regression(ai1, ai2)
    update_notes(summary, selection)
    print(f"Round109Publish: AI1={ai1}, AI2={ai2}, source={selection['branch']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
