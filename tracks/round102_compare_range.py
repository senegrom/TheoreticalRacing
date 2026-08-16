#!/usr/bin/env python3
"""Compare an AI1 candidate jar with the exact current-AI1 jar over a seed range."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT_RE = re.compile(r"^(\d+) p(\d+) ")


def configure(source: Path, destination: Path) -> None:
    lines = []
    for line in source.read_text().splitlines():
        if re.match(r"^player[1-8]Kind=", line):
            line = line.split("=", 1)[0] + "=AI1"
        lines.append(line)
    destination.write_text("\n".join(lines) + "\n")


def parse_log(path: Path) -> dict:
    moves: dict[int, int] = {}
    finishes: dict[int, int] = {}
    crashes: set[int] = set()
    saw_results = False
    for line in path.read_text().splitlines():
        if line.startswith("# results"):
            saw_results = True
        match = RESULT_RE.match(line)
        if match is None:
            continue
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if "CRASH" in line:
            crashes.add(player)
        elif "FINISH" in line:
            finishes[player] = moves[player]
    if not saw_results:
        raise RuntimeError(f"invalid log: {path}")
    return {"finishes": finishes, "crashes": sorted(crashes)}


def run_column(jar: Path, track: str, start: int, end: int, label: str, tmp: Path) -> float:
    props = tmp / f"{label}.properties"
    configure(ROOT / "tracks" / "bench.properties", props)
    log = tmp / f"{label}-{track}.log"
    started = time.perf_counter()
    result = subprocess.run([
        "java", "-Djava.awt.headless=true", "-jar", str(jar), "--auto",
        "--track", track, "--props", str(props), "--log", str(log),
        "--seed", f"{start}-{end}",
    ], cwd=ROOT, text=True, capture_output=True, timeout=5400)
    elapsed = time.perf_counter() - started
    (tmp / f"{label}-{track}.stdout").write_text(result.stdout)
    (tmp / f"{label}-{track}.stderr").write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(
            f"{label} {track} failed with {result.returncode}: {result.stderr[-2000:]}"
        )
    return elapsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.start < 1 or args.end < args.start:
        raise SystemExit("invalid seed range")

    with tempfile.TemporaryDirectory(prefix=f"r102-{args.track}-") as directory:
        tmp = Path(directory)
        baseline_seconds = run_column(
            args.baseline.resolve(), args.track, args.start, args.end, "baseline", tmp
        )
        candidate_seconds = run_column(
            args.candidate.resolve(), args.track, args.start, args.end, "candidate", tmp
        )
        summary = {
            "track": args.track,
            "seed_start": args.start,
            "seed_end": args.end,
            "pairs": args.end - args.start + 1,
            "identical": 0,
            "faster": 0,
            "slower": 0,
            "safety_gain": 0,
            "safety_regression": 0,
            "redistribution": 0,
            "net_moves": 0,
            "baseline_seconds": baseline_seconds,
            "candidate_seconds": candidate_seconds,
            "runtime_ratio": candidate_seconds / baseline_seconds,
            "events": [],
        }
        for seed in range(args.start, args.end + 1):
            baseline = parse_log(tmp / f"baseline-{args.track}_s{seed}.log")
            candidate = parse_log(tmp / f"candidate-{args.track}_s{seed}.log")
            if candidate == baseline:
                summary["identical"] += 1
                continue
            bf, cf = baseline["finishes"], candidate["finishes"]
            bc, cc = baseline["crashes"], candidate["crashes"]
            bsum, csum = sum(bf.values()), sum(cf.values())
            if len(cf) < len(bf) or len(cc) > len(bc):
                kind = "safety_regression"
            elif len(cf) > len(bf) or len(cc) < len(bc):
                kind = "safety_gain"
            elif csum < bsum:
                kind = "faster"
            elif csum > bsum:
                kind = "slower"
            else:
                kind = "redistribution"
            summary[kind] += 1
            summary["net_moves"] += csum - bsum
            summary["events"].append({
                "seed": seed,
                "classification": kind,
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
    if summary["safety_regression"] or summary["slower"] or summary["redistribution"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
