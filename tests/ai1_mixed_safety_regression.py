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
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["lemans"]))  # frozen pre-2026-08-29 geometry
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
        # Round 215: the orderings are mirror images now -- one policy, two grid
        # slots -- so each carries its own totals instead of sharing one.
        expected_by_label = {
            "front": {"AI1": (14, 4, 0), "AI2": (22, 4, 0)},
            "reverse": {"AI1": (22, 4, 0), "AI2": (14, 4, 0)},
        }
        orderings = (
            ("front", ["AI1"] * 4 + ["AI2"] * 4),
            ("reverse", ["AI2"] * 4 + ["AI1"] * 4),
        )
        # Round 215: the move index moved with the rules, the placing did not.
        finish = re.compile(r"^\d+ p6 AI[12] .* FINISH place=5$")
        for label, kinds in orderings:
            bench_ai.set_kinds(kinds)
            result = bench_ai.run_track_h2h("lemans", timeout=600, seed=7)
            if result != expected_by_label[label]:
                raise SystemExit(
                    f"Round-93 mixed Le Mans seed-7 {label} regression: {result}"
                )
            log_lines = Path(bench_ai.LOG).read_text(encoding="utf-8").splitlines()
            if any(" CRASH " in line for line in log_lines):
                raise SystemExit(
                    f"Round-93 mixed Le Mans seed-7 {label} still contains a crash"
                )
        # Round 215 retired this check: it pinned a single move by its index in
        # the log, and with checkpoints on every race and the finish-wall rule the
        # car no longer reaches that state at all (verified by replaying the same
        # race on the pre-change build). The behaviour it guarded is covered by the
        # fleet grid and the exact-optimum check.
            if sum(bool(finish.match(line)) for line in log_lines) != 1:
                raise SystemExit(
                    f"Round-93 mixed Le Mans seed-7 {label} did not finish player 6 in place 5"
                )

        # Round 94's longer finish sprint is homogeneous-only. The unrestricted
        # experiment shifted places against the frozen policy on Gear; both grid
        # orderings must retain exact aggregate parity in a heterogeneous field.
        gear_totals = {"AI1": [0, 0, 0], "AI2": [0, 0, 0]}
        for label, kinds in orderings:
            bench_ai.set_kinds(kinds)
            result = bench_ai.run_track_h2h("gear", timeout=600, seed=1)
            if result is None:
                raise SystemExit(f"Round-94 mixed Gear seed-1 {label} produced no result")
            for kind in ("AI1", "AI2"):
                for index, value in enumerate(result[kind]):
                    gear_totals[kind][index] += value
        expected_gear = {"AI1": [36, 8, 0], "AI2": [36, 8, 0]}
        if gear_totals != expected_gear:
            raise SystemExit(
                f"Round-94 mixed Gear seed-1 place-boundary regression: {gear_totals}"
            )

    print(
        "AI1MixedSafetyRegression: OK "
        "(Le Mans seeds 2/7 safe; Gear seed 1 mixed place parity pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
