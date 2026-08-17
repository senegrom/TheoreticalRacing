#!/usr/bin/env python3
"""Exact per-seed comparison of a Round 106 AI1 jar against Round 105."""
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
    text = (ROOT / "tracks" / "bench.properties").read_text()
    text = re.sub(r"(?m)^(player[1-8]Kind=).*$", r"\1AI1", text)
    text = re.sub(r"(?m)^nPlayers=\d+$", "nPlayers=8", text)
    destination.write_text(text)


def parse_log(path: Path) -> dict:
    moves: dict[int, int] = {}
    finishes: dict[int, int] = {}
    crashes: list[int] = []
    order: list[int] = []
    saw_results = False
    for line in path.read_text().splitlines():
        if line.startswith("# results"):
            saw_results = True
        match = RESULT_RE.match(line)
        if not match:
            continue
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if " CRASH " in line:
            crashes.append(player)
        elif " FINISH " in line:
            finishes[player] = moves[player]
            order.append(player)
    if not saw_results:
        raise RuntimeError(f"incomplete race log: {path}")
    return {"finishes": finishes, "crashes": sorted(crashes), "order": order}


def run_column(jar: Path, label: str, track: str, start: int, end: int, tmp: Path) -> float:
    props = tmp / f"{label}.properties"
    configure(props)
    log = tmp / f"{label}-{track}.log"
    command = [
        "java", "-Djava.awt.headless=true", "-jar", str(jar.resolve()),
        "--auto", "--track", track, "--props", str(props),
        "--log", str(log), "--seed", f"{start}-{end}",
    ]
    started = time.perf_counter()
    result = subprocess.run(
        command, cwd=ROOT, text=True, capture_output=True,
        timeout=max(900, 60 * (end - start + 1)),
    )
    elapsed = time.perf_counter() - started
    (tmp / f"{label}.stdout").write_text(result.stdout)
    (tmp / f"{label}.stderr").write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(
            f"{label} {track} failed with {result.returncode}: {result.stderr[-2000:]}"
        )
    return elapsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix=f"r106-{args.track}-") as directory:
        tmp = Path(directory)
        baseline_seconds = run_column(
            args.baseline, "baseline", args.track, args.start, args.end, tmp
        )
        candidate_seconds = run_column(
            args.candidate, "candidate", args.track, args.start, args.end, tmp
        )
        summary = {
            "track": args.track,
            "start": args.start,
            "end": args.end,
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
            baseline_finishers = baseline["finishes"]
            candidate_finishers = candidate["finishes"]
            baseline_crashes = baseline["crashes"]
            candidate_crashes = candidate["crashes"]
            baseline_moves = sum(baseline_finishers.values())
            candidate_moves = sum(candidate_finishers.values())
            if (len(candidate_finishers) < len(baseline_finishers)
                    or len(candidate_crashes) > len(baseline_crashes)):
                classification = "safety_regression"
            elif (len(candidate_finishers) > len(baseline_finishers)
                    or len(candidate_crashes) < len(baseline_crashes)):
                classification = "safety_gain"
            elif candidate_moves < baseline_moves:
                classification = "faster"
            elif candidate_moves > baseline_moves:
                classification = "slower"
            else:
                classification = "redistribution"
            summary[classification] += 1
            summary["net_moves"] += candidate_moves - baseline_moves
            summary["events"].append({
                "seed": seed,
                "classification": classification,
                "baseline": baseline,
                "candidate": candidate,
                "baseline_moves": baseline_moves,
                "candidate_moves": candidate_moves,
                "delta": candidate_moves - baseline_moves,
            })

    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["slower"] or summary["safety_regression"] or summary["redistribution"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
