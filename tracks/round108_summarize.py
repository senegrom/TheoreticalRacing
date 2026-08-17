#!/usr/bin/env python3
"""Merge Round 108 per-track exact comparisons and enforce promotion policy."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

BAD_CLASSES = ("safety_regression", "slower", "redistribution")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("--expected-pairs", type=int, default=3500)
    parser.add_argument("--out", type=Path, default=Path("round108-summary.json"))
    args = parser.parse_args()

    summary: dict[str, object] = {
        "pairs": 0,
        "counts": {},
        "net_moves": 0,
        "events": [],
        "runtime_ratios": {},
    }
    counts: dict[str, int] = summary["counts"]  # type: ignore[assignment]
    events: list[dict[str, object]] = summary["events"]  # type: ignore[assignment]
    ratios: dict[str, float] = summary["runtime_ratios"]  # type: ignore[assignment]

    paths = sorted(args.results.rglob("*.json"))
    if not paths:
        raise SystemExit(f"no result JSON files under {args.results}")
    for path in paths:
        data = json.loads(path.read_text())
        if not {"track", "pairs", "counts", "events"} <= data.keys():
            continue
        summary["pairs"] = int(summary["pairs"]) + int(data["pairs"])
        summary["net_moves"] = int(summary["net_moves"]) + int(data["net_moves"])
        ratios[str(data["track"])] = float(data["runtime_ratio"])
        for key, value in data["counts"].items():
            counts[key] = counts.get(key, 0) + int(value)
        for event in data["events"]:
            events.append({"track": data["track"], **event})

    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))

    bad = sum(counts.get(key, 0) for key in BAD_CLASSES)
    by_case = {(str(event["track"]), int(event["seed"])): event["classification"] for event in events}
    assert summary["pairs"] == args.expected_pairs, summary
    assert bad == 0, summary
    assert counts.get("safety_gain", 0) >= 1, summary
    assert by_case.get(("zandvoort", 115)) == "safety_gain", summary
    assert ("hungaroring", 144) not in by_case, summary
    assert ("lemans", 4) not in by_case, summary
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
