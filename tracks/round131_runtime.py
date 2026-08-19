#!/usr/bin/env python3
"""Alternating warm runtime gate for the Round-131 point-containment cache."""
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
    ("zandvoort", 31, 33, 0.95),
    ("nurburgring", 17, 19, 0.80),
    ("monaco", 14, 16, 0.95),
    ("interlagos", 45, 47, 1.05),
    ("sprint", 1, 10, 1.05),
]


def write_props(path: Path) -> None:
    lines: list[str] = []
    for line in (ROOT / "tracks" / "bench.properties").read_text().splitlines():
        if re.match(r"^player[1-8]Kind=", line):
            line = line.split("=", 1)[0] + "=AI2"
        lines.append(line)
    path.write_text("\n".join(lines) + "\n")


def run(jar: Path, track: str, start: int, end: int, label: str,
        work: Path, cache: Path) -> tuple[float, dict[int, str]]:
    props = work / "bench.properties"
    pattern = work / f"{label}-{track}.log"
    env = os.environ.copy()
    env["RACING_REACH_CACHE"] = str(cache)
    began = time.perf_counter()
    result = subprocess.run([
        "java", "-Djava.awt.headless=true", "-jar", str(jar.resolve()),
        "--auto", "--track", track, "--props", str(props),
        "--log", str(pattern), "--seed", f"{start}-{end}",
    ], cwd=ROOT, env=env, text=True, capture_output=True, timeout=7200)
    elapsed = time.perf_counter() - began
    if result.returncode:
        raise RuntimeError(f"{label} {track} failed: {result.stderr[-4000:]}")
    stem = pattern.with_suffix("")
    hashes: dict[int, str] = {}
    for seed in range(start, end + 1):
        log = Path(f"{stem}_s{seed}{pattern.suffix}")
        if not log.is_file():
            raise FileNotFoundError(log)
        hashes[seed] = hashlib.sha256(log.read_bytes()).hexdigest()
    return elapsed, hashes


def measure_case(baseline: Path, candidate: Path, track: str, start: int,
                 end: int, limit: float, pairs: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix=f"round131-runtime-{track}-") as directory:
        work = Path(directory)
        cache = work / "reach-cache"
        write_props(work / "bench.properties")
        run(baseline, track, start, end, "warm-baseline", work, cache)
        run(candidate, track, start, end, "warm-candidate", work, cache)
        baseline_times: list[float] = []
        candidate_times: list[float] = []
        pair_ratios: list[float] = []
        for index in range(pairs):
            order = [("baseline", baseline), ("candidate", candidate)]
            if index & 1:
                order.reverse()
            measured: dict[str, tuple[float, dict[int, str]]] = {}
            for label, jar in order:
                measured[label] = run(
                    jar, track, start, end, f"pair-{index}-{label}", work, cache)
            baseline_time, baseline_hashes = measured["baseline"]
            candidate_time, candidate_hashes = measured["candidate"]
            if baseline_hashes != candidate_hashes:
                mismatches = [seed for seed in baseline_hashes
                              if baseline_hashes[seed] != candidate_hashes.get(seed)]
                raise RuntimeError(f"{track} log mismatch: {mismatches}")
            baseline_times.append(baseline_time)
            candidate_times.append(candidate_time)
            pair_ratios.append(candidate_time / baseline_time)
    median_baseline = statistics.median(baseline_times)
    median_candidate = statistics.median(candidate_times)
    ratio = median_candidate / median_baseline
    row: dict[str, object] = {
        "track": track,
        "start": start,
        "end": end,
        "races_per_run": end - start + 1,
        "limit": limit,
        "baseline_times": baseline_times,
        "candidate_times": candidate_times,
        "pair_ratios": pair_ratios,
        "median_baseline": median_baseline,
        "median_candidate": median_candidate,
        "ratio": ratio,
        "byte_identical": True,
    }
    if ratio > limit:
        raise RuntimeError(f"runtime limit exceeded: {row}")
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--pairs", type=int, default=3)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for case in CASES:
        row = measure_case(args.baseline, args.candidate, *case, args.pairs)
        rows.append(row)
        print(json.dumps(row, indent=2), flush=True)
    total_baseline = sum(float(row["median_baseline"]) for row in rows)
    total_candidate = sum(float(row["median_candidate"]) for row in rows)
    aggregate_ratio = total_candidate / total_baseline
    output = {
        "pairs_per_case": args.pairs,
        "cases": rows,
        "total_median_baseline": total_baseline,
        "total_median_candidate": total_candidate,
        "aggregate_ratio": aggregate_ratio,
        "aggregate_limit": 0.90,
        "viable": aggregate_ratio <= 0.90,
    }
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))
    if not output["viable"]:
        raise SystemExit(f"aggregate runtime limit exceeded: {aggregate_ratio:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
