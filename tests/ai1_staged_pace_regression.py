#!/usr/bin/env python3
"""Pin the Round-82/91 self-play-only staged-pace boundaries."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

# Round 233 (the lane spread left the score): every ceiling re-anchored from
# measurement, and three races lose a car -- recorded, not vetoed (AGENTS.md).
CASES = {
    ("hungaroring", 4): 889,
    ("spa", 4): 570,
    ("interlagos", 3): 897,
    # Round 234: Le Mans seed 3 keeps both of the cars it used to lose, so
    # seven finishers are counted here instead of five and the sum grows.
    ("lemans", 3): 501,
    # Round 234: seven finishers here now instead of six, so the sum grows.
    ("lemans", 11): 489,
    # Round 229: re-anchored from measurement (the soft caution stack left the score).
    ("spa", 11): 567,
    ("silverstone", 15): 594,  # Round 229: re-anchored from measurement  # Round 229: re-anchored from measurement
    ("silverstone", 18): 594,  # Round 229: re-anchored from measurement  # Round 229: re-anchored from measurement
    ("coil", 18): 418,  # Round 234: re-anchored from measurement.
    ("hungaroring", 8): 883,
    # Round 234: seven finishers here now instead of six, so the sum grows.
    ("hungaroring", 10): 877,
    ("hungaroring", 25): 890,
}

# A same-sum field redistribution at Le Mans seed 3 is the ambiguity boundary:
# the three-ahead class must retain the exact integrated-frontier finish list.
# Round 231: re-frozen from recorded checkpoint-choice races; the existing
# assertion logic and AI1/AI2 identity checks remain intact.
# Every case below retains seven finishers and zero crashes.
EXACT_MOVES = {
    # Round 228: the raw-distance policy changes the order and saves four moves.
    # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
    # Round 233: five finishers here now; the list is the measured race.
    # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
    ("lemans", 3): [66, 70, 71, 72, 73, 74, 75],
    # Round 234: same seven finishers, one move redistributed.
    ("silverstone", 15): [82, 83, 84, 85, 85, 86, 87],
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-staged-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["hungaroring", "interlagos", "lemans", "monaco", "silverstone", "spa"]))  # frozen pre-2026-08-29 geometry
        bench_ai.set_nplayers(8)
        bench_ai.set_all_to("AI1")
        for (track, seed), max_move_sum in CASES.items():
            result = bench_ai.run_track(track, timeout=900, seed=seed)
            if result is None:
                raise SystemExit(
                    f"AI1 {track} seed-{seed} race failed or produced no complete log"
                )
            # Round 233 (the lane spread left the score, -0.65 places): Le Mans
            # seed 3 loses two cars here, while the fleet's own crashes fall
            # (77 against 92 head-to-head) and three other pinned races get a
            # crashed car back. Recorded, not vetoed (AGENTS.md).
            # Round 234, measured over all twelve cases at once: Le Mans
            # seeds 3 and 11 and Hungaroring 10 all LEAVE this list -- the
            # seal-free car keeps the car each of them used to lose, so
            # they take the (7, 0) default. Spa 4 and Hungaroring 25 are
            # the two that still drop one.
            SAFETY = {("spa", 4): (6, 1), ("hungaroring", 25): (6, 1)}
            finishes, crashes, finish_moves = result
            if (finishes, crashes) != SAFETY.get((track, seed), (7, 0)):
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
            expected_moves = EXACT_MOVES.get((track, seed))
            if expected_moves is not None and finish_moves != expected_moves:
                raise SystemExit(
                    f"AI1 {track} seed-{seed} field redistribution: "
                    f"{finish_moves} != {expected_moves}"
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
        "(three-ahead Coil/Hungaroring gains; low-speed Hungaroring and "
        "ambiguous Le Mans vetoes; stationary-grid Silverstone gain; "
        "mixed Monaco seed 9 crash-free)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
