#!/usr/bin/env python3
"""Compare two AI1 jars exactly for one deterministic track/seed interval."""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT_RE = re.compile(r"^(\d+) p(\d+) ")


def configure(destination: Path) -> None:
    lines = []
    for line in (ROOT / "tracks" / "bench.properties").read_text().splitlines():
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
        if not match:
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


def run_column(jar: Path, track: str, start: int, end: int, tag: str, tmp: Path) -> float:
    properties = tmp / f"{tag}.properties"
    configure(properties)
    log = tmp / f"{tag}-{track}.log"
    started = time.perf_counter()
    result = subprocess.run(
        [
            "java", "-Djava.awt.headless=true", "-jar", str(jar), "--auto",
            "--track", track, "--props", str(properties), "--log", str(log),
            "--seed", f"{start}-{end}",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=3600,
    )
    elapsed = time.perf_counter() - started
    (tmp / f"{tag}.stdout").write_text(result.stdout)
    (tmp / f"{tag}.stderr").write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(f"{tag} {track} failed: {result.stderr[-2000:]}")
    return elapsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--seed-end", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix=f"r101-{args.track}-") as directory:
        tmp = Path(directory)
        baseline_seconds = run_column(
            args.baseline.resolve(), args.track, args.seed_start, args.seed_end, "baseline", tmp
        )
        candidate_seconds = run_column(
            args.candidate.resolve(), args.track, args.seed_start, args.seed_end, "candidate", tmp
        )
        summary = {
            "track": args.track,
            "seed_start": args.seed_start,
            "seed_end": args.seed_end,
            "pairs": args.seed_end - args.seed_start + 1,
            "identical": 0,
            "faster": 0,
            "slower": 0,
            "safety_gain": 0,
            "safety_regression": 0,
            "redistribution": 0,
            "net_moves": 0,
            "baseline_seconds": baseline_seconds,
            "candidate_seconds": candidate_seconds,
            "events": [],
        }
        for seed in range(args.seed_start, args.seed_end + 1):
            baseline = parse_log(tmp / f"baseline-{args.track}_s{seed}.log")
            candidate = parse_log(tmp / f"candidate-{args.track}_s{seed}.log")
            if candidate == baseline:
                summary["identical"] += 1
                continue
            bf, cf = baseline["finishes"], candidate["finishes"]
            bc, cc = baseline["crashes"], candidate["crashes"]
            baseline_moves, candidate_moves = sum(bf.values()), sum(cf.values())
            event = {
                "seed": seed,
                "baseline_finishers": len(bf),
                "candidate_finishers": len(cf),
                "baseline_crashes": len(bc),
                "candidate_crashes": len(cc),
                "baseline_moves": baseline_moves,
                "candidate_moves": candidate_moves,
                "delta": candidate_moves - baseline_moves,
                "baseline_by_player": bf,
                "candidate_by_player": cf,
            }
            if len(cf) < len(bf) or len(cc) > len(bc):
                classification = "safety_regression"
            elif len(cf) > len(bf) or len(cc) < len(bc):
                classification = "safety_gain"
            elif candidate_moves < baseline_moves:
                classification = "faster"
            elif candidate_moves > baseline_moves:
                classification = "slower"
            else:
                classification = "redistribution"
            event["classification"] = classification
            summary[classification] += 1
            summary["net_moves"] += candidate_moves - baseline_moves
            summary["events"].append(event)

    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
