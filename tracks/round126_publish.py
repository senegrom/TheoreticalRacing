#!/usr/bin/env python3
"""Generate Round 126's permanent regression and campaign notes."""
from __future__ import annotations

import json
from pathlib import Path
import textwrap

SUMMARY = Path("round126-summary.json")
TEST = Path("tests/ai1_equal_speed_veto_regression.py")


def tuple_result(result: dict) -> tuple[int, int, list[int]]:
    finishes = result["finishes"]
    return len(finishes), len(result["crashes"]), sorted(int(v) for v in finishes.values())


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    if summary.get("pairs") != 3500 or summary.get("bad") != 0:
        raise SystemExit(f"invalid Round 126 summary: {summary}")
    events = [e for e in summary["events"]
              if e["track"] == "zandvoort" and e["seed"] == 115
              and e["classification"] == "safety_gain"]
    if len(events) != 1:
        raise SystemExit(f"Round 126 target evidence missing: {summary}")
    event = events[0]
    expected = {
        "AI1": {"zandvoort:115": tuple_result(event["candidate"])},
        "AI2": {"zandvoort:115": tuple_result(event["baseline"])},
    }

    source = f'''#!/usr/bin/env python3
"""Pin Round 126's equal-speed false-target rescue."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

CASES = [("zandvoort", 115)]
EXPECTED = {expected!r}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {{"AI1": {{}}, "AI2": {{}}}}
    with tempfile.TemporaryDirectory(prefix="round126-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for track, seed in CASES:
                actual[kind][f"{{track}}:{{seed}}"] = bench_ai.run_track(
                    track, timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-126 regression: {{actual}}, expected {{EXPECTED}}")
    ai1 = EXPECTED["AI1"]["zandvoort:115"]
    ai2 = EXPECTED["AI2"]["zandvoort:115"]
    if not (ai1[0] > ai2[0] and ai1[1] < ai2[1]):
        raise SystemExit(f"Round-126 safety contract lost: {{EXPECTED}}")
    print("AI1EqualSpeedVetoRegression: OK (Zandvoort s115 rescued; AI2 frozen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    TEST.write_text(source)

    counts = summary["counts"]
    section = textwrap.dedent(f"""
    ## Round 126: equal-speed false-target veto

    The residual Zandvoort seed-115 failure was not a bad initial choice but a
    false survival switch.  The topology-shaped eight-round world abandoned an
    equal-speed chosen lane for an alternative that the bounded faithful-rival
    world killed, while that same faithful world kept the chosen lane alive.
    AI1 now compares both landings only for an equal-map-turn, equal-speed,
    positive-trap switch in a large homogeneous field and vetoes precisely the
    true-alive to true-dead transition.  AI2 is explicitly excluded and remains
    the frozen control; every non-equal-speed ladder decision is unchanged.

    The exact {summary['pairs']}-pair differential recorded
    {counts.get('safety_gain', 0)} safety gain(s), zero safety regressions,
    zero individual slowdowns, zero redistributions and net
    {summary['net_moves']} finisher moves.  Zandvoort seed 115 is the required
    target rescue.  The documented residual safety frontier is now the accepted
    Hairpin seed 68 finish-denial seal plus ultra-deep Zandvoort seed 195.

    """)
    development = Path("AI_DEVELOPMENT.md")
    text = development.read_text()
    heading = "## Round 126: equal-speed false-target veto\n"
    if heading not in text:
        anchor = "## Highest-value next directions\n"
        if anchor not in text:
            raise SystemExit("AI_DEVELOPMENT anchor missing")
        development.write_text(text.replace(anchor, section + anchor, 1))

    memory = Path("racing-memory.md")
    marker = "## Round 126: equal-speed false-target veto\n"
    text = memory.read_text()
    if marker not in text:
        anchor = "## Round 114 (local agent):"
        if anchor not in text:
            raise SystemExit("racing-memory anchor missing")
        note = textwrap.dedent(f"""
        ## Round 126: equal-speed false-target veto

        Ported and re-certified the unfinished Zandvoort s115 mechanism on the
        Round-124 master.  At an equal-map-turn, equal-speed, positive-trap
        topology switch in a large homogeneous AI1 field, the bounded
        certification-cap faithful-rival world is run on both landings.  A
        switch is vetoed only when it would leave a true-alive chosen line for
        a true-dead target.  AI2 is kind-gated out.

        Exact gate: {summary['pairs']} pairs,
        {counts.get('safety_gain', 0)} safety gain(s), zero safety regressions,
        individual slowdowns or redistributions.  Zandvoort s115 is rescued.
        Residual frontier: accepted hairpin s68 and ultra-deep zandvoort s195.

        """)
        memory.write_text(text.replace(anchor, note + anchor, 1))

    print(f"Round126Publish: wrote {TEST} and documented the target rescue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
