#!/usr/bin/env python3
"""Pin the Round-78/79 field-externality boundaries.

Decision specimen (2026-11-13): the boundaries were vetoes on the field's cost,
which round 279 removed (the racecraft rule: a faster own line is not refused
for what it costs the rivals). What is left of rounds 78 and 79 in the code is
their trigger and a comparison on the mover's own verdict: in a compact pack or
a convoy the private-lane switch is taken only when the same scorer world reads
it strictly better for the mover than the pick. The two races below hold no
real decision of that comparison on round 345's grids, so the pin also races
one in which it keeps the pick, Zigzag seed 2 (SPECIMEN below).
"""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
import decision_specimen  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

# Round 231: re-frozen from recorded checkpoint-choice races; the existing
# assertion logic remains intact. (Its AI1/AI2 identity checks retired on
# 2026-09-27: one policy under both labels, pinned by ai1_label_invariance.)
# Every case below retains seven finishers and zero crashes, except where
# SAFETY records the measured finishers and crashes (Cog s1 in round 326;
# none since round 328).
EXPECTED = {
    # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 260: re-frozen from measurement (the faithful joint world as a chooser).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); seven finishers and no crash as before, but p3 (seventh home before, on its 67th move) now wins on its 65th, p6 and p8 (third and fifth before) are second and third, on their 66th as before, p1 (the winner before, on its 65th) is fourth on its 67th, p2 fifth on its 67th (sixth before), p4 (the car still running at the end before, after 66 moves) sixth on its 67th and p5 (second before, on its 65th) seventh on its 68th; p7 (fourth home before, on its 66th) is the car still running at the end, after 67 moves (sum 462 -> 466).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); seven finishers and no crash as before, p3 still the winner on its 65th move, but p5 (seventh home before, on its 68th) is now second on its 65th, p1 (fourth before, on its 67th) third on its 66th, p2 fourth on its 67th (fifth before), p6 (second before, on its 66th) fifth on its 67th, p7 (the car still running at the end before, after 67 moves) sixth on its 67th and p4 (sixth before, on its 67th) seventh on its 68th; p8 (third home before, on its 66th) is the car still running at the end, after 67 moves (sum 466 -> 465).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
    # Round 331: re-frozen from measurement (the relevant rival keeps its three stronger forecast moves beside the second and third rivals').
    # Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full policy in every decision).
    # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy).
    # Round 335: re-frozen from measurement (every rival but the relevant one plays its first two forecast moves by its full policy).
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); Zigzag s1 starts from a new grid and is a new race, with seven finishers and no crash: p1, p4 and p6 finish first to third on their 65th moves, p2 and p7 fourth and fifth on their 66th and p5 and p8 sixth and seventh on their 67th, and p3 is the car still running at the end, after 67 moves (sum 461).
    ("zigzag", 1): [65, 65, 65, 66, 66, 67, 67],
    # Round 228: the raw-distance policy saves eight finisher moves in this race.
    # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); Cog s1 loses a car: p8 (the car still running at the end before, after 47 moves) now crashes on its 9th move, at turn 72 ((99,23)->(94,20), into the outer wall: p2 had taken (92,20), p8's one landing from (99,23) at v(-6,-4) that did not cross the wall, at turn 66), and seven finishers become six; p3 (seventh home before, on its 48th) is the car still running at the end, after 47 moves, so it is placed seventh and p8 eighth as before -- the classification is unchanged; p1, p2, p4, p5, p6 and p7 finish as before -- recorded, not vetoed (AGENTS.md).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); Cog s1 gets its car back: p8 no longer crashes on its 9th move (turn 72, now (101,25)->(95,22) ok: it braked S to v(-4,-4) at (106,28) on its 7th, at turn 56, and never reached round 326's (99,23) at v(-6,-4)) and is the car still running at the end, after 46 moves; p3 (the car still running at the end before, after 47 moves) now finishes third on its 46th, p4 (third before, on its 46th) fourth on its 47th, and p5, p6 and p7 each one place lower, fifth to seventh on their 47th as before; p1 and p2 finish as before, first and second on their 46th -- seven finishers and no crash again, as before round 326, so the case leaves SAFETY and takes the (7, 0) default.
    # Round 336: re-frozen from measurement (gates are ordinary landings wherever the exact potential prices them).
    # Round 341: re-frozen from measurement (the score's rival twin plays the rival's own gate rules).
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); Cog s1 starts from a new grid and is a new race, with seven finishers and no crash: p1, p2 and p3 finish first to third on their 46th moves, p5, p6 and p7 fourth to sixth on their 47th and p4 seventh on its 48th, and p8 is the car still running at the end, after 47 moves (sum 327).
    ("cog", 1): [46, 46, 46, 47, 47, 47, 48],
}
# Round 326: the measured (finishers, crashes) of a case that no longer keeps
# seven finishers and zero crashes; every other case takes the (7, 0) default.
# Round 328: Cog s1 keeps every car again, so no case needs an entry.
SAFETY = {}


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


# Decision specimen (2026-11-13). A fleet scan (the 83 courses other than the Nordschleife over seeds 1-40, eight AI2
# cars, one lap, random starts: 3,320 races; a scratch build that prints the legs of top-level decisions only) found
# the pack comparison deciding 65 real private-lane switches: it let 31 through and kept the pick in 34. In Zigzag s2
# at turn 69 p5, on its 9th of 66 moves, stands at (50,54) with v(8,0). The private-lane override's candidate is
# NONE, v(8,0), 64 speed2, onto (58,54), and all seven rivals stand within nine cells of that landing: a compact pack
# by the override's test, which allows ten. The pick is SW, v(7,1), 50 speed2; the same scorer world reads both lines
# alike for the mover (53 against 53), so the comparison keeps SW. The race has seven finishers and no crash: p1 and
# p2 finish on their 65th move and p3, p4, p5, p7 and p8 on their 66th, and p6 is the car still running at the end,
# after 66 moves (526 turns). With the comparison not run in top-level decisions, a twin scratch build races the same
# race through turn 68 and plays NONE at turn 69. The twin is not a pure one: without the comparison the candidate's
# own forecast counts three rivals, as the code has it outside a pack, and six with it.
SPECIMEN = decision_specimen.Specimen(
    "zigzag", 2, (7, 0, [65, 65, 66, 66, 66, 66, 66]),
    "0a417f980b0a7203ba37b12424fa701c9a0ea8fa5e31dd98371948c7ed297d50",
    "69 p5 AI SW v(8,0)→(7,1) (50,54)→(57,55) ok",
)


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-field-") as directory:
        bench_ai.configure_runtime(directory)
        for track, seed in EXPECTED:
            check(track, seed)

    decision_specimen.check("pack comparison", SPECIMEN)

    print(
        "AI1FieldNeutralRegression: OK "
        "(Zigzag seed 1 and Cog seed 1: 7 finishers / 0 crashes, finish moves pinned; "
        "decision specimen pinned on Zigzag s2)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
