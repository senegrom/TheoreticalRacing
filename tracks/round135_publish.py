#!/usr/bin/env python3
"""Document Round 135 after exact identity and dual-order runtime gates pass."""
from __future__ import annotations

import json
from pathlib import Path
import re
import textwrap

SUMMARY = Path("round135-summary.json")
RUNTIME = Path("round135-runtime.json")
BASE_SHA = Path("round135-base-sha.txt")
HEADING = "## Round 135: fixed-finish supporting-line reject"


def percent_gain(ratio: float) -> str:
    return f"{(1.0 - ratio) * 100.0:.1f}%"


def comparison(ratio: float) -> str:
    delta = (1.0 - ratio) * 100.0
    return f"{abs(delta):.1f}% {'faster' if delta >= 0 else 'slower'}"


def insert_section(path: Path, section: str) -> None:
    text = path.read_text()
    if HEADING in text:
        return
    for anchor in (
        "## Round 134: exact point-containment cache",
        "## Round 129 promoted: measured frontier pace for both driver kinds",
    ):
        if anchor in text:
            path.write_text(text.replace(anchor, section + anchor, 1))
            return
    raise SystemExit(f"documentation anchor missing in {path}")


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    runtime = json.loads(RUNTIME.read_text())
    base_sha = BASE_SHA.read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", base_sha):
        raise SystemExit(f"invalid Round 135 parent SHA: {base_sha!r}")
    if (summary.get("baseline_sha") != base_sha
            or summary.get("pairs") != 3500
            or summary.get("mismatches") != 0
            or not summary.get("viable")):
        raise SystemExit(f"invalid Round 135 exact summary: {summary}")
    if not runtime.get("viable") or runtime.get("aggregate_ratio", 2.0) > 0.94:
        raise SystemExit(f"invalid Round 135 runtime evidence: {runtime}")
    rows = {row["track"]: row for row in runtime["cases"]}
    required = {"monaco", "zandvoort", "nurburgring", "bigoval", "sprint"}
    if set(rows) != required:
        raise SystemExit(f"unexpected Round 135 runtime cases: {rows}")

    section = textwrap.dedent(f"""
    {HEADING} — {percent_gain(runtime['aggregate_ratio'])} faster on the measured wall

    Post-cache JFR profiling put the general `Line2D.linesIntersect` routine at
    the top of the remaining decision-time profile. Nearly every candidate move
    lies strictly on one side of the fixed finish line, but the old path paid
    the full relative-CCW segment test before learning that.

    `crossesFinish` now computes the two oriented areas against the finish
    line's supporting line first. When both signs are strictly equal, segment
    intersection is mathematically impossible and the method returns false.
    Opposite-sign, zero, NaN and degenerate cases still run the exact original
    `Line2D.linesIntersect` predicate and the unchanged forward-heading test.
    The shortcut is therefore one-sided: it can skip impossible crossings but
    cannot create or remove a finish.

    Exact gate: {summary['pairs']} all-AI2 baseline/candidate race pairs across
    all 26 tracks, with every complete race log byte-identical. Java tests,
    headless smoke, goldens, all permanent AI pins, the homogeneous mirror
    probe, tooling tests and Python compilation passed on the candidate and on
    a fresh production checkout.

    Four-pair dual-order warm batches measured Monaco
    {comparison(rows['monaco']['ratio'])}, Zandvoort
    {comparison(rows['zandvoort']['ratio'])}, Nürburgring
    {comparison(rows['nurburgring']['ratio'])}, Big Oval
    {comparison(rows['bigoval']['ratio'])} and Sprint
    {comparison(rows['sprint']['ratio'])}. Across the weighted medians the
    candidate is {percent_gain(runtime['aggregate_ratio'])} faster. Promotion
    required at least a six-percent aggregate win and no measured case more
    than five percent slower.

    """)
    insert_section(Path("AI_DEVELOPMENT.md"), section)
    insert_section(Path("racing-memory.md"), section)
    print("Round135Publish: documented fixed-finish supporting-line reject")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
