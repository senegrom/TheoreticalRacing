#!/usr/bin/env python3
"""Pin Round 96's neutral-coast acceleration pace boundary."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

EXPECTED = {
    "AI1": (7, 0, [65, 66, 66, 66, 66, 67, 68]),
    "AI2": (7, 0, [65, 66, 66, 66, 66, 67, 68]),
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    results = {}
    with tempfile.TemporaryDirectory(prefix="ai1-neutral-accel-pace-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            results[kind] = bench_ai.run_track("zigzag", timeout=900, seed=2)

    for kind, expected in EXPECTED.items():
        if results[kind] != expected:
            raise SystemExit(
                f"Round-96 Zigzag seed-2 {kind} regression: "
                f"{results[kind]}, expected {expected}"
            )

    ai1_sum = sum(results["AI1"][2])
    ai2_sum = sum(results["AI2"][2])
    if ai1_sum != 464 or ai2_sum != 464 or ai1_sum != ai2_sum:
        raise SystemExit(
            f"Round-96 promoted neutral acceleration lost identity: AI1 {results['AI1']}, "
            f"AI2 {results['AI2']}"
        )

    print(
        "AI1NeutralAccelPaceRegression: OK "
        f"(Zigzag seed 2 promoted tie at {ai1_sum} finisher moves)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
