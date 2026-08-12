#!/usr/bin/env python3
"""Pin the Round-80 energy-capped staged-pace boundaries."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

# Hungaroring seed 4 captures the retained open-line gain. The other cases are
# exact false-gain or crash counterexamples that shaped the gate. Faster future
# policies remain allowed, but no case may lose a finisher, crash, or exceed the
# pinned Round-79/80 move ceiling.
CASES = {
    ("hungaroring", 4): 868,
    ("spa", 4): 580,
    ("interlagos", 3): 875,
    ("lemans", 11): 486,
    ("spa", 11): 572,
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

    print(
        "AI1StagedPaceRegression: OK "
        "(Hungaroring gain; Spa, Interlagos and Le Mans counterexamples no slower)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
