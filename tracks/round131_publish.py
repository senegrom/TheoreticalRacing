#!/usr/bin/env python3
"""Document Round 131 after exact log identity and runtime gates pass."""
from __future__ import annotations

import json
from pathlib import Path
import textwrap

SUMMARY = Path("round131-summary.json")
RUNTIME = Path("round131-runtime.json")
HEADING = "## Round 131: exact point-containment cache"


def percent_gain(ratio: float) -> str:
    return f"{(1.0 - ratio) * 100.0:.1f}%"


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    runtime = json.loads(RUNTIME.read_text())
    if (summary.get("baseline_sha") != "cf709da7288c740e5594cb0418ab8c910ca72051"
            or summary.get("pairs") != 3500
            or summary.get("mismatches") != 0
            or not summary.get("viable")):
        raise SystemExit(f"invalid Round 131 exact summary: {summary}")
    if not runtime.get("viable") or runtime.get("aggregate_ratio", 2.0) > 0.90:
        raise SystemExit(f"invalid Round 131 runtime evidence: {runtime}")

    rows = {row["track"]: row for row in runtime["cases"]}
    required = {"zandvoort", "nurburgring", "monaco", "interlagos", "sprint"}
    if set(rows) != required:
        raise SystemExit(f"unexpected runtime cases: {rows}")

    section = textwrap.dedent(f"""
    {HEADING} — {percent_gain(runtime['aggregate_ratio'])} faster on the measured wall

    Round 130 removed boxed mobility-search overhead and left `Area.contains`
    as the dominant sampled leaf. Round 131 closes that independent geometry
    frontier. The residual exact line scan repeatedly asks whether the same
    rational point lies inside the fixed track: a Zandvoort audit found roughly
    36% duplicate exact point probes within one race.

    The legality path now first reuses the existing conservative RES=4
    sub-raster for points whose complete subcell was already proven interior.
    Unproven points fall back to the exact AWT `Area.contains` verdict, stored in
    an allocation-free open-addressed table keyed by both raw IEEE-754
    coordinate bit patterns. Collisions are resolved by full two-key equality;
    resizing preserves every entry. The cache is cleared whenever track
    geometry is rebuilt, so interactive track changes cannot reuse stale
    verdicts. No geometry approximation or AI-policy rule changed.

    Exact gate: {summary['pairs']} all-AI2 baseline/candidate race pairs across
    all 26 tracks, with **every complete race log byte-identical**. The full
    Java suite, headless smoke, golden corpus, strict AI mirror probe and every
    permanent AI regression pin passed on the JDK 25 candidate and again from
    the production checkout.

    Alternating warm batches against the already-faster Round 130 champion:
    Zandvoort {percent_gain(rows['zandvoort']['ratio'])} faster,
    Nürburgring {percent_gain(rows['nurburgring']['ratio'])} faster,
    Monaco {percent_gain(rows['monaco']['ratio'])} faster,
    Interlagos {percent_gain(rows['interlagos']['ratio'])} faster and
    Sprint {percent_gain(rows['sprint']['ratio'])} faster. Across the five
    weighted medians the candidate is {percent_gain(runtime['aggregate_ratio'])}
    faster. A finish-line bounding-box shortcut was rejected separately after
    measuring slower; only the exact point cache shipped.

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

    print("Round131Publish: documented exact point-containment cache")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
