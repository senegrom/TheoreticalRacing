#!/usr/bin/env python3
"""Pin the Round-133 vmax overspeed deep check.

Every harvest-25 slow-track crash was one serpentine2 commitment: with
vx=10 on the bottom straight, accelerating to max-axis 11 is a 5-9-round
joint doom (the static reach map holds a solo escape line, but traffic
occupies the escape rows). The deep suppressed world at the certification
cap is the only shipped world that sees it, so the leg re-verdicts
acceleration into the top speed band with scorer-8 alone. Seeds 6 and 35
carry the commitment in different slots (p7 and p6); both races must now
run crash-free under the alternating mixed field.

Round 310: the deep-pack route that carried these commitments to the
round-133 vmax check (and its fallback route) went with the
danger-joint-search family -- the leg is reached only through the
round-232 kinematic confirm now, which arms only on courses with
checkpoints (game.lapGates != null). serpentine2 races with checkpoints
disabled, so nothing in these two races reaches the leg any more; the
pinned outcome is unchanged under the promoted champion (measured), so the
pin now guards that outcome.

Round 331: seed 35 loses two AI1 cars at the west end of the westbound
straight above the bottom one, not at the round-133 site: after running at
max-axis 11 there, each runs out of road once an AI2 car holds its one
escape landing (SAFETY below). The bottom-straight commitment itself still
passes (p1 accelerates E to v(11,0) from (76,113) on move 97 and survives
the right-end hairpin). The pin now guards seed 6 crash-free under both
labels, seed 35 crash-free for AI2, and seed 35's AI1 half at its measured
two crashes.

Round 333: seed 35 keeps both AI1 cars again -- they still reach max-axis 11
on that straight drifting outward, but stop the drift on their next move and
finish, never coming onto the outer wall's line, y=101 (SAFETY below) -- so
both seeds run crash-free under both labels again, the round-133 contract. No car in seed 35 goes beyond max-axis 10 on the bottom
straight any more; in seed 6, p6 and p8 (AI2) accelerate to v(11,0) there on
moves 94 and 96, and both finish.

Round 345: random starts are each car's own draw from the seed's SplitMix64
stream, so both seeds race from new grids, and the commitments and crashes
named above (the harvest-25 commitment in p7 and p6, the round-331 and
round-333 races) were the races on the grids before round 345. On the new
grids the bottom-straight commitment is p8's in seed 6 (AI2: E to v(11,1)
from (78,113) on its 12th move, turn 96) and p6's in seed 35 (AI2: SE to
v(11,0) from (68,113) on its 11th move, turn 86), and both cars come through
the right-end hairpin. Seed 35 runs crash-free under both labels; seed 6
loses one AI2 car, p8 on its 87th move, at the west end of the second
westbound straight after running at max-axis 11 there (SAFETY below). The
pin now guards seed 35 crash-free under both labels, seed 6 crash-free for
AI1, and seed 6's AI2 half at its measured one crash.

2026-11-13: outcome pin, awaiting a decision specimen. The leg judges only a
pick that the kinematic confirm's own forecast reads alive, and the confirm
runs only on courses with checkpoints. A fleet scan (the 83 courses other than
the Nordschleife over seeds 1-40, eight AI2 cars, one lap, random starts, 3,320
races, raced by a scratch build that prints the legs of top-level decisions
only; 72 of the courses have checkpoints, 2,880 of the races) found the confirm
switching a real pick that accelerates into max-axis 11 or more 133 times, in
68 races. Raced again by a build that also names the danger search's speed leg,
those 68 races show the round-133 leg judging 66 real picks and killing none:
the 133 picks died in the confirm's own forecast, where the leg does not run.
"""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

# The measured crash count of a seed's label that no longer runs crash-free;
# every other seed and label takes the 0 default.
# Round 331: re-frozen from measurement (the relevant rival keeps its three stronger forecast moves beside the second and third rivals'); seed 35 loses two AI1 cars in two separate wall crashes two moves apart, at the west end of the westbound straight above the bottom one, before the left-end hairpin: p7 (fourth home before, on its 179th move) crashes on its 39th, move 311, NE from (45,101) at v(-9,1) to (37,101), and p1 (seventh home before, on its 181st) on its 40th, move 313, NE from (38,101) at v(-8,1) to (31,101). Neither target cell held a car: each car was on the outer wall's line (y=101) still drifting outward, where every landing runs along the wall or crosses it. Each had found its one landing that could still stop for the hairpin held by an AI2 car on its 38th move: p7, on move 303 from (54,100) at v(-10,1), found (45,100) at v(-9,0) held by p8 (there since move 296), and p1, on move 297 from (55,98) at v(-10,2), found (46,99) at v(-9,1) held by p4 (there since move 292). Both had accelerated W to max-axis 11 from v(-10,0) on their 35th move (p1 on move 273, p7 on move 279) and turned toward the outer wall at that speed on their 36th -- the class the docstring describes, on another straight. p6, p8, p3, p5 and p2 come home first to fifth and p4 is still the car running at the end, now after 179 moves (180 before). The race parts from round 330's on move 175 (p7's 22nd). Seed 6 stays crash-free under both labels; its finishers move -- recorded, not vetoed (AGENTS.md).
# Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full policy in every decision); seed 35 keeps both AI1 cars it lost in rounds 331 and 332: p7 (crashed on its 39th, move 311, before) comes home second on its 178th and p1 (crashed on its 40th, move 313, before) seventh on its 181st. Both still accelerate to max-axis 11 on the westbound straight above the bottom one, drifting outward (p7 SW to v(-11,1) at (76,100) on its 34th, move 271; p1 SW to v(-11,1) at (76,99) on its 36th, move 281), but stop the drift on their next move (p7 N to v(-11,0), p1 NE to v(-10,0)) and brake for the left-end hairpin turning inward, never coming onto the outer wall's line (y=101). p6 still wins on its 177th and p3 is still third on its 179th; p4 (the car still running at the end before, after 179 moves) is fourth on its 179th, p8 (second before, on its 178th) fifth on its 179th and p5 (fourth before, on its 179th) sixth on its 180th, and p2 (fifth home before, on its 180th) is the car still running at the end, after 180 moves. The race parts from round 332's on move 2 (p2's 1st). Seed 6 stays crash-free under both labels; the race parts from round 332's on move 54 (p6's 7th) and its finishers move. Both seeds run crash-free under both labels again, so no seed and label needs an entry.
# Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); seed 6 loses one AI2 car: p8 crashes on its 87th move, at turn 696, NE from (38,69) at v(-8,1) to (31,69), at the west end of the second westbound straight (the fourth straight from the bottom, between y=62 and y=69), before the left-end hairpin. The target cell held no car: p8 was on the outer wall's line (y=69) still drifting outward, where every landing runs along the wall or crosses it. It had accelerated W to max-axis 11 from v(-10,0) at (87,66) on its 82nd move (turn 656), coasted at v(-11,0) to (65,66) on its 83rd (turn 664), drifted outward braking to v(-10,1) on its 84th (SE to (55,67), turn 672), braked to v(-9,1) on its 85th (E to (46,68), turn 680) and came onto the wall's line on its 86th (E to v(-8,1), from (46,68) to (38,69), turn 688), beside p5 (AI1) on (38,68), there since turn 685 -- the kind of commitment the docstring describes, on another straight. p3, p4, p1, p2, p6 and p5 come home first to sixth, on their 177th, 178th, 179th, 179th, 179th and 180th moves, and p7 (AI1) is the car still running at the end, after 179 moves -- recorded, not vetoed (AGENTS.md). Seed 35 runs crash-free under both labels: p3, p5, p7, p8, p1, p2 and p6 come home first to seventh, on their 177th, 178th, 178th, 179th, 180th, 180th and 180th moves, and p4 is the car still running at the end, after 180 moves.
SAFETY = {(6, "AI2"): 1}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-vmax-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        bench_ai.set_kinds(["AI1", "AI2"] * 4)
        for seed in (6, 35):
            result = bench_ai.run_track_h2h("serpentine2", timeout=600, seed=seed)
            if result is None:
                raise SystemExit(f"mixed serpentine2 seed-{seed} race failed or produced no log")
            for kind in ("AI1", "AI2"):
                place_sum, cars, crashes = result[kind]
                expected = SAFETY.get((seed, kind), 0)
                if crashes != expected:
                    raise SystemExit(
                        "Round-133 vmax-deep regression: "
                        f"seed {seed} {kind} place_sum={place_sum}, "
                        f"cars={cars}, crashes={crashes}, expected {expected}"
                    )
    print("AI1 vmax deep pins hold (mixed serpentine2 seeds 6 and 35, as measured)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
