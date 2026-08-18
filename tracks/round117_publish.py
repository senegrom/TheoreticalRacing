#!/usr/bin/env python3
"""Generate Round 117's permanent pin and development record after verification."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import textwrap

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402


def measure_boundaries() -> dict[str, dict[int, object]]:
    actual: dict[str, dict[int, object]] = {"AI1": {}, "AI2": {}}
    with tempfile.TemporaryDirectory(prefix="round117-pin-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for seed in (5, 22, 86):
                actual[kind][seed] = bench_ai.run_track("coil", timeout=1200, seed=seed)
    for seed in (5, 22):
        if actual["AI1"][seed] != actual["AI2"][seed]:
            raise SystemExit(f"Round-117 control changed on Coil seed {seed}: {actual}")
    ai1 = actual["AI1"][86]
    ai2 = actual["AI2"][86]
    if ai1[0:2] != ai2[0:2] or len(ai1[2]) != len(ai2[2]):
        raise SystemExit(f"Round-117 target safety/order contract failed: {actual}")
    if any(a > b for a, b in zip(ai1[2], ai2[2])) or sum(ai1[2]) >= sum(ai2[2]):
        raise SystemExit(f"Round-117 target is not Pareto-faster: {actual}")
    return actual


def write_test(expected: dict[str, dict[int, object]]) -> None:
    source = f'''#!/usr/bin/env python3
"""Pin Round 117's AI1-only synchronized six-ahead acceleration."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

EXPECTED = {expected!r}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {{"AI1": {{}}, "AI2": {{}}}}
    with tempfile.TemporaryDirectory(prefix="round117-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for seed in (5, 22, 86):
                actual[kind][seed] = bench_ai.run_track("coil", timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-117 regression: {{actual}}, expected {{EXPECTED}}")
    for seed in (5, 22):
        if actual["AI1"][seed] != actual["AI2"][seed]:
            raise SystemExit(f"Round-117 control changed on seed {{seed}}: {{actual}}")
    ai1, ai2 = actual["AI1"][86], actual["AI2"][86]
    if ai1[0:2] != ai2[0:2] or any(a > b for a, b in zip(ai1[2], ai2[2])):
        raise SystemExit(f"Round-117 Pareto contract lost: {{actual}}")
    if sum(ai1[2]) >= sum(ai2[2]):
        raise SystemExit(f"Round-117 pace gain lost: {{actual}}")
    print("AI1SixAheadAccelRegression: OK (Coil s86 faster; s5/s22 and AI2 frozen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    Path("tests/ai1_six_ahead_accel_regression.py").write_text(source)


def update_docs(summary: dict[str, object]) -> None:
    counts = summary["counts"]
    events = summary["events"]
    gains = [event for event in events if event["classification"] == "pareto_faster"]
    section = f"""## Round 117: synchronized exact-six-ahead acceleration

Round 106 capped its strict field-acceleration proof at five rivals ahead. A
sixth-place extension exposed one genuine Coil pace gain and two field
redistributions from the same local move. Board reconstruction found a
track-independent separator: only the good state has a previously moved rival
adjacent to the candidate landing with the candidate's exact velocity. That
synchronized formation may enter the existing eight-round high-energy proof;
lone back-marker accelerations remain excluded. Round 115's moderate
speed-squared 9..15 frontier stays capped at five ahead and AI2 stays frozen.

The exact {summary['pairs']}-pair gate recorded {counts.get('pareto_faster', 0)}
Pareto-faster race(s), {counts.get('safety_gain', 0)} safety gain(s), zero
slower races, zero safety regressions, zero field redistributions and a net
{summary['net_moves']} finisher moves. The changed races were
{', '.join(f"{event['track']} seed {event['seed']}" for event in gains)}.

"""
    development = Path("AI_DEVELOPMENT.md")
    text = development.read_text()
    heading = "## Round 117: synchronized exact-six-ahead acceleration\n"
    if heading not in text:
        anchor = "## Highest-value next directions\n"
        development.write_text(
            text.replace(anchor, section + anchor, 1) if anchor in text else section + text
        )

    memory = Path("racing-memory.md")
    marker = "ROUND 117 (synchronized exact-six-ahead acceleration):"
    text = memory.read_text()
    if marker not in text:
        note = textwrap.dedent(
            f"""

            {marker} AI1 may enter the established high-energy field
            acceleration with exactly six rivals ahead only when a previously
            moved rival is adjacent to the proposed landing and already carries
            the candidate velocity. Exact gate: {summary['pairs']} pairs,
            {counts.get('pareto_faster', 0)} Pareto gain(s),
            {counts.get('safety_gain', 0)} safety gain(s), zero slower,
            safety-regression or redistribution outcomes, net
            {summary['net_moves']} finisher moves. Coil s5/s22 are exact controls;
            Coil s86 is the target gain. AI2 remains frozen.
            """
        )
        memory.write_text(text.rstrip() + note)


def main() -> int:
    summary = json.loads(Path("round117-summary.json").read_text())
    counts = summary["counts"]
    bad = sum(counts.get(key, 0) for key in (
        "slower", "safety_regression", "redistribution", "aggregate_faster"))
    if summary.get("pairs") != 3500 or bad or counts.get("pareto_faster", 0) < 1:
        raise SystemExit(f"invalid Round-117 summary: {summary}")
    expected = measure_boundaries()
    write_test(expected)
    update_docs(summary)
    print(f"Round117Publish: {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
