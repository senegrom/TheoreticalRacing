#!/usr/bin/env python3
"""Alternating warm runtime guard for the Round 111 speed-nine candidate."""
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
CASES = (("coil", 33), ("interlagos", 26), ("spa", 57), ("zandvoort", 99))


def write_props(path: Path) -> None:
    lines = []
    for line in (ROOT / "tracks" / "bench.properties").read_text().splitlines():
        if re.match(r"^player[1-8]Kind=", line):
            line = line.split("=", 1)[0] + "=AI1"
        lines.append(line)
    path.write_text("\n".join(lines) + "\n")


def timed_run(jar: Path, track: str, seed: int) -> float:
    with tempfile.TemporaryDirectory(prefix="r111-time-") as directory:
        tmp = Path(directory)
        props = tmp / "bench.properties"
        log = tmp / "race.log"
        write_props(props)
        started = time.perf_counter()
        result = subprocess.run(
            [
                "java", "-Djava.awt.headless=true", "-jar", str(jar),
                "--auto", "--track", track, "--props", str(props),
                "--log", str(log), "--seed", str(seed),
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
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    baseline = args.baseline.resolve()
    candidate = args.candidate.resolve()
    rows = []
    for track, seed in CASES:
        timed_run(baseline, track, seed)
        timed_run(candidate, track, seed)
        bt = []
        ct = []
        for index in range(args.repetitions):
            if index % 2:
                bt.append(timed_run(baseline, track, seed))
                ct.append(timed_run(candidate, track, seed))
            else:
                ct.append(timed_run(candidate, track, seed))
                bt.append(timed_run(baseline, track, seed))
        ratio = statistics.median(ct) / statistics.median(bt)
        row = {
            "track": track,
            "seed": seed,
            "ratio": ratio,
            "baseline": bt,
            "candidate": ct,
        }
        rows.append(row)
        if ratio > args.max_ratio:
            raise SystemExit(f"runtime regression: {row}")
    args.out.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
    print(json.dumps(rows, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
