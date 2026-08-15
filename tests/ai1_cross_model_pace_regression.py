#!/usr/bin/env python3
"""Pin Round 95's strict cross-model pace retention."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

EXPECTED = {
    "AI1": (7, 0, [82, 83, 84, 85, 85, 86, 88]),
    "AI2": (7, 0, [82, 83, 84, 85, 85, 86, 88]),
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    results = {}
    with tempfile.TemporaryDirectory(prefix="ai1-cross-model-pace-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            results[kind] = bench_ai.run_track("silverstone", timeout=900, seed=1)

    for kind, expected in EXPECTED.items():
        if results[kind] != expected:
            raise SystemExit(
                f"Round-95 Silverstone seed-1 {kind} regression: "
                f"{results[kind]}, expected {expected}"
            )

    ai1_sum = sum(results["AI1"][2])
    ai2_sum = sum(results["AI2"][2])
    if ai1_sum != 593 or ai2_sum != 593 or results["AI1"] != results["AI2"]:
        raise SystemExit(
            f"Round-95 champion self-tie lost: AI1 {results['AI1']}, AI2 {results['AI2']}"
        )

    print(
        "AI1CrossModelPaceRegression: OK "
        f"(promoted Silverstone seed 1 self-tie at {ai1_sum} finisher moves)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
