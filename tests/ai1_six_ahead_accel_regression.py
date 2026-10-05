#!/usr/bin/env python3
"""Pin Round 117's synchronized six-ahead acceleration after promotion."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

PROMOTED = {
    # The s5 and s22 controls race in ai1_six_ahead_high_speed_regression, which
    # pins the same races by summary and digest (review, 2026-09-28).
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    86: (7, 0, [58, 59, 60, 60, 60, 60, 61]),
}
LEGACY_CHAMPION_86 = (7, 0, [58, 59, 61, 61, 62, 62, 63])
EXPECTED = {kind: PROMOTED for kind in LABELS}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {kind: {} for kind in LABELS}
    with tempfile.TemporaryDirectory(prefix="round117-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            for seed in (86,):
                actual[kind][seed] = bench_ai.run_track("coil", timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-117 promoted regression: {actual}, expected {EXPECTED}")
    result = actual[LABELS[0]][86]
    if result[:2] != LEGACY_CHAMPION_86[:2] or any(
            a > b for a, b in zip(result[2], LEGACY_CHAMPION_86[2])):
        raise SystemExit(f"Round-117 Pareto contract lost: {result}, {LEGACY_CHAMPION_86}")
    if sum(result[2]) >= sum(LEGACY_CHAMPION_86[2]):
        raise SystemExit(f"Round-117 pace gain lost: {result}, {LEGACY_CHAMPION_86}")
    print("AI1SixAheadAccelRegression: OK (Coil s86 promoted; its s5/s22 controls race in the high-speed pin)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
