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
the pin now holds the measured (place sum, finishers, crashes) per seed
and label.
"""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

EXPECTED = {
    36: {"AI1": (19, 4, 1), "AI2": (17, 4, 0)},
    45: {"AI1": (18, 4, 0), "AI2": (18, 4, 0)},
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
                place_sum, finishers, crashes = result[kind]
                if (place_sum, finishers, crashes) != EXPECTED[seed][kind]:
                    raise SystemExit(
                        "Round-128 fast-funnel regression: "
                        f"seed {seed} {kind} place_sum={place_sum}, "
                        f"finishers={finishers}, crashes={crashes}, "
                        f"expected {EXPECTED[seed][kind]}"
                    )
    print("AI1 fast finish-funnel pins hold (mixed Le Mans seeds 36 and 45, measured)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
