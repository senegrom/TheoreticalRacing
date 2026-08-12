#!/usr/bin/env python3
"""Pin the Round-81 self-play-only staged-pace boundaries."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

CASES = {
    ("hungaroring", 4): 868,
    ("spa", 4): 580,
    ("interlagos", 3): 875,
    ("lemans", 11): 486,
    ("spa", 11): 572,
    ("silverstone", 15): 585,
    ("silverstone", 18): 589,
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-staged-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        bench_ai.set_all_to("AI1")
        for (track, seed), max_move_sum in CASES.items():
            result = bench_ai.run_track(track, timeout=900, seed=seed)
            if result is None:
                raise SystemExit(
                    f"AI1 {track} seed-{seed} race failed or produced no complete log"
                )
            finishes, crashes, finish_moves = result
            if finishes != 7 or crashes != 0:
                raise SystemExit(
                    f"AI1 {track} seed-{seed} safety regression: "
                    f"finishes={finishes}, crashes={crashes}"
                )
            move_sum = sum(finish_moves)
            if move_sum > max_move_sum:
                raise SystemExit(
                    f"AI1 {track} seed-{seed} pace regression: "
                    f"finisher move sum {move_sum} exceeds {max_move_sum}"
                )

        # The unrestricted certificate changed player 3's opening line on
        # Monaco seed 9 and caused a frozen AI2 car to crash 442 global moves
        # later. Self-play-only gating must leave this mixed field crash-free.
        bench_ai.set_kinds(["AI1"] * 4 + ["AI2"] * 4)
        mixed = bench_ai.run_track_h2h("monaco", timeout=900, seed=9)
        if mixed is None:
            raise SystemExit("mixed Monaco seed-9 race failed or produced no complete log")
        if mixed["AI1"][1:] != (4, 0) or mixed["AI2"][1:] != (4, 0):
            raise SystemExit(f"mixed Monaco seed-9 safety regression: {mixed}")

    print(
        "AI1StagedPaceRegression: OK "
        "(Hungaroring and Silverstone gains; Spa, Interlagos and Le Mans no slower; "
        "mixed Monaco seed 9 crash-free)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
