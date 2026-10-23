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
    # Round 247: seven finishers here now instead of six, so the sum grows.
    ("spa", 4): 573,
    ("interlagos", 3): 897,
    # Round 234: Le Mans seed 3 keeps both of the cars it used to lose, so
    # seven finishers are counted here instead of five and the sum grows.
    ("lemans", 3): 501,
    # Round 234: seven finishers here now instead of six, so the sum grows.
    ("lemans", 11): 489,
    # Round 229: re-anchored from measurement (the soft caution stack left the score).
    ("spa", 11): 569,  # Round 247: re-anchored from measurement.
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
    ("silverstone", 15): 601,  # Round 229: re-anchored from measurement  # Round 229: re-anchored from measurement  # Round 229: re-anchored from measurement
    ("silverstone", 18): 594,  # Round 229: re-anchored from measurement  # Round 229: re-anchored from measurement
    ("coil", 18): 421,  # Rounds 234 and 247: re-anchored from measurement.
    # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes).
    ("hungaroring", 8): 884,
    # Round 234: seven finishers here now instead of six, so the sum grows.
    ("hungaroring", 10): 877,
    ("hungaroring", 25): 890,
}

# A same-sum field redistribution at Le Mans seed 3 is the ambiguity boundary:
# the three-ahead class must retain the exact integrated-frontier finish list.
# Round 231: re-frozen from recorded checkpoint-choice races; the existing
# assertion logic and AI1/AI2 identity checks remain intact.
# Round 248 (the physical world model): Le Mans seed 3 has six finishers.
EXACT_MOVES = {
    # Round 228: the raw-distance policy changes the order and saves four moves.
    # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
    # Round 233: five finishers here now; the list is the measured race.
    # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 260: re-frozen from measurement (the chooser).
    # Round 278: re-frozen from measurement (the chooser's pick stands); seven finishers again.
    # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes); p7 crashes, six finishers.
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they
    # collect paid); p7 and p5 crash, five finishers.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts);
    # p7 and p5, which crashed there, now finish -- seven finishers again.
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted);
    # the same seven finishers in the same order, p6 and p7 each home one move later (on their 71st and 72nd).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too);
    # the same seven finishers in the same order, p7 home one move earlier, on its 71st (on its 72nd in the list pinned
    # since round 310), and p8 still the car running at the end, after 70 moves (71 before); no crash, one move fewer
    # (483 -> 482) -- round 303's list again -- and the ceiling above keeps its value.
    ("lemans", 3): [66, 67, 68, 69, 70, 71, 71],
    # Round 234: same seven finishers, one move redistributed.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted);
    # the same seven finishers in a new order (p4 now wins on its 82nd move), one move fewer.
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win);
    # the same seven finishers in a new order (p1 now wins on its 82nd move), one move more.
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time);
    # the same seven finishers in a new order (p2 now wins on its 83rd move; p1, the winner before on its
    # 82nd, finishes seventh on its 86th), four moves more; p8 is still the car running at the end.
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy);
    # p2 still wins on its 83rd move, but p3, p4 and p5 (fourth, fifth and third in round 326's race, on their 87th, 87th
    # and 86th) are now second to fourth on their 83rd, 84th and 84th, p6 and p7 fifth and sixth on their 85th (sixth and
    # seventh on their 87th before), p8 (the car still running at the end before, after 86 moves) seventh on its 85th, and
    # p1 (second home on its 84th before) is the car still running at the end, after 85 moves; no crash, twelve moves
    # fewer (601 -> 589), and the ceiling above keeps its value.
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger
    # forecast moves); p2 still wins on its 83rd move, p4 is now second on its 83rd and p3 third on its 84th (third on its
    # 84th and second on its 83rd before), p5, p6 and p7 finish fourth to sixth as before, on their 84th, 85th and 85th,
    # p1 (the car still running at the end before, after 85 moves) seventh on its 86th, and p8 (seventh home on its 85th
    # before) is the car still running at the end, after 85 moves; no crash, one move more (589 -> 590), and the ceiling
    # above keeps its value.
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too);
    # p2 still wins on its 83rd move, p3 is now second on its 83rd and p4 third on its 84th (third on its 84th and second
    # on its 83rd before), p6 fourth on its 84th (fifth on its 85th before), p1 (seventh before, on its 86th) fifth on its
    # 85th, p5 sixth on its 85th (fourth on its 84th before), p7 seventh on its 85th (sixth on its 85th before), and p8 is
    # still the car running at the end, after 84 moves (85 before); no crash, one move fewer (590 -> 589) -- round 328's
    # list again, in a new order -- and the ceiling above keeps its value.
    ("silverstone", 15): [83, 83, 84, 84, 85, 85, 85],
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
            # Round 247: Spa 4 keeps its seventh car too; Hungaroring 25 still
            # drops one.
            # Round 248 (the physical world model): four more races drop a car
            # and Hungaroring 25 drops two -- recorded, not vetoed (AGENTS.md).
            # Round 254 (the danger guard in a faithful world): Le Mans 11 keeps
            # its seventh car again.
            # Round 260 (the chooser): Hungaroring 10 and 25 keep every car
            # they used to lose; Spa 4, Interlagos 3 and Hungaroring 8 each drop
            # one -- recorded, not vetoed (AGENTS.md).
            # Round 278 (the chooser's pick stands): Spa 4, Interlagos 3, Le Mans 3
            # and Hungaroring 8 keep every car; Le Mans 11 drops one again --
            # recorded, not vetoed (AGENTS.md).
            # Round 279 (four rule-conformance and correctness fixes): Le Mans 3
            # drops one again (p7 on turn 63) -- recorded, not vetoed (AGENTS.md).
            # Round 296 (landings priced with the checkpoints they collect paid):
            # Le Mans 3 drops a second car (p7 on its 8th move, p5 on its 54th) and
            # Le Mans 11 keeps its seventh -- recorded, not vetoed (AGENTS.md).
            # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts);
            # Le Mans 3 keeps both cars it lost (p5 now finishes on its 71st move, p7 on
            # its 73rd), so it leaves this list and takes the (7, 0) default.
            # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout);
            # Hungaroring 4, a car short since round 248, keeps every car (p7, lost on its
            # 11th move before, is still running after 127 moves when p4 finishes seventh
            # on its 128th), so it leaves this list and takes the (7, 0) default;
            # Interlagos 3 drops one (p7 on its 56th move) -- recorded, not vetoed (AGENTS.md).
            # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties);
            # Interlagos 3 keeps every car again (p7, lost on its 56th move in round 300a, now
            # finishes seventh on its 130th), so it leaves this list and takes the (7, 0) default;
            # Hungaroring 4 drops one again (p4 on its 46th move), and Hungaroring 10, whole since
            # round 260, drops one again (p5 on its 11th move) -- recorded, not vetoed (AGENTS.md).
            # Round 301c: re-frozen from measurement (the mover plays its own scorer in four more danger
            # searches); Le Mans 11, whole since round 296, drops two (p8 on its 40th move, p7 on its
            # 41st) -- recorded, not vetoed (AGENTS.md).
            # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted);
            # Le Mans 11 keeps both cars it lost in round 301c (p7 now finishes sixth on its 71st move,
            # p8 seventh on its 72nd) and Hungaroring 10 keeps its car again (p5, lost on its 11th move
            # since round 301a', now finishes seventh on its 128th), so both leave this list and take
            # the (7, 0) default; Silverstone 18, whole in every round since this pin began (round 83),
            # drops one (p8 on its 75th move), and Hungaroring 4 still drops one, now p2 on its 12th
            # move -- recorded, not vetoed (AGENTS.md).
            # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast
            # continuation moves; a rival's forecast crash is no win); Silverstone 18 keeps its car
            # again (p8, lost on its 75th move in round 303, is still running after 84 moves when p7
            # finishes seventh on its 85th), so it leaves this list and takes the (7, 0) default, and
            # Hungaroring 4 still drops one, now p3 on its 32nd move -- recorded, not vetoed (AGENTS.md).
            # Round 310: re-frozen from measurement (the danger-joint-search family deleted);
            # Hungaroring 25, whole since round 260, drops one (p6 on its 10th move, into the wall at
            # (102,159) in the first corner; p4, seventh home on its 128th before, is the car still
            # running at the end, after 126 moves), and Hungaroring 4 still drops one, now p2 on its
            # 44th move -- recorded, not vetoed (AGENTS.md).
            # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place,
            # then time); Hungaroring 4, a car short since round 301a', keeps every car (p2, lost on its
            # 44th move in round 310, is still running after 128 moves when p1 finishes seventh on its
            # 129th), so it leaves this list and takes the (7, 0) default, and Hungaroring 25 still drops
            # one, now p4 on its 6th move (at turn 44, (95,147)->(97,149), on the run to the first
            # corner; p6, lost on its 10th move in round 310, is the car still running at the end, after
            # 126 moves, and the six finishers finish as before) -- recorded, not vetoed (AGENTS.md).
            # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast
            # moves by its full policy); Hungaroring 25, a car short since round 310, keeps every car (p4,
            # lost on its 45th move in round 326, at turn 356, (59,117)->(61,118) -- on its 6th in round
            # 316 --, now finishes seventh on its 128th, and p6 is still the car running at the end, after
            # 127 moves), so it leaves this list and takes the (7, 0) default; Hungaroring 8, whole since
            # round 278, drops one: p3 (the car still running at the end before, after 128 moves) crashes
            # on its 45th move, at turn 355, on that very cell and velocity ((59,117)->(61,118) at v(3,2),
            # into the outer wall of the bend): on its 44th, at turn 347, p1, p7 and p6 held (59,116),
            # (60,116) and (61,116), so its only landings on the track were (59,117) and (60,117), on the
            # outer edge, from which every landing crosses the wall. p5, seventh home on its 128th before,
            # is the car still running at the end, after 126 moves, and p2, p4, p6, p7, p8 and p1 finish as
            # before -- recorded, not vetoed (AGENTS.md).
            # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of
            # aware's three stronger forecast moves); Hungaroring 8, a car short since round 328, keeps every
            # car (p3, lost on its 45th move in round 328, now finishes seventh on its 128th, and p5 is still
            # the car running at the end, after 127 moves), so it leaves this list and takes the (7, 0)
            # default. Hungaroring 4, whole since round 316, drops one again: p7 (third home on its 123rd
            # before) crashes on its 11th move, at turn 87, ((100,162)->(99,164) at v(0,3), into the outer
            # wall of the first corner): on its 10th, at turn 79, p4 held (100,161), so its only landing on
            # the track was (100,162), the outer wall's corner, from which every landing crosses the wall.
            # p8, p2 and p4 (fourth, sixth and the car still running at the end before) now finish third to
            # fifth on their 123rd, 125th and 126th, p1 (fifth before, on its 126th) sixth on its 128th, p3
            # (seventh home on its 128th before) is the car still running at the end, after 127 moves, and p5
            # and p6 finish first and second as before. Silverstone 18, whole since round 305/309, drops one:
            # p3 (the winner before, on its 83rd move) crashes on its 57th, at turn 451, ((78,74)->(83,71) at
            # v(5,-2), into the inside wall of the hairpin): on its 55th, at turn 435, p1 held (73,77), the
            # one landing from which it could still make the hairpin, and p2 (75,76), so its free landings on
            # the track were (73,76) and (74,76), at v(5,-3) and v(6,-3), from which the wall comes within
            # three moves. p2 (sixth before, on its 85th) now wins on its 83rd, p1 (fifth before, on its 85th)
            # is second on its 84th, p5, p4 and p6 (second, third and fourth before) third to fifth on their
            # 84th, 85th and 85th, p8 sixth on its 85th (seventh before), and p7 is still the car running at
            # the end, after 85 moves -- recorded, not vetoed (AGENTS.md).
            # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one
            # stronger forecast move too); Hungaroring 4 and Silverstone 18, each a car short since round 329,
            # keep every car, so both leave this list, which is empty now: every case takes the (7, 0)
            # default. Hungaroring 4: p7 (lost on its 11th move in round 329, at turn 87) now finishes sixth on
            # its 127th, p1 (sixth before, on its 128th) seventh on its 129th, p3 is still the car running at
            # the end, after 128 moves, and p5, p6, p8, p2 and p4 finish first to fifth as before, on their
            # 121st, 122nd, 123rd, 125th and 126th (873 moves, under the ceiling of 889). Silverstone 18: p3
            # (lost on its 57th move in round 329, at turn 451) now finishes third on its 84th, p4 (fourth
            # before, on its 85th) second on its 83rd, p1 and p5 (second and third before, on their 84th)
            # fourth and fifth on their 85th, p7 (the car still running at the end before, after 85 moves)
            # sixth on its 86th, p8 (sixth before, on its 85th) seventh on its 86th, p6 (fifth before, on its
            # 85th) is the car still running at the end, after 86 moves, and p2 still wins on its 83rd (592
            # moves, under the ceiling of 594).
            SAFETY = {}
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
        # Round 260 (the chooser): an AI2 car dies here now. The rule records
        # the crash rather than vetoing it (AGENTS.md); the pin keeps the
        # measured pair, so a further change still fails.
        # Round 278: the AI2 car keeps its race, so the mixed field is crash-free again.
        # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one
        # stronger forecast move too); an AI2 car dies here again: p7 (fifth home before, on its 116th
        # move) crashes on its 10th, at turn 79, ((85,29)->(85,24) at v(0,-4), into the outer wall of the
        # first right-hander): on its 9th, at turn 71, p1 held (85,30) and p6 (85,31), so its only free landing
        # on the track was (85,29), the outer wall's corner, from which every landing crosses the wall.
        # p1 (seventh before, on its 119th) is now second on its 114th, p3 (the car still running at the
        # end before, after 118 moves) third on its 115th, p4, p5 and p6 (second to fourth before, on
        # their 113th, 114th and 115th) fourth to sixth on their 116th, 117th and 118th, p8 (sixth before,
        # on its 117th) is the car still running at the end, after 117 moves, and p2 still wins on its
        # 112th; the place sums move from 18 and 18 to AI1 10 and AI2 26 -- recorded, not vetoed
        # (AGENTS.md). As in round 260, the pin keeps the measured pair, AI2 (4, 1).
        if mixed["AI1"][1:] != (4, 0) or mixed["AI2"][1:] != (4, 1):
            raise SystemExit(f"mixed Monaco seed-9 safety regression: {mixed}")

    print(
        "AI1StagedPaceRegression: OK "
        "(three-ahead Coil/Hungaroring gains; low-speed Hungaroring and "
        "ambiguous Le Mans vetoes; stationary-grid Silverstone gain; "
        "mixed Monaco seed 9 safety pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
