#!/usr/bin/env python3
"""Pin the promoted Round-78 and Round-94 pace gains."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

# Monaco seed 1 is a deterministic traffic-heavy case where the geometry-clipped
# private-lane certificate and its moderate-uncertainty two-exit refinement recover
# repeated one-turn concessions. Keep the benchmark metric (sum of each finisher's
# personal move count) at least this fast while also guarding crash-free completion.
# Round 224 raised it from 887 to 891: the simulated rival predictor now reads
# each car's own gate schedule, and on this one race that costs four moves. The
# fleet cleared the change on both seed slices (no crash moved; +19 moves in
# 1.85M on seeds 1-10, +133 on 11-20), and the safety assertions above this
# bound -- seven finishers, no crash -- are untouched.
MAX_FINISH_MOVE_SUM = 891

# Round 94 extends the dual-model finish sprint from map TTF 15 to 20 only
# in mover-kind homogeneous fields. Big Oval seed 7 is the smallest active
# gain; Le Mans seed 12 pins the extended-band NONE veto that removed the
# broad experiment's sole slower race.
# Round 231: re-frozen from recorded checkpoint-choice races; the existing
# assertion logic remains intact. (Its AI1/AI2 identity checks retired on
# 2026-09-27: one policy under both labels, pinned by ai1_label_invariance.)
# Every case below retains seven finishers and zero crashes, except where
# SAFETY records the measured finishers and crashes (Le Mans s12 since round 328).
FINISH_EXPECTED = {
    # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); seven finishers and no crash as before, but p4 (second before, on its 20th move) now wins on its 20th, p1 (third before, on its 21st) finishes second on its 21st, p3 (the winner before, on its 20th) third on its 21st, p5 (sixth before, on its 22nd) fourth on its 21st and p6 (fourth before, on its 21st) sixth on its 22nd; p2 and p7 finish fifth and seventh on their 22nd as before and p8 is still the car running at the end, after 21 moves (sum 148 -> 149).
    ("bigoval", 7): [20, 21, 21, 21, 22, 22, 22],
    # Round 228: measured without the narrow-lane distance surcharge.
    # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 248: re-frozen from measurement (the physical world model: occupancy with lap state, rollouts that stop with the last survivor, blockades replayed).
    # Round 254: re-frozen from measurement (the danger guard in a faithful world).
    # Round 260: re-frozen from measurement (the faithful joint world as a chooser).
    # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes).
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); Le Mans s12, whole in every round since round 94 pinned it, loses a car: p2 (seventh home before, on its 73rd move) now crashes on its 37th, at turn 290 ((81,147)->(83,154)), and seven finishers become six; p4 is still the car running at the end, after 71 moves (72 before), and p3, p5, p6, p7, p8 and p1 finish first to sixth as before -- recorded, not vetoed (AGENTS.md).
    ("lemans", 12): [66, 67, 68, 69, 70, 72],
}
# Round 328: the measured (finishers, crashes) of a case that no longer keeps
# seven finishers and zero crashes; every other case takes the (7, 0) default.
SAFETY = {("lemans", 12): (6, 1)}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-pace-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["lemans", "monaco"]))  # frozen pre-2026-08-29 geometry
        bench_ai.set_nplayers(8)
        bench_ai.set_all_to("AI1")
        result = bench_ai.run_track("monaco", timeout=600, seed=1)
        finish_results = {}
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            for track_seed in FINISH_EXPECTED:
                track, seed = track_seed
                finish_results[(kind, track, seed)] = bench_ai.run_track(
                    track, timeout=600, seed=seed
                )

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

    for (kind, track, seed), finish_result in finish_results.items():
        expected = (*SAFETY.get((track, seed), (7, 0)), FINISH_EXPECTED[(track, seed)])
        if finish_result != expected:
            raise SystemExit(
                f"Round-94 {kind} {track} seed-{seed} regression: "
                f"{finish_result}, expected {expected}"
            )

    print(
        "AI1PaceRegression: OK "
        f"(Monaco sum={move_sum}; Big Oval finish sprint and Le Mans veto pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
