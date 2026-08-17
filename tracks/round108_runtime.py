#!/usr/bin/env python3
"""Alternating warm runtime guard for a Round 108 baseline/candidate pair."""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = (("zandvoort", 115), ("lemans", 4), ("circle", 10))


def write_props(path: Path) -> None:
    source = ROOT / "tracks" / "bench.properties"
    lines: list[str] = []
    for line in source.read_text().splitlines():
        if re.match(r"^player[1-8]Kind=", line):
            line = line.split("=", 1)[0] + "=AI1"
        lines.append(line)
    path.write_text("\n".join(lines) + "\n")


def timed_run(jar: Path, track: str, seed: int) -> float:
    with tempfile.TemporaryDirectory(prefix="r108-time-") as directory:
        tmp = Path(directory)
        props = tmp / "bench.properties"
        log = tmp / "race.log"
        write_props(props)
        started = time.perf_counter()
        result = subprocess.run(
            [
                "java",
                "-Djava.awt.headless=true",
                "-jar",
                str(jar),
                "--auto",
                "--track",
                track,
                "--props",
                str(props),
                "--log",
                str(log),
                "--seed",
                str(seed),
            ],
            cwd=ROOT,
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
    parser.add_argument("--max-ratio", type=float, default=1.50)
    parser.add_argument("--out", type=Path, default=Path("round108-runtime.json"))
    args = parser.parse_args()
    baseline = args.baseline.resolve()
    candidate = args.candidate.resolve()
    if args.repetitions < 3:
        raise SystemExit("at least three repetitions are required")

    rows: list[dict[str, object]] = []
    for track, seed in CASES:
        timed_run(baseline, track, seed)
        timed_run(candidate, track, seed)
        baseline_times: list[float] = []
        candidate_times: list[float] = []
        for index in range(args.repetitions):
            if index % 2:
                baseline_times.append(timed_run(baseline, track, seed))
                candidate_times.append(timed_run(candidate, track, seed))
            else:
                candidate_times.append(timed_run(candidate, track, seed))
                baseline_times.append(timed_run(baseline, track, seed))
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
