#!/usr/bin/env python3
"""Pin the Round-178 thin-ridge hold check.

The lobe2 harvest-32 crashes commit by HOLDING max-axis 10 onto a
one-lane alive-map ridge (<= 2 alive successors at the chosen landing)
whose single thread a rival body closes 40 cells downstream. No train
rival within Chebyshev 3, ring-wide waist, dense field -- invisible to
the round-175 bar, the round-83 funnel signal, and the round-83 deep
guard alike. The root check audits scorer-8 (never a verdict), escalates
DEAD-or-loud (thread >= 4) fires to the true-6 verdict, and switches
only to a certified quiet-alive alternative. Seeds 111 and 132 carry
the commitment in different slots; both races must now run crash-free
under the alternating mixed field.
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
        for seed in (111, 132):
            result = bench_ai.run_track_h2h("lobe2", timeout=600, seed=seed)
            if result is None:
                raise SystemExit(f"mixed lobe2 seed-{seed} race failed or produced no log")
            for kind in ("AI1", "AI2"):
                place_sum, finishers, crashes = result[kind]
                if crashes != 0:
                    raise SystemExit(
                        "Round-178 thin-ridge regression: "
                        f"seed {seed} {kind} place_sum={place_sum}, "
                        f"finishers={finishers}, crashes={crashes}"
                    )
    print("AI1 thin-ridge pins hold (mixed lobe2 seeds 111 and 132)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
