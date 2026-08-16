#!/usr/bin/env python3
"""Compare Round 103 candidate and current master for one track and both AIs."""
# Gate trigger retained so materializer-only fixes rerun the exact differential.
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT_RE = re.compile(r"^(\d+) p(\d+) ")


def configure(source: Path, destination: Path, kind: str) -> None:
    lines = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if re.match(r"^player[1-8]Kind=", line):
            line = line.split("=", 1)[0] + "=" + kind
        lines.append(line)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_log(path: Path) -> dict[str, object]:
    moves: dict[int, int] = {}
    finishes: dict[int, int] = {}
    crashes: set[int] = set()
    saw_results = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# results"):
            saw_results = True
        match = RESULT_RE.match(line)
        if not match:
            continue
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if " CRASH " in line:
            crashes.add(player)
        elif " FINISH " in line:
            finishes[player] = moves[player]
    if not saw_results:
        raise RuntimeError(f"invalid log: {path}")
    return {"finishes": finishes, "crashes": sorted(crashes)}


def run_column(jar: Path, track: str, start: int, end: int, kind: str,
               label: str, tmp: Path) -> list[Path]:
    props = tmp / f"{label}-{kind}.properties"
    configure(ROOT / "tracks" / "bench.properties", props, kind)
    log = tmp / f"{label}-{kind}-{track}.log"
    completed = subprocess.run(
        [
            "java", "-Djava.awt.headless=true", "-jar", str(jar.resolve()),
            "--auto", "--track", track, "--props", str(props),
            "--log", str(log), "--seed", f"{start}-{end}",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=14_400,
    )
    if completed.returncode:
        raise RuntimeError(
            f"{label} {kind} {track} failed with {completed.returncode}: "
            f"{completed.stderr[-3000:]}"
        )
    base, ext = log.with_suffix(""), log.suffix
    paths = [Path(f"{base}_s{seed}{ext}") for seed in range(start, end + 1)]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise RuntimeError("missing per-seed logs: " + ", ".join(missing[:5]))
    return paths


def classify(candidate: dict[str, object], champion: dict[str, object]) -> tuple[str, int]:
    if candidate == champion:
        return "identical", 0
    cf = candidate["finishes"]
    bf = champion["finishes"]
    cc = candidate["crashes"]
    bc = champion["crashes"]
    assert isinstance(cf, dict) and isinstance(bf, dict)
    assert isinstance(cc, list) and isinstance(bc, list)
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

    report: dict[str, object] = {
        "track": args.track,
        "start": args.start,
        "end": args.end,
        "pairs": (args.end - args.start + 1) * 2,
        "by_kind": {},
    }
    bad = False
    with tempfile.TemporaryDirectory(prefix=f"r103-{args.track}-") as directory:
        tmp = Path(directory)
        for kind in ("AI1", "AI2"):
            baseline_paths = run_column(
                args.baseline, args.track, args.start, args.end, kind, "baseline", tmp
            )
            candidate_paths = run_column(
                args.candidate, args.track, args.start, args.end, kind, "candidate", tmp
            )
            summary: dict[str, object] = {
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
            for seed, baseline_path, candidate_path in zip(
                range(args.start, args.end + 1), baseline_paths, candidate_paths
            ):
                champion = parse_log(baseline_path)
                candidate = parse_log(candidate_path)
                classification, delta = classify(candidate, champion)
                summary[classification] = int(summary[classification]) + 1
                summary["net_moves"] = int(summary["net_moves"]) + delta
                if classification != "identical":
                    cf = candidate["finishes"]
                    bf = champion["finishes"]
                    cc = candidate["crashes"]
                    bc = champion["crashes"]
                    assert isinstance(cf, dict) and isinstance(bf, dict)
                    assert isinstance(cc, list) and isinstance(bc, list)
                    summary["events"].append({
                        "seed": seed,
                        "classification": classification,
                        "delta": delta,
                        "candidate_finishers": len(cf),
                        "champion_finishers": len(bf),
                        "candidate_crashes": len(cc),
                        "champion_crashes": len(bc),
                        "candidate_moves": sum(cf.values()),
                        "champion_moves": sum(bf.values()),
                        "candidate_by_player": cf,
                        "champion_by_player": bf,
                    })
            report["by_kind"][kind] = summary
            if any(int(summary[name]) for name in (
                "slower", "safety_regression", "redistribution"
            )):
                bad = True

    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
