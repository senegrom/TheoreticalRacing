#!/usr/bin/env python3
"""Pin the Round-78/79 field-externality boundaries."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

EXPECTED = {
    ("zigzag", 1): [65, 65, 66, 66, 67, 68, 68],
    ("cog", 1): [49, 49, 49, 50, 51, 51, 52],
}


def run(track: str, seed: int, kind: str) -> tuple[int, int, list[int]]:
    bench_ai.set_nplayers(8)
    bench_ai.set_all_to(kind)
    result = bench_ai.run_track(track, timeout=600, seed=seed)
    if result is None:
        raise SystemExit(
            f"{kind} {track} seed-{seed} race failed or produced no complete log"
        )
    return result


def check(track: str, seed: int) -> None:
    expected_moves = EXPECTED[(track, seed)]
    ai1 = run(track, seed, "AI1")
    ai2 = run(track, seed, "AI2")

    for kind, result in (("AI1", ai1), ("AI2", ai2)):
        finishes, crashes, finish_moves = result
        if finishes != 7 or crashes != 0:
            raise SystemExit(
                f"{kind} {track} seed-{seed} field regression: "
                f"finishes={finishes}, crashes={crashes}"
            )
        if finish_moves != expected_moves:
            raise SystemExit(
                f"{kind} {track} seed-{seed} pace changed: "
                f"finish moves {finish_moves} != {expected_moves}"
            )

    if ai1[2] != ai2[2]:
        raise SystemExit(
            f"AI1 {track} seed-{seed} field-neutrality regression: "
            f"AI1 finish moves {ai1[2]} != AI2 {ai2[2]}"
        )


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-field-") as directory:
        bench_ai.configure_runtime(directory)
        for track, seed in EXPECTED:
            check(track, seed)

    print(
        "AI1FieldNeutralRegression: OK "
        "(Zigzag seed 1 and Cog seed 1 match AI2, 7 finishers / 0 crashes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
