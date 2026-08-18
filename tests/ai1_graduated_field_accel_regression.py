#!/usr/bin/env python3
"""Pin Round 115's AI1-only low-energy field acceleration."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

EXPECTED = {'AI1': {1: (7, 0, [58, 59, 60, 61, 62, 62, 63]), 38: (7, 0, [58, 59, 61, 61, 62, 62, 62]), 106: (7, 0, [58, 59, 60, 62, 62, 63, 63])}, 'AI2': {1: (7, 0, [58, 59, 60, 62, 62, 63, 63]), 38: (7, 0, [58, 59, 61, 61, 62, 62, 63]), 106: (7, 0, [58, 59, 60, 62, 62, 63, 63])}}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {"AI1": {}, "AI2": {}}
    with tempfile.TemporaryDirectory(prefix="round115-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for seed in (1, 38, 106):
                actual[kind][seed] = bench_ai.run_track("coil", timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-115 regression: {actual}, expected {EXPECTED}")
    for seed in (1, 38):
        ai1, ai2 = actual["AI1"][seed], actual["AI2"][seed]
        if ai1[0:2] != ai2[0:2] or any(a > b for a, b in zip(ai1[2], ai2[2])):
            raise SystemExit(f"Round-115 Pareto contract lost on seed {seed}: {ai1}, {ai2}")
        if sum(ai1[2]) >= sum(ai2[2]):
            raise SystemExit(f"Round-115 pace gain lost on seed {seed}: {ai1}, {ai2}")
    if actual["AI1"][106] != actual["AI2"][106]:
        raise SystemExit(f"Round-115 coast control changed: {actual}")
    print("AI1GraduatedFieldAccelRegression: OK (Coil seeds 1/38 faster; seed 106 and AI2 frozen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
