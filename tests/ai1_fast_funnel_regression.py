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
asserts zero crashes rather than eight finishers.
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

    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-funnel-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        bench_ai.set_kinds(["AI1", "AI2"] * 4)
        for seed in (36, 45):
            result = bench_ai.run_track_h2h("lemans", timeout=600, seed=seed)
            if result is None:
                raise SystemExit(f"mixed Le Mans seed-{seed} race failed or produced no log")
            for kind in ("AI1", "AI2"):
                place_sum, finishers, crashes = result[kind]
                if crashes != 0:
                    raise SystemExit(
                        "Round-128 fast-funnel regression: "
                        f"seed {seed} {kind} place_sum={place_sum}, "
                        f"finishers={finishers}, crashes={crashes}"
                    )
    print("AI1 fast finish-funnel pins hold (mixed Le Mans seeds 36 and 45)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
