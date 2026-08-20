#!/usr/bin/env python3
"""Document Round 160 after exact identity and runtime gates pass."""
from __future__ import annotations

import json
from pathlib import Path
import re
import textwrap

SUMMARY = Path("round160-summary.json")
RUNTIME = Path("round160-runtime.json")
BASE_SHA = Path("round160-base-sha.txt")
HEADING = "## Round 160: direct blocked-cell bitsets for mobility search"


def comparison(ratio: float) -> str:
    delta = (1.0 - ratio) * 100.0
    return f"{abs(delta):.1f}% {'faster' if delta >= 0 else 'slower'}"


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    runtime = json.loads(RUNTIME.read_text())
    base_sha = BASE_SHA.read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", base_sha):
        raise SystemExit(f"invalid Round-160 parent SHA: {base_sha!r}")
    if (
        summary.get("baseline_sha") != base_sha
        or summary.get("candidate") != "direct_blocked_bitsets"
        or summary.get("pairs") != 3500
        or summary.get("mismatches") != 0
        or summary.get("byte_identical_tracks") != 26
        or not summary.get("viable")
    ):
        raise SystemExit(f"invalid Round-160 exact summary: {summary}")
    if runtime.get("aggregate_ratio", 2.0) > 0.95 or not runtime.get("viable"):
        raise SystemExit(f"invalid Round-160 runtime evidence: {runtime}")
    rows = {row["track"]: row for row in runtime["cases"]}
    required = {"monaco", "nurburgring", "zandvoort", "interlagos", "sprint"}
    if (
        set(rows) != required
        or any(row["ratio"] > 1.05 for row in rows.values())
        or any(not row["byte_identical"] for row in rows.values())
    ):
        raise SystemExit(f"unexpected Round-160 runtime cases: {rows}")

    aggregate_gain = (1.0 - runtime["aggregate_ratio"]) * 100.0
    section = textwrap.dedent(
        f"""
        {HEADING} — {aggregate_gain:.1f}% faster on the measured batch wall

        The four-ply mobility search repeatedly tested candidate landings
        against the same small predicted blocked-cell sets. Round 160 keeps the
        exact 64-bit cell lists for the outside-grid fallback, while adding one
        collision-free in-grid bitset per ply. Ordinary membership tests become
        a direct word-and-bit probe instead of a linear scan.

        Outer and nested mobility searches retain separate reusable primitive
        workspaces. Resetting clears only words touched by the preceding
        projection. Every bit is derived from the original exact cell list;
        lookup semantics, memo epochs, rollout policy and selected moves are
        unchanged.

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

    anchors = (
        "## Round 158: share immutable legality rasters across auto batches",
        "## Round 157: share immutable progress maps across auto batches",
    )
    for filename in ("AI_DEVELOPMENT.md", "racing-memory.md"):
        path = Path(filename)
        text = path.read_text()
        if HEADING in text:
            continue
        anchor = next((candidate for candidate in anchors if candidate in text), None)
        if anchor is None:
            raise SystemExit(f"{filename}: Round-157/158 anchor missing")
        path.write_text(text.replace(anchor, section + anchor, 1))

    print("Round160Publish: documented direct blocked-cell bitsets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
