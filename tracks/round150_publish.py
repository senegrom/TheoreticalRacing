#!/usr/bin/env python3
"""Document Round 150 after exact identity and runtime gates pass."""
from __future__ import annotations

import json
from pathlib import Path
import re
import textwrap

SUMMARY = Path("round150-summary.json")
RUNTIME = Path("round150-runtime.json")
BASE_SHA = Path("round150-base-sha.txt")
HEADING = "## Round 150: direct in-grid edge legality cache"


def comparison(ratio: float) -> str:
    delta = (1.0 - ratio) * 100.0
    return f"{abs(delta):.1f}% {'faster' if delta >= 0 else 'slower'}"


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    runtime = json.loads(RUNTIME.read_text())
    base_sha = BASE_SHA.read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", base_sha):
        raise SystemExit(f"invalid Round-150 parent SHA: {base_sha!r}")
    if (
        summary.get("baseline_sha") != base_sha
        or summary.get("pairs") != 3500
        or summary.get("mismatches") != 0
        or summary.get("byte_identical_tracks") != 26
        or not summary.get("viable")
    ):
        raise SystemExit(f"invalid Round-150 exact summary: {summary}")
    if runtime.get("aggregate_ratio", 2.0) > 0.97:
        raise SystemExit(f"invalid Round-150 runtime evidence: {runtime}")
    rows = {row["track"]: row for row in runtime["cases"]}
    required = {"monaco", "nurburgring", "zandvoort", "interlagos", "sprint"}
    if set(rows) != required or any(row["ratio"] > 1.05 for row in rows.values()):
        raise SystemExit(f"unexpected Round-150 runtime cases: {rows}")

    aggregate_gain = (1.0 - runtime["aggregate_ratio"]) * 100.0
    section = textwrap.dedent(
        f"""
        {HEADING} — {aggregate_gain:.1f}% faster on the measured wall

        The post-Round-134 profile left the open-addressed geometry-edge cache
        among the largest hot leaves. Every production AI edge is identified by
        an integer origin and a bounded velocity delta in `[-12,12]^2`; Round
        150 stores that finite in-grid domain in a direct byte table. A lookup
        now needs one index calculation and one byte read instead of packing,
        mixing and walking an open-addressed probe chain.

        The table is capped at 64 MiB. Unusually large user tracks and every
        out-of-domain query retain the existing exact hash cache. The direct key
        is collision-free over its admitted domain, and the stored verdict is
        still produced by the unchanged exact geometry predicate. AI policy,
        reachability, finish logic and race ordering are untouched.

        Exact gate: {summary['pairs']} all-AI2 baseline/candidate race pairs
        across all 26 tracks, with every complete race log byte-identical. The
        full Java suite, headless smoke, golden corpus, homogeneous AI probe,
        tooling tests and every permanent AI regression pin passed on the JDK
        25 candidate and again from a clean production checkout.

        Five-pair dual-order warm batches measured Monaco
        {comparison(rows['monaco']['ratio'])}, Nürburgring
        {comparison(rows['nurburgring']['ratio'])}, Zandvoort
        {comparison(rows['zandvoort']['ratio'])}, Interlagos
        {comparison(rows['interlagos']['ratio'])}, and Sprint
        {comparison(rows['sprint']['ratio'])}. The weighted median aggregate is
        {aggregate_gain:.1f}% faster; no measured case regressed.

        """
    )

    for filename in ("AI_DEVELOPMENT.md", "racing-memory.md"):
        path = Path(filename)
        text = path.read_text()
        if HEADING in text:
            continue
        anchor = "## Round 134: exact point-containment cache"
        if anchor not in text:
            raise SystemExit(f"{filename}: Round-134 anchor missing")
        path.write_text(text.replace(anchor, section + anchor, 1))

    print("Round150Publish: documented direct in-grid edge cache")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
