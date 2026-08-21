#!/usr/bin/env python3
"""Generate Round 176's permanent regression pin and development notes."""
from __future__ import annotations

import json
from pathlib import Path
import textwrap

EXPECTED = (7, 0, [59, 60, 60, 61, 61, 62, 63])


def write_regression() -> None:
    source = f'''#!/usr/bin/env python3
"""Pin Round 176's faithful-rival veto for one-successor finish sprints.

Rand3 seed 1 used to replace safe NW at move 448 with map-faster N.  Both
historical sprint proxy worlds called N a finish, but faithful rivals occupy its
only continuation at round five and p8 crashed.  The narrow L1 sprint confirm
keeps NW: every previously finishing driver retains its personal move count and
p8 now finishes in 62 moves.
"""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

EXPECTED = {EXPECTED!r}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    with tempfile.TemporaryDirectory(prefix="round176-sprint-confirm-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            actual = bench_ai.run_track("rand3", timeout=1800, seed=1)
            if actual != EXPECTED:
                raise SystemExit(
                    f"Round-176 {{kind}} regression: {{actual}}, expected {{EXPECTED}}"
                )
    print("Round176FinishSprintTrueConfirm: OK (rand3 s1 rescued for AI1 and AI2)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    Path("tests/ai1_finish_sprint_true_confirm_regression.py").write_text(source)


def update_notes(summary: dict, runtime: dict) -> None:
    counts = summary["counts"]
    ratio = runtime["aggregate_ratio"]
    section = textwrap.dedent(f"""

    ## Round 176: faithful-rival confirmation for one-successor finish sprints

    Rand3 seed 1 exposed a false finish certificate at move 448.  The normal
    scorer chose NW and the perfect rollout finishes that line in five rounds;
    the Round-75 sprint override selected map-faster N, which both proxy worlds
    called a finish, but faithful rivals seal its only continuation at true
    round five.  Champion policy now runs that fifth-round faithful-rival veto
    only for traffic-dependent L1 sprint candidates with map TTF at least five.

    Exact gate: {summary['pairs']} paired races across {summary['tracks']} tracks,
    {counts.get('safety_gain', 0)} safety gain(s), {counts.get('faster', 0)}
    same-safety pace gain(s), and zero slower races, safety regressions,
    safety tradeoffs, redistributions or outcome-identical trajectory changes.
    The alternating warm runtime ratio was {ratio:.4f}.  Rand3 seed 1 changes
    from six logged finishers and one crash to seven logged finishers and zero
    crashes; every previous finisher keeps the same personal move count.
    """)
    development = Path("AI_DEVELOPMENT.md")
    text = development.read_text()
    marker = "## Round 176: faithful-rival confirmation for one-successor finish sprints"
    if marker not in text:
        development.write_text(text.rstrip() + section + "\n")

    memory = Path("racing-memory.md")
    text = memory.read_text()
    marker = "ROUND 176 (finish-sprint true confirm):"
    if marker not in text:
        note = textwrap.dedent(f"""

        {marker} rand3 s1 is closed by a five-round faithful-rival veto on the
        exact L1 finish-sprint class.  Gate: {summary['pairs']} pairs,
        {counts.get('safety_gain', 0)} safety gain(s), no bad outcomes;
        alternating runtime ratio {ratio:.4f}.
        """)
        memory.write_text(text.rstrip() + note + "\n")


def main() -> int:
    summary = json.loads(Path("round176-summary.json").read_text())
    runtime = json.loads(Path("round176-runtime.json").read_text())
    if summary.get("pairs") != 3518 or not summary.get("viable"):
        raise SystemExit(f"invalid Round-176 summary: {summary}")
    if not runtime.get("viable"):
        raise SystemExit(f"invalid Round-176 runtime evidence: {runtime}")
    write_regression()
    update_notes(summary, runtime)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
