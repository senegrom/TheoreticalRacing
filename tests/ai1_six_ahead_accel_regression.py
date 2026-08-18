#!/usr/bin/env python3
"""Pin Round 117's AI1-only synchronized six-ahead acceleration."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

EXPECTED = {'AI1': {5: (7, 0, [58, 59, 60, 61, 62, 62, 62]), 22: (7, 0, [58, 59, 60, 61, 61, 62, 63]), 86: (7, 0, [58, 59, 61, 61, 62, 62, 62])}, 'AI2': {5: (7, 0, [58, 59, 60, 61, 62, 62, 62]), 22: (7, 0, [58, 59, 60, 61, 61, 62, 63]), 86: (7, 0, [58, 59, 61, 61, 62, 62, 63])}}


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
        raise SystemExit(f"Round-117 regression: {actual}, expected {EXPECTED}")
    for seed in (5, 22):
        if actual["AI1"][seed] != actual["AI2"][seed]:
            raise SystemExit(f"Round-117 control changed on seed {seed}: {actual}")
    ai1, ai2 = actual["AI1"][86], actual["AI2"][86]
    if ai1[0:2] != ai2[0:2] or any(a > b for a, b in zip(ai1[2], ai2[2])):
        raise SystemExit(f"Round-117 Pareto contract lost: {actual}")
    if sum(ai1[2]) >= sum(ai2[2]):
        raise SystemExit(f"Round-117 pace gain lost: {actual}")
    print("AI1SixAheadAccelRegression: OK (Coil s86 faster; s5/s22 and AI2 frozen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
