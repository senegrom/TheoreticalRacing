#!/usr/bin/env python3
"""Pin Round 103's six-rival switch-target confirmation for both agents."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

EXPECTED = (7, 0, [65, 65, 65, 66, 67, 67, 68])


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    results = {}
    with tempfile.TemporaryDirectory(prefix="true-confirm-r103-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            results[kind] = bench_ai.run_track("zigzag", timeout=1200, seed=76)
    for kind, actual in results.items():
        if actual != EXPECTED:
            raise SystemExit(
                f"Round-103 Zigzag seed-76 {kind} regression: {actual}, expected {EXPECTED}"
            )
    if results["AI1"] != results["AI2"]:
        raise SystemExit(f"Round-103 agent identity lost: {results}")
    print("AITrueRivalConfirmationRegression: OK (Zigzag s76 7 finishers, 0 crashes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
