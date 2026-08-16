#!/usr/bin/env python3
"""Compare a Round 104 candidate jar against the exact current champion."""
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
    lines = []
    for line in source.read_text().splitlines():
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
    return {"finishes": finishes, "crashes": sorted(crashes)}


def run_column(jar: Path, track: str, start: int, end: int, kind: str,
               label: str, tmp: Path) -> float:
    props = tmp / f"{label}-{kind}.properties"
    configure(ROOT / "tracks" / "bench.properties", props, kind)
    log = tmp / f"{label}-{kind}-{track}.log"
    started = time.perf_counter()
    result = subprocess.run(
        [
            "java", "-Djava.awt.headless=true", "-jar", str(jar), "--auto",
            "--track", track, "--props", str(props), "--log", str(log),
            "--seed", f"{start}-{end}",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=7200,
    )
    elapsed = time.perf_counter() - started
    (tmp / f"{label}-{kind}-{track}.stdout").write_text(result.stdout)
    (tmp / f"{label}-{kind}-{track}.stderr").write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(
            f"{label} {kind} {track} failed with {result.returncode}: "
            f"{result.stderr[-4000:]}"
        )
    return elapsed


def classify(candidate: dict, baseline: dict) -> tuple[str, int]:
    cf, bf = candidate["finishes"], baseline["finishes"]
    cc, bc = candidate["crashes"], baseline["crashes"]
    csum, bsum = sum(cf.values()), sum(bf.values())
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
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    summary = {
        "track": args.track,
        "start": args.start,
        "end": args.end,
        "pairs": 0,
        "counts": {
            "identical": 0,
            "faster": 0,
            "slower": 0,
            "safety_gain": 0,
            "safety_regression": 0,
            "redistribution": 0,
        },
        "net_moves": 0,
        "candidate_identity_mismatches": [],
        "events": [],
        "seconds": {},
    }

    with tempfile.TemporaryDirectory(prefix=f"r104-{args.track}-") as directory:
        tmp = Path(directory)
        for label, jar in (("baseline", args.baseline), ("candidate", args.candidate)):
            for kind in ("AI1", "AI2"):
                summary["seconds"][f"{label}_{kind}"] = run_column(
                    jar.resolve(), args.track, args.start, args.end, kind, label, tmp
                )

        for seed in range(args.start, args.end + 1):
            candidate_by_kind = {}
            for kind in ("AI1", "AI2"):
                baseline = parse_log(tmp / f"baseline-{kind}-{args.track}_s{seed}.log")
                candidate = parse_log(tmp / f"candidate-{kind}-{args.track}_s{seed}.log")
                candidate_by_kind[kind] = candidate
                summary["pairs"] += 1
                if candidate == baseline:
                    summary["counts"]["identical"] += 1
                    continue
                classification, delta = classify(candidate, baseline)
                summary["counts"][classification] += 1
                summary["net_moves"] += delta
                summary["events"].append(
                    {
                        "kind": kind,
                        "seed": seed,
                        "classification": classification,
                        "delta": delta,
                        "baseline_finishers": len(baseline["finishes"]),
                        "candidate_finishers": len(candidate["finishes"]),
                        "baseline_crashes": len(baseline["crashes"]),
                        "candidate_crashes": len(candidate["crashes"]),
                        "baseline_moves": sum(baseline["finishes"].values()),
                        "candidate_moves": sum(candidate["finishes"].values()),
                        "baseline_by_player": baseline["finishes"],
                        "candidate_by_player": candidate["finishes"],
                    }
                )
            if candidate_by_kind["AI1"] != candidate_by_kind["AI2"]:
                summary["candidate_identity_mismatches"].append(
                    {
                        "seed": seed,
                        "AI1": candidate_by_kind["AI1"],
                        "AI2": candidate_by_kind["AI2"],
                    }
                )

    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    bad = summary["counts"]["slower"] + summary["counts"]["safety_regression"]
    bad += summary["counts"]["redistribution"]
    bad += len(summary["candidate_identity_mismatches"])
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
