#!/usr/bin/env python3
"""Pin Round 103's six-rival true-confirmation crash rescue."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

AI1_EXPECTED = (7, 0, [65, 65, 65, 66, 67, 67, 68])
AI2_CONTROL = (6, 1, [65, 65, 66, 66, 67, 67])


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    with tempfile.TemporaryDirectory(prefix="true-rival-roster-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        bench_ai.set_all_to("AI1")
        ai1 = bench_ai.run_track("zigzag", timeout=1200, seed=76)
        bench_ai.set_all_to("AI2")
        ai2 = bench_ai.run_track("zigzag", timeout=1200, seed=76)
    if ai1 != AI1_EXPECTED:
        raise SystemExit(f"Round-103 AI1 Zigzag seed-76 regression: {ai1}, expected {AI1_EXPECTED}")
    if ai2 != AI2_CONTROL:
        raise SystemExit(f"Round-103 frozen AI2 control moved: {ai2}, expected {AI2_CONTROL}")
    print("AI1TrueRivalRosterRegression: OK (AI1 rescues Zigzag seed 76; frozen AI2 control retained)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
