#!/usr/bin/env python3
"""Exact batched baseline/candidate comparison for one track and seed range."""
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
    return {
        "finishes": finishes,
        "crashes": sorted(crashes),
        "order": [
            player for player, _ in sorted(finishes.items(), key=lambda item: (item[1], item[0]))
        ],
        "sum": sum(finishes.values()),
    }


def run_range(jar: Path, track: str, start: int, end: int, kind: str,
              label: str, work: Path) -> tuple[dict[int, dict[str, object]], float]:
    props = work / f"{label}.properties"
    pattern = work / f"{label}-{track}.log"
    write_props(props, kind)
    env = os.environ.copy()
    env["RACING_REACH_CACHE"] = str(work / "reach-cache")
    started = time.perf_counter()
    result = subprocess.run(
        ["java", "-Djava.awt.headless=true", "-jar", str(jar.resolve()),
         "--auto", "--track", track, "--props", str(props),
         "--log", str(pattern), "--seed", f"{start}-{end}"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=7200,
    )
    elapsed = time.perf_counter() - started
    if result.returncode:
        raise RuntimeError(f"{label} {track} failed: {result.stderr[-3000:]}")
    base = pattern.with_suffix("")
    rows: dict[int, dict[str, object]] = {}
    for seed in range(start, end + 1):
        path = Path(f"{base}_s{seed}{pattern.suffix}")
        if not path.is_file():
            raise FileNotFoundError(path)
        rows[seed] = parse_log(path)
    return rows, elapsed


def classify(baseline: dict[str, object], candidate: dict[str, object]) -> tuple[str, dict[int, int]]:
    if candidate == baseline:
        return "identical", {}
    bf = baseline["finishes"]
    cf = candidate["finishes"]
    bc = baseline["crashes"]
    cc = candidate["crashes"]
    assert isinstance(bf, dict) and isinstance(cf, dict)
    assert isinstance(bc, list) and isinstance(cc, list)
    deltas = {int(p): int(cf[p]) - int(m) for p, m in bf.items() if p in cf}
    if len(cf) < len(bf) or len(cc) > len(bc):
        return "safety_regression", deltas
    if len(cf) > len(bf) or len(cc) < len(bc):
        return "safety_gain", deltas
    if set(cf) != set(bf) or candidate["order"] != baseline["order"]:
        return "redistribution", deltas
    values = list(deltas.values())
    if all(delta <= 0 for delta in values) and any(delta < 0 for delta in values):
        return "pareto_faster", deltas
    if all(delta >= 0 for delta in values) and any(delta > 0 for delta in values):
        return "slower", deltas
    if sum(values) < 0:
        return "aggregate_faster", deltas
    return "redistribution", deltas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--baseline-kind", default="AI1")
    parser.add_argument("--candidate-kind", default="AI1")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix=f"round116-{args.track}-") as directory:
        work = Path(directory)
        baseline, baseline_seconds = run_range(
            args.baseline, args.track, args.start, args.end,
            args.baseline_kind, "baseline", work)
        candidate, candidate_seconds = run_range(
            args.candidate, args.track, args.start, args.end,
            args.candidate_kind, "candidate", work)

    counts = {key: 0 for key in (
        "identical", "pareto_faster", "aggregate_faster", "slower",
        "safety_gain", "safety_regression", "redistribution")}
    events: list[dict[str, object]] = []
    net_moves = 0
    for seed in range(args.start, args.end + 1):
        classification, deltas = classify(baseline[seed], candidate[seed])
        counts[classification] += 1
        net_moves += int(candidate[seed]["sum"]) - int(baseline[seed]["sum"])
        if classification != "identical":
            events.append({
                "seed": seed,
                "classification": classification,
                "deltas": deltas,
                "baseline": baseline[seed],
                "candidate": candidate[seed],
            })
    output = {
        "track": args.track,
        "start": args.start,
        "end": args.end,
        "pairs": args.end - args.start + 1,
        "counts": counts,
        "events": events,
        "net_moves": net_moves,
        "baseline_seconds": baseline_seconds,
        "candidate_seconds": candidate_seconds,
        "runtime_ratio": candidate_seconds / baseline_seconds,
    }
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
