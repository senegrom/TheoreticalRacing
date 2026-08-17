#!/usr/bin/env python3
"""Compare the Round 107 candidate jar against the exact live-master jar."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT_RE = re.compile(r"^(\d+) p(\d+) ")


def configure(source: Path, destination: Path, kind: str = "AI1") -> None:
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
        raise RuntimeError(f"invalid race log: {path}")
    return {"finishes": finishes, "crashes": sorted(crashes)}


def run_column(jar: Path, track: str, end_seed: int, label: str, tmp: Path) -> None:
    props = tmp / f"{label}.properties"
    configure(ROOT / "tracks" / "bench.properties", props)
    log = tmp / f"{label}-{track}.log"
    result = subprocess.run(
        [
            "java", "-Djava.awt.headless=true", "-jar", str(jar.resolve()),
            "--auto", "--track", track, "--props", str(props),
            "--log", str(log), "--seed", f"1-{end_seed}",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=7200,
    )
    if result.returncode:
        raise RuntimeError(
            f"{label} {track} failed with {result.returncode}: {result.stderr[-3000:]}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    summary = {
        "track": args.track,
        "pairs": args.end,
        "counts": {},
        "net_moves": 0,
        "events": [],
    }
    with tempfile.TemporaryDirectory(prefix=f"round107-{args.track}-") as directory:
        tmp = Path(directory)
        run_column(args.baseline, args.track, args.end, "baseline", tmp)
        run_column(args.candidate, args.track, args.end, "candidate", tmp)
        for seed in range(1, args.end + 1):
            baseline = parse_log(tmp / f"baseline-{args.track}_s{seed}.log")
            candidate = parse_log(tmp / f"candidate-{args.track}_s{seed}.log")
            if candidate == baseline:
                classification = "identical"
            else:
                bf, cf = baseline["finishes"], candidate["finishes"]
                bc, cc = baseline["crashes"], candidate["crashes"]
                bsum, csum = sum(bf.values()), sum(cf.values())
                if len(cf) < len(bf) or len(cc) > len(bc):
                    classification = "safety_regression"
                elif len(cf) > len(bf) or len(cc) < len(bc):
                    classification = "safety_gain"
                elif csum < bsum:
                    classification = "faster"
                elif csum > bsum:
                    classification = "slower"
                else:
                    classification = "redistribution"
                summary["net_moves"] += csum - bsum
                summary["events"].append(
                    {
                        "seed": seed,
                        "classification": classification,
                        "delta": csum - bsum,
                        "baseline": baseline,
                        "candidate": candidate,
                    }
                )
            summary["counts"][classification] = (
                summary["counts"].get(classification, 0) + 1
            )

    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    bad = sum(
        summary["counts"].get(key, 0)
        for key in ("safety_regression", "slower", "redistribution")
    )
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
