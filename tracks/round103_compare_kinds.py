#!/usr/bin/env python3
"""Prove AI1 and AI2 produce identical per-seed outcomes from one jar."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT_RE = re.compile(r"^(\d+) p(\d+) ")


def configure(destination: Path, kind: str) -> None:
    text = (ROOT / "tracks" / "bench.properties").read_text(encoding="utf-8")
    for number in range(1, 9):
        text = re.sub(
            rf"^player{number}Kind=.*$",
            f"player{number}Kind={kind}",
            text,
            flags=re.MULTILINE,
        )
    destination.write_text(text, encoding="utf-8")


def parse(path: Path) -> dict[str, object]:
    moves: dict[int, int] = {}
    finishes: dict[int, int] = {}
    order: list[int] = []
    crashes: list[int] = []
    turns: list[str] = []
    saw_results = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# results"):
            saw_results = True
        match = RESULT_RE.match(line)
        if not match:
            continue
        normalized = line.replace("AI1", "AI").replace("AI2", "AI")
        turns.append(normalized)
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if " CRASH " in line:
            crashes.append(player)
        elif " FINISH " in line:
            finishes[player] = moves[player]
            order.append(player)
    if not saw_results:
        raise RuntimeError(f"incomplete log: {path}")
    return {
        "turns": turns,
        "finishes": finishes,
        "finish_order": order,
        "crashes": crashes,
    }


def run(jar: Path, track: str, start: int, end: int, kind: str, tmp: Path) -> list[dict[str, object]]:
    props = tmp / f"{kind}.properties"
    log = tmp / f"{kind}-{track}.log"
    configure(props, kind)
    result = subprocess.run(
        [
            "java", "-Djava.awt.headless=true", "-jar", str(jar.resolve()),
            "--auto", "--track", track, "--props", str(props),
            "--log", str(log), "--seed", f"{start}-{end}",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=7200,
    )
    if result.returncode != 0 or "Aborting" in result.stdout:
        raise RuntimeError(f"{kind} failed: {result.stderr[-3000:]}")
    base, extension = log.with_suffix(""), log.suffix
    return [parse(Path(f"{base}_s{seed}{extension}")) for seed in range(start, end + 1)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix=f"r103-identity-{args.track}-") as name:
        tmp = Path(name)
        ai1 = run(args.jar, args.track, args.start, args.end, "AI1", tmp)
        ai2 = run(args.jar, args.track, args.start, args.end, "AI2", tmp)

    events = []
    identical = 0
    for seed, (left, right) in enumerate(zip(ai1, ai2, strict=True), start=args.start):
        if left == right:
            identical += 1
        else:
            events.append({"seed": seed, "AI1": left, "AI2": right})
    report = {
        "track": args.track,
        "seed_start": args.start,
        "seed_end": args.end,
        "pairs": args.end - args.start + 1,
        "identical": identical,
        "different": len(events),
        "events": events,
    }
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if events else 0


if __name__ == "__main__":
    raise SystemExit(main())
