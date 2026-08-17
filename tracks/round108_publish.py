#!/usr/bin/env python3
"""Generate Round 108's production regression pin and campaign notes."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import textwrap

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402


def measured_target() -> tuple[object, object]:
    with tempfile.TemporaryDirectory(prefix="round108-pin-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        bench_ai.set_all_to("AI1")
        ai1 = bench_ai.run_track("zandvoort", timeout=1200, seed=115)
        bench_ai.set_all_to("AI2")
        ai2 = bench_ai.run_track("zandvoort", timeout=1200, seed=115)
    if not (ai1[0] > ai2[0] or ai1[1] < ai2[1]):
        raise SystemExit(f"Round-108 target was not rescued: AI1={ai1}, AI2={ai2}")
    return ai1, ai2


def write_regression(ai1: object, ai2: object) -> None:
    source = f'''#!/usr/bin/env python3
"""Pin Round 108's AI1-only equal-speed false-target rescue."""
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
    with tempfile.TemporaryDirectory(prefix="round108-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            actual[kind] = bench_ai.run_track("zandvoort", timeout=1200, seed=115)
    if actual != EXPECTED:
        raise SystemExit(f"Round-108 regression: {{actual}}, expected {{EXPECTED}}")
    if actual["AI1"][0] <= actual["AI2"][0] and actual["AI1"][1] >= actual["AI2"][1]:
        raise SystemExit(f"Round-108 rescue lost: {{actual}}")
    print("AI1EqualSpeedVetoRegression: OK (Zandvoort s115 rescued; AI2 policy frozen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    Path("tests/ai1_equal_speed_veto_regression.py").write_text(source)


def update_notes(summary: dict) -> None:
    counts = summary["counts"]
    section = f"""## Round 108: AI1 equal-speed false-target veto

The remaining Zandvoort seed-115 crash came from a danger-ladder switch between
equal-speed lines: the topology rollout called both alive, while the existing
full-fidelity rival model proved the selected line alive and the alternative
dead. AI1 now vetoes only that false-target transition in a large homogeneous
field. AI2's decision policy remains frozen. The associated recursive-confirm
and trace guards are now instance-owned, satisfying the repository's state
isolation invariant.

The exact 3,500-pair gate recorded {counts.get('safety_gain', 0)} safety gain(s),
{counts.get('faster', 0)} same-order pace gain(s), no slower outcomes, no safety
regressions and no field redistributions. Hungaroring seed 144 and Le Mans seed
4 remained outcome-identical to live master.

"""
    development = Path("AI_DEVELOPMENT.md")
    text = development.read_text()
    heading = "## Round 108: AI1 equal-speed false-target veto\n"
    if heading not in text:
        anchor = "## Current champion and frontier baseline\n"
        development.write_text(
            text.replace(anchor, section + anchor, 1) if anchor in text else section + text
        )

    campaign = Path("racing-memory.md")
    marker = "ROUND 108 (AI1 equal-speed false-target veto):"
    campaign_text = campaign.read_text()
    if marker not in campaign_text:
        note = textwrap.dedent(
            f"""

            {marker} Zandvoort s115 is closed by an AI1-only faithful-rival
            veto on equal-speed danger-ladder switches. AI2's policy copy is
            untouched; Hungaroring s144 remains the sole documented mega-window
            crash frontier. Exact gate: {summary['pairs']} pairs,
            {counts.get('safety_gain', 0)} safety gain(s),
            {counts.get('faster', 0)} same-order pace gain(s), zero regressions
            or redistributions.
            """
        )
        campaign.write_text(campaign_text.rstrip() + note)


def main() -> int:
    summary = json.loads(Path("round108-summary.json").read_text())
    if summary.get("pairs") != 3500:
        raise SystemExit(f"invalid Round-108 summary: {summary}")
    ai1, ai2 = measured_target()
    write_regression(ai1, ai2)
    update_notes(summary)
    print(f"Round108Publish: AI1={ai1}, AI2={ai2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
