#!/usr/bin/env python3
"""Strict per-seed outcome and byte comparison for Round 176."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
MOVE_RE = re.compile(r"^\d+ p(\d+) ")
PLACE_RE = re.compile(r"FINISH place=(\d+)")


def configure(destination: Path, kind: str) -> None:
    lines: list[str] = []
    for line in (ROOT / "tracks" / "bench.properties").read_text().splitlines():
        if re.match(r"^player[1-8]Kind=", line):
            line = line.split("=", 1)[0] + "=" + kind
        lines.append(line)
    destination.write_text("\n".join(lines) + "\n")


def parse_log(path: Path) -> dict:
    raw = path.read_bytes()
    moves: dict[int, int] = {}
    finishes: dict[int, int] = {}
    places: dict[int, int] = {}
    crashes: set[int] = set()
    saw_results = False
    for line in raw.decode("utf-8").splitlines():
        if line.startswith("# results"):
            saw_results = True
        match = MOVE_RE.match(line)
        if not match:
            continue
        player = int(match.group(1))
        moves[player] = moves.get(player, 0) + 1
        if "CRASH" in line:
            crashes.add(player)
        elif "FINISH" in line:
            finishes[player] = moves[player]
            place = PLACE_RE.search(line)
            if place is None:
                raise RuntimeError(f"finish without place: {line}")
            places[player] = int(place.group(1))
    if not saw_results:
        raise RuntimeError(f"incomplete log: {path}")
    order = [player for player, _ in sorted(places.items(), key=lambda item: item[1])]
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "finishes": finishes,
        "crashes": sorted(crashes),
        "order": order,
    }


def run_column(jar: Path, track: str, start: int, end: int, kind: str,
               label: str, tmp: Path, cache: Path) -> float:
    props = tmp / f"{label}.properties"
    configure(props, kind)
    log = tmp / f"{label}-{track}.log"
    env = os.environ.copy()
    env["RACING_REACH_CACHE"] = str(cache)
    began = time.perf_counter()
    result = subprocess.run(
        ["java", "-Djava.awt.headless=true", "-jar", str(jar.resolve()),
         "--auto", "--track", track, "--props", str(props),
         "--log", str(log), "--seed", f"{start}-{end}"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=14400,
    )
    elapsed = time.perf_counter() - began
    if result.returncode:
        raise RuntimeError(
            f"{label} {track} exited {result.returncode}:\n{result.stderr[-5000:]}"
        )
    return elapsed


def seed_log(tmp: Path, label: str, track: str, seed: int,
             start: int, end: int) -> Path:
    ranged = tmp / f"{label}-{track}_s{seed}.log"
    if ranged.is_file():
        return ranged
    single = tmp / f"{label}-{track}.log"
    if start == end and single.is_file():
        return single
    matches = list(tmp.glob(f"{label}-{track}*s{seed}.log"))
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(f"missing {label} {track} seed {seed} log")


def relative_order(order: list[int], players: set[int]) -> list[int]:
    return [player for player in order if player in players]


def classify(candidate: dict, baseline: dict) -> tuple[str, dict]:
    if candidate["sha256"] == baseline["sha256"]:
        return "identical", {}

    cf, bf = candidate["finishes"], baseline["finishes"]
    cc, bc = set(candidate["crashes"]), set(baseline["crashes"])
    shared = set(cf) & set(bf)
    slower = {p: cf[p] - bf[p] for p in sorted(shared) if cf[p] > bf[p]}
    faster = {p: cf[p] - bf[p] for p in sorted(shared) if cf[p] < bf[p]}
    order_ok = relative_order(candidate["order"], shared) == relative_order(
        baseline["order"], shared
    )
    details = {
        "baseline": baseline,
        "candidate": candidate,
        "slower": slower,
        "faster": faster,
        "shared_order_preserved": order_ok,
    }

    if cc - bc or set(bf) - set(cf):
        return "safety_regression", details
    if cc < bc:
        if slower or not order_ok:
            return "safety_tradeoff", details
        return "safety_gain", details
    if cc != bc or set(cf) != set(bf) or not order_ok:
        return "redistribution", details
    if slower:
        return "slower", details
    if faster:
        return "faster", details
    return "trajectory_change", details


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
    if args.start > args.end:
        raise SystemExit("start must not exceed end")

    keys = (
        "identical", "faster", "slower", "safety_gain", "safety_tradeoff",
        "safety_regression", "redistribution", "trajectory_change",
    )
    with tempfile.TemporaryDirectory(prefix=f"r176-{args.track}-") as directory:
        tmp = Path(directory)
        cache = tmp / "reach-cache"
        baseline_seconds = run_column(
            args.baseline, args.track, args.start, args.end,
            args.baseline_kind, "baseline", tmp, cache,
        )
        candidate_seconds = run_column(
            args.candidate, args.track, args.start, args.end,
            args.candidate_kind, "candidate", tmp, cache,
        )
        summary = {
            "track": args.track,
            "start": args.start,
            "end": args.end,
            "pairs": args.end - args.start + 1,
            "counts": {key: 0 for key in keys},
            "baseline_seconds": baseline_seconds,
            "candidate_seconds": candidate_seconds,
            "runtime_ratio": candidate_seconds / baseline_seconds,
            "events": [],
        }
        for seed in range(args.start, args.end + 1):
            baseline = parse_log(seed_log(tmp, "baseline", args.track, seed,
                                          args.start, args.end))
            candidate = parse_log(seed_log(tmp, "candidate", args.track, seed,
                                           args.start, args.end))
            classification, details = classify(candidate, baseline)
            summary["counts"][classification] += 1
            if classification != "identical":
                summary["events"].append({
                    "seed": seed,
                    "classification": classification,
                    **details,
                })

    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
