#!/usr/bin/env python3
"""Document Round 134 after exact identity and dual-order runtime gates pass."""
# Relaunched after the shared fast-funnel and vmax-deep promotions advanced master.
from __future__ import annotations

import json
from pathlib import Path
import re
import textwrap

SUMMARY = Path("round134-summary.json")
RUNTIME = Path("round134-runtime.json")
BASE_SHA = Path("round134-base-sha.txt")
HEADING = "## Round 134: exact point-containment cache"


def percent_gain(ratio: float) -> str:
    return f"{(1.0 - ratio) * 100.0:.1f}%"


def comparison(ratio: float) -> str:
    delta = (1.0 - ratio) * 100.0
    if delta >= 0:
        return f"{delta:.1f}% faster"
    return f"{-delta:.1f}% slower"


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    runtime = json.loads(RUNTIME.read_text())
    base_sha = BASE_SHA.read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", base_sha):
        raise SystemExit(f"invalid Round 134 parent SHA: {base_sha!r}")
    if (summary.get("baseline_sha") != base_sha
            or summary.get("pairs") != 3500
            or summary.get("mismatches") != 0
            or not summary.get("viable")):
        raise SystemExit(f"invalid Round 134 exact summary: {summary}")
    if not runtime.get("viable") or runtime.get("aggregate_ratio", 2.0) > 0.95:
        raise SystemExit(f"invalid Round 134 runtime evidence: {runtime}")

    rows = {row["track"]: row for row in runtime["cases"]}
    required = {"zandvoort", "nurburgring", "monaco", "interlagos", "sprint"}
    if set(rows) != required:
        raise SystemExit(f"unexpected runtime cases: {rows}")

    section = textwrap.dedent(f"""
    {HEADING} — {percent_gain(runtime['aggregate_ratio'])} faster on the measured wall

    Round 130 removed boxed mobility-search overhead and left `Area.contains`
    as the dominant sampled leaf. Round 134 closes that independent geometry
    frontier. The residual exact line scan repeatedly asks whether the same
    rational point lies inside the fixed track; the cache stores only the
    unchanged exact AWT verdict.

    The legality path first reuses the existing conservative RES=4 sub-raster
    for points whose complete subcell was already proven interior. Unproven
    points fall back to `Area.contains`, with the result stored in an
    allocation-free open-addressed table keyed by both raw IEEE-754 coordinate
    bit patterns. Collisions require full two-key equality, resizing preserves
    every entry, and the table is cleared whenever track geometry is rebuilt.
    No geometry approximation or AI-policy rule changed.

    Exact gate: {summary['pairs']} all-AI2 baseline/candidate race pairs across
    all 26 tracks, with **every complete race log byte-identical**. The full
    Java suite, headless smoke, golden corpus, homogeneous AI probe, tooling
    tests and every permanent AI regression pin passed on the JDK 25 candidate
    and again from the production checkout.

    Four-pair dual-order warm batches against the current champion measured:
    Zandvoort {comparison(rows['zandvoort']['ratio'])},
    Nürburgring {comparison(rows['nurburgring']['ratio'])},
    Monaco {comparison(rows['monaco']['ratio'])},
    Interlagos {comparison(rows['interlagos']['ratio'])} and
    Sprint {comparison(rows['sprint']['ratio'])}. Across the five weighted
    medians the candidate is {percent_gain(runtime['aggregate_ratio'])}
    faster. Promotion required at least a five-percent aggregate win and no
    measured case more than five percent slower.

    """)

    development = Path("AI_DEVELOPMENT.md")
    text = development.read_text()
    if HEADING not in text:
        anchor = "## Round 129 promoted: measured frontier pace for both driver kinds\n"
        if anchor not in text:
            raise SystemExit("AI_DEVELOPMENT Round-129 anchor missing")
        development.write_text(text.replace(anchor, section + anchor, 1))

    memory = Path("racing-memory.md")
    text = memory.read_text()
    if HEADING not in text:
        anchor = "## Round 129 promoted: measured frontier pace for both driver kinds\n"
        if anchor not in text:
            raise SystemExit("racing-memory Round-129 anchor missing")
        memory.write_text(text.replace(anchor, section + anchor, 1))

    print("Round134Publish: documented exact point-containment cache")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
