#!/usr/bin/env python3
"""Dual-order exact runtime screen for adaptive cold/warm geometry caches."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("sprint", 1, 150),
    ("monaco", 1, 20),
    ("zandvoort", 31, 40),
    ("nurburgring", 17, 19),
    ("interlagos", 45, 47),
]


def write_props(path: Path) -> None:
    lines: list[str] = []
    for line in (ROOT / "tracks" / "bench.properties").read_text().splitlines():
        if re.match(r"^player[1-8]Kind=", line):
            line = line.split("=", 1)[0] + "=AI2"
        lines.append(line)
    path.write_text("\n".join(lines) + "\n")


def run(
    jar: Path,
    track: str,
    start: int,
    end: int,
    label: str,
    work: Path,
    cache: Path,
) -> tuple[float, dict[int, str]]:
    pattern = work / f"{label}-{track}.log"
    env = os.environ.copy()
    env["RACING_REACH_CACHE"] = str(cache)
    began = time.perf_counter()
    result = subprocess.run(
        [
            "java",
            "-Djava.awt.headless=true",
            "-jar",
            str(jar.resolve()),
            "--auto",
            "--track",
            track,
            "--props",
            str(work / "bench.properties"),
            "--log",
            str(pattern),
            "--seed",
            f"{start}-{end}",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=7200,
    )
    elapsed = time.perf_counter() - began
    if result.returncode:
        raise RuntimeError(f"{label} {track} failed: {result.stderr[-5000:]}")
    stem = pattern.with_suffix("")
    hashes: dict[int, str] = {}
    for seed in range(start, end + 1):
        log = Path(f"{stem}_s{seed}{pattern.suffix}")
        if not log.is_file():
            raise FileNotFoundError(log)
        hashes[seed] = hashlib.sha256(log.read_bytes()).hexdigest()
    return elapsed, hashes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--pairs", type=int, default=5)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    for track, start, end in CASES:
        with tempfile.TemporaryDirectory(prefix=f"round152-{track}-") as directory:
            work = Path(directory)
            cache = work / "reach-cache"
            write_props(work / "bench.properties")

            # Populate the disk cache and warm both JVMs before timing. Every
            # measured invocation then exercises one cache-load race followed
            # by the in-process memo path for the remainder of the seed range.
            run(args.baseline, track, start, end, "warm-baseline", work, cache)
            run(args.candidate, track, start, end, "warm-candidate", work, cache)

            baseline_times: list[float] = []
            candidate_times: list[float] = []
            pair_ratios: list[float] = []
            for index in range(args.pairs):
                order = [("baseline", args.baseline), ("candidate", args.candidate)]
                if index & 1:
                    order.reverse()
                measured = {
                    label: run(
                        jar,
                        track,
                        start,
                        end,
                        f"pair-{index}-{label}",
                        work,
                        cache,
                    )
                    for label, jar in order
                }
                baseline_seconds, baseline_hashes = measured["baseline"]
                candidate_seconds, candidate_hashes = measured["candidate"]
                if baseline_hashes != candidate_hashes:
                    bad = [
                        seed
                        for seed in baseline_hashes
                        if baseline_hashes[seed] != candidate_hashes.get(seed)
                    ]
                    raise RuntimeError(f"{track} byte mismatch: {bad}")
                baseline_times.append(baseline_seconds)
                candidate_times.append(candidate_seconds)
                pair_ratios.append(candidate_seconds / baseline_seconds)

        median_baseline = statistics.median(baseline_times)
        median_candidate = statistics.median(candidate_times)
        row: dict[str, object] = {
            "track": track,
            "start": start,
            "end": end,
            "races_per_run": end - start + 1,
            "baseline_times": baseline_times,
            "candidate_times": candidate_times,
            "pair_ratios": pair_ratios,
            "median_baseline": median_baseline,
            "median_candidate": median_candidate,
            "ratio": median_candidate / median_baseline,
            "byte_identical": True,
        }
        rows.append(row)
        print(json.dumps(row, indent=2), flush=True)

    total_baseline = sum(float(row["median_baseline"]) for row in rows)
    total_candidate = sum(float(row["median_candidate"]) for row in rows)
    output = {
        "pairs_per_case": args.pairs,
        "cases": rows,
        "total_median_baseline": total_baseline,
        "total_median_candidate": total_candidate,
        "aggregate_ratio": total_candidate / total_baseline,
        "screen_threshold": 0.95,
    }
    output["promising"] = output["aggregate_ratio"] <= output["screen_threshold"]
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
