#!/usr/bin/env python3
"""Pin the Round-78 compressed-field externality boundary."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

EXPECTED_FINISH_MOVE_SUM = 465


def run(kind: str) -> tuple[int, int, list[int]]:
    bench_ai.set_nplayers(8)
    bench_ai.set_all_to(kind)
    result = bench_ai.run_track("zigzag", timeout=600, seed=1)
    if result is None:
        raise SystemExit(f"{kind} Zigzag seed-1 race failed or produced no complete log")
    return result


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-field-") as directory:
        bench_ai.configure_runtime(directory)
        ai1 = run("AI1")
        ai2 = run("AI2")

    for kind, result in (("AI1", ai1), ("AI2", ai2)):
        finishes, crashes, finish_moves = result
        if finishes != 7 or crashes != 0:
            raise SystemExit(
                f"{kind} Zigzag seed-1 field regression: "
                f"finishes={finishes}, crashes={crashes}"
            )
        move_sum = sum(finish_moves)
        if move_sum != EXPECTED_FINISH_MOVE_SUM:
            raise SystemExit(
                f"{kind} Zigzag seed-1 pace changed: "
                f"finisher move sum {move_sum} != {EXPECTED_FINISH_MOVE_SUM}"
            )

    if ai1[2] != ai2[2]:
        raise SystemExit(
            "AI1 Zigzag seed-1 field-neutrality regression: "
            f"AI1 finish moves {ai1[2]} != AI2 {ai2[2]}"
        )

    print(
        "AI1FieldNeutralRegression: OK "
        f"(finishes=7/7, crashes=0/0, finisher-move-sum={EXPECTED_FINISH_MOVE_SUM})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
