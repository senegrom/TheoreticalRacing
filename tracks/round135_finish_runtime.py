#!/usr/bin/env python3
"""Dual-order incremental runtime screen for the integer finish kernel."""
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
    ("monaco", 1, 10),
    ("nurburgring", 17, 19),
    ("zandvoort", 31, 33),
    ("interlagos", 45, 47),
    ("sprint", 1, 100),
]


def write_props(path: Path) -> None:
    rows = []
    for line in (ROOT / "tracks" / "bench.properties").read_text().splitlines():
        if re.match(r"^player[1-8]Kind=", line):
            line = line.split("=", 1)[0] + "=AI2"
        rows.append(line)
    path.write_text("\n".join(rows) + "\n")


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
    parser.add_argument("--pairs", type=int, default=4)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for track, start, end in CASES:
        with tempfile.TemporaryDirectory(prefix=f"round135-finish-{track}-") as directory:
            work = Path(directory)
            cache = work / "reach-cache"
            write_props(work / "bench.properties")
            run(args.baseline, track, start, end, "warm-baseline", work, cache)
            run(args.candidate, track, start, end, "warm-candidate", work, cache)
            baseline_times: list[float] = []
            candidate_times: list[float] = []
            pair_ratios: list[float] = []
            for index in range(args.pairs):
                order = [("baseline", args.baseline), ("candidate", args.candidate)]
                if index & 1:
                    order.reverse()
                measured = {}
                for label, jar in order:
                    measured[label] = run(
                        jar, track, start, end, f"pair-{index}-{label}", work, cache)
                bt, bh = measured["baseline"]
                ct, ch = measured["candidate"]
                if bh != ch:
                    bad = [seed for seed in bh if bh[seed] != ch.get(seed)]
                    raise RuntimeError(f"{track} byte mismatch: {bad}")
                baseline_times.append(bt)
                candidate_times.append(ct)
                pair_ratios.append(ct / bt)
        mb = statistics.median(baseline_times)
        mc = statistics.median(candidate_times)
        row = {
            "track": track,
            "start": start,
            "end": end,
            "races_per_run": end - start + 1,
            "baseline_times": baseline_times,
            "candidate_times": candidate_times,
            "pair_ratios": pair_ratios,
            "median_baseline": mb,
            "median_candidate": mc,
            "ratio": mc / mb,
            "byte_identical": True,
        }
        rows.append(row)
        print(json.dumps(row, indent=2), flush=True)
    tb = sum(row["median_baseline"] for row in rows)
    tc = sum(row["median_candidate"] for row in rows)
    output = {
        "pairs_per_case": args.pairs,
        "cases": rows,
        "total_median_baseline": tb,
        "total_median_candidate": tc,
        "aggregate_ratio": tc / tb,
        "screen_threshold": 0.97,
    }
    output["promising"] = output["aggregate_ratio"] <= output["screen_threshold"]
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
