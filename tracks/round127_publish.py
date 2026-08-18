#!/usr/bin/env python3
"""Generate Round 127's permanent regression and campaign notes."""
from __future__ import annotations

import json
from pathlib import Path
import textwrap

SUMMARY = Path("round127-summary.json")
TEST = Path("tests/ai1_dense_fast_funnel_regression.py")


def tuple_result(result: dict) -> tuple[int, int, list[int]]:
    finishes = result["finishes"]
    return len(finishes), len(result["crashes"]), sorted(int(v) for v in finishes.values())


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    if summary.get("pairs") != 3500 or summary.get("bad") != 0:
        raise SystemExit(f"invalid Round 127 summary: {summary}")
    events = [
        event for event in summary["events"]
        if event["track"] == "zandvoort"
        and event["seed"] == 195
        and event["classification"] == "safety_gain"
    ]
    if len(events) != 1:
        raise SystemExit(f"Round 127 target evidence missing: {summary}")
    event = events[0]
    expected = {
        "AI1": {"zandvoort:195": tuple_result(event["candidate"])},
        "AI2": {"zandvoort:195": tuple_result(event["baseline"])},
    }

    source = f'''#!/usr/bin/env python3
"""Pin Round 127's dense fast-funnel rescue."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

CASES = [("zandvoort", 195)]
EXPECTED = {expected!r}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {{"AI1": {{}}, "AI2": {{}}}}
    with tempfile.TemporaryDirectory(prefix="round127-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for track, seed in CASES:
                actual[kind][f"{{track}}:{{seed}}"] = bench_ai.run_track(
                    track, timeout=1800, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-127 regression: {{actual}}, expected {{EXPECTED}}")
    ai1 = EXPECTED["AI1"]["zandvoort:195"]
    ai2 = EXPECTED["AI2"]["zandvoort:195"]
    if not (ai1[0] > ai2[0] and ai1[1] < ai2[1]):
        raise SystemExit(f"Round-127 safety contract lost: {{EXPECTED}}")
    print("AI1DenseFastFunnelRegression: OK (Zandvoort s195 rescued; AI2 frozen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    TEST.write_text(source)

    counts = summary["counts"]
    section = textwrap.dedent(f"""
    ## Round 127: dense fast-funnel certificate

    Zandvoort seed 195 was the remaining ultra-deep corridor failure.  The
    selected speed-7-plus line entered a sustained width-three funnel but did
    not die until faithful rollout round eleven, beyond the established
    eight-round sparse-funnel certificate.  AI1 now pays for a twelve-round
    scorer-field check only in a large homogeneous, tightly packed field whose
    fast landing enters that narrow sustained geometry.  A switch remains
    survival-only and must brake to a lower-energy candidate no more than one
    empty-map turn slower.  The sparse fast-funnel arm and AI2 are unchanged.

    The exact {summary['pairs']}-pair differential recorded
    {counts.get('safety_gain', 0)} safety gain(s), zero safety regressions,
    zero individual slowdowns, zero aggregate-only gains and zero field
    redistributions.  Zandvoort seed 195 is the required rescue; all other
    changed races, if any, satisfy the same fail-closed safety contract.

    """)
    development = Path("AI_DEVELOPMENT.md")
    text = development.read_text()
    heading = "## Round 127: dense fast-funnel certificate\n"
    if heading not in text:
        anchor = "## Highest-value next directions\n"
        if anchor not in text:
            raise SystemExit("AI_DEVELOPMENT anchor missing")
        development.write_text(text.replace(anchor, section + anchor, 1))

    memory = Path("racing-memory.md")
    marker = "## Round 127: dense fast-funnel certificate\n"
    text = memory.read_text()
    if marker not in text:
        anchor = "## Round 126: equal-speed false-target veto\n"
        if anchor not in text:
            raise SystemExit("racing-memory Round-126 anchor missing")
        note = textwrap.dedent(f"""
        ## Round 127: dense fast-funnel certificate

        The Zandvoort s195 forensic oracle found the chosen fast corridor line
        alive through round eight but dead at faithful round eleven, with
        lower-energy survivors available earlier.  AI1 now invokes a direct
        twelve-round scorer-field certificate only for a large homogeneous
        pack entering a sustained width-three-or-narrower funnel.  A target is
        accepted only when it survives, brakes, and costs at most one map turn.
        AI2 remains frozen.

        Exact gate: {summary['pairs']} pairs,
        {counts.get('safety_gain', 0)} safety gain(s), zero safety regressions,
        individual slowdowns, aggregate-only gains or redistributions.

        """)
        memory.write_text(text.replace(anchor, note + anchor, 1))

    print(f"Round127Publish: wrote {TEST} and documented the dense-funnel rescue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
