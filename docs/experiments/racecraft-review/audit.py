#!/usr/bin/env python3
"""Summarize proposed versus returned actions without rerunning a policy.
Supply one race per file, not concatenated batch races or independent replays.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


def summarize(paths: list[Path]) -> dict:
    counts: Counter = Counter()
    overrides: Counter = Counter()
    models: Counter = Counter()
    for path in paths:
        seen = set()
        with path.open(encoding="utf-8-sig") as source:
            for line_number, line in enumerate(source, 1):
                prefix, _, payload = line.partition(" ")
                if prefix not in ("RACECRAFT_REVIEW", "RACECRAFT_DUEL"):
                    continue
                try:
                    row = json.loads(payload)
                    if not isinstance(row, dict) or row.get("schema") != 1:
                        raise ValueError("unsupported audit schema")
                    if prefix == "RACECRAFT_DUEL":
                        for key in ("nodes", "cacheHits"):
                            if type(row[key]) is not int or row[key] < 0:
                                raise ValueError("invalid duel counter: " + key)
                        for key in ("exhausted", "retainedProof", "completedProof"):
                            if type(row[key]) is not bool:
                                raise ValueError("invalid duel flag: " + key)
                        counts["duel_searches"] += 1
                        counts["duel_nodes"] += row["nodes"]
                        counts["duel_cache_hits"] += row["cacheHits"]
                        counts["duel_budget_exhaustions"] += row["exhausted"]
                        counts["duel_retained_proofs"] += row["retainedProof"]
                        counts["duel_discarded_proofs"] += row["exhausted"] and row["completedProof"] and not row["retainedProof"]
                        continue
                    key = (row["turn"], row["player"])
                    if key in seen:
                        raise ValueError("duplicate root decision; supply one race per file")
                    seen.add(key)
                    counts["decisions"] += 1
                    stages = row["stages"]
                    selected = row["selected"]
                    by_stage = {entry["stage"]: entry["action"] for entry in stages}
                    for before, after in zip(stages, stages[1:]):
                        if before["action"] != after["action"]:
                            overrides[after["stage"]] += 1
                    if stages and selected != stages[-1]["action"]:
                        overrides["later-guards/final"] += 1
                    if "chooser" in by_stage:
                        counts["chooser_decisions"] += 1
                        counts["chooser_changes_from_scorer"] += by_stage["chooser"] != by_stage["scorer"]
                        counts["chooser_overridden_before_execution"] += selected != by_stage["chooser"]
                        counts["executed_changes_from_scorer"] += selected != by_stage["scorer"]
                    else:
                        counts["no_chooser_decisions"] += 1
                    for candidate in row["candidates"]:
                        models[candidate["model"]] += 1
                except (ValueError, TypeError, KeyError, AttributeError) as exc:
                    raise ValueError(f"{path}:{line_number}: {exc}") from exc
    if not counts["decisions"]:
        raise ValueError("no real-decision audit records found")
    return {"schema": 1, "files": len(paths), "counts": dict(sorted(counts.items())),
            "stage_changes": dict(sorted(overrides.items())),
            "forecast_evaluations": dict(sorted(models.items())),
            "interpretation": "diagnostic counters, not finishing-place or performance evidence"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", type=Path, nargs="+")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(summarize(args.logs), indent=2))
    except (OSError, ValueError) as exc:
        print(f"audit: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
