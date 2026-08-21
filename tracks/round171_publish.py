#!/usr/bin/env python3
"""Record the verified Round 171 projected-occupancy optimization."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    summary = json.loads(Path("round171-summary.json").read_text())
    runtime = json.loads(Path("round171-runtime.json").read_text())
    assert summary["pairs"] == 3500 and summary["mismatches"] == 0, summary
    assert summary["byte_identical_tracks"] == 26 and summary["viable"], summary
    assert runtime["viable"] and runtime["aggregate_ratio"] <= 0.98, runtime

    ratio = float(runtime["aggregate_ratio"])
    speedup = (1.0 - ratio) * 100.0
    per_case = ", ".join(
        f"{row['track']} {float(row['ratio']):.4f}x"
        for row in runtime["cases"]
    )
    section = f"""## Round 171: direct projected-occupancy maps

The remaining opponent-world occupancy tests used linear scans through the
projected player rows inside recursive successor scoring and two-round
simulation. Round 171 replaces those scans with exact touched-cell count maps.
Counts retain duplicate-cell semantics, while mover removal and reinsertion
keep the changing simulated board exact without clearing the whole grid.

The promotion gate compared 3,500 paired races across all 26 tracks and found
zero byte differences. Seven-pair alternating timing measured an aggregate
candidate/baseline ratio of {ratio:.6f} ({speedup:.2f}% lower wall time). The
per-case ratios were: {per_case}.

"""

    development = Path("AI_DEVELOPMENT.md")
    text = development.read_text()
    heading = "## Round 171: direct projected-occupancy maps\n"
    if heading not in text:
        anchor = "## Current champion and frontier baseline\n"
        development.write_text(
            text.replace(anchor, section + anchor, 1)
            if anchor in text else section + text
        )

    campaign = Path("racing-memory.md")
    marker = "ROUND 171 (direct projected-occupancy maps):"
    text = campaign.read_text()
    if marker not in text:
        campaign.write_text(
            text.rstrip()
            + "\n\n"
            + marker
            + f" exact touched-cell counts replace repeated linear scans of "
              "projected opponent positions. The 26-track gate was byte-identical "
              f"over {summary['pairs']} races; alternating runtime ratio {ratio:.6f} "
              f"({speedup:.2f}% faster).\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
