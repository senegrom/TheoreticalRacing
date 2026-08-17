#!/usr/bin/env python3
"""Run and compare exact all-AI1 race windows for Round 111.

A pace gain is accepted only when every pre-existing finisher is no slower,
the finisher set, crash set and finish order are unchanged, and at least one
driver finishes sooner. Aggregate gains that make another driver slower or
reorder the field are classified as redistribution rather than hidden as a win.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
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


def parse_log(path: Path) -> dict[str, object]:
    moves: dict[int, int] = {}
    finishes: dict[int, int] = {}
    crashes: set[int] = set()
    saw_results = False
    for line in path.read_text().splitlines():
        if line.startswith("# results"):
            saw_results = True
        match = RESULT_RE.match(line)
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
        player
        for player, _ in sorted(finishes.items(), key=lambda item: (item[1], item[0]))
    ]
    return {
        "finishes": finishes,
        "crashes": sorted(crashes),
        "order": order,
    }


def seed_log(directory: Path, label: str, track: str, seed: int,
             start: int, end: int) -> Path:
    exact = directory / f"{label}-{track}_s{seed}.log"
    if exact.is_file():
        return exact
    single = directory / f"{label}-{track}.log"
    if start == end and single.is_file():
        return single
    matches = list(directory.glob(f"{label}-{track}*s{seed}.log"))
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(
        f"missing {label} log for {track} seed {seed}; matches={matches}"
    )


def run_column(jar: Path, track: str, start: int, end: int, label: str,
               directory: Path, kind: str = "AI1") -> dict[str, object]:
    directory.mkdir(parents=True, exist_ok=True)
    props = directory / f"{label}.properties"
    configure(props, kind)
    log = directory / f"{label}-{track}.log"
    started = time.perf_counter()
    completed = subprocess.run(
        [
            "java", "-Djava.awt.headless=true", "-jar", str(jar.resolve()),
            "--auto", "--track", track, "--props", str(props.resolve()),
            "--log", str(log.resolve()), "--seed", f"{start}-{end}",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=5400,
    )
    elapsed = time.perf_counter() - started
    (directory / f"{label}-{track}.stdout").write_text(completed.stdout)
    (directory / f"{label}-{track}.stderr").write_text(completed.stderr)
    if completed.returncode:
        raise RuntimeError(
            f"{label} {track} exited {completed.returncode}: "
            f"{completed.stderr[-4000:]}"
        )
    for seed in range(start, end + 1):
        seed_log(directory, label, track, seed, start, end)
    result = {
        "track": track,
        "label": label,
        "start": start,
        "end": end,
        "seconds": elapsed,
    }
    (directory / f"{label}-{track}-runtime.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    return result


def classify(candidate: dict[str, object], baseline: dict[str, object]) -> tuple[str, int, dict[int, int]]:
    cf = candidate["finishes"]
    bf = baseline["finishes"]
    cc = candidate["crashes"]
    bc = baseline["crashes"]
    assert isinstance(cf, dict) and isinstance(bf, dict)
    assert isinstance(cc, list) and isinstance(bc, list)
    delta = sum(cf.values()) - sum(bf.values())

    if candidate == baseline:
        return "identical", 0, {}
    if len(cf) < len(bf) or len(cc) > len(bc):
        return "safety_regression", delta, {}
    if len(cf) > len(bf) or len(cc) < len(bc):
        return "safety_gain", delta, {}
    if (set(cf) != set(bf) or set(cc) != set(bc)
            or candidate["order"] != baseline["order"]):
        return "redistribution", delta, {}

    by_player = {int(player): int(cf[player]) - int(bf[player]) for player in bf}
    if any(change > 0 for change in by_player.values()):
        if all(change >= 0 for change in by_player.values()):
            return "slower", delta, by_player
        return "redistribution", delta, by_player
    if any(change < 0 for change in by_player.values()):
        return "pareto_faster", delta, by_player
    return "identical", 0, by_player


def compare(track: str, start: int, end: int, baseline_dir: Path,
            candidate_dir: Path, out: Path) -> dict[str, object]:
    classes = (
        "identical", "pareto_faster", "slower", "safety_gain",
        "safety_regression", "redistribution",
    )
    summary: dict[str, object] = {
        "track": track,
        "start": start,
        "end": end,
        "pairs": end - start + 1,
        "counts": {name: 0 for name in classes},
        "net_moves": 0,
        "events": [],
    }
    counts = summary["counts"]
    events = summary["events"]
    assert isinstance(counts, dict) and isinstance(events, list)
    for seed in range(start, end + 1):
        baseline = parse_log(seed_log(baseline_dir, "baseline", track, seed, start, end))
        candidate = parse_log(seed_log(candidate_dir, "candidate", track, seed, start, end))
        classification, delta, by_player = classify(candidate, baseline)
        counts[classification] = int(counts[classification]) + 1
        summary["net_moves"] = int(summary["net_moves"]) + delta
        if classification != "identical":
            events.append(
                {
                    "seed": seed,
                    "classification": classification,
                    "delta": delta,
                    "by_player": by_player,
                    "baseline": baseline,
                    "candidate": candidate,
                }
            )
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run")
    run.add_argument("--jar", type=Path, required=True)
    run.add_argument("--track", required=True)
    run.add_argument("--start", type=int, required=True)
    run.add_argument("--end", type=int, required=True)
    run.add_argument("--label", required=True)
    run.add_argument("--directory", type=Path, required=True)
    run.add_argument("--kind", default="AI1")

    cmp_parser = sub.add_parser("compare")
    cmp_parser.add_argument("--track", required=True)
    cmp_parser.add_argument("--start", type=int, required=True)
    cmp_parser.add_argument("--end", type=int, required=True)
    cmp_parser.add_argument("--baseline-dir", type=Path, required=True)
    cmp_parser.add_argument("--candidate-dir", type=Path, required=True)
    cmp_parser.add_argument("--out", type=Path, required=True)

    args = parser.parse_args()
    if args.start > args.end:
        raise SystemExit("start must not exceed end")
    if args.command == "run":
        print(json.dumps(run_column(
            args.jar, args.track, args.start, args.end, args.label,
            args.directory, args.kind,
        ), indent=2, sort_keys=True))
    else:
        compare(
            args.track, args.start, args.end,
            args.baseline_dir, args.candidate_dir, args.out,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
