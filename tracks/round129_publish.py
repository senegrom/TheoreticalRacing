#!/usr/bin/env python3
"""Document Round 129 after the exact frontier-promotion gate passes."""
from __future__ import annotations

import json
from pathlib import Path
import textwrap

SUMMARY = Path("round129-summary.json")


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    counts = summary.get("counts", {})
    bad = sum(counts.get(key, 0) for key in (
        "aggregate_faster", "slower", "safety_regression", "redistribution"))
    if summary.get("pairs") != 3500 or bad != 0:
        raise SystemExit(f"invalid Round 129 summary: {summary}")
    if counts.get("pareto_faster", 0) < 4 or counts.get("safety_gain", 0) < 1:
        raise SystemExit(f"missing Round 129 gains: {summary}")

    section = textwrap.dedent(f"""
    ## Round 129 promoted: measured frontier pace for both driver kinds

    The harvest-23 alternating 4v4 census measured AI1 ahead of frozen AI2 on
    21 of 22 tracks, with a 2.05-place-sum advantage per race. Round 129
    promotes the already separately certified Round 115 moderate-energy,
    Round 117 synchronized six-ahead and Round 124 phase-consistent trap
    acceleration arms to AI2 as well. Round 126's homogeneous equal-speed
    false-target veto is promoted with them, repairing Zandvoort seed 115 for
    both kinds. The Round 128 mixed finish-funnel confirm remains AI1-only: it
    is a safety frontier, not a pace arm, and a broad mirror was prohibitively
    expensive in mixed recursive confirmation.

    Exact gate: {summary['pairs']} all-AI2 baseline/candidate pairs,
    {counts.get('pareto_faster', 0)} Pareto-faster race(s),
    {counts.get('safety_gain', 0)} safety gain(s), zero individual slowdowns,
    zero safety regressions, zero aggregate-only gains and zero finisher-set
    redistributions. The permanent Round 115/117/124/126 pins now require the
    promoted result from both AI1 and AI2.

    """)

    development = Path("AI_DEVELOPMENT.md")
    text = development.read_text()
    heading = "## Round 129 promoted: measured frontier pace for both driver kinds\n"
    if heading not in text:
        anchor = "## Fast development loop\n"
        if anchor not in text:
            raise SystemExit("AI_DEVELOPMENT anchor missing")
        development.write_text(text.replace(anchor, section + anchor, 1))

    memory = Path("racing-memory.md")
    text = memory.read_text()
    if heading not in text:
        anchor = "## Mixed h2h census (harvest-23, analysis): frontier -2.05/race over champion\n"
        if anchor not in text:
            raise SystemExit("racing-memory anchor missing")
        memory.write_text(text.replace(anchor, section + anchor, 1))

    print("Round129Publish: documented exact frontier promotion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
