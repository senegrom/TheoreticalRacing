#!/usr/bin/env python3
"""Pin the Round-78/79 field-externality boundaries."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

# Round 231: re-frozen from recorded checkpoint-choice races; the existing
# assertion logic remains intact. (Its AI1/AI2 identity checks retired on
# 2026-09-27: one policy under both labels, pinned by ai1_label_invariance.)
# Every case below retains seven finishers and zero crashes.
EXPECTED = {
    # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 260: re-frozen from measurement (the faithful joint world as a chooser).
    ("zigzag", 1): [65, 65, 65, 66, 66, 66, 66],
    # Round 228: the raw-distance policy saves eight finisher moves in this race.
    # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
    ("cog", 1): [46, 47, 47, 47, 47, 48, 49],
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
    for kind in LABELS:
        finishes, crashes, finish_moves = run(track, seed, kind)
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


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-field-") as directory:
        bench_ai.configure_runtime(directory)
        for track, seed in EXPECTED:
            check(track, seed)

    print(
        "AI1FieldNeutralRegression: OK "
        "(Zigzag seed 1 and Cog seed 1: 7 finishers / 0 crashes, finish moves pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
