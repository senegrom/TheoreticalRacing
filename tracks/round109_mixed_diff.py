#!/usr/bin/env python3
"""Compare the broad ESC diagnostic on every heterogeneous safety pin."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOVE_RE = re.compile(r"^\d+ p\d+ ")
RESULT_RE = re.compile(r"^(\d+) p(\d+) (AI1|AI2) ")

CASES = (
    ("lemans-s2-reverse", "lemans", 2, ["AI2"] * 4 + ["AI1"] * 4),
    ("lemans-s7-front", "lemans", 7, ["AI1"] * 4 + ["AI2"] * 4),
    ("lemans-s7-reverse", "lemans", 7, ["AI2"] * 4 + ["AI1"] * 4),
    ("gear-s1-front", "gear", 1, ["AI1"] * 4 + ["AI2"] * 4),
    ("gear-s1-reverse", "gear", 1, ["AI2"] * 4 + ["AI1"] * 4),
)


def properties(path: Path, kinds: list[str]) -> None:
    lines = []
    for line in (ROOT / "tracks" / "bench.properties").read_text().splitlines():
        match = re.match(r"^player([1-8])Kind=", line)
        if match:
            line = f"player{match.group(1)}Kind={kinds[int(match.group(1)) - 1]}"
        lines.append(line)
    path.write_text("\n".join(lines) + "\n")


def run(jar: Path, label: str, case: str, track: str, seed: int,
        kinds: list[str], tmp: Path) -> Path:
    props = tmp / f"{case}-{label}.properties"
    log = tmp / f"{case}-{label}.log"
    properties(props, kinds)
    result = subprocess.run(
        ["java", "-Djava.awt.headless=true", "-jar", str(jar), "--auto",
         "--track", track, "--props", str(props), "--log", str(log), "--seed", str(seed)],
        cwd=ROOT, text=True, capture_output=True, timeout=1200,
    )
    (tmp / f"{case}-{label}.stdout").write_text(result.stdout)
    (tmp / f"{case}-{label}.stderr").write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(f"{case} {label} failed: {result.stderr[-3000:]}")
    return log


def outcome(path: Path) -> dict:
    finishers = {"AI1": 0, "AI2": 0}
    crashes = {"AI1": 0, "AI2": 0}
    places = {"AI1": 0, "AI2": 0}
    moves = []
    for line in path.read_text().splitlines():
        if MOVE_RE.match(line):
            moves.append(line)
        match = RESULT_RE.match(line)
        if not match:
            continue
        kind = match.group(3)
        if " FINISH " in line:
            finishers[kind] += 1
            place_match = re.search(r"place=(\d+)", line)
            if place_match:
                places[kind] += int(place_match.group(1))
        elif " CRASH " in line:
            crashes[kind] += 1
    return {"finishers": finishers, "crashes": crashes, "places": places, "moves": moves}


def first_difference(left: list[str], right: list[str]) -> dict | None:
    size = max(len(left), len(right))
    for index in range(size):
        a = left[index] if index < len(left) else None
        b = right[index] if index < len(right) else None
        if a != b:
            lo = max(0, index - 3)
            hi = index + 4
            return {
                "move_list_index": index,
                "baseline": a,
                "candidate": b,
                "baseline_context": left[lo:hi],
                "candidate_context": right[lo:hi],
            }
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    report = []
    with tempfile.TemporaryDirectory(prefix="r109-mixed-") as directory:
        tmp = Path(directory)
        for case, track, seed, kinds in CASES:
            baseline_log = run(args.baseline.resolve(), "baseline", case, track, seed, kinds, tmp)
            candidate_log = run(args.candidate.resolve(), "candidate", case, track, seed, kinds, tmp)
            baseline = outcome(baseline_log)
            candidate = outcome(candidate_log)
            diff = first_difference(baseline.pop("moves"), candidate.pop("moves"))
            row = {
                "case": case,
                "track": track,
                "seed": seed,
                "kinds": kinds,
                "baseline": baseline,
                "candidate": candidate,
                "first_difference": diff,
            }
            report.append(row)
            print(json.dumps(row, indent=2, sort_keys=True))
            if diff:
                for source in (baseline_log, candidate_log):
                    destination = args.out.parent / f"{case}-{source.stem.split('-')[-1]}.log"
                    destination.write_text(source.read_text())

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
