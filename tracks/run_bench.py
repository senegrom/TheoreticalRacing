#!/usr/bin/env python3
"""Portable launcher for bench_ai.py.

The historical benchmark module keeps its mutable paths as globals. This wrapper
points them at the current checkout and a temporary properties/log directory so
benchmark runs never modify user.properties and do not depend on one developer's
Windows paths.
"""

from __future__ import annotations

import atexit
import os
from pathlib import Path
import shutil
import sys
import tempfile

import bench_ai


ROOT = Path(__file__).resolve().parents[1]
TMP = Path(tempfile.mkdtemp(prefix="theoretical-racing-bench-"))
atexit.register(lambda: shutil.rmtree(TMP, ignore_errors=True))

bench_ai.JAR = str(ROOT / "theoreticRacing.jar")
bench_ai.LOG = str(TMP / "last_game.log")
bench_ai.PROPS = str(TMP / "bench.properties")
shutil.copyfile(ROOT / "tracks" / "bench.properties", bench_ai.PROPS)


def main(argv: list[str]) -> None:
    args = list(argv)
    h2h = "--h2h" in args
    one_v_one = "--1v1" in args
    four_p = "--4p" in args
    slow = "--slow" in args
    args = [a for a in args if a not in ("--h2h", "--1v1", "--4p", "--slow")]

    if "--seeds" in args:
        i = args.index("--seeds")
        bench_ai.SEEDS = list(range(1, int(args[i + 1]) + 1))
        args = args[:i] + args[i + 2 :]
        print(f"# statistical bench: {len(bench_ai.SEEDS)} randomized start grids per track")

    tracks = args if args else (bench_ai.SLOW_TRACKS if slow else bench_ai.DEFAULT_TRACKS)
    if one_v_one:
        bench_ai.bench_field(tracks, 2, 1, "1v1")
    elif four_p:
        bench_ai.bench_field(tracks, 4, 2, "4p")
    elif h2h:
        bench_ai.bench_field(tracks, 8, 4, "h2h")
    else:
        bench_ai.bench(tracks)


if __name__ == "__main__":
    main(sys.argv[1:])
