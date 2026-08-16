#!/usr/bin/env python3
"""Pin Round 103's full-policy survival rescues for both agents."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

CASES = (("zigzag", 76), ("monaco", 88), ("zandvoort", 88))


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    results = {}
    with tempfile.TemporaryDirectory(prefix="true-confirm-r103-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for track, seed in CASES:
                results[(kind, track, seed)] = bench_ai.run_track(
                    track, timeout=1800, seed=seed
                )
    for kind in ("AI1", "AI2"):
        for track, seed in CASES:
            actual = results[(kind, track, seed)]
            if actual[0] != 7 or actual[1] != 0:
                raise SystemExit(
                    f"Round-103 {track} seed-{seed} {kind} rescue lost: {actual}"
                )
    for track, seed in CASES:
        ai1 = results[("AI1", track, seed)]
        ai2 = results[("AI2", track, seed)]
        if ai1 != ai2:
            raise SystemExit(
                f"Round-103 agent identity lost at {track} seed {seed}: "
                f"AI1 {ai1}, AI2 {ai2}"
            )
    print(
        "AITrueRivalConfirmationRegression: OK "
        "(Zigzag/Monaco/Zandvoort rescues mirrored, 7 finishers / 0 crashes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
