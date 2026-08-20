#!/usr/bin/env python3
"""Document Round 157 after exact identity and runtime gates pass."""
from __future__ import annotations

import json
from pathlib import Path
import re
import textwrap

SUMMARY = Path("round157-summary.json")
RUNTIME = Path("round157-runtime.json")
BASE_SHA = Path("round157-base-sha.txt")
HEADING = "## Round 157: share immutable progress maps across auto batches"


def comparison(ratio: float) -> str:
    delta = (1.0 - ratio) * 100.0
    return f"{abs(delta):.1f}% {'faster' if delta >= 0 else 'slower'}"


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    runtime = json.loads(RUNTIME.read_text())
    base_sha = BASE_SHA.read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", base_sha):
        raise SystemExit(f"invalid Round-157 parent SHA: {base_sha!r}")
    if (
        summary.get("baseline_sha") != base_sha
        or summary.get("candidate") != "shared_distance_maps"
        or summary.get("pairs") != 3500
        or summary.get("mismatches") != 0
        or summary.get("byte_identical_tracks") != 26
        or not summary.get("viable")
    ):
        raise SystemExit(f"invalid Round-157 exact summary: {summary}")
    if runtime.get("aggregate_ratio", 2.0) > 0.98 or not runtime.get("viable"):
        raise SystemExit(f"invalid Round-157 runtime evidence: {runtime}")
    rows = {row["track"]: row for row in runtime["cases"]}
    required = {"monaco", "nurburgring", "zandvoort", "interlagos", "sprint"}
    if (
        set(rows) != required
        or any(row["ratio"] > 1.05 for row in rows.values())
        or any(not row["byte_identical"] for row in rows.values())
    ):
        raise SystemExit(f"unexpected Round-157 runtime cases: {rows}")

    aggregate_gain = (1.0 - runtime["aggregate_ratio"]) * 100.0
    section = textwrap.dedent(
        f"""
        {HEADING} — {aggregate_gain:.1f}% faster on the measured batch wall

        The distance-to-finish BFS and its derived progress-ring widths are
        immutable functions of track geometry, yet every seed in an auto batch
        rebuilt them before racing. Round 157 adopts one exact pair for every
        subsequent `RaceGame` carrying the same geometry cache key.

        The access-ordered pool is capped at eight million integer entries
        (roughly 32 MiB plus row overhead). Interactive games remain private.
        Concurrent first builders may duplicate work, but publication retains
        one exact pair; no array is modified after publication. AI policy,
        reachability products, geometry verdicts and race ordering are
        untouched.

        Exact gate: {summary['pairs']} all-AI2 baseline/candidate race pairs
        across all 26 tracks, with every complete race log byte-identical. The
        full Java suite, headless smoke, golden corpus, homogeneous AI probe,
        tooling tests and every permanent AI regression pin passed on the JDK
        25 candidate and again from a clean production checkout.

        Seven-pair dual-order warm batches measured Monaco
        {comparison(rows['monaco']['ratio'])}, Nürburgring
        {comparison(rows['nurburgring']['ratio'])}, Zandvoort
        {comparison(rows['zandvoort']['ratio'])}, Interlagos
        {comparison(rows['interlagos']['ratio'])}, and Sprint
        {comparison(rows['sprint']['ratio'])}. The weighted median aggregate is
        {aggregate_gain:.1f}% faster; no measured case crossed the five-percent
        regression limit.

        """
    )

    for filename in ("AI_DEVELOPMENT.md", "racing-memory.md"):
        path = Path(filename)
        text = path.read_text()
        if HEADING in text:
            continue
        anchor = "## Round 156: share exact dense edge caches across auto batches"
        if anchor not in text:
            raise SystemExit(f"{filename}: Round-156 anchor missing")
        path.write_text(text.replace(anchor, section + anchor, 1))

    print("Round157Publish: documented shared immutable progress maps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
