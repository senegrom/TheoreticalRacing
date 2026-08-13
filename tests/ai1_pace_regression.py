#!/usr/bin/env python3
"""Pin the Round-78 AI1 pace gain without changing the frozen AI2 corpus."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

# Monaco seed 1 is a deterministic traffic-heavy case where the geometry-clipped
# private-lane certificate and its moderate-uncertainty two-exit refinement recover
# repeated one-turn concessions. Keep the benchmark metric (sum of each finisher's
# personal move count) at least this fast while also guarding crash-free completion.
MAX_FINISH_MOVE_SUM = 799


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-pace-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        bench_ai.set_all_to("AI1")
        result = bench_ai.run_track("monaco", timeout=600, seed=1)

    if result is None:
        raise SystemExit("AI1 Monaco seed-1 race failed or produced no complete log")
    finishes, crashes, finish_moves = result
    if finishes != 7 or crashes != 0:
        raise SystemExit(
            f"AI1 Monaco seed-1 safety regression: finishes={finishes}, crashes={crashes}"
        )
    move_sum = sum(finish_moves)
    if move_sum > MAX_FINISH_MOVE_SUM:
        raise SystemExit(
            "AI1 Monaco seed-1 pace regression: "
            f"finisher move sum {move_sum} exceeds {MAX_FINISH_MOVE_SUM}"
        )

    print(
        "AI1PaceRegression: OK "
        f"(finishes={finishes}, crashes={crashes}, finisher-move-sum={move_sum})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
