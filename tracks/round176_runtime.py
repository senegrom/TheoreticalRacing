#!/usr/bin/env python3
"""Alternating warm runtime guard for Round 176."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time

import round176_compare as compare

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("rand3", 1, 1),
    ("monaco", 1, 5),
    ("lemans", 1, 5),
    ("zandvoort", 31, 35),
    ("sprint", 1, 20),
)
ALLOWED = {"identical", "faster", "safety_gain"}


def run_once(jar: Path, track: str, start: int, end: int, label: str,
             tmp: Path, cache: Path) -> tuple[float, dict[int, dict]]:
    props = tmp / f"{label}.properties"
    compare.configure(props, "AI1")
    pattern = tmp / f"{label}-{track}.log"
    env = os.environ.copy()
    env["RACING_REACH_CACHE"] = str(cache)
    began = time.perf_counter()
    result = subprocess.run(
        ["java", "-Djava.awt.headless=true", "-jar", str(jar.resolve()),
         "--auto", "--track", track, "--props", str(props),
         "--log", str(pattern), "--seed", f"{start}-{end}"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=14400,
    )
    elapsed = time.perf_counter() - began
    if result.returncode:
        raise RuntimeError(f"{label} {track} failed: {result.stderr[-5000:]}")
    logs = {
        seed: compare.parse_log(compare.seed_log(tmp, label, track, seed, start, end))
        for seed in range(start, end + 1)
    }
    return elapsed, logs


def validate_pair(track: str, baseline: dict[int, dict],
                  candidate: dict[int, dict]) -> dict[int, str]:
    classes: dict[int, str] = {}
    for seed, baseline_log in baseline.items():
        classification, _ = compare.classify(candidate[seed], baseline_log)
        if classification not in ALLOWED:
            raise RuntimeError(
                f"{track} seed {seed}: disallowed runtime-pair outcome {classification}"
            )
        classes[seed] = classification
    if track == "rand3" and classes.get(1) != "safety_gain":
        raise RuntimeError(f"rand3 seed 1 rescue missing: {classes}")
    if track != "rand3" and any(value != "identical" for value in classes.values()):
        raise RuntimeError(f"unexpected changed control race on {track}: {classes}")
    return classes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--pairs", type=int, default=5)
    parser.add_argument("--aggregate-limit", type=float, default=1.12)
    parser.add_argument("--case-limit", type=float, default=1.25)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.pairs < 5:
        raise SystemExit("at least five alternating pairs are required")

    rows: list[dict[str, object]] = []
    for track, start, end in CASES:
        with tempfile.TemporaryDirectory(prefix=f"r176-time-{track}-") as directory:
            tmp = Path(directory)
            cache = tmp / "reach-cache"
            run_once(args.baseline, track, start, end, "warm-baseline", tmp, cache)
            run_once(args.candidate, track, start, end, "warm-candidate", tmp, cache)
            baseline_times: list[float] = []
            candidate_times: list[float] = []
            classifications: list[dict[int, str]] = []
            for index in range(args.pairs):
                order = [("baseline", args.baseline), ("candidate", args.candidate)]
                if index & 1:
                    order.reverse()
                measured = {
                    label: run_once(jar, track, start, end,
                                    f"pair-{index}-{label}", tmp, cache)
                    for label, jar in order
                }
                baseline_time, baseline_logs = measured["baseline"]
                candidate_time, candidate_logs = measured["candidate"]
                classifications.append(
                    validate_pair(track, baseline_logs, candidate_logs)
                )
                baseline_times.append(baseline_time)
                candidate_times.append(candidate_time)
        median_baseline = statistics.median(baseline_times)
        median_candidate = statistics.median(candidate_times)
        rows.append({
            "track": track,
            "start": start,
            "end": end,
            "baseline_times": baseline_times,
            "candidate_times": candidate_times,
            "median_baseline": median_baseline,
            "median_candidate": median_candidate,
            "ratio": median_candidate / median_baseline,
            "classifications": classifications,
        })

    total_baseline = sum(float(row["median_baseline"]) for row in rows)
    total_candidate = sum(float(row["median_candidate"]) for row in rows)
    output = {
        "pairs_per_case": args.pairs,
        "cases": rows,
        "total_median_baseline": total_baseline,
        "total_median_candidate": total_candidate,
        "aggregate_ratio": total_candidate / total_baseline,
        "aggregate_limit": args.aggregate_limit,
        "case_limit": args.case_limit,
    }
    output["viable"] = (
        output["aggregate_ratio"] <= args.aggregate_limit
        and all(float(row["ratio"]) <= args.case_limit for row in rows)
    )
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))
    if not output["viable"]:
        raise SystemExit("Round 176 runtime guard failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
