#!/usr/bin/env python3
"""Compare one exact race between a baseline and a Round 115 candidate jar."""
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
MOVE_RE = re.compile(r"^(\d+) p(\d+) ")


def write_props(path: Path, kind: str) -> None:
    lines: list[str] = []
    for line in (ROOT / "tracks" / "bench.properties").read_text().splitlines():
        if re.match(r"^player[1-8]Kind=", line):
            line = line.split("=", 1)[0] + "=" + kind
        lines.append(line)
    path.write_text("\n".join(lines) + "\n")


def parse_log(path: Path) -> dict[str, object]:
    moves: dict[int, int] = {}
    finishes: dict[int, int] = {}
    crashes: set[int] = set()
    saw_results = False
    for line in path.read_text().splitlines():
        if line.startswith("# results"):
            saw_results = True
        match = MOVE_RE.match(line)
        if match is None:
            continue
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if "CRASH" in line:
            crashes.add(player)
        elif "FINISH" in line:
            finishes[player] = moves[player]
    if not saw_results:
        raise RuntimeError(f"invalid race log: {path}")
    order = [
        player for player, _ in sorted(finishes.items(), key=lambda item: (item[1], item[0]))
    ]
    return {
        "finishes": finishes,
        "crashes": sorted(crashes),
        "order": order,
        "sum": sum(finishes.values()),
    }


def run(jar: Path, track: str, seed: int, kind: str, label: str, work: Path) -> tuple[dict[str, object], float]:
    props = work / f"{label}.properties"
    log = work / f"{label}.log"
    write_props(props, kind)
    env = os.environ.copy()
    env["RACING_REACH_CACHE"] = str(work / "reach-cache")
    started = time.perf_counter()
    result = subprocess.run(
        [
            "java", "-Djava.awt.headless=true", "-jar", str(jar.resolve()),
            "--auto", "--track", track, "--props", str(props),
            "--log", str(log), "--seed", str(seed),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=1800,
    )
    elapsed = time.perf_counter() - started
    (work / f"{label}.stdout").write_text(result.stdout)
    (work / f"{label}.stderr").write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(
            f"{label} {track} seed {seed} exited {result.returncode}: "
            f"{result.stderr[-3000:]}"
        )
    return parse_log(log), elapsed


def classify(baseline: dict[str, object], candidate: dict[str, object]) -> tuple[str, dict[int, int]]:
    if candidate == baseline:
        return "identical", {}
    baseline_finishes = baseline["finishes"]
    candidate_finishes = candidate["finishes"]
    baseline_crashes = baseline["crashes"]
    candidate_crashes = candidate["crashes"]
    assert isinstance(baseline_finishes, dict) and isinstance(candidate_finishes, dict)
    assert isinstance(baseline_crashes, list) and isinstance(candidate_crashes, list)
    deltas = {
        int(player): int(candidate_finishes[player]) - int(moves)
        for player, moves in baseline_finishes.items()
        if player in candidate_finishes
    }
    if len(candidate_finishes) < len(baseline_finishes) or len(candidate_crashes) > len(baseline_crashes):
        return "safety_regression", deltas
    if len(candidate_finishes) > len(baseline_finishes) or len(candidate_crashes) < len(baseline_crashes):
        return "safety_gain", deltas
    if set(candidate_finishes) != set(baseline_finishes) or candidate["order"] != baseline["order"]:
        return "redistribution", deltas
    values = list(deltas.values())
    if all(delta <= 0 for delta in values) and any(delta < 0 for delta in values):
        return "pareto_faster", deltas
    if all(delta >= 0 for delta in values) and any(delta > 0 for delta in values):
        return "slower", deltas
    return "redistribution", deltas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--baseline-kind", default="AI1")
    parser.add_argument("--candidate-kind", default="AI1")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix=f"round115-{args.track}-{args.seed}-") as directory:
        work = Path(directory)
        baseline, baseline_seconds = run(
            args.baseline, args.track, args.seed, args.baseline_kind, "baseline", work
        )
        candidate, candidate_seconds = run(
            args.candidate, args.track, args.seed, args.candidate_kind, "candidate", work
        )
    classification, deltas = classify(baseline, candidate)
    output = {
        "track": args.track,
        "seed": args.seed,
        "baseline_kind": args.baseline_kind,
        "candidate_kind": args.candidate_kind,
        "classification": classification,
        "deltas": deltas,
        "baseline_seconds": baseline_seconds,
        "candidate_seconds": candidate_seconds,
        "runtime_ratio": candidate_seconds / baseline_seconds,
        "baseline": baseline,
        "candidate": candidate,
    }
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
