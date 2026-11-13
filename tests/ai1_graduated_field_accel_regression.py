#!/usr/bin/env python3
"""Pin Round 115's low-energy field acceleration after promotion.

Decision specimen (2026-11-13): on round 345's grids the three races below hold
one real switch of the field acceleration, in seed 1, and it is of round 106's
class (a gain of 16), not of round 115's (9 to 15). The pin also races one that
holds a round-115 switch, Coil seed 4 (SPECIMEN below).
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

PROMOTED = {
    # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
    # Round 233: re-frozen from measurement (the lane spread left the score).
    # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 260: re-frozen from measurement (the faithful joint world as a chooser).
    # Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
    # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes).
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); no crash, p8 (the car still running at the end before) now finishes fifth in 60 own moves, p7 (sixth home in 60 before) is the car still running at the end, and p6 finishes one own move slower, seventh in 61 (sum 417 -> 418).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy).
    # Round 331: re-frozen from measurement (the relevant rival keeps its three stronger forecast moves beside the second and third rivals').
    # Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full policy in every decision).
    # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy).
    # Round 335: measured (every rival but the relevant one plays its first two forecast moves by its full policy); the same summary, a different classification: no crash, p3 second in 59 (third before), p8 one own move faster, third in 59 (fifth in 60 before), p2 one slower, fourth in 60 (second in 59 before), p4 fifth in 60 (fourth before), p6 sixth in 61 (seventh before), p7 (the car still running at the end before, after 60 own moves) now finishes seventh in 61, and p5 (sixth home in 61 before) is the car still running at the end, after 61 own moves; p1 still wins in 58 (sum 418, unchanged).
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); a new grid and a new race: no crash, p3 wins in 58 own moves, p4 and p8 second and third in 59, p7 fourth in 60, p1, p2 and p5 fifth to seventh in 61, and p6 is the car still running at the end, after 60 own moves (sum 419).
    1: (7, 0, [58, 59, 59, 60, 61, 61, 61]),
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); no crash, p8 (the car still running at the end before) now finishes seventh in 61 own moves, p7 (seventh home in 61 before) is the car still running at the end, p3 finishes two own moves slower, sixth in 61, and p5 one slower, fourth in 60 (sum 416 -> 419).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
    # Round 335: measured (every rival but the relevant one plays its first two forecast moves by its full policy); the same summary as before (round 334's, which the box loop re-froze here without a note, as it did round 333's), a different classification: no crash, p4 one own move faster, third in 60 (fifth in 61 before), and p3 one slower, fifth in 61 (third in 60 before); p1, p2, p5, p6 and p7 finish as before, in 58, 59, 60, 61 and 61, and p8 is still the car running at the end, after 60 own moves (sum 420, unchanged).
    # Round 343: re-frozen from measurement (a rival whose simulated move finishes leaves the score's simulated round); no crash, p3 now finishes third in 60 own moves (fifth in 61 before), so p4 and p5 are fourth and fifth, in 60 as before (third and fourth before), p6 and p7 each one own move faster, sixth and seventh in 60 (61 before), and p8 is still the car running at the end, after 59 own moves (60 before); p1 and p2 finish as before; the race is the round-342 race through turn 370, the first change is p3's 47th move at turn 371 (S instead of SE) (sum 420 -> 417).
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); a new grid and a new race: no crash, p1 wins in 58 own moves, p2 and p4 second and third in 59, p3 and p6 fourth and fifth in 60, p5 and p7 sixth and seventh in 61, and p8 is the car still running at the end, after 60 own moves (sum 418).
    38: (7, 0, [58, 59, 59, 60, 60, 61, 61]),
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); p7, seventh home in 60 moves before, now crashes on its 50th move and seven finishers become six, p4 (fifth home before) the car still running at the end -- recorded, not vetoed.
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); p7 no longer crashes on its 50th move and p4, the car still running at the end before, now finishes fourth in 60 moves: six finishers become seven, p7 the car still running at the end -- crash-free again, and that is what is pinned.
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); still crash-free: p7, the car still running at the end before, now finishes fifth in 60 moves, p8 (sixth home in 60 moves before) the car still running at the end.
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); still crash-free, the same seven finish and p8 is still the car running at the end: p2, p3, p4 and p5 each finish one own move faster, second to fifth in 59, 59, 60 and 60, p7 one slower, seventh in 61, and p6 (second home in 59 before) two slower, sixth in 61 (sum 419 -> 418).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
    # Round 335: re-frozen from measurement (every rival but the relevant one plays its first two forecast moves by its full policy); still crash-free (before is round 334's race, which the box loop re-froze here without a note, as it did round 333's): p7 finishes one own move faster, sixth in 60 (seventh in 61 before), p8 (the car still running at the end before, after 60 own moves) now finishes seventh in 60, and p6 (sixth home in 61 before) is the car still running at the end, after 60 own moves; p1 to p5 finish first to fifth as before, in 58, 59, 59, 60 and 60 -- the list of round 328 again (sum 418 -> 416).
    # Round 343: re-frozen from measurement (a rival whose simulated move finishes leaves the score's simulated round); still crash-free: p8 now finishes fourth in 60 own moves (seventh in 60 before), p3 one own move slower, third in 60 (59 before), p4 and p5 each one slower, fifth and sixth in 61 (fourth and fifth in 60 before), p6 (the car still running at the end before, after 60 own moves) now finishes seventh in 61, and p7 (sixth home in 60 before) is the car still running at the end, after 60 own moves; p1 and p2 finish as before; the race is the round-342 race through turn 359, the first change is p8's 45th move at turn 360 (S instead of SE) (sum 416 -> 420).
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); a new grid and a new race, no longer crash-free: p7 crashes on its 27th own move, at turn 215 ((10,65)→(10,69)), and six cars finish -- p1 wins in 58 own moves, p2 and p8 second and third in 59, and p3, p4 and p5 fourth to sixth in 60 -- and p6 is the car still running at the end, after 59 own moves; the crash-free outcome pinned since round 303 is re-frozen to the measured one, the crash recorded, not vetoed (AGENTS.md) (sum 356).
    106: (6, 1, [58, 59, 59, 60, 60, 60]),
}
# Seed 106 was the round-115 coast control, pinned equal to the legacy
# champion; re-freezes moved it, so EXPECTED alone pins it now (review,
# 2026-09-29: the old alias compared it with itself).
# Round 345: LEGACY_CHAMPION is retired, and with it the round-115 Pareto
# contract and pace-gain checks for seeds 1 and 38 in main(). It held the
# pre-round-115 champion's races on Coil seeds 1 and 38, on the grids before
# round 345, the races round 115's acceleration gained on. Random starts now
# draw every car's own cell, so those races no longer exist, and the legacy
# policy cannot be raced on the new grids. The historical numbers, for the
# record:
# LEGACY_CHAMPION = {
#     1: (7, 0, [58, 59, 60, 62, 62, 63, 63]),
#     38: (7, 0, [58, 59, 61, 61, 62, 62, 63]),
# }
EXPECTED = {kind: PROMOTED for kind in LABELS}
# Decision specimen (2026-11-13). A fleet scan (the 83 courses other than the Nordschleife over seeds 1-40, eight AI2
# cars, one lap, random starts: 3,320 races; a scratch build that prints the legs of top-level decisions only) found
# 30 real switches of round 115's class: at most five rivals ahead and a speed-squared gain of 9 to 15 from a pick
# below 49, onto an untrapped landing (three more such gains land on a trapped one, which round 124 admits). Six are
# on the Coil, in seeds 4, 8, 23, 28, 34 and 40. In Coil s4 at turn 115 p3, on its 15th of 61 moves, stands at
# (36,10) with v(-6,1) and four live rivals ahead by the override's own test: p8 at (33,9), p4 at (30,10), p2 at
# (29,12) and p1 at (28,12). Its pick is SE to v(-5,2), 29 speed2, and the override switches it to S, v(-6,2), 40
# speed2: a gain of 11, one map turn faster (44 to 43, inside round 115's limit of 45). The race has seven finishers
# and no crash: p1 wins on its 58th move, p2 and p4 follow on their 59th, p8 on its 60th and p3, p5 and p6 on their
# 61st, and p7 is the car still running at the end, after 60 moves (479 turns). With the moderate-gain admission off
# in top-level decisions only, a twin scratch build races the same race through turn 114 and plays SE at turn 115.
SPECIMEN = decision_specimen.Specimen(
    "coil", 4, (7, 0, [58, 59, 59, 60, 61, 61, 61]),
    "87009853eae2c7457a5ec35dd074acbf8cc6d3bf3dfc2df1e723bb16721d39ac",
    "115 p3 AI S v(-6,1)→(-6,2) (36,10)→(30,12) ok",
)


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {kind: {} for kind in LABELS}
    with tempfile.TemporaryDirectory(prefix="round115-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            for seed in (1, 38, 106):
                actual[kind][seed] = bench_ai.run_track("coil", timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-115 promoted regression: {actual}, expected {EXPECTED}")
    # Round 345: the Pareto contract and the pace gain against LEGACY_CHAMPION
    # on seeds 1 and 38 are retired (see above); EXPECTED is the pin.
    decision_specimen.check("round-115", SPECIMEN)
    print(
        "AI1GraduatedFieldAccelRegression: OK "
        "(Coil s1/s38 promoted; s106 frozen; decision specimen pinned on Coil s4)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
