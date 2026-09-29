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
both lobe2 races (seeds 111 and 132) must run crash-free.

Round 185 selectively extends that audit to a trap-zero, signed speed-10
hold whose three alive exits narrow to child widths exactly 1/2/3. On
rand13 seed 4, player 7's old S line crashes three turns later; the
scorer certificate instead selects SE, which finishes third; the mixed
roster below must take that same promoted rescue.
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
        expected_ai2 = {111: 0, 132: 0}
        for seed in (111, 132):
            result = bench_ai.run_track_h2h("lobe2", timeout=600, seed=seed)
            if result is None:
                raise SystemExit(f"mixed lobe2 seed-{seed} race failed or produced no log")
            place_sum, cars, crashes = result["AI1"]
            if crashes != 0:
                raise SystemExit(
                    "Round-178 thin-ridge regression: "
                    f"seed {seed} AI1 place_sum={place_sum}, "
                    f"cars={cars}, crashes={crashes}"
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
        # What the round-185 rescue bought is that p7 SURVIVES the ridge -- its
        # old line crashed three turns later. Since round 232 it is the car still
        # racing at the flag, auto-placed eighth; zero AI1 crashes below include
        # p7's survival, so the separate log scan for a p7 crash is retired
        # (review, 2026-09-29).
        expected = {"AI1": (17, 4, 0), "AI2": (19, 4, 0)}
        if result != expected:
            raise SystemExit(
                "Round-185 width-three ridge regression: "
                f"p7=AI1, result={result}"
            )
    print("AI1 ridge pins hold (lobe2 seeds 111/132; rand13 seed 4)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
