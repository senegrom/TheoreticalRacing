#!/usr/bin/env python3
"""Generate Round 116 regression pins and campaign documentation."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import textwrap

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

CONTROLS = (("silverstone", 78), ("silverstone", 112), ("spa", 12))


def measure(cases: list[tuple[str, int]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="round116-publish-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for track, seed in cases:
            values: dict[str, object] = {}
            for kind in ("AI1", "AI2"):
                bench_ai.set_all_to(kind)
                values[kind] = bench_ai.run_track(track, timeout=1800, seed=seed)
            rows.append({"track": track, "seed": seed, **values})
    return rows


def write_test(rows: list[dict[str, object]], gains: set[tuple[str, int]]) -> None:
    source = f'''#!/usr/bin/env python3
"""Pin Round 116's AI1-only high-speed 12-round pace proof."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

CASES = {rows!r}
GAINS = {sorted(gains)!r}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = []
    with tempfile.TemporaryDirectory(prefix="round116-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for case in CASES:
            values = {{}}
            for kind in ("AI1", "AI2"):
                bench_ai.set_all_to(kind)
                values[kind] = bench_ai.run_track(case["track"], timeout=1800, seed=case["seed"])
            actual.append({{"track": case["track"], "seed": case["seed"], **values}})
    if actual != CASES:
        raise SystemExit(f"Round-116 regression: {{actual}}, expected {{CASES}}")
    for case in actual:
        key = (case["track"], case["seed"])
        ai1, ai2 = case["AI1"], case["AI2"]
        if key in GAINS:
            if ai1[0:2] != ai2[0:2] or any(a > b for a, b in zip(ai1[2], ai2[2])):
                raise SystemExit(f"Round-116 Pareto contract lost on {{key}}: {{ai1}}, {{ai2}}")
            if sum(ai1[2]) >= sum(ai2[2]):
                raise SystemExit(f"Round-116 pace gain lost on {{key}}: {{ai1}}, {{ai2}}")
        elif ai1 != ai2:
            raise SystemExit(f"Round-116 exclusion control changed on {{key}}: {{ai1}}, {{ai2}}")
    print("AI1HighSpeedH12Regression: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    Path("tests/ai1_high_speed_h12_regression.py").write_text(source)


def update_docs(summary: dict[str, object]) -> None:
    counts = summary["counts"]
    events = summary["events"]
    assert isinstance(counts, dict) and isinstance(events, list)
    gains = [event for event in events if event["classification"] == "pareto_faster"]
    gain_lines = "\n".join(
        f"- {event['track']} seed {event['seed']}: "
        f"{event['baseline']['sum']} -> {event['candidate']['sum']} finisher moves."
        for event in gains
    )
    section = f"""## Round 116: high-speed moderate acceleration with a 12-round proof

Round 115's low-energy acceleration remains unchanged and has priority. AI1 may
now consider the complementary high-speed, map-TTF-at-most-45 class for
speed-squared gains 9..15, but only under a twelve-round scorer-field proof.
The existing homogeneous-roster, forward-pack, trap-zero, uncertainty-zero,
funnel, seal and downstream danger contracts remain mandatory. AI2 stays the
frozen Round-115 control.

The exact {summary['pairs']}-pair differential recorded
{counts.get('pareto_faster', 0)} Pareto-faster race(s),
{counts.get('safety_gain', 0)} safety gain(s), no slower races, no safety
regressions and no field redistributions. Net finisher moves changed by
{summary['net_moves']}.

{gain_lines}

Silverstone seeds 78 and 112 and Spa seed 12 remain exact exclusion controls;
the old eight-round proof changed their fields, while the narrowed twelve-round
rule does not.

"""
    development = Path("AI_DEVELOPMENT.md")
    text = development.read_text()
    heading = "## Round 116: high-speed moderate acceleration with a 12-round proof\n"
    if heading not in text:
        anchor = "## Highest-value next directions\n"
        development.write_text(text.replace(anchor, section + anchor, 1))

    memory = Path("racing-memory.md")
    marker = "ROUND 116 (high-speed H12 field acceleration):"
    text = memory.read_text()
    if marker not in text:
        note = textwrap.dedent(f"""

        {marker} AI1 extends the Round-115 moderate acceleration class only to
        high-speed states within TTF 45 and requires a 12-round scorer-field
        proof. Exact gate: {summary['pairs']} pairs,
        {counts.get('pareto_faster', 0)} Pareto gain(s),
        {counts.get('safety_gain', 0)} safety gain(s), zero slower,
        safety-regression or redistribution outcomes, net
        {summary['net_moves']} finisher moves. AI2 remains frozen.
        """)
        memory.write_text(text.rstrip() + note)


def main() -> int:
    summary = json.loads(Path("round116-summary.json").read_text())
    gains = {
        (str(event["track"]), int(event["seed"]))
        for event in summary["events"]
        if event["classification"] == "pareto_faster"
    }
    cases = sorted(gains | set(CONTROLS))
    rows = measure(cases)
    write_test(rows, gains)
    update_docs(summary)
    print(json.dumps({"measured": rows, "gains": sorted(gains)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
