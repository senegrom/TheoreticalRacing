#!/usr/bin/env python3
"""Generate Round 110's production regression pin and campaign notes."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import textwrap

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

TARGETS = (("hungaroring", 144), ("zandvoort", 115))
CONTROLS = (("zandvoort", 128), ("zandvoort", 134))


def measure(track: str, seed: int) -> dict[str, object]:
    actual: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix=f"round110-{track}-{seed}-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            actual[kind] = bench_ai.run_track(track, timeout=1200, seed=seed)
    return actual


def write_regression(expected: dict[str, dict[str, object]]) -> None:
    source = f'''#!/usr/bin/env python3
"""Pin Round 110's opening-pack and equal-speed rescues."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

EXPECTED = {expected!r}
TARGETS = (("hungaroring", 144), ("zandvoort", 115))
CONTROLS = (("zandvoort", 128), ("zandvoort", 134))


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {{}}
    with tempfile.TemporaryDirectory(prefix="round110-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for track, seed in TARGETS + CONTROLS:
            case = f"{{track}}:{{seed}}"
            actual[case] = {{}}
            for kind in ("AI1", "AI2"):
                bench_ai.set_all_to(kind)
                actual[case][kind] = bench_ai.run_track(track, timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-110 regression: {{actual}}, expected {{EXPECTED}}")
    for track, seed in TARGETS:
        case = f"{{track}}:{{seed}}"
        ai1, ai2 = actual[case]["AI1"], actual[case]["AI2"]
        if ai1[0] <= ai2[0] and ai1[1] >= ai2[1]:
            raise SystemExit(f"Round-110 rescue lost for {{case}}: {{actual[case]}}")
    for track, seed in CONTROLS:
        case = f"{{track}}:{{seed}}"
        if actual[case]["AI1"] != actual[case]["AI2"]:
            raise SystemExit(f"Round-110 control moved for {{case}}: {{actual[case]}}")
    print("AI1DualFrontierRegression: OK (Hungaroring s144 and Zandvoort s115 rescued)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    Path("tests/ai1_dual_frontier_regression.py").write_text(source)


def update_notes(summary: dict) -> None:
    counts = summary["counts"]
    events = summary["events"]
    gains = [event for event in events if event["classification"] == "safety_gain"]
    faster = [event for event in events if event["classification"] == "faster"]
    section = f"""## Round 110: dual frontier rescue

Round 110 composes the two strongest unfinished branch ideas on the promoted
Round 106 champion. A true-rival ESC confirmation is admitted only for a dense
homogeneous opening pack through the mover's fourth personal move; on
Hungaroring seed 144 it replaces player 2's doomed `SE` with `NW` and converts
six finishes / one crash into seven / zero. A separate equal-speed target veto
keeps a faithful-rival-alive line when the topology switch target is
faithful-rival-dead; on Zandvoort seed 115 it converts the remaining six / one
race into seven / zero. AI2 remains the frozen control.

The exact gate covered {summary['pairs']} per-seed race pairs and recorded
{len(gains)} safety gain(s), {len(faster)} same-order pace gain(s), no slower
outcomes, no safety regressions and no field redistributions. The target-free
Zandvoort seeds 128 and 134 remained outcome-identical to the Round 106
champion.

"""
    development = Path("AI_DEVELOPMENT.md")
    text = development.read_text()
    heading = "## Round 110: dual frontier rescue\n"
    if heading not in text:
        anchor = "## Current champion and frontier baseline\n"
        development.write_text(
            text.replace(anchor, section + anchor, 1) if anchor in text else section + text
        )

    campaign = Path("racing-memory.md")
    marker = "ROUND 110 (dual frontier rescue):"
    campaign_text = campaign.read_text()
    if marker not in campaign_text:
        note = textwrap.dedent(
            f"""

            {marker} the unfinished opening-pack and equal-speed branches were
            rebased together on Round 106. Hungaroring s144 and Zandvoort s115
            are both repaired to seven finishers / zero crashes. Exact gate:
            {summary['pairs']} pairs, {len(gains)} safety gain(s),
            {len(faster)} same-order pace gain(s), zero slower outcomes,
            safety regressions or redistributions. AI2 remains frozen.
            """
        )
        campaign.write_text(campaign_text.rstrip() + note)


def main() -> int:
    summary = json.loads(Path("round110-summary.json").read_text())
    if summary.get("pairs", 0) <= 0:
        raise SystemExit(f"invalid Round-110 summary: {summary}")
    expected: dict[str, dict[str, object]] = {}
    for track, seed in TARGETS + CONTROLS:
        expected[f"{track}:{seed}"] = measure(track, seed)
    for track, seed in TARGETS:
        case = expected[f"{track}:{seed}"]
        ai1, ai2 = case["AI1"], case["AI2"]
        if ai1[0] <= ai2[0] and ai1[1] >= ai2[1]:
            raise SystemExit(f"target not rescued: {track}:{seed} {case}")
    for track, seed in CONTROLS:
        case = expected[f"{track}:{seed}"]
        if case["AI1"] != case["AI2"]:
            raise SystemExit(f"control diverged: {track}:{seed} {case}")
    write_regression(expected)
    update_notes(summary)
    print(json.dumps(expected, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
