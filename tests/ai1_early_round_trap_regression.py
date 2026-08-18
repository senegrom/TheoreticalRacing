#!/usr/bin/env python3
"""Pin Round 124's phase-consistent trap-L2 pace gains."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

CASES = [('silverstone', 93)]
EXPECTED = {'AI1': {'silverstone:93': (7, 0, [81, 82, 83, 84, 85, 85, 87])}, 'AI2': {'silverstone:93': (7, 0, [81, 82, 83, 84, 85, 86, 87])}}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {"AI1": {}, "AI2": {}}
    with tempfile.TemporaryDirectory(prefix="round124-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for track, seed in CASES:
                actual[kind][f"{track}:{seed}"] = bench_ai.run_track(
                    track, timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-124 regression: {actual}, expected {EXPECTED}")
    for key in EXPECTED["AI1"]:
        ai1, ai2 = EXPECTED["AI1"][key], EXPECTED["AI2"][key]
        if ai1[:2] != ai2[:2] or any(a > b for a, b in zip(ai1[2], ai2[2])):
            raise SystemExit(f"Round-124 Pareto contract lost on {key}: {EXPECTED}")
        if sum(ai1[2]) >= sum(ai2[2]):
            raise SystemExit(f"Round-124 pace gain lost on {key}: {EXPECTED}")
    print("AI1EarlyRoundTrapRegression: OK (all measured gains faster; AI2 frozen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
