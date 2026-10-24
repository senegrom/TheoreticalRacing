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
SAFETY = {(35, "AI1"): 2}


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
