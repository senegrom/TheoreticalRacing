#!/usr/bin/env python3
"""Cheap move-for-move AI1/AI2 divergence probe.

Use this before a full benchmark to learn whether an AI1 experiment changes any
selected race at all and to locate the first changed decision. It is not part of
normal CI because AI1 is intentionally allowed to diverge from frozen AI2.
"""

from __future__ import annotations

import argparse
from itertools import zip_longest
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

DEFAULT_TRACKS = ["sprint", "hairpin", "lemans", "hungaroring"]


def normalized_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        if line.startswith("player") or line.startswith("# turns") or line.startswith("# results") \
                or (line and line[0].isdigit()):
            lines.append(line.replace("AI1", "AI").replace("AI2", "AI"))
    return lines


def run_log(track: str, seed: int, kind: str) -> tuple[list[str], tuple[int, int, list[int]]]:
    bench_ai.set_nplayers(8)
    bench_ai.set_all_to(kind)
    result = bench_ai.run_track(track, timeout=600, seed=seed)
    if result is None:
        raise RuntimeError(f"{track} seed {seed} {kind}: invalid race")
    text = Path(bench_ai.LOG).read_text(encoding="utf-8")
    return normalized_lines(text), result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tracks", nargs="*", default=DEFAULT_TRACKS)
    parser.add_argument("--seeds", type=int, default=1, help="number of consecutive seeds")
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--allow-divergence", action="store_true", help="report differences without a failing exit code")
    args = parser.parse_args()
    if args.seeds < 1 or args.seed_start < 1:
        parser.error("seed start and count must be positive")
    if not Path(bench_ai.JAR).is_file():
        parser.error("theoreticRacing.jar not found; run build_main.sh first")

    divergences = 0
    with tempfile.TemporaryDirectory(prefix="theoretical-racing-probe-") as directory:
        bench_ai.configure_runtime(directory)
        for track in args.tracks:
            for seed in range(args.seed_start, args.seed_start + args.seeds):
                ai1_lines, ai1_summary = run_log(track, seed, "AI1")
                ai2_lines, ai2_summary = run_log(track, seed, "AI2")
                if ai1_lines == ai2_lines:
                    print(f"{track} seed {seed}: IDENTICAL {ai1_summary}")
                    continue
                divergences += 1
                print(f"{track} seed {seed}: DIVERGED AI1={ai1_summary} AI2={ai2_summary}")
                for index, (left, right) in enumerate(zip_longest(ai1_lines, ai2_lines), start=1):
                    if left != right:
                        print(f"  first normalized-log difference at line {index}")
                        print(f"  AI1: {left}")
                        print(f"  AI2: {right}")
                        break
    print(f"probe complete: {divergences} divergent race(s)")
    return 0 if args.allow_divergence or divergences == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
