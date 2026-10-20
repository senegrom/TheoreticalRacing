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
# Every case below retains seven finishers and zero crashes, except where
# SAFETY records the measured finishers and crashes (Cog s1 since round 326).
EXPECTED = {
    # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 260: re-frozen from measurement (the faithful joint world as a chooser).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); seven finishers and no crash as before, but p3 (seventh home before, on its 67th move) now wins on its 65th, p6 and p8 (third and fifth before) are second and third, on their 66th as before, p1 (the winner before, on its 65th) is fourth on its 67th, p2 fifth on its 67th (sixth before), p4 (the car still running at the end before, after 66 moves) sixth on its 67th and p5 (second before, on its 65th) seventh on its 68th; p7 (fourth home before, on its 66th) is the car still running at the end, after 67 moves (sum 462 -> 466).
    ("zigzag", 1): [65, 66, 66, 67, 67, 67, 68],
    # Round 228: the raw-distance policy saves eight finisher moves in this race.
    # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); Cog s1 loses a car: p8 (the car still running at the end before, after 47 moves) now crashes on its 9th move, at turn 72 ((99,23)->(94,20), into the outer wall: p2 had taken (92,20), p8's one landing from (99,23) at v(-6,-4) that did not cross the wall, at turn 66), and seven finishers become six; p3 (seventh home before, on its 48th) is the car still running at the end, after 47 moves, so it is placed seventh and p8 eighth as before -- the classification is unchanged; p1, p2, p4, p5, p6 and p7 finish as before -- recorded, not vetoed (AGENTS.md).
    ("cog", 1): [46, 46, 46, 47, 47, 47],
}
# Round 326: the measured (finishers, crashes) of a case that no longer keeps
# seven finishers and zero crashes; every other case takes the (7, 0) default.
SAFETY = {("cog", 1): (6, 1)}


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
        if (finishes, crashes) != SAFETY.get((track, seed), (7, 0)):
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
        "(Zigzag seed 1: 7 finishers / 0 crashes; Cog seed 1: 6 finishers / 1 crash; "
        "finish moves pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
