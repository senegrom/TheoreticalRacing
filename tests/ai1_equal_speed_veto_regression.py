#!/usr/bin/env python3
"""Pin Round 108's AI1-only equal-speed false-target rescue."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

EXPECTED = {"AI1": (7, 0, [139, 140, 141, 142, 143, 144, 145]), "AI2": (6, 1, [139, 140, 141, 143, 144, 146])}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {}
    with tempfile.TemporaryDirectory(prefix="round108-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            actual[kind] = bench_ai.run_track("zandvoort", timeout=1200, seed=115)
    if actual != EXPECTED:
        raise SystemExit(f"Round-108 regression: {actual}, expected {EXPECTED}")
    if actual["AI1"][0] <= actual["AI2"][0] and actual["AI1"][1] >= actual["AI2"][1]:
        raise SystemExit(f"Round-108 rescue lost: {actual}")
    print("AI1EqualSpeedVetoRegression: OK (Zandvoort s115 rescued; AI2 policy frozen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
