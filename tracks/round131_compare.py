#!/usr/bin/env python3
"""Require byte-identical race logs for a seeded baseline/candidate range."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def write_props(path: Path, kind: str) -> None:
    lines: list[str] = []
    for line in (ROOT / "tracks" / "bench.properties").read_text().splitlines():
        if re.match(r"^player[1-8]Kind=", line):
            line = line.split("=", 1)[0] + "=" + kind
        lines.append(line)
    path.write_text("\n".join(lines) + "\n")


def run_range(jar: Path, track: str, start: int, end: int, kind: str,
              label: str, work: Path, reach_cache: Path) -> tuple[dict[int, Path], float]:
    props = work / f"{label}.properties"
    pattern = work / f"{label}-{track}.log"
    write_props(props, kind)
    env = os.environ.copy()
    env["RACING_REACH_CACHE"] = str(reach_cache)
    started = time.perf_counter()
    result = subprocess.run(
        ["java", "-Djava.awt.headless=true", "-jar", str(jar.resolve()),
         "--auto", "--track", track, "--props", str(props),
         "--log", str(pattern), "--seed", f"{start}-{end}"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=7200,
    )
    elapsed = time.perf_counter() - started
    if result.returncode:
        raise RuntimeError(f"{label} {track} failed: {result.stderr[-4000:]}")
    stem = pattern.with_suffix("")
    rows: dict[int, Path] = {}
    for seed in range(start, end + 1):
        log = Path(f"{stem}_s{seed}{pattern.suffix}")
        if not log.is_file():
            raise FileNotFoundError(log)
        rows[seed] = log
    return rows, elapsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--kind", default="AI2")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.start > args.end:
        raise SystemExit("start must not exceed end")

    with tempfile.TemporaryDirectory(prefix=f"round131-{args.track}-") as directory:
        work = Path(directory)
        reach_cache = work / "reach-cache"
        baseline, baseline_seconds = run_range(
            args.baseline, args.track, args.start, args.end,
            args.kind, "baseline", work, reach_cache)
        candidate, candidate_seconds = run_range(
            args.candidate, args.track, args.start, args.end,
            args.kind, "candidate", work, reach_cache)

    mismatches = [seed for seed in range(args.start, args.end + 1)
                  if baseline[seed].read_bytes() != candidate[seed].read_bytes()]
    output = {
        "track": args.track,
        "start": args.start,
        "end": args.end,
        "pairs": args.end - args.start + 1,
        "identical": len(mismatches) == 0,
        "mismatches": mismatches,
        "baseline_seconds": baseline_seconds,
        "candidate_seconds": candidate_seconds,
        "runtime_ratio": candidate_seconds / baseline_seconds,
    }
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))
    if mismatches:
        raise SystemExit(f"{args.track}: {len(mismatches)} byte-different logs: {mismatches[:20]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
