#!/usr/bin/env python3
"""Exact per-seed comparison of two TheoreticalRacing policy jars."""
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


def configure(source: Path, destination: Path, kind: str) -> None:
    lines: list[str] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if re.match(r"^player[1-8]Kind=", line):
            line = line.split("=", 1)[0] + "=" + kind
        lines.append(line)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_log(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise RuntimeError(f"missing race log: {path}")
    moves: dict[int, int] = {}
    finishes: dict[int, int] = {}
    finish_order: list[int] = []
    crashes: set[int] = set()
    total_turns = 0
    saw_results = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# results"):
            saw_results = True
        match = RESULT_RE.match(line)
        if not match:
            continue
        total_turns += 1
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if " CRASH " in line:
            crashes.add(player)
        elif " FINISH " in line:
            finishes[player] = moves[player]
            finish_order.append(player)
    if not saw_results:
        raise RuntimeError(f"incomplete race log: {path}")
    return {
        "finishes": finishes,
        "finish_order": finish_order,
        "crashes": sorted(crashes),
        "total_turns": total_turns,
    }


def run_column(
    jar: Path,
    track: str,
    seed_start: int,
    seed_end: int,
    kind: str,
    tmp: Path,
    label: str,
) -> tuple[float, list[dict[str, object]]]:
    props = tmp / f"{label}.properties"
    configure(ROOT / "tracks" / "bench.properties", props, kind)
    log = tmp / f"{label}-{track}.log"
    command = [
        "java", "-Djava.awt.headless=true", "-jar", str(jar.resolve()),
        "--auto", "--track", track, "--props", str(props), "--log", str(log),
        "--seed", f"{seed_start}-{seed_end}",
    ]
    started = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=7200,
    )
    elapsed = time.perf_counter() - started
    (tmp / f"{label}-{track}.stdout").write_text(result.stdout, encoding="utf-8")
    (tmp / f"{label}-{track}.stderr").write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0 or "Aborting" in result.stdout:
        raise RuntimeError(
            f"{label} {track} failed with {result.returncode}: "
            f"{result.stderr[-3000:]}"
        )
    base, extension = log.with_suffix(""), log.suffix
    parsed = [
        parse_log(Path(f"{base}_s{seed}{extension}"))
        for seed in range(seed_start, seed_end + 1)
    ]
    return elapsed, parsed


def classify(candidate: dict[str, object], baseline: dict[str, object]) -> tuple[str, int]:
    if candidate == baseline:
        return "identical", 0
    cf = candidate["finishes"]
    bf = baseline["finishes"]
    cc = candidate["crashes"]
    bc = baseline["crashes"]
    assert isinstance(cf, dict) and isinstance(bf, dict)
    assert isinstance(cc, list) and isinstance(bc, list)
    csum = sum(int(value) for value in cf.values())
    bsum = sum(int(value) for value in bf.values())
    if len(cf) < len(bf) or len(cc) > len(bc):
        return "safety_regression", csum - bsum
    if len(cf) > len(bf) or len(cc) < len(bc):
        return "safety_gain", csum - bsum
    if csum < bsum:
        return "faster", csum - bsum
    if csum > bsum:
        return "slower", csum - bsum
    return "redistribution", 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--kind", choices=("AI1", "AI2"), default="AI1")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.start < 1 or args.end < args.start:
        parser.error("invalid seed range")

    with tempfile.TemporaryDirectory(prefix=f"r103-{args.track}-") as directory:
        tmp = Path(directory)
        baseline_seconds, baseline = run_column(
            args.baseline, args.track, args.start, args.end, args.kind, tmp, "baseline"
        )
        candidate_seconds, candidate = run_column(
            args.candidate, args.track, args.start, args.end, args.kind, tmp, "candidate"
        )

    counts = {
        "identical": 0,
        "faster": 0,
        "safety_gain": 0,
        "slower": 0,
        "safety_regression": 0,
        "redistribution": 0,
    }
    events: list[dict[str, object]] = []
    net_moves = 0
    baseline_turns = 0
    candidate_turns = 0
    for offset, (before, after) in enumerate(zip(baseline, candidate, strict=True)):
        seed = args.start + offset
        classification, delta = classify(after, before)
        counts[classification] += 1
        net_moves += delta
        baseline_turns += int(before["total_turns"])
        candidate_turns += int(after["total_turns"])
        if classification != "identical":
            events.append({
                "seed": seed,
                "classification": classification,
                "delta": delta,
                "baseline": before,
                "candidate": after,
            })

    result = {
        "track": args.track,
        "kind": args.kind,
        "seed_start": args.start,
        "seed_end": args.end,
        "pairs": args.end - args.start + 1,
        "counts": counts,
        "net_moves": net_moves,
        "events": events,
        "baseline_seconds": baseline_seconds,
        "candidate_seconds": candidate_seconds,
        "runtime_ratio": candidate_seconds / baseline_seconds,
        "baseline_seconds_per_turn": baseline_seconds / max(1, baseline_turns),
        "candidate_seconds_per_turn": candidate_seconds / max(1, candidate_turns),
        "runtime_per_turn_ratio": (
            candidate_seconds / max(1, candidate_turns)
        ) / (baseline_seconds / max(1, baseline_turns)),
    }
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    bad = counts["slower"] + counts["safety_regression"] + counts["redistribution"]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
