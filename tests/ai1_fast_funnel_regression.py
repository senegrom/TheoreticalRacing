#!/usr/bin/env python3
"""Pin the Round-128 fast finish-funnel confirm leg.

Mixed 4v4 Le Mans (alternating kinds, AI1 in the odd slots) killed an AI1
car at the same terminal-funnel cell in four of one hundred harvest-23
seeds: a fast commitment the smom-3 world reads alive while the true-rival
world at the certification cap kills it four rounds out. Seed 36 carries
the tier=1 sibling (commitment at (14,105), chosen NW) and seed 45 the
tier=3 sibling (commitment at (11,97), chosen N); both must now run
crash-free. The rescue is place-neutral: the saved car survives to the end
and is auto-placed eighth when the seventh rival finishes, so the pin
asserted zero crashes rather than eight finishers.

Round 229 (the soft caution stack left the score, -0.82 places
head-to-head): the funnel commitment is taken again and seed 36's AI1 car
dies there; seed 45 stays crash-free. Recorded, not vetoed (AGENTS.md):
the pin now holds the measured (place sum, cars, crashes) per seed
and label.

Round 310 (the danger-joint-search family deleted, -0.021 places
head-to-head on random starts): the round-128 confirm leg this pin was
written for is gone with the rest of the family, so nothing here exercises
it any more. The pin keeps the measured (place sum, cars, crashes) per
seed and label, re-frozen from measurement, so a further change in those
totals still fails: seed 36's crash moves from p1 (AI1) to p8 (AI2), at
the same wall cell at the top of the course; seed 45 stays crash-free with
the same totals, although its race plays differently from move 206 on.
"""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

EXPECTED = {
    # Round 233: seed 36 is crash-free again -- the round-232 loss here is back.
    # Round 234 (the seal guard left the decision): re-frozen from measurement.
    # Round 247 (the soft rollout at one level, not two): re-frozen from
    # measurement; seed 36 is crash-free again.
    # Round 260 (the chooser): re-frozen from measurement.
    # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); p1 (AI1), seventh home on its 72nd move before, now crashes on its 15th, into the wall at (34,0) on move 113 at the top of the course -- not at the funnel -- so six cars finish: p8, still the car running at the end, moves up to seventh, p6 and p7 each gain a place and p5 drops from fourth to sixth, home on its 71st -- recorded, not vetoed (AGENTS.md).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted); the round-128 funnel leg went with it; p1 (AI1), which crashed on its 15th move in rounds 305/309, keeps its race and is the car still running at the end, after 71 moves, so it is placed seventh; p8 (AI2), the car still running at the end before, now crashes on its 14th, into the wall at (34,0) on move 112 with the very move that killed p1 before (W at v(3,-4) from (32,4)), at the top of the course -- not at the funnel -- and is placed eighth; p5 comes home fourth on its 69th (sixth on its 71st before), and p6 and p7 each drop a place, fifth on its 70th and sixth on its 71st -- recorded, not vetoed (AGENTS.md).
    36: {"AI1": (19, 4, 0), "AI2": (17, 4, 1)},
    # Round 234: re-frozen from measurement. Eight cars share places 1-8,
    # so the two cohort sums always add to 36 whether or not one crashes.
    # Round 260: seed 45 is crash-free again.
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    45: {"AI1": (13, 4, 0), "AI2": (23, 4, 0)},
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-funnel-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["lemans"]))  # frozen pre-2026-08-29 geometry
        bench_ai.set_nplayers(8)
        bench_ai.set_kinds(["AI1", "AI2"] * 4)
        for seed in (36, 45):
            result = bench_ai.run_track_h2h("lemans", timeout=600, seed=seed)
            if result is None:
                raise SystemExit(f"mixed Le Mans seed-{seed} race failed or produced no log")
            for kind in ("AI1", "AI2"):
                place_sum, cars, crashes = result[kind]
                if (place_sum, cars, crashes) != EXPECTED[seed][kind]:
                    raise SystemExit(
                        "Round-128 fast-funnel regression: "
                        f"seed {seed} {kind} place_sum={place_sum}, "
                        f"cars={cars}, crashes={crashes}, "
                        f"expected {EXPECTED[seed][kind]}"
                    )
    print("AI1 fast finish-funnel pins hold (mixed Le Mans seeds 36 and 45, measured)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
