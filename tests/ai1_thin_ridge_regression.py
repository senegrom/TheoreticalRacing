#!/usr/bin/env python3
"""Pin the Round-178 thin-ridge hold check.

The lobe2 harvest-32 crashes commit by HOLDING max-axis 10 onto a
one-lane alive-map ridge (<= 2 alive successors at the chosen landing)
whose single thread a rival body closes 40 cells downstream. No train
rival within Chebyshev 3, ring-wide waist, dense field -- invisible to
the round-175 bar, the round-83 funnel signal, and the round-83 deep
guard alike. The root check audits scorer-8 (never a verdict), escalates
DEAD-or-loud (thread >= 4) fires to the true-6 verdict, and switches
only to a certified quiet-alive alternative. Rounds 178-180 were
promoted on the user's order, so every car runs the ridge check and
both lobe2 races (seeds 111 and 132) had to run crash-free.

Round 185 selectively extends that audit to a trap-zero, signed speed-10
hold whose three alive exits narrow to child widths exactly 1/2/3. On
rand13 seed 4, player 7's old S line crashes three turns later; the
scorer certificate instead selects SE, which finishes third; the mixed
roster below must take that same promoted rescue.

Round 305/309 (aware plays the mover's first five forecast continuation
moves; a rival's forecast crash is no win): seed 132 is no longer
crash-free. p6 and p8, both AI2 slots, run straight along row 8 at the
top of the course by their 14th moves, braking one notch a round, and at
v(-5,0) cannot make the bend: both crash into its outer wall on their
17th moves. Recorded, not vetoed (AGENTS.md): the AI2 slots' crash count
is pinned per seed as measured, and the AI1 slots stay crash-free on
both seeds.

Round 310: the round-178/185 thin-ridge hold check went with the
danger-joint-search family; the pinned outcome is unchanged under the
promoted champion (measured), so the pin now guards that outcome.

Round 326 (every chooser call ranks by projected place, nested ones
too): seed 132 is crash-free again. p6 and p8 start down into the bend
on their 14th and 15th moves instead of running along row 8, and both
keep their race. The AI2 slots' crash count stays pinned per seed as
measured -- none on either seed now -- and the AI1 slots stay
crash-free on both.

Round 335 (every rival but the relevant one plays its first two forecast
moves by its full policy): seed 132 loses an AI1 slot, for the first
time in this pin. p7 comes down the left side of the course four abreast
with p2, p6 and p5 and moves last of them: on its 35th move the three
landings from which it could still make the bend at the bottom,
(17..19,114), are held by those three cars, so it coasts to (18,115) at
v(3,6), from where no line makes the bend, and runs into the outer wall
on row 130 on its 41st. That is not the round-178 thin ridge -- no
speed-10 hold, three alive exits rather than one thread, closed at once
by bodies right beside it rather than 40 cells downstream -- and since
round 310 the pin guards the outcome, not a check. Recorded, not vetoed
(AGENTS.md): the AI1 slots' crash count is now pinned per seed as
measured too (one on seed 132, none on seed 111), and the AI2 slots stay
crash-free on both seeds.

Round 336 (gates are ordinary landings wherever the exact potential
prices them): seed 132 is crash-free again. p7 still comes down the left
side of the course with p2, p6 and p5, but p5 now holds (12,103) when p7
moves on its 33rd, so it lands two cells further left, on (10,103), and
comes through (12,109) and (15,114) instead of (15,109) and (18,115): it
makes the bend on row 124 and comes home seventh on its 54th. The AI1
slots' crash count stays pinned per seed as measured -- none on either
seed now -- and the AI2 slots stay crash-free on both; round 335's
account above stands as the record of that crash.

Round 345 (random starts: each car's own draw from the seed's SplitMix64
stream): every seed starts from a new grid and is a new race. The races
this docstring describes -- the lobe2 crashes on seeds 111 and 132 that
the round-178 check cleared, p7's speed-10 hold on rand13 seed 4 and its
round-185 rescue, and the crashes of rounds 305/309 and 335 -- were races
on the grid before round 345. The new races are crash-free in every slot:
on lobe2 seed 111 seven cars finish and p6, an AI2 slot, is the car still
running at the end; on seed 132 seven finish and p8, an AI2 slot, is the
car still running; on rand13 seed 4 seven finish, p7 fifth on its 66th
move, and p4, an AI2 slot, is the car still running. As since round 310,
the pin guards the measured outcome: the per-seed crash counts of both
cohorts on lobe2, none on either seed, and the rand13 place sums and crash
counts.
"""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-ridge-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        bench_ai.set_kinds(["AI1", "AI2"] * 4)
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); seed 132 loses two cars, p6 (sixth home on its 54th move before) and p8 (the car still running at the end before), both AI2 slots, into the outer wall at the top of the course at (60,7) and (61,7) on moves 134 and 136, both their 17th, so five cars finish and p7 (seventh home before) is the car still running at the end, after 52 moves; seed 111 and every AI1 slot stay crash-free -- recorded, not vetoed (AGENTS.md).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); seed 132 is crash-free again: p6 and p8, which crashed into the outer wall at the top of the course on their 17th moves (moves 134 and 136) in round 316, as in round 305/309, now start down into the bend on their 14th and 15th moves (S from (82,9), SE from (76,8)) instead of running along row 8 -- p6 comes home fifth on its 53rd and p8 is the car still running at the end, after 53 moves; p5 is fourth on its 53rd (fifth before), p2 sixth on its 54th (fourth on its 53rd before) and p7, the car still running at the end before, seventh on its 54th; p1, p3 and p4 still come home first to third. Seed 111 and every AI1 slot stay crash-free. The race parts from round 316's on move 109 (p5's 14th).
        expected_ai2 = {111: 0, 132: 0}
        # Round 335: re-frozen from measurement (every rival but the relevant one plays its first two forecast moves by its full policy); seed 132 loses p7, an AI1 slot (seventh home on its 54th move before), into the outer wall at the bottom of the course on its 41st move (move 327: from (38,130) at v(5,1), on the wall itself, every move runs along it or leaves the track, and it goes N to (43,130)). On its 35th, move 279, from (15,109) at v(3,6), its three landings that could still make the bend, (17,114), (18,114) and (19,114) at v(2..4,5), were held by p2, p6 and p5 (there since moves 274, 278 and 277), the cars it had come down the left side with, four abreast, and it coasted to (18,115). Six cars finish: p1 and p3 still first and second on their 51st, p4 third on its 52nd (sixth on its 54th before), p2 fourth on its 53rd (fifth on its 54th before), p5 fifth on its 53rd (third on its 52nd before) and p6 sixth on its 54th (fourth on its 53rd before); p8 is still the car running at the end, after 53 moves. The race parts from round 334's on move 22 (p6's 3rd). Seed 111 stays crash-free, and the AI2 slots stay crash-free on both seeds -- recorded, not vetoed (AGENTS.md): the AI1 slots' crash count is pinned per seed as measured, like the AI2 slots' (per seed since round 180).
        # Round 336: re-frozen from measurement (gates are ordinary landings wherever the exact potential prices them); seed 132 is crash-free again, as it was from round 326 to round 334: p7, lost on its 41st move in round 335, is seventh home on its 54th, and the place sums are AI1 14 and AI2 22 (16 and 20 before). On its 33rd, move 263, from (9,96) at v(2,8), p7 found (12,103), the landing it took in round 335, held by p5 (on (14,105) there before), and landed on (10,103) at v(1,7); on its 35th, move 279, it ran from (12,109) at v(2,6) to (15,114) at v(3,5) instead of coasting from (15,109) to (18,115) at v(3,6), and at move 327, where it crashed from (38,130) before, it runs from (40,124) to (48,123), round the bend. p1 still wins on its 51st, p3 is second on its 52nd (51st before), p4 still third on its 52nd, p5 fourth on its 53rd (fifth before), p2 fifth on its 54th (fourth on its 53rd before) and p6 still sixth on its 54th; p8 is still the car running at the end, after 53 moves. The race parts from round 335's on move 93 (p5's 12th). Seed 111 stays crash-free, and the AI2 slots stay crash-free on both seeds. The dict stays per seed: it records that this contract is frozen by measurement.
        # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); both seeds start from new grids and are new races, crash-free in every slot, so both dicts keep their values. Seed 111: p1 wins on its 51st move, p2 and p3 are second and third on their 52nd, p4, p5, p7 and p8 fourth to seventh on their 53rd, and p6 is the car still running at the end, after 53 moves; the place sums are AI1 15 and AI2 21. Seed 132: p1 wins on its 51st, p2, p4 and p6 are second to fourth on their 52nd, p3 and p5 fifth and sixth on their 53rd, p7 seventh on its 54th, and p8 is the car still running at the end, after 53 moves; the place sums are AI1 19 and AI2 17.
        expected_ai1 = {111: 0, 132: 0}
        for seed in (111, 132):
            result = bench_ai.run_track_h2h("lobe2", timeout=600, seed=seed)
            if result is None:
                raise SystemExit(f"mixed lobe2 seed-{seed} race failed or produced no log")
            place_sum, cars, crashes = result["AI1"]
            if crashes != expected_ai1[seed]:
                raise SystemExit(
                    "Round-178 thin-ridge regression: "
                    f"seed {seed} AI1 place_sum={place_sum}, "
                    f"cars={cars}, crashes={crashes}, "
                    f"expected {expected_ai1[seed]}"
                )
            place_sum, cars, crashes = result["AI2"]
            if crashes != expected_ai2[seed]:
                raise SystemExit(
                    "Round-178 thin-ridge regression (AI2 baseline drift): "
                    f"seed {seed} AI2 place_sum={place_sum}, "
                    f"cars={cars}, crashes={crashes}, "
                    f"expected {expected_ai2[seed]}"
                )

        # 2026-09-27: one ordering; the second was the same race with the labels
        # swapped (one policy since round 222). p7 is an AI1 slot.
        bench_ai.set_kinds(["AI1", "AI2"] * 4)
        result = bench_ai.run_track_h2h("rand13", timeout=600, seed=4)
        # Round 215: one policy in two grid slots, so the totals mirror
        # Round 216 re-froze the place sums: the exact pace term reorders
        # the finish without touching what the pin guards -- four cars home
        # and none lost, whichever grid slot carries p7.
        # Round 226: the place sums moved with the needle tie-break; the pin
        # guards four cars home and none lost, and that is unchanged.
        # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
        # Round 232 (the kinematic confirm): re-frozen from measurement.
        # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
        # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
        # Round 260: re-frozen from measurement (the faithful joint world as a chooser).
        # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
        # What the round-185 rescue bought is that p7 SURVIVES the ridge -- its
        # old line crashed three turns later. Since round 232 it is the car still
        # racing at the flag, auto-placed eighth; zero AI1 crashes below include
        # p7's survival, so the separate log scan for a p7 crash is retired
        # (review, 2026-09-29).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); no crash, and p7 survives, now home seventh on its 67th move (fifth on its 66th before); p3 (the car still running at the end before) finishes fourth on its 66th, p6 fifth (fourth before), p1 sixth on its 67th (seventh on its 68th before), and p8 (sixth home before) is the car still running at the end, after 66 moves.
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); no crash, and p7 survives, now home sixth on its 67th move (seventh on its 67th before); p4 wins on its 65th (second before), p2 is second on its 66th (first on its 65th before), p3 (the car still running at the end before) third on its 66th, p5 fourth on its 66th (third on its 65th before), p6 fifth on its 67th (fourth on its 66th before) and p8 seventh on its 68th (fifth on its 66th before), and p1 (sixth home on its 67th before) is the car still running at the end, after 68 moves. The race parts from round 316's on move 64 (p8's 8th).
        # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
        # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy).
        # Round 335: re-frozen from measurement (every rival but the relevant one plays its first two forecast moves by its full policy); no crash, and p7 survives, now home sixth on its 67th move (seventh on its 68th before); p3 still wins on its 65th, p2 is second on its 66th (third before), p4 third on its 66th (second on its 65th before), p5 still fourth, now on its 67th (66th before), p6 (the car still running at the end before, after 68 moves) fifth on its 67th and p8 seventh on its 68th (fifth on its 66th before), and p1 (sixth home on its 68th before) is the car still running at the end, after 68 moves -- round 330's place sums again. The race parts from round 334's on move 30 (p6's 4th).
        # Round 336: re-frozen from measurement (gates are ordinary landings wherever the exact potential prices them); no crash, and p7 survives, still home sixth on its 67th move; p2 now wins on its 65th (second on its 66th before), p4 is second on its 65th (third on its 66th before), p5 third on its 65th (fourth on its 67th before), p3 fourth on its 66th (the winner before, on its 65th), p6 still fifth, now on its 66th (67th before), p8 still seventh, now on its 67th (68th before), and p1 is still the car running at the end, after 67 moves (68 before) -- round 326's place sums again. The race parts from round 335's on move 85 (p5's 11th).
        # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); seed 4 starts from a new grid and is a new race, with no crash: p1, p3 and p5 finish first to third on their 65th moves, p6, p7 and p8 fourth to sixth on their 66th, p2 seventh on its 68th, and p4 is the car still running at the end, after 67 moves -- place sums AI1 11 and AI2 25. The round-185 rescue and p7's survival narrated above were the race on the grid before round 345; in the new race p7, an AI1 slot as before, starts on (140,20) and comes home fifth, and the zero AI1 crashes still include its survival.
        expected = {"AI1": (11, 4, 0), "AI2": (25, 4, 0)}
        if result != expected:
            raise SystemExit(
                "Round-185 width-three ridge regression: "
                f"p7=AI1, result={result}"
            )
    print("AI1 ridge pins hold (lobe2 seeds 111/132; rand13 seed 4)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
