#!/usr/bin/env python3
"""Alternating warm-cache runtime guard for the Round 115 candidate."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
CASES = (("coil", 1), ("spa", 12), ("silverstone", 78))


def write_props(path: Path) -> None:
    lines: list[str] = []
    for line in (ROOT / "tracks" / "bench.properties").read_text().splitlines():
        if re.match(r"^player[1-8]Kind=", line):
            line = line.split("=", 1)[0] + "=AI1"
        lines.append(line)
    path.write_text("\n".join(lines) + "\n")


def timed_run(jar: Path, track: str, seed: int, work: Path, serial: int) -> float:
    log = work / f"race-{serial}.log"
    env = os.environ.copy()
    env["RACING_REACH_CACHE"] = str(work / "reach-cache")
    started = time.perf_counter()
    result = subprocess.run(
        [
            "java", "-Djava.awt.headless=true", "-jar", str(jar.resolve()),
            "--auto", "--track", track, "--props", str(work / "bench.properties"),
            "--log", str(log), "--seed", str(seed),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=1800,
    )
    elapsed = time.perf_counter() - started
    if result.returncode:
        raise RuntimeError(f"{jar.name} {track} failed: {result.stderr[-3000:]}")
    return elapsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--max-ratio", type=float, default=1.35)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.repetitions < 3:
        raise SystemExit("at least three repetitions are required")

    rows: list[dict[str, object]] = []
    serial = 0
    for track, seed in CASES:
        with tempfile.TemporaryDirectory(prefix=f"round115-runtime-{track}-") as directory:
            work = Path(directory)
            write_props(work / "bench.properties")
            serial += 1
            timed_run(args.baseline, track, seed, work, serial)
            serial += 1
            timed_run(args.candidate, track, seed, work, serial)
            baseline_times: list[float] = []
            candidate_times: list[float] = []
            for index in range(args.repetitions):
                if index % 2:
                    serial += 1
                    baseline_times.append(timed_run(args.baseline, track, seed, work, serial))
                    serial += 1
                    candidate_times.append(timed_run(args.candidate, track, seed, work, serial))
                else:
                    serial += 1
                    candidate_times.append(timed_run(args.candidate, track, seed, work, serial))
                    serial += 1
                    baseline_times.append(timed_run(args.baseline, track, seed, work, serial))
        ratio = statistics.median(candidate_times) / statistics.median(baseline_times)
        row: dict[str, object] = {
            "track": track,
            "seed": seed,
            "ratio": ratio,
            "baseline": baseline_times,
            "candidate": candidate_times,
        }
        rows.append(row)
        if ratio > args.max_ratio:
            raise SystemExit(f"runtime regression: {row}")

    args.out.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
    print(json.dumps(rows, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
