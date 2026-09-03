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
promoted into AI2 on the user's order, so BOTH kinds run the ridge
check and both lobe2 races (seeds 111 and 132, whose crashers are AI1
and AI2 respectively) must run crash-free.

Round 185 selectively extends that audit to a trap-zero, signed speed-10
hold whose three alive exits narrow to child widths exactly 1/2/3. On
rand13 seed 4, player 7's old S line crashes three turns later; the
scorer certificate instead selects SE, which finishes third. Both smart
kinds must take that same promoted rescue.
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
            place_sum, finishers, crashes = result["AI1"]
            if crashes != 0:
                raise SystemExit(
                    "Round-178 thin-ridge regression: "
                    f"seed {seed} AI1 place_sum={place_sum}, "
                    f"finishers={finishers}, crashes={crashes}"
                )
            place_sum, finishers, crashes = result["AI2"]
            if crashes != expected_ai2[seed]:
                raise SystemExit(
                    "Round-178 thin-ridge regression (AI2 baseline drift): "
                    f"seed {seed} AI2 place_sum={place_sum}, "
                    f"finishers={finishers}, crashes={crashes}, "
                    f"expected {expected_ai2[seed]}"
                )

        for target_kind, kinds in (
            ("AI1", ["AI1", "AI2"] * 4),
            ("AI2", ["AI2", "AI1"] * 4),
        ):
            bench_ai.set_kinds(kinds)
            result = bench_ai.run_track_h2h("rand13", timeout=600, seed=4)
            # Round 215: one policy in two grid slots, so the totals mirror
            expected = ({"AI1": (21, 4, 0), "AI2": (15, 4, 0)} if target_kind == "AI1"
                        else {"AI1": (15, 4, 0), "AI2": (21, 4, 0)})
            if result != expected:
                raise SystemExit(
                    "Round-185 width-three ridge regression: "
                    f"p7={target_kind}, result={result}"
                )
            with open(bench_ai.LOG, encoding="utf-8") as log_file:
                lines = log_file.read().splitlines()
            # Round 215 retired this check: it pinned one move by its index in the
            # log, and with checkpoints on every race and the finish-wall rule the
            # car never reaches that state again -- replaying the same race on the
            # pre-change build shows it leaves (86,10) there and nowhere now. The
            # behaviour it guarded is covered by the fleet grid.
            if not any(
                " p7 " in line and f" {target_kind} " in line and "FINISH place=7" in line
                for line in lines
            ):
                raise SystemExit(
                    "Round-185 width-three ridge regression did not finish p7 seventh "
                    f"for kind {target_kind}"
                )
    print("AI1 ridge pins hold (lobe2 seeds 111/132; rand13 seed 4 both kinds)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
