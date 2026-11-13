#!/usr/bin/env python3
"""Pin the promoted Round-78 and Round-94 pace gains.

Decision specimens (2026-11-13): on round 345's grids the three races below hold
no real switch of the private-lane override that stands (Le Mans s12 has one,
which the kinematic confirm undoes) and no round-94 sprint. The pin also races
one race with each: Monaco seed 3 on the live track and Big Oval seed 12
(PRIVATE_LANE_SPECIMEN and SPRINT_BAND_SPECIMEN below).
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

# Monaco seed 1 is a deterministic traffic-heavy case where the geometry-clipped
# private-lane certificate and its moderate-uncertainty two-exit refinement recover
# repeated one-turn concessions. Keep the benchmark metric (sum of each finisher's
# personal move count) at least this fast while also guarding crash-free completion.
# Round 224 raised it from 887 to 891: the simulated rival predictor now reads
# each car's own gate schedule, and on this one race that costs four moves. The
# fleet cleared the change on both seed slices (no crash moved; +19 moves in
# 1.85M on seeds 1-10, +133 on 11-20), and the safety assertions above this
# bound -- seven finishers, no crash -- are untouched.
# Round 329: re-frozen from measurement (a second rival in contact with the mover
# plays one of aware's three stronger forecast moves); Monaco seed 1, whole in every
# round since round 83 pinned it, loses a car: p7 (fifth home before, on its 116th
# move) crashes on its 17th, at turn 135, ((103,5)->(104,1) at v(2,-4), into the
# outer wall where the climb turns right): on its 15th, at turn 119, p8 held
# (101,10), the one landing from which it could still make the bend, and from each
# of its free landings only one more move stays on the track. Seven finishers become
# six: p4 (seventh before, on its 119th) is now third on its 114th, p5 (the car still
# running at the end before, after 118 moves) fourth on its 115th, p6 (fourth before,
# on its 115th) fifth on its 116th, p3 (third before, on its 114th) is the car still
# running at the end, after 117 moves, and p1, p2 and p8 finish first, second and
# sixth as before -- recorded, not vetoed (AGENTS.md). SAFETY below records the
# measured (6, 1); the six finishers sum to 687 and this bound keeps its value.
# Round 330: re-frozen from measurement (a third rival in contact with the mover
# plays one stronger forecast move too); Monaco seed 1 keeps every car again: p7
# (lost on its 17th move in round 329, at turn 135) now finishes fourth on its
# 115th, p6 (fifth before, on its 116th) third on its 114th, p8 (sixth before, on
# its 117th) fifth on its 116th, p3 (the car still running at the end before, after
# 117 moves) sixth on its 118th, p4 (third before, on its 114th) seventh on its
# 119th, p5 (fourth before, on its 115th) is the car still running at the end, after
# 118 moves, and p1 and p2 finish first and second as before. SAFETY below drops the
# entry round 329 added, so the race takes the (7, 0) default again; the seven
# finishers sum to 807 and this bound keeps its value.
# Round 345: re-frozen from measurement (random starts: each car's own draw from
# the seed's SplitMix64 stream); every race described above was on the grid before
# round 345. Monaco seed 1 starts from a new grid and is a new race, with seven
# finishers and no crash: p6, p7 and p8 finish first to third on their 113th, 114th
# and 115th moves, p1 fourth on its 117th, p2 fifth on its 118th, p4 sixth on its
# 119th and p5 seventh on its 120th, and p3 is the car still running at the end,
# after 120 moves; the seven finishers sum to 816. The bound moves with the race:
# it is this race's own measured sum, with no margin -- round 224 set it to 891
# because this race took four moves more than the 887 it had measured -- and later
# rounds kept it while the race ran faster. 891 was the round-224 sum of the race
# on the grid before round 345, which no longer exists, so the bound is re-derived
# from the new race: 816.
MAX_FINISH_MOVE_SUM = 816

# Round 94 extends the dual-model finish sprint from map TTF 15 to 20 only
# in mover-kind homogeneous fields. Big Oval seed 7 is the smallest active
# gain; Le Mans seed 12 pins the extended-band NONE veto that removed the
# broad experiment's sole slower race.
# Round 345: that gain and that veto were measured on the grid before round
# 345. Both seeds now start from new grids (random starts: each car's own draw
# from the seed's SplitMix64 stream) and are new races, pinned below by their
# measured finish moves.
# Round 231: re-frozen from recorded checkpoint-choice races; the existing
# assertion logic remains intact. (Its AI1/AI2 identity checks retired on
# 2026-09-27: one policy under both labels, pinned by ai1_label_invariance.)
# Every case below retains seven finishers and zero crashes, except where
# SAFETY records the measured finishers and crashes (Le Mans s12 in rounds 328 to
# 330; none since round 331).
FINISH_EXPECTED = {
    # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); seven finishers and no crash as before, but p4 (second before, on its 20th move) now wins on its 20th, p1 (third before, on its 21st) finishes second on its 21st, p3 (the winner before, on its 20th) third on its 21st, p5 (sixth before, on its 22nd) fourth on its 21st and p6 (fourth before, on its 21st) sixth on its 22nd; p2 and p7 finish fifth and seventh on their 22nd as before and p8 is still the car running at the end, after 21 moves (sum 148 -> 149).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves); seven finishers and no crash as before, but p3 (third before, on its 21st move) now wins on its 20th, p4 (the winner before, on its 20th) finishes second on its 20th, p1 (second before, on its 21st) third on its 21st, p2 (fifth before, on its 22nd) fourth on its 22nd and p5 (fourth before, on its 21st) fifth on its 22nd; p6 and p7 finish sixth and seventh on their 22nd as before and p8 is still the car running at the end, after 21 moves (sum 149, unchanged).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too); seven finishers and no crash as before, but p6 (sixth before, on its 22nd move) now finishes fourth on its 21st, so p2 and p5 (fourth and fifth before) finish fifth and sixth, on their 22nd as before; p3, p4 and p1 finish first to third on their 20th, 20th and 21st as before, p7 seventh on its 22nd as before, and p8 is still the car running at the end, after 21 moves -- round 303's list again (sum 149 -> 148).
    # Round 331: re-frozen from measurement (the relevant rival keeps its three stronger forecast moves beside the second and third rivals'); seven finishers and no crash as before, but p4 (second before, on its 20th move) now wins on its 20th, p1 (third before, on its 21st) finishes second on its 21st, p3 (the winner before, on its 20th) third on its 21st, p5 (sixth before, on its 22nd) fourth on its 21st and p6 (fourth before, on its 21st) sixth on its 22nd; p2 and p7 finish fifth and seventh on their 22nd as before and p8 is still the car running at the end, after 21 moves -- round 328's list and classification again (sum 148 -> 149).
    # Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full policy in every decision).
    # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy).
    # Round 335: re-frozen from measurement (every rival but the relevant one plays its first two forecast moves by its full policy).
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); Big Oval s7 starts from a new grid and is a new race, with seven finishers and no crash: p1, p4 and p5 finish first to third on their 21st moves and p2, p3, p6 and p7 fourth to seventh on their 22nd, and p8 is the car still running at the end, after 21 moves (sum 151).
    ("bigoval", 7): [21, 21, 21, 22, 22, 22, 22],
    # Round 228: measured without the narrow-lane distance surcharge.
    # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 248: re-frozen from measurement (the physical world model: occupancy with lap state, rollouts that stop with the last survivor, blockades replayed).
    # Round 254: re-frozen from measurement (the danger guard in a faithful world).
    # Round 260: re-frozen from measurement (the faithful joint world as a chooser).
    # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes).
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); Le Mans s12, whole in every round since round 94 pinned it, loses a car: p2 (seventh home before, on its 73rd move) now crashes on its 37th, at turn 290 ((81,147)->(83,154)), and seven finishers become six; p4 is still the car running at the end, after 71 moves (72 before), and p3, p5, p6, p7, p8 and p1 finish first to sixth as before -- recorded, not vetoed (AGENTS.md).
    # Round 331: re-frozen from measurement (the relevant rival keeps its three stronger forecast moves beside the second and third rivals'); Le Mans s12 keeps every car again: p2 (lost on its 37th move in rounds 328 to 330, at turn 290, (81,147)->(83,154)) now finishes seventh on its 73rd, as before round 328 -- it leaves round 330's line on its 9th move, at turn 66 (SE to v(3,-3) and (11,22), where it played E to v(3,-4) and (11,21)), and on its 37th, at turn 290, plays N from (82,143) at v(2,7), to (2,6) and (84,149) -- and p4 is still the car running at the end, after 72 moves (71 before); p3, p5, p6, p7, p8 and p1 finish first to sixth as before -- round 296's list again, so the case leaves SAFETY and takes the (7, 0) default.
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); Le Mans s12 starts from a new grid and is a new race, with seven finishers and no crash: p1 wins on its 66th move, p2, p3, p5, p6, p7 and p8 finish second to seventh on their 67th, 68th, 69th, 70th, 71st and 72nd, and p4 is the car still running at the end, after 72 moves (sum 483).
    ("lemans", 12): [66, 67, 68, 69, 70, 71, 72],
}
# Round 328: the measured (finishers, crashes) of a case that no longer keeps
# seven finishers and zero crashes; every other case takes the (7, 0) default.
# Round 329: the Monaco seed-1 AI1 race joins it (see MAX_FINISH_MOVE_SUM above);
# Le Mans s12 still loses p2 on its 37th move, at turn 290, as in round 328.
# Round 330: the Monaco seed-1 AI1 race leaves it again (see MAX_FINISH_MOVE_SUM
# above); Le Mans s12 still loses p2 on its 37th move, at turn 290, as in rounds
# 328 and 329, and its six finishers and the car still running at the end, p4
# after 71 moves, finish as before.
# Round 331: Le Mans s12 keeps every car again (p2 finishes seventh on its 73rd;
# see FINISH_EXPECTED above), so no case needs an entry. The Monaco seed-1 AI1
# race stays whole: it leaves round 330's race on p5's 16th move, at turn 125, but
# keeps its classification -- seven finishers, p5 still the car running at the end
# after 118 moves -- and its 807 moves, under MAX_FINISH_MOVE_SUM.
# Round 345: all three races start from new grids (random starts: each car's own
# draw from the seed's SplitMix64 stream) and are new races; each keeps seven
# finishers and no crash, so no case needs an entry.
SAFETY = {}
# Decision specimens (2026-11-13). A fleet scan (the 83 courses other than the Nordschleife over seeds 1-40, eight
# AI2 cars, one lap, random starts: 3,320 races; a scratch build that prints the legs of top-level decisions only)
# found the private-lane override switching 390 real picks that stood, 15 of them on Monaco, and the finish sprint
# taking 19 real moves in round 94's band (16 to 20 map turns from the finish), four of them on the Big Oval.
# Monaco s3, the live track (the Monaco race above runs the frozen fixture geometry): at turn 228 p4, on its 29th of
# 141 moves, stands at (168,17) with v(2,3). Its pick is NW to v(1,2), 5 speed2, and the private-lane override
# switches it to S, v(2,4), 20 speed2, one map turn faster (110 to 109). The race has seven finishers and no crash:
# p1 wins on its 134th move, p2, p3, p5, p6 and p8 follow on their 135th, 136th, 137th, 138th and 139th and p7 on its
# 141st, and p4 is the car still running at the end, after 141 moves (1,101 turns). With the override's switch off in
# top-level decisions only, a twin scratch build races the same race through turn 227 and plays NW at turn 228.
PRIVATE_LANE_SPECIMEN = decision_specimen.Specimen(
    "monaco", 3, (7, 0, [134, 135, 136, 137, 138, 139, 141]),
    "6042735c13dd912a8bed83b8a58b49f8669b3c2476676beb3385ccd7268b0c0a",
    "228 p4 AI S v(2,3)→(2,4) (168,17)→(170,21) ok",
)
# Big Oval s12: at turn 4 p4 makes its first move, from rest at (9,45). Its pick is N, and the finish sprint takes
# NW, v(-1,-1), 19 map turns from the finish, inside the band round 94 opened. The race has seven finishers and no
# crash: p1, p2, p3 and p4 finish on their 21st move and p5, p6 and p8 on their 22nd, and p7 is the car still running
# at the end, after 22 moves (172 turns). With that band closed in top-level decisions only, the twin races the same
# race through turn 3 and plays N at turn 4.
SPRINT_BAND_SPECIMEN = decision_specimen.Specimen(
    "bigoval", 12, (7, 0, [21, 21, 21, 21, 22, 22, 22]),
    "651a462010e443193639d30ae8e7ddb39f9c5d4fab8c16e22d75f38c82abd669",
    "4 p4 AI NW v(0,0)→(-1,-1) (9,45)→(8,44) ok",
)


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
    if (finishes, crashes) != SAFETY.get(("monaco", 1), (7, 0)):
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

    decision_specimen.check("private-lane", PRIVATE_LANE_SPECIMEN)
    decision_specimen.check("round-94 sprint band", SPRINT_BAND_SPECIMEN)

    # Round 345: the message named round 94's Big Oval finish sprint and Le Mans veto, decisions of the races on
    # the grid before round 345; it names what is pinned.
    print(
        "AI1PaceRegression: OK "
        f"(Monaco sum={move_sum}; Big Oval seed 7 and Le Mans seed 12 finish moves pinned; "
        "decision specimens pinned on Monaco s3 and Big Oval s12)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
