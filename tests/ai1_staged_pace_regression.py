#!/usr/bin/env python3
"""Pin the Round-82/91 self-play-only staged-pace boundaries.

Decision specimens (2026-11-13): on round 345's grids the thirteen races below
hold six real switches of the staged override, none with exactly three rivals
ahead (round 82's class) and none from rest on the grid (round 91's). The pin
also races one race with each: Le Mans seed 1 on the live track and Coil seed 6
(THREE_AHEAD_SPECIMEN and LAUNCH_SPECIMEN below). Two of the boundaries it was
written for cannot be raced by an all-AI field any more: the finite field
rollout of the three-ahead class left the code in round 291 (Le Mans s3), and
since round 223 only a human rival closes the self-play gate (Monaco s9).
"""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
import decision_specimen  # noqa: E402

# Round 233 (the lane spread left the score): every ceiling re-anchored from
# measurement, and three races lose a car -- recorded, not vetoed (AGENTS.md).
# Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
# every case starts from a new grid and is a new race, and every ceiling below was measured on a race on the grid
# before round 345, so each is re-anchored to its new race: the ceiling is the new race's measured finisher move
# sum, with no margin, as round 233 and every later re-anchoring set it. Each entry's round-345 note gives its
# race; the cars a race loses are under SAFETY in main().
CASES = {
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
    # p1 to p4 finish first to fourth on their 121st to 124th moves, p6 fifth on its 125th, p8 sixth on its 126th and
    # p5 seventh on its 128th; no crash, and p7 is the car still running at the end, after 127 moves: 869 moves, the
    # ceiling (889 before, measured on the grid before round 345).
    ("hungaroring", 4): 869,
    # Round 247: seven finishers here now instead of six, so the sum grows.
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
    # p1 to p5 finish first to fifth on their 79th, 80th, 81st, 82nd and 82nd moves, and p6 and p7 sixth and seventh
    # on their 83rd; no crash, and p8 is the car still running at the end, after 82 moves: 570 moves, the ceiling
    # (573 before, measured on the grid before round 345).
    ("spa", 4): 570,
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
    # p1 to p7 finish first to seventh on their 124th to 130th moves; no crash, and p8 is the car still running at the
    # end, after 129 moves: 889 moves, the ceiling (897 before, measured on the grid before round 345).
    ("interlagos", 3): 889,
    # Round 234: Le Mans seed 3 keeps both of the cars it used to lose, so
    # seven finishers are counted here instead of five and the sum grows.
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
    # seven finishers and no crash (the list is under EXACT_MOVES), and p6 is the car still running at the end, after
    # 72 moves: 486 moves, the ceiling (501 before, measured on the grid before round 345).
    ("lemans", 3): 486,
    # Round 234: seven finishers here now instead of six, so the sum grows.
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
    # six finishers: p2 wins on its 66th move, p3 is second on its 67th, p5 third on its 68th, p6 and p7 fourth and
    # fifth on their 69th, and p1 sixth on its 71st; p8 crashes on its 7th (see the safety notes in main), and p4 is
    # the car still running at the end, after 70 moves: 410 moves, the ceiling (489 before, measured on the grid
    # before round 345).
    ("lemans", 11): 410,
    # Round 229: re-anchored from measurement (the soft caution stack left the score).
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
    # p5 wins on its 78th move, p6 is second on its 79th, p3 third on its 82nd, p8 fourth on its 83rd, p2 and p7 fifth
    # and sixth on their 84th, and p1 seventh on its 85th; no crash, and p4 is the car still running at the end, after
    # 84 moves: 575 moves, the ceiling (569 before, measured on the grid before round 345).
    ("spa", 11): 575,  # Round 247: re-anchored from measurement.
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
    # six finishers (the list is under EXACT_MOVES); p8 crashes on its 75th move (see the safety notes in main), and
    # p7 is the car still running at the end, after 85 moves: 502 moves, the ceiling (601 before, measured on the grid
    # before round 345).
    ("silverstone", 15): 502,  # Round 229: re-anchored from measurement  # Round 229: re-anchored from measurement  # Round 229: re-anchored from measurement
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
    # p2 and p5 finish first and second on their 82nd moves, p3 and p6 third and fourth on their 83rd, p1 fifth on its
    # 84th, and p4 and p7 sixth and seventh on their 86th; no crash, and p8 is the car still running at the end, after
    # 85 moves: 586 moves, the ceiling (594 before, measured on the grid before round 345).
    ("silverstone", 18): 586,  # Round 229: re-anchored from measurement  # Round 229: re-anchored from measurement
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
    # p1 wins on its 58th move, p2 and p8 are second and third on their 59th, p5 fourth on its 60th, and p3, p4 and p6
    # fifth to seventh on their 61st; no crash, and p7 is the car still running at the end, after 60 moves: 419 moves,
    # the ceiling (421 before, measured on the grid before round 345).
    ("coil", 18): 419,  # Rounds 234 and 247: re-anchored from measurement.
    # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes).
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
    # p1 wins on its 122nd move, p2 is second on its 123rd, p6 third on its 124th, p7 fourth on its 125th, p8 fifth on
    # its 126th, p3 sixth on its 128th and p4 seventh on its 129th; no crash, and p5 is the car still running at the
    # end, after 128 moves: 877 moves, the ceiling (884 before, measured on the grid before round 345).
    ("hungaroring", 8): 877,
    # Round 234: seven finishers here now instead of six, so the sum grows.
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
    # six finishers: p1 and p2 finish first and second on their 121st and 122nd moves, and p4, p5, p6 and p7 third to
    # sixth on their 123rd to 126th; p3 crashes on its 5th (see the safety notes in main), and p8 is the car still
    # running at the end, after 125 moves: 741 moves, the ceiling (877 before, measured on the grid before round 345).
    ("hungaroring", 10): 741,
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
    # p1, p2 and p3 finish first to third on their 121st, 122nd and 123rd moves, p7 fourth on its 124th, p8 fifth on
    # its 125th, p4 sixth on its 127th and p5 seventh on its 128th; no crash, and p6 is the car still running at the
    # end, after 127 moves: 870 moves, the ceiling (890 before, measured on the grid before round 345).
    ("hungaroring", 25): 870,
}

# A same-sum field redistribution at Le Mans seed 3 is the ambiguity boundary:
# the three-ahead class must retain the exact integrated-frontier finish list.
# Round 231: re-frozen from recorded checkpoint-choice races; the existing
# assertion logic and AI1/AI2 identity checks remain intact.
# Round 248 (the physical world model): Le Mans seed 3 has six finishers.
# Round 345: that boundary was the Le Mans seed-3 race on the grid before round 345. Every seed now starts from a
# new grid and is a new race, and each list below pins its new race's finish list exactly, as measured.
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
    # Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full policy in every
    # decision); the same seven finishers in the same order, p7 home one move later, on its 72nd (on its 71st since round
    # 330), and p8 still the car running at the end, after 71 moves (70 before); no crash, one move more (482 -> 483) --
    # the list pinned from round 310 to round 329 again -- and the ceiling above keeps its value.
    # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy);
    # the same seven finishers in the same order, p7 home one move earlier, on its 71st (on its 72nd since round 333),
    # and p8 still the car running at the end, after 70 moves (71 before); no crash, one move fewer (483 -> 482) --
    # the list of rounds 303 and 330 again -- and the ceiling above keeps its value.
    # Round 341: re-frozen from measurement (the score's rival twin plays the rival's own gate rules).
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
    # p3 wins on its 66th move, p5 is second on its 67th, p7 third on its 68th, p8 fourth on its 69th, p1 fifth on its
    # 71st, p2 sixth on its 72nd and p4 seventh on its 73rd; no crash, and p6 is the car still running at the end,
    # after 72 moves (486 moves, the ceiling above).
    ("lemans", 3): [66, 67, 68, 69, 71, 72, 73],
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
    # Round 331: re-frozen from measurement (the relevant rival keeps its three stronger forecast moves beside the second
    # and third rivals'); p2 still wins on its 83rd move, p1 (fifth before, on its 85th) is now second on its 84th, p3
    # (second before, on its 83rd) third on its 84th, p4 (third before, on its 84th) fourth on its 85th, p5 fifth on its
    # 85th (sixth before), p6 (fourth before, on its 84th) sixth on its 86th, p7 seventh on its 86th (on its 85th before),
    # and p8 is still the car running at the end, after 85 moves (84 before); no crash, four moves more (589 -> 593), and
    # the ceiling above keeps its value.
    # Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full policy in every
    # decision); six finishers now instead of seven: p6 (sixth home before, on its 86th) crashes on its 76th move (see the
    # safety notes in main), p7 is now sixth on its 86th (seventh before), p8 is still the car running at the end, after
    # 85 moves, and p2, p1, p3, p4 and p5 finish first to fifth as before, on their 83rd, 84th, 84th, 85th and 85th; the
    # sum drops with the lost car (593 -> 507), and the ceiling above keeps its value.
    # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy);
    # still six finishers, a different car lost: p5 (fifth home before, on its 85th) now crashes on its 75th move (see
    # the safety notes in main), p6 (lost on its 76th move in round 333) is now fifth on its 85th, p1 (second before, on
    # its 84th) now wins on its 83rd, p2 (the winner before, on its 83rd) is second on its 83rd, p4 fourth on its 84th
    # (on its 85th before), p3 and p7 finish third and sixth as before, on their 84th and 86th, and p8 is still the car
    # running at the end, after 85 moves; two moves fewer (507 -> 505), and the ceiling above keeps its value.
    # Round 335: re-frozen from measurement (every rival but the relevant one plays its first two forecast moves by its
    # full policy); seven finishers again and no crash: p5 (lost on its 75th move in round 334) is now the car still
    # running at the end, after 86 moves (see the safety notes in main), p8 (the car still running at the end before,
    # after 85 moves) seventh on its 86th, p2 (second before, on its 83rd) now wins on its 83rd, p1 (the winner before,
    # on its 83rd) is second on its 84th, p6 (fifth before, on its 85th) third on its 84th, p3 (third before, on its
    # 84th) fourth on its 85th, p7 (sixth before, on its 86th) fifth on its 85th, and p4 (fourth before, on its 84th)
    # sixth on its 86th; the sum grows with the regained car (505 -> 593) -- round 331's list again, in a new order --
    # and the ceiling above keeps its value.
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
    # six finishers: p1 wins on its 82nd move, p3 and p4 are second and third on their 83rd, p5 and p6 fourth and
    # fifth on their 84th, and p2 sixth on its 86th; p8 crashes on its 75th, at turn 600, across the needle (see the
    # safety notes in main), and p7 is the car still running at the end, after 85 moves (502 moves, the ceiling above).
    ("silverstone", 15): [82, 83, 83, 84, 84, 86],
}


# Decision specimens (2026-11-13). A fleet scan (the 83 courses other than the Nordschleife over seeds 1-40, eight
# AI2 cars, one lap, random starts: 3,320 races; a scratch build that prints the legs of top-level decisions only)
# found the staged override switching 2,279 real picks: 99 with exactly three rivals ahead, the class round 82
# opened, and 30 from rest on the grid, where round 91 orders the cars by track distance.
# Le Mans s1, the live track (the Le Mans races above run the frozen fixture geometry): at turn 85 p5, on its 11th
# move, stands at (37,17) with v(3,-4) and exactly three live rivals ahead ((rival - mover) . velocity > 0): p4 at
# (38,16), p6 at (38,15) and p1 at (43,13). Its pick is S to v(3,-3), 18 speed2, above round 82's floor of 16, and
# the override switches it to SE, v(4,-3), 25 speed2, one map turn faster (136 to 135). The race has six finishers
# and one crash: p6 wins on its 147th move, p8, p1 and p2 follow on their 148th, 149th and 150th and p3 and p4 on
# their 152nd, p7 crashes on its 54th move (turn 431), and p5 is the car still running at the end, after 151 moves
# (1,103 turns). With the override off in top-level decisions only, a twin scratch build races the same race through
# turn 84 and plays S at turn 85.
THREE_AHEAD_SPECIMEN = decision_specimen.Specimen(
    "lemans", 1, (6, 1, [147, 148, 149, 150, 152, 152]),
    "37f5048d64f5df2f3d99429166d88a2ee4f5ce869e83c5a5b0cde9bac98dd5f6",
    "85 p5 AI SE v(3,-4)→(4,-3) (37,17)→(41,14) ok",
)
# Coil s6: at turn 2 p2 makes its first move, from rest on the grid at (82,48), with five rivals ahead by track
# distance. Its pick is E, and the override switches it to N, v(0,-1), one map turn faster (58 to 57). The race has
# seven finishers and no crash: p1 wins on its 58th move, p2 and p4 follow on their 59th, p3, p5 and p6 on their 60th
# and p7 on its 61st, and p8 is the car still running at the end, after 60 moves (477 turns). With the override off
# in top-level decisions only, the twin races the same race through turn 1 and plays E at turn 2.
LAUNCH_SPECIMEN = decision_specimen.Specimen(
    "coil", 6, (7, 0, [58, 59, 59, 60, 60, 60, 61]),
    "816c31c703e3f45641b150db847d3de095c809a22b24c625aa380028f9687c1d",
    "2 p2 AI N v(0,0)→(0,-1) (82,48)→(82,47) ok",
)


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
            # Round 331: re-frozen from measurement (the relevant rival keeps its three stronger forecast
            # moves beside the second and third rivals'); three races lose a car and join this list --
            # recorded, not vetoed (AGENTS.md). Spa 4, whole since round 278: p1 (fifth home before, on its
            # 82nd move) crashes on its 28th, at turn 217, ((105,136)->(104,141) at v(-1,5), into the
            # outer wall of the right-hand kink before the hairpin): on its 24th, at turn 185, p4 held
            # (101,115) and p6 (101,116), the two landings from which it could still make the kink, so every
            # free landing reached the wall within six moves. p8 (third before, on its 80th) is now second on
            # its 79th, p2 and p3 (fourth and sixth before, on their 81st and 82nd) third and fourth on their
            # 81st, p6 (the car still running at the end before, after 82 moves) fifth on its 82nd, p7 (second
            # before, on its 79th) sixth on its 82nd, p4 (seventh home on its 83rd before) is the car still
            # running at the end, after 82 moves, and p5 still wins on its 78th. Spa 11, whole in every round
            # since this pin began (round 83): p7 (seventh home before, on its 82nd move) crashes on its 5th,
            # at turn 39, ((34,14)->(35,10) at v(1,-4), into the inside wall of the first corner): every
            # landing on the track from (34,14) at v(0,-3) -- (33,10), (33,11), (34,11), (33,12) and (34,12)
            # -- was held, by p4, p6, p1, p3 and p2, so every free landing crosses the wall. p6 (sixth before,
            # on its 82nd) is now third on its 80th, p3 (third before, on its 80th) fourth on its 82nd, p4 and
            # p5 (fourth and fifth before, on their 81st) fifth on its 82nd and sixth on its 83rd, p8 is still
            # the car running at the end, after 82 moves (81 before), and p1 and p2 finish first and second as
            # before, on their 78th and 79th. Hungaroring 25, whole since round 328: p6 (the car still running
            # at the end before, after 127 moves) crashes on its 6th move, at turn 46, ((95,147)->(97,149) at
            # v(2,2), along the outer wall on the run to the first corner -- the cells p4 crashed on in round
            # 316): on its 5th, at turn 38, it ran onto (95,147), on the wall's line, from which at v(3,2) the
            # one landing that stays on the track is (97,150), and p4 took that landing on its 6th, at turn 44
            # (in round 330 p4 coasted to (97,151) there and p6 took (97,150)). p4 (seventh home before, on its
            # 128th) is the car still running at the end, after 126 moves, and p3, p5, p7, p8, p1 and p2 finish
            # first to sixth as before. Hungaroring 4 and Silverstone 18, whole again since round 330, keep
            # every car (872 and 589 moves, under the ceilings of 889 and 594).
            # Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its
            # full policy in every decision). Spa 4, a car short since round 331, keeps every car, so it leaves
            # this list and takes the (7, 0) default: p1, lost on its 28th move in round 331, now makes the
            # kink -- at turn 217, where it crashed from (105,136) before, it runs from (102,141) to (100,147)
            # -- and is the car still running at the end, after 83 moves; p5 still wins, on its 79th (78th
            # before), p7 (sixth before, on its 82nd) is now second on its 80th, p3 (fourth before) third on
            # its 81st, p8 (second before, on its 79th) fourth on its 81st, p4 (the car still running at the
            # end before, after 82 moves) fifth on its 82nd, p2 (third before, on its 81st) sixth on its 83rd,
            # and p6 (fifth before, on its 82nd) seventh on its 83rd (569 moves, under the ceiling of 573).
            # Silverstone 15, whole in every round since this pin began (round 83), drops one and joins this
            # list -- recorded, not vetoed (AGENTS.md): p6 (sixth home before, on its 86th move) crashes on its
            # 76th, at turn 606, ((30,31)->(25,31) at v(-5,0), across the needle that forms the inside wall of
            # the hairpin before the finish, one cell short of its tip): on its 75th, at turn 598, it ran onto
            # (30,31), from which at v(-4,1) the one landing that stays on the track is (27,33), round the
            # needle's tip, and p4 took that landing on its 76th, at turn 604, so every free landing crosses
            # the wall. p7 (seventh before, on its 86th) is now sixth on its 86th, p8 is still the car running
            # at the end, after 85 moves, and p2, p1, p3, p4 and p5 finish first to fifth as before. Spa 11
            # (p7 on its 5th move, at turn 39; the race is round 331's through turn 102) and Hungaroring 25
            # (p6 on its 6th, at turn 46; the race is unchanged) still drop one each.
            # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its
            # full policy). Spa 11 and Hungaroring 25, each a car short since round 331, keep every car, so both
            # leave this list and take the (7, 0) default. Spa 11: p7, lost on its 5th move since round 331, now
            # makes the first corner -- at turn 39, where it crashed from (34,14) before, it runs from (31,14) to
            # (32,12) -- and finishes fourth on its 81st; p5 (sixth before, on its 83rd) is now second on its 79th,
            # p8 (the car still running at the end before, after 82 moves) fifth on its 82nd, p4 (fifth before, on
            # its 82nd) sixth on its 83rd, p2 (second before, on its 79th) seventh on its 84th, p3 (fourth before, on
            # its 82nd) is the car still running at the end, after 83 moves, and p1 and p6 finish first and third as
            # before, on their 78th and 80th (567 moves, under the ceiling of 569). Hungaroring 25: p6, lost on its
            # 6th move since round 331, now makes the run to the first corner -- at turn 46, where it crashed from
            # (95,147) before, it runs from (92,145) to (95,148) -- and is the car still running at the end, after
            # 127 moves, p4 (the car still running at the end before, after 126 moves) is seventh on its 128th, and
            # p3, p5, p7, p8, p1 and p2 finish first to sixth as before -- the classification of rounds 328 to 330
            # again (871 moves, under the ceiling of 890). Silverstone 15 still drops one, now p5 -- recorded, not
            # vetoed (AGENTS.md): p5 (fifth home before, on its 85th move) crashes on its 75th, at turn 597, on the
            # cells p6 crashed on in round 333 ((30,31)->(25,31) at v(-5,0), across the needle that forms the
            # inside wall of the hairpin before the finish): on its 74th, at turn 589, it ran onto (30,31), from
            # which at v(-4,1) the one landing that stays on the track is (27,33), round the needle's tip, and p3
            # took that landing on its 75th, at turn 595, so every free landing crosses the wall. The race is round
            # 333's through turn 85; p6, lost on its 76th move in round 333, is now fifth on its 85th (the rest is
            # under EXACT_MOVES). The other nine cases keep every car, as in round 333, each under its ceiling.
            # Round 335: re-frozen from measurement (every rival but the relevant one plays its first two forecast
            # moves by its full policy). Silverstone 15, a car short since round 333, keeps every car, so it leaves
            # this list and takes the (7, 0) default: p5, lost on its 75th move in round 334, now rounds the needle --
            # at turn 597, where it crashed from (30,31) before, it runs from (39,29) to (35,29), two moves further
            # back -- and is the car still running at the end, after 86 moves (the race is round 334's through turn
            # 355; the rest is under EXACT_MOVES). Three races lose a car and join this list -- recorded, not vetoed
            # (AGENTS.md). Silverstone 18, whole since round 330: p7 (seventh home before, on its 85th move) crashes
            # on its 75th, at turn 599, on the cells of Silverstone 15's crash in rounds 333 and 334 ((30,31)->(25,31)
            # at v(-5,0), across the needle that forms the inside wall of the hairpin before the finish): on its 74th,
            # at turn 591, it ran onto (30,31), from which at v(-4,1) the one landing that stays on the track is
            # (27,33), round the needle's tip, and p4 took that landing on its 75th, at turn 596, so every free landing
            # crosses the wall. The race is round 334's through turn 389; p1 (second before, on its 83rd) now wins on
            # its 83rd, p3 (the winner before, on its 82nd) is second on its 83rd, p2 and p4 (fourth and third before,
            # on their 84th and 83rd) third and fourth on their 84th, p5 fifth on its 85th (on its 84th before), p8
            # (the car still running at the end before, after 84 moves) sixth on its 85th, and p6 (sixth before, on its
            # 85th) is the car still running at the end, after 85 moves (504 moves, under the ceiling of 594).
            # Hungaroring 8, whole since round 329: p5 (the car still running at the end before, after 127 moves)
            # crashes on its 46th move, at turn 365, ((56,117)->(58,119) at v(2,2), into the outer wall of the bend
            # where p3 crashed in round 328): on its 44th, at turn 349, from (49,110) at v(5,4), p8 held (53,113), the
            # one landing from which it could still make the bend (taken on p8's 43rd, at turn 344), so every free
            # landing reached the wall within two moves. The race first plays differently on p3's 1st move, at turn
            # 3; p8 (fifth before, on its 125th) is the car still running at the end, after 126 moves, p1 and p3
            # (sixth and seventh before, on their 127th and 128th) fifth and sixth on their 126th and 127th, and p2,
            # p4, p6 and p7 finish first to fourth as before, on their 121st, 122nd, 123rd and 124th (743 moves, under
            # the ceiling of 884). Hungaroring 25, whole again since round 334: p1 (fifth home before, on its 126th
            # move) crashes on its 47th, at turn 369, ((60,117)->(62,118) at v(2,1), into the outer wall of the same
            # bend, where p4 crashed in round 326): on its 46th, at turn 361, from (57,115) at v(4,2), p4 held
            # (60,116), the one landing from which it could still make the bend (taken on p4's 45th, at turn 356), so
            # its free landings on the track, (61,116), (62,116) and (60,117), each left every landing across the
            # wall. The race first plays differently on p1's 1st move, at turn 1; p2 and p4 (sixth and seventh before,
            # on their 127th and 128th) are now fifth and sixth on their 126th and 127th, p6 is still the car running
            # at the end, after 126 moves (127 before), and p3, p5, p7 and p8 finish first to fourth as before, on
            # their 121st, 122nd, 123rd and 124th (743 moves, under the ceiling of 890). The other eight cases keep
            # every car, as in round 334, each under its ceiling.
            # Round 336: re-frozen from measurement (gates are ordinary landings wherever the exact potential prices
            # them). Hungaroring 8, a car short since round 335, keeps every car, so it leaves this list and takes the
            # (7, 0) default: p5, lost on its 46th move in round 335, now makes the bend. The race first plays
            # differently on p8's 42nd move, at turn 336, where it brakes a notch harder, to (48,111) instead of
            # (49,111); after its 43rd, at turn 344, it stands on (52,113), so (53,113), the one landing from which p5
            # could still make the bend, is free, p5 takes it on its 44th, at turn 349, and at turn 365, where it
            # crashed from (56,117) before, it runs from (57,115) to (60,116). p5 is seventh home on its 128th, p8 is
            # still the car running at the end, after 127 moves (126 before), and p2, p4, p6, p7, p1 and p3 finish
            # first to sixth as before, on their 121st, 122nd, 123rd, 124th, 126th and 127th (871 moves, under the
            # ceiling of 884). Silverstone 18 and Hungaroring 25, each a car short since round 335, still drop one --
            # recorded, not vetoed (AGENTS.md). Silverstone 18: p7 on its 75th, at turn 599; the race is round 335's
            # byte for byte. Hungaroring 25: p1 on its 47th, at turn 369, on the same cells and in the same way; the
            # race is round 335's through turn 370 (the first move that differs is p3's 47th, at turn 371), p3, p5, p7,
            # p8, p2 and p4 finish first to sixth as before, and p6 is still the car running at the end, after 126
            # moves. The other nine cases keep every car, as in round 335, each under its ceiling. Silverstone 15, Spa
            # 4, Spa 11 and Coil 18 are round 335's races byte for byte, and Le Mans 3, which first plays differently
            # on p1's 24th move, at turn 185, comes home on the same moves, so both lists under EXACT_MOVES stand.
            # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64
            # stream). Every case starts from a new grid and is a new race; the races narrated above were races on the
            # grid before round 345. Three new races lose a car and make up this list -- recorded, not vetoed
            # (AGENTS.md). Le Mans 11: p8 crashes on its 7th move, at turn 56, NW from (9,23) at v(1,-4) to (9,18) at
            # v(0,-5); it ran onto (9,23) on its 6th, at turn 48, W from (8,27) at v(2,-4). p2, p3, p5, p6, p7 and p1
            # finish first to sixth on their 66th, 67th, 68th, 69th, 69th and 71st, and p4 is the car still running at
            # the end, after 70 moves (410 moves, the ceiling). Silverstone 15: p8 crashes on its 75th move, at turn
            # 600, on the cells of the needle crashes of rounds 333 to 335 ((30,31)->(25,31) at v(-5,0), across the
            # needle that forms the inside wall of the hairpin before the finish): on its 74th, at turn 592, it ran
            # onto (30,31), from which at v(-4,1) the one landing that stays on the track is (27,33), round the needle's
            # tip; p4 held that landing then (since its 74th, at turn 588), and p5 took it on its 75th, at turn 597, as
            # p4 left it, so every free landing crosses the wall. p1, p3, p4, p5, p6 and p2 finish first to sixth (the
            # list is under EXACT_MOVES), and p7 is the car still running at the end, after 85 moves (502 moves, the
            # ceiling). Hungaroring 10: p3 crashes on its 5th move, at turn 35, on the cells of Hungaroring 25's crashes
            # in rounds 316 and 331 ((95,147)->(97,149) at v(2,2), along the outer wall on the run to the first
            # corner): on its 4th, at turn 27, it ran onto (95,147), on the wall's line, from which at v(3,2) the one
            # landing that stays on the track is (97,150), and p7 took that landing on its 4th, at turn 31, so every
            # free landing crosses the wall. p1, p2, p4, p5, p6 and p7 finish first to sixth on their 121st to 126th,
            # and p8 is the car still running at the end, after 125 moves (741 moves, the ceiling). The other nine
            # cases, Silverstone 18 and Hungaroring 25 (on this list before) among them, finish seven cars with no
            # crash and take the (7, 0) default, each at its ceiling.
            SAFETY = {("lemans", 11): (6, 1), ("silverstone", 15): (6, 1), ("hungaroring", 10): (6, 1)}
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
        # Round 345: that race, and every race narrated below, was a race on the
        # grid before round 345; seed 9 now starts from a new grid (see the
        # round-345 note below).
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
        # Round 331: re-frozen from measurement (the relevant rival keeps its three stronger forecast
        # moves beside the second and third rivals'); a second AI2 car dies here: p5 (fifth home before,
        # on its 117th move) crashes on its 17th, at turn 127, ((106,3)->(107,-1) at v(1,-4), into the
        # outer wall where the climb turns right): on its 15th, at turn 113, p4 held (103,7), the one
        # landing from which it could still make the bend, so every free landing reached the wall within
        # two moves. p7 still crashes on its 10th, at turn 79, as in round 330: the race is round 330's
        # through turn 108. p4 (fourth before, on its 116th) is now second on its 113th, p6 (sixth before,
        # on its 118th) third on its 114th, p8 (the car still running at the end before, after 117 moves)
        # fourth on its 115th, p1 (second before, on its 114th) fifth on its 117th, p3 (third before, on
        # its 115th) is the car still running at the end, after 116 moves, and p2 still wins on its 112th;
        # the place sums move from AI1 10 and AI2 26 to AI1 14 and AI2 22 -- recorded, not vetoed
        # (AGENTS.md). As in rounds 260 and 330, the pin keeps the measured pair, AI2 (4, 2).
        # Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its
        # full policy in every decision); both AI2 cars keep their race and an AI1 car dies instead, the
        # first this pin has recorded: p3 (the car still running at the end before, after 116 moves)
        # crashes on its 9th move, at turn 67, ((84,32)->(82,28) at v(-2,-4), into the outer wall of the
        # first right-hander, the wall p7 hit before): on its 8th, at turn 59, p1 held (84,33), the one
        # landing from which it could still make the bend, so its only free landing on the track was
        # (84,32), on the outer wall's line, from which every landing crosses the wall. The race first
        # plays differently on p7's 4th move, at turn 31; p7 (lost on its 10th move since round 330) is
        # now the car still running at the end, after 117 moves, p5 (lost on its 17th in round 331) third
        # on its 114th, p6, p8 and p1 (third to fifth before, on their 114th, 115th and 117th) fourth to
        # sixth on their 115th, 116th and 118th, and p2 and p4 still finish first and second, on their
        # 112th and 113th; the place sums move from AI1 14 and AI2 22 to AI1 17 and AI2 19 -- recorded,
        # not vetoed (AGENTS.md). As in rounds 260, 330 and 331, the pin keeps the measured pair, now
        # AI1 (4, 1) and AI2 (4, 0).
        # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its
        # full policy); the AI1 car keeps its race and two AI2 cars die again. The race is round 331's
        # through turn 45 (round 333's left it on p7's 4th move, at turn 31). p3, lost on its 9th move in
        # round 333, brakes harder on its 7th, at turn 51, as in round 331, and at turn 67, where it crashed
        # from (84,32) before, runs from (84,34) to (84,32) at v(0,-2); it is again the car still running at
        # the end, after 116 moves. p7 (the car still running at the end before, after 117 moves) again
        # crashes on its 10th, at turn 79, as in rounds 330 and 331 ((85,29)->(85,24) at v(0,-5), into the
        # outer wall of the first right-hander): on its 9th, at turn 71, p1 held (85,30) and p6 (85,31), so
        # its only free landing on the track was (85,29), the outer wall's corner, from which every landing
        # crosses the wall. p8 (fifth home before, on its 116th move) crashes on its 68th, at turn 486,
        # ((12,109)->(11,113) at v(-1,4), into the outer wall of the left-hand kink at the end of the narrow
        # run south): on its 67th, at turn 479, from (12,104) at v(0,6), p1 held (13,109), the one landing
        # from which it could still make the kink (taken on p1's 67th, at turn 473), so its free landings on
        # the track, (12,109), (13,110) and (13,111), each left every landing across the wall. p1 (sixth
        # before, on its 118th) is now fifth on its 117th, and p2, p4, p5 and p6 still finish first to
        # fourth, on their 112th, 113th, 114th and 115th; the place sums move from AI1 17 and AI2 19 to AI1
        # 14 and AI2 22 -- recorded, not vetoed (AGENTS.md). As in rounds 260, 330, 331 and 333, the pin
        # keeps the measured pair, now AI1 (4, 0) and AI2 (4, 2) -- round 331's pair again.
        # Round 335: re-frozen from measurement (every rival but the relevant one plays its first two forecast moves
        # by its full policy); one of the two AI2 cars keeps its race. The race first plays differently on p7's 2nd
        # move, at turn 15, where it steps south to (94,51) instead of waiting on (94,50). p7, lost on its 10th move
        # in rounds 330, 331 and 334, now makes the first right-hander -- at turn 79, where it crashed from (85,29)
        # before, it runs from (86,38) to (85,36) -- and is the car still running at the end, after 117 moves; p3
        # (the car still running at the end before, after 116 moves) is now sixth on its 118th. p8 still crashes on
        # its 68th, on the same cells and in the same way, now at turn 544 (486 before): on its 67th, at turn 536,
        # from (12,104) at v(0,6), p1 held (13,109), the one landing from which it could still make the kink (taken
        # on p1's 67th, at turn 529), so its free landings on the track, (12,109), (13,110) and (13,111), each left
        # every landing across the wall. p2, p4, p5, p6 and p1 still finish first to fifth, on their 112th, 113th,
        # 114th, 115th and 117th; the place sums stay AI1 14 and AI2 22 -- recorded, not vetoed (AGENTS.md). As in
        # rounds 260, 330, 331, 333 and 334, the pin keeps the measured pair, now AI1 (4, 0) and AI2 (4, 1) -- the
        # pair of rounds 260 and 330 again.
        # Round 336: re-frozen from measurement (gates are ordinary landings wherever the exact potential prices
        # them); the last AI2 car keeps its race and the mixed field is crash-free again, for the first time since
        # round 329. The race first plays differently on p1's 34th move, at turn 265, where it steps east to (119,4)
        # instead of south to (118,5). p1 then comes down from the climb behind p8 instead of ahead of it, crossing
        # the first checkpoint on its 51st, at turn 401 (on its 48th, at turn 377, before), a turn after p8, so it no
        # longer holds (13,109) at the kink. p8, lost on its 68th move in rounds 334 and 335, holds its speed on its
        # 66th, at turn 528, landing on (12,103) at v(0,5) instead of accelerating to (12,104) at v(0,6), and takes
        # p6's line round the kink: at turn 544, where it crashed from (12,109) before, it runs from (13,107) to
        # (15,111). It finishes fifth on its 116th, as in round 333. p1 (fifth before, on its 117th) is now sixth on
        # its 118th, p3 (sixth before, on its 118th) seventh on its 119th, p7 is still the car running at the end,
        # after 118 moves (117 before), and p2, p4, p5 and p6 still finish first to fourth, on their 112th, 113th,
        # 114th and 115th; the place sums move from AI1 14 and AI2 22 to AI1 16 and AI2 20. As in rounds 260, 330,
        # 331, 333, 334 and 335, the pin keeps the measured pair, now AI1 (4, 0) and AI2 (4, 0) -- the pair of rounds
        # 278 to 329 again, the crash-free field this check began with.
        # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream);
        # seed 9 starts from a new grid and is a new race, and the mixed field is crash-free: p4, an AI1 car, wins on
        # its 113th move, the four AI2 cars p5, p6, p7 and p8 are second to fifth on their 114th, 115th, 116th and
        # 117th, p2 and p3 sixth and seventh on their 119th and 120th, and p1 is the car still running at the end,
        # after 120 moves; the place sums are AI1 22 and AI2 14. As in every round since 260, the pin keeps the
        # measured pair, AI1 (4, 0) and AI2 (4, 0).
        if mixed["AI1"][1:] != (4, 0) or mixed["AI2"][1:] != (4, 0):
            raise SystemExit(f"mixed Monaco seed-9 safety regression: {mixed}")

    decision_specimen.check("staged three-ahead", THREE_AHEAD_SPECIMEN)
    decision_specimen.check("staged launch", LAUNCH_SPECIMEN)

    # Round 345: the message named the races before round 345 (round 82/91's gains and vetoes); it names what is
    # pinned.
    print(
        "AI1StagedPaceRegression: OK "
        "(twelve all-AI1 races: finisher and crash counts and move-sum ceilings pinned, "
        "Le Mans seed 3 and Silverstone seed 15 finish lists exact; "
        "mixed Monaco seed 9 safety pinned; "
        "decision specimens pinned on Le Mans s1 and Coil s6)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
