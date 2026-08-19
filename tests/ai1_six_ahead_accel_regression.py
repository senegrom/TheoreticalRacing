#!/usr/bin/env python3
"""Pin Round 117's synchronized six-ahead acceleration after promotion."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

PROMOTED = {
    5: (7, 0, [58, 59, 60, 61, 62, 62, 62]),
    22: (7, 0, [58, 59, 60, 61, 61, 62, 63]),
    86: (7, 0, [58, 59, 61, 61, 62, 62, 62]),
}
LEGACY_CHAMPION_86 = (7, 0, [58, 59, 61, 61, 62, 62, 63])
EXPECTED = {kind: PROMOTED for kind in ("AI1", "AI2")}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {"AI1": {}, "AI2": {}}
    with tempfile.TemporaryDirectory(prefix="round117-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for seed in (5, 22, 86):
                actual[kind][seed] = bench_ai.run_track("coil", timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-117 promoted regression: {actual}, expected {EXPECTED}")
    if actual["AI1"] != actual["AI2"]:
        raise SystemExit(f"Round-117 promotion is not mirrored: {actual}")
    result = actual["AI1"][86]
    if result[:2] != LEGACY_CHAMPION_86[:2] or any(
            a > b for a, b in zip(result[2], LEGACY_CHAMPION_86[2])):
        raise SystemExit(f"Round-117 Pareto contract lost: {result}, {LEGACY_CHAMPION_86}")
    if sum(result[2]) >= sum(LEGACY_CHAMPION_86[2]):
        raise SystemExit(f"Round-117 pace gain lost: {result}, {LEGACY_CHAMPION_86}")
    print("AI1SixAheadAccelRegression: OK (Coil s86 promoted; s5/s22 controls pinned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
