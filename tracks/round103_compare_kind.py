#!/usr/bin/env python3
"""Compare one agent kind between an exact baseline and candidate jar."""
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "round103_exact", ROOT / "tracks" / "round101_compare_exact.py"
)
EXACT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(EXACT)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--kind", choices=("AI1", "AI2"), required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix=f"r103-{args.kind}-{args.track}-") as directory:
        tmp = Path(directory)
        EXACT.run_column(args.baseline.resolve(), args.track, args.end, args.kind, tmp)
        for path in tmp.glob(f"{args.kind}-{args.track}_s*.log"):
            path.rename(tmp / path.name.replace(f"{args.kind}-", "baseline-", 1))
        EXACT.run_column(args.candidate.resolve(), args.track, args.end, args.kind, tmp)

        summary = {
            "track": args.track,
            "kind": args.kind,
            "pairs": args.end,
            "identical": 0,
            "faster": 0,
            "slower": 0,
            "safety_gain": 0,
            "safety_regression": 0,
            "redistribution": 0,
            "net_moves": 0,
            "events": [],
        }
        for seed in range(1, args.end + 1):
            baseline = EXACT.parse_log(tmp / f"baseline-{args.track}_s{seed}.log")
            candidate = EXACT.parse_log(tmp / f"{args.kind}-{args.track}_s{seed}.log")
            if candidate == baseline:
                summary["identical"] += 1
                continue
            bf, cf = baseline["finishes"], candidate["finishes"]
            bc, cc = baseline["crashes"], candidate["crashes"]
            bsum, csum = sum(bf.values()), sum(cf.values())
            if len(cf) < len(bf) or len(cc) > len(bc):
                classification = "safety_regression"
            elif len(cf) > len(bf) or len(cc) < len(bc):
                classification = "safety_gain"
            elif csum < bsum:
                classification = "faster"
            elif csum > bsum:
                classification = "slower"
            else:
                classification = "redistribution"
            summary[classification] += 1
            summary["net_moves"] += csum - bsum
            summary["events"].append({
                "seed": seed,
                "classification": classification,
                "delta": csum - bsum,
                "baseline_finishers": len(bf),
                "candidate_finishers": len(cf),
                "baseline_crashes": len(bc),
                "candidate_crashes": len(cc),
                "baseline_moves": bsum,
                "candidate_moves": csum,
                "baseline_by_player": bf,
                "candidate_by_player": cf,
            })

    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["slower"] or summary["safety_regression"] or summary["redistribution"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
