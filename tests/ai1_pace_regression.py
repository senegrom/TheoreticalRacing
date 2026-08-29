#!/usr/bin/env python3
"""Pin the promoted Round-78 and Round-94 pace gains."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

# Monaco seed 1 is a deterministic traffic-heavy case where the geometry-clipped
# private-lane certificate and its moderate-uncertainty two-exit refinement recover
# repeated one-turn concessions. Keep the benchmark metric (sum of each finisher's
# personal move count) at least this fast while also guarding crash-free completion.
MAX_FINISH_MOVE_SUM = 799

# Round 94 extends the dual-model finish sprint from map TTF 15 to 20 only
# in mover-kind homogeneous fields. Big Oval seed 7 is the smallest active
# gain; Le Mans seed 12 pins the extended-band NONE veto that removed the
# broad experiment's sole slower race.
FINISH_EXPECTED = {
    ("bigoval", 7): [20, 20, 21, 21, 22, 22, 23],
    ("lemans", 12): [65, 67, 69, 71, 73, 75, 76],
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-pace-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["lemans", "monaco"]))  # frozen pre-2026-08-29 geometry
        bench_ai.set_nplayers(8)
        bench_ai.set_all_to("AI1")
        result = bench_ai.run_track("monaco", timeout=600, seed=1)
        finish_results = {}
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for track_seed in FINISH_EXPECTED:
                track, seed = track_seed
                finish_results[(kind, track, seed)] = bench_ai.run_track(
                    track, timeout=600, seed=seed
                )

    if result is None:
        raise SystemExit("AI1 Monaco seed-1 race failed or produced no complete log")
    finishes, crashes, finish_moves = result
    if finishes != 7 or crashes != 0:
        raise SystemExit(
            f"AI1 Monaco seed-1 safety regression: finishes={finishes}, crashes={crashes}"
        )
    move_sum = sum(finish_moves)
    if move_sum > MAX_FINISH_MOVE_SUM:
        raise SystemExit(
            "AI1 Monaco seed-1 pace regression: "
            f"finisher move sum {move_sum} exceeds {MAX_FINISH_MOVE_SUM}"
        )

    for (kind, track, seed), finish_result in finish_results.items():
        expected = (7, 0, FINISH_EXPECTED[(track, seed)])
        if finish_result != expected:
            raise SystemExit(
                f"Round-94 {kind} {track} seed-{seed} regression: "
                f"{finish_result}, expected {expected}"
            )

    print(
        "AI1PaceRegression: OK "
        f"(Monaco sum={move_sum}; Big Oval finish sprint and Le Mans veto pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
