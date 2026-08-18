#!/usr/bin/env python3
"""Generate Round 119's permanent regression and campaign notes."""
from __future__ import annotations

import json
from pathlib import Path
import textwrap

SUMMARY = Path("round119-summary.json")
TEST = Path("tests/ai1_six_ahead_moderate_regression.py")


def tuple_result(result: dict) -> tuple[int, int, list[int]]:
    finishes = result["finishes"]
    return len(finishes), len(result["crashes"]), sorted(int(v) for v in finishes.values())


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    if summary.get("pairs") != 3500:
        raise SystemExit(f"invalid Round 119 summary: {summary}")
    bad = sum(summary["counts"].get(key, 0) for key in
              ("aggregate_faster", "slower", "safety_regression", "redistribution"))
    events = [e for e in summary["events"] if e["classification"] == "pareto_faster"]
    if bad or not events:
        raise SystemExit(f"Round 119 is not promotable: {summary}")

    expected: dict[str, dict[str, tuple[int, int, list[int]]]] = {"AI1": {}, "AI2": {}}
    cases: list[tuple[str, int]] = []
    for event in events:
        track, seed = str(event["track"]), int(event["seed"])
        key = f"{track}:{seed}"
        cases.append((track, seed))
        expected["AI1"][key] = tuple_result(event["candidate"])
        expected["AI2"][key] = tuple_result(event["baseline"])

    test_source = f'''#!/usr/bin/env python3
"""Pin Round 119's synchronized six-ahead moderate acceleration gains."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

CASES = {cases!r}
EXPECTED = {expected!r}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {{"AI1": {{}}, "AI2": {{}}}}
    with tempfile.TemporaryDirectory(prefix="round119-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for track, seed in CASES:
                actual[kind][f"{{track}}:{{seed}}"] = bench_ai.run_track(
                    track, timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-119 regression: {{actual}}, expected {{EXPECTED}}")
    for key in EXPECTED["AI1"]:
        ai1, ai2 = EXPECTED["AI1"][key], EXPECTED["AI2"][key]
        if ai1[:2] != ai2[:2] or any(a > b for a, b in zip(ai1[2], ai2[2])):
            raise SystemExit(f"Round-119 Pareto contract lost on {{key}}: {{EXPECTED}}")
        if sum(ai1[2]) >= sum(ai2[2]):
            raise SystemExit(f"Round-119 pace gain lost on {{key}}: {{EXPECTED}}")
    print("AI1SixAheadModerateRegression: OK (all measured gains faster; AI2 frozen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    TEST.write_text(test_source)

    counts = summary["counts"]
    changed = ", ".join(f"{e['track']} seed {e['seed']}" for e in events)
    section = textwrap.dedent(f"""
    ## Round 119: synchronized six-ahead moderate acceleration

    Round 117's exact-six-ahead formation proof required an adjacent previously
    moved rival already carrying the candidate velocity, but admitted only the
    old high-energy gain>=16 class. Round 119 lets that same synchronized
    formation use Round 115's short-range moderate gain 9..15 certificate.
    AI1, non-coast, low incumbent speed, TTF<=45, zero trap/uncertainty,
    unsealable landing, strict eight-round mover/field improvement, and all
    downstream danger vetoes remain mandatory. AI2 remains frozen.

    The exact {summary['pairs']}-pair differential recorded
    {counts.get('pareto_faster', 0)} Pareto-faster race(s),
    {counts.get('safety_gain', 0)} safety gain(s), zero individual slowdowns,
    zero safety regressions, zero field redistributions, and net
    {summary['net_moves']} finisher moves. Changed races: {changed}.

    """)
    development = Path("AI_DEVELOPMENT.md")
    text = development.read_text()
    heading = "## Round 119: synchronized six-ahead moderate acceleration\n"
    if heading not in text:
        anchor = "## Highest-value next directions\n"
        development.write_text(text.replace(anchor, section + anchor, 1))

    memory = Path("racing-memory.md")
    marker = "ROUND 119 (synchronized six-ahead moderate acceleration):"
    text = memory.read_text()
    if marker not in text:
        note = textwrap.dedent(f"""

        {marker} Round 117's adjacent prior candidate-velocity-peer formation
        now admits Round 115's moderate gain 9..15 band under the same strict
        eight-round mover/field proof. Exact gate: {summary['pairs']} pairs,
        {counts.get('pareto_faster', 0)} Pareto gain(s), zero individual
        slowdowns, safety regressions or redistributions, net
        {summary['net_moves']} finisher moves. Changed races: {changed}. AI2
        remains frozen.
        """)
        memory.write_text(text.rstrip() + note + "\n")

    print(f"Round119Publish: wrote {TEST} and documented {len(events)} gain(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
