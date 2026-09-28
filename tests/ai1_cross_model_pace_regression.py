#!/usr/bin/env python3
"""Pin Round 95's strict cross-model pace retention."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

EXPECTED = {
    # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
    # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 248: re-frozen from measurement (the physical world model: occupancy with lap state, rollouts that stop with the last survivor, blockades replayed).
    # Round 260 (the chooser): Silverstone s1 loses a car here -- recorded,
    # not vetoed (AGENTS.md); the finisher moves below are the pin's subject.
    "AI2": (6, 1, [82, 83, 83, 84, 84, 85]),
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    results = {}
    with tempfile.TemporaryDirectory(prefix="ai1-cross-model-pace-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["silverstone"]))  # frozen pre-repair geometry
        bench_ai.set_nplayers(8)
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            results[kind] = bench_ai.run_track("silverstone", timeout=900, seed=1)

    for kind, expected in EXPECTED.items():
        if results[kind] != expected:
            raise SystemExit(
                f"Round-95 Silverstone seed-1 {kind} regression: "
                f"{results[kind]}, expected {expected}"
            )

    move_sum = sum(results[LABELS[0]][2])
    # Round 229: 596 is the sum of the re-frozen finisher moves.
    # Round 247: 586 (the soft rollout at one level, not two). Round 248: 587.
    # Round 260: 501 is the sum of the six re-frozen finisher moves.
    if move_sum != 501:
        raise SystemExit(f"Round-95 promoted finisher moves lost: {results[LABELS[0]]}")

    print(
        "AI1CrossModelPaceRegression: OK "
        f"(promoted Silverstone seed 1 at {move_sum} finisher moves)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
