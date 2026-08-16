#!/usr/bin/env python3
"""Compare exact current-master and Round 104 jars per track and AI kind."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path.cwd()
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
               label: str, tmp: Path) -> list[Path]:
    props = tmp / f"{label}-{kind}.properties"
    configure(ROOT / "tracks/bench.properties", props, kind)
    log = tmp / f"{label}-{kind}-{track}.log"
    completed = subprocess.run([
        "java", "-Djava.awt.headless=true", "-jar", str(jar.resolve()),
        "--auto", "--track", track, "--props", str(props), "--log", str(log),
        "--seed", f"{start}-{end}",
    ], cwd=ROOT, text=True, capture_output=True, timeout=18_000)
    if completed.returncode:
        raise RuntimeError(
            f"{label} {kind} {track} failed: {completed.stderr[-3000:]}"
        )
    base, ext = log.with_suffix(""), log.suffix
    paths = [Path(f"{base}_s{seed}{ext}") for seed in range(start, end + 1)]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise RuntimeError("missing logs: " + ", ".join(missing[:5]))
    return paths


def classify(candidate: dict, baseline: dict) -> tuple[str, int]:
    if candidate == baseline:
        return "identical", 0
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
    report = {
        "track": args.track,
        "start": args.start,
        "end": args.end,
        "pairs": (args.end - args.start + 1) * 2,
        "by_kind": {},
    }
    bad = False
    with tempfile.TemporaryDirectory(prefix=f"r104-{args.track}-") as directory:
        tmp = Path(directory)
        for kind in ("AI1", "AI2"):
            bpaths = run_column(
                args.baseline, args.track, args.start, args.end, kind, "baseline", tmp
            )
            cpaths = run_column(
                args.candidate, args.track, args.start, args.end, kind, "candidate", tmp
            )
            summary = {
                "pairs": args.end - args.start + 1,
                "identical": 0,
                "faster": 0,
                "slower": 0,
                "safety_gain": 0,
                "safety_regression": 0,
                "redistribution": 0,
                "net_moves": 0,
                "events": [],
            }
            for seed, bpath, cpath in zip(
                range(args.start, args.end + 1), bpaths, cpaths
            ):
                baseline = parse_log(bpath)
                candidate = parse_log(cpath)
                classification, delta = classify(candidate, baseline)
                summary[classification] += 1
                summary["net_moves"] += delta
                if classification != "identical":
                    cf, bf = candidate["finishes"], baseline["finishes"]
                    cc, bc = candidate["crashes"], baseline["crashes"]
                    summary["events"].append({
                        "seed": seed,
                        "classification": classification,
                        "delta": delta,
                        "candidate_finishers": len(cf),
                        "baseline_finishers": len(bf),
                        "candidate_crashes": len(cc),
                        "baseline_crashes": len(bc),
                        "candidate_moves": sum(cf.values()),
                        "baseline_moves": sum(bf.values()),
                        "candidate_by_player": cf,
                        "baseline_by_player": bf,
                    })
            report["by_kind"][kind] = summary
            if (summary["slower"] or summary["safety_regression"]
                    or summary["redistribution"]):
                bad = True
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
