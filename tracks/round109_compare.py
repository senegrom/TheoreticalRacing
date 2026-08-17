#!/usr/bin/env python3
"""Exact same-policy per-seed comparison for Round 109 diagnostics."""
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


def configure(destination: Path, kind: str) -> None:
    lines: list[str] = []
    for line in (ROOT / "tracks" / "bench.properties").read_text().splitlines():
        if re.match(r"^player[1-8]Kind=", line):
            line = line.split("=", 1)[0] + "=" + kind
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
    order = [player for player, _ in sorted(finishes.items(), key=lambda item: (item[1], item[0]))]
    return {"finishes": finishes, "crashes": sorted(crashes), "order": order}


def run(jar: Path, track: str, start: int, end: int, kind: str, label: str, tmp: Path) -> float:
    props = tmp / f"{label}.properties"
    configure(props, kind)
    log = tmp / f"{label}-{track}.log"
    started = time.perf_counter()
    result = subprocess.run(
        ["java", "-Djava.awt.headless=true", "-jar", str(jar), "--auto",
         "--track", track, "--props", str(props), "--log", str(log),
         "--seed", f"{start}-{end}"],
        cwd=ROOT, text=True, capture_output=True, timeout=5400,
    )
    elapsed = time.perf_counter() - started
    (tmp / f"{label}-{track}.stdout").write_text(result.stdout)
    (tmp / f"{label}-{track}.stderr").write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(f"{label} {track} failed: {result.stderr[-3000:]}")
    return elapsed


def seed_log(tmp: Path, label: str, track: str, seed: int, start: int, end: int) -> Path:
    ranged = tmp / f"{label}-{track}_s{seed}.log"
    if ranged.is_file():
        return ranged
    single = tmp / f"{label}-{track}.log"
    if start == end and single.is_file():
        return single
    matches = list(tmp.glob(f"{label}-{track}*s{seed}.log"))
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(f"log for {label} {track} seed {seed} not found")


def classify(candidate: dict, baseline: dict) -> tuple[str, int]:
    if candidate == baseline:
        return "identical", 0
    cf, bf = candidate["finishes"], baseline["finishes"]
    cc, bc = candidate["crashes"], baseline["crashes"]
    delta = sum(cf.values()) - sum(bf.values())
    if len(cf) < len(bf) or len(cc) > len(bc):
        return "safety_regression", delta
    if len(cf) > len(bf) or len(cc) < len(bc):
        return "safety_gain", delta
    if set(cf) != set(bf) or candidate["order"] != baseline["order"]:
        return "redistribution", delta
    if delta < 0:
        return "faster", delta
    if delta > 0:
        return "slower", delta
    return "redistribution", delta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--kind", default="AI1")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix=f"r109-{args.track}-") as directory:
        tmp = Path(directory)
        baseline_seconds = run(args.baseline.resolve(), args.track, args.start, args.end,
                               args.kind, "baseline", tmp)
        candidate_seconds = run(args.candidate.resolve(), args.track, args.start, args.end,
                                args.kind, "candidate", tmp)
        summary = {
            "track": args.track, "start": args.start, "end": args.end,
            "pairs": args.end - args.start + 1,
            "counts": {key: 0 for key in ("identical", "faster", "slower", "safety_gain",
                                           "safety_regression", "redistribution")},
            "net_moves": 0,
            "baseline_seconds": baseline_seconds,
            "candidate_seconds": candidate_seconds,
            "runtime_ratio": candidate_seconds / baseline_seconds,
            "events": [],
        }
        for seed in range(args.start, args.end + 1):
            baseline = parse_log(seed_log(tmp, "baseline", args.track, seed, args.start, args.end))
            candidate = parse_log(seed_log(tmp, "candidate", args.track, seed, args.start, args.end))
            classification, delta = classify(candidate, baseline)
            summary["counts"][classification] += 1
            summary["net_moves"] += delta
            if classification != "identical":
                summary["events"].append({"seed": seed, "classification": classification,
                                          "delta": delta, "baseline": baseline,
                                          "candidate": candidate})

    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
