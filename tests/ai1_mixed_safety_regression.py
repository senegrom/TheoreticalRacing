#!/usr/bin/env python3
"""Pin the Round-78 and Round-93 heterogeneous-field safety boundaries."""

from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    # The unrestricted fast two-exit proof accelerated an AI1 car in this
    # heterogeneous field and caused a different AI1 car to crash 66 global
    # moves later. Keeping fast mixed-field candidates on the wider three-exit
    # certificate makes the race match the crash-free pre-private-lane policy.
    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-mixed-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        bench_ai.set_kinds(["AI2"] * 4 + ["AI1"] * 4)
        result = bench_ai.run_track_h2h("lemans", timeout=600, seed=2)

        if result is None:
            raise SystemExit("AI1 mixed Le Mans seed-2 race failed or produced no complete log")
        for kind in ("AI1", "AI2"):
            place_sum, finishers, crashes = result[kind]
            if finishers != 4 or crashes != 0:
                raise SystemExit(
                    "AI1 mixed-field safety regression: "
                    f"{kind} place_sum={place_sum}, finishers={finishers}, crashes={crashes}"
                )

        # Round 93: in both kind orderings, player 6 used to choose S from the
        # fast L2 state below and crash 30 global moves later. The normal
        # three-round model sees that landing alive but fragile; a bounded
        # four-round scorer-rival recheck proves S dies and SW survives.
        expected = {"AI1": (18, 4, 0), "AI2": (18, 4, 0)}
        orderings = (
            ("front", ["AI1"] * 4 + ["AI2"] * 4),
            ("reverse", ["AI2"] * 4 + ["AI1"] * 4),
        )
        target = re.compile(
            r"^502 p6 AI[12] SW v\(-2,-8\).*\(-3,-7\) "
            r"\(13,101\).*\(10,94\) ok$"
        )
        finish = re.compile(r"^563 p6 AI[12] .* FINISH place=5$")
        for label, kinds in orderings:
            bench_ai.set_kinds(kinds)
            result = bench_ai.run_track_h2h("lemans", timeout=600, seed=7)
            if result != expected:
                raise SystemExit(
                    f"Round-93 mixed Le Mans seed-7 {label} regression: {result}"
                )
            log_lines = Path(bench_ai.LOG).read_text(encoding="utf-8").splitlines()
            if any(" CRASH " in line for line in log_lines):
                raise SystemExit(
                    f"Round-93 mixed Le Mans seed-7 {label} still contains a crash"
                )
            if sum(bool(target.match(line)) for line in log_lines) != 1:
                raise SystemExit(
                    f"Round-93 mixed Le Mans seed-7 {label} did not take the pinned SW rescue"
                )
            if sum(bool(finish.match(line)) for line in log_lines) != 1:
                raise SystemExit(
                    f"Round-93 mixed Le Mans seed-7 {label} did not finish player 6 in place 5"
                )

    print(
        "AI1MixedSafetyRegression: OK "
        "(seed 2 crash-free; seed 7 both orderings take SW, p6 finishes, crashes=0/0)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
