#!/usr/bin/env python3
"""Pin Round 126's equal-speed false-target rescue."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

CASES = [("zandvoort", 115)]
EXPECTED = {'AI1': {'zandvoort:115': (7, 0, [139, 140, 141, 142, 143, 144, 145])}, 'AI2': {'zandvoort:115': (6, 1, [139, 140, 141, 143, 144, 146])}}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {"AI1": {}, "AI2": {}}
    with tempfile.TemporaryDirectory(prefix="round126-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for track, seed in CASES:
                actual[kind][f"{track}:{seed}"] = bench_ai.run_track(
                    track, timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-126 regression: {actual}, expected {EXPECTED}")
    ai1 = EXPECTED["AI1"]["zandvoort:115"]
    ai2 = EXPECTED["AI2"]["zandvoort:115"]
    if not (ai1[0] > ai2[0] and ai1[1] < ai2[1]):
        raise SystemExit(f"Round-126 safety contract lost: {EXPECTED}")
    print("AI1EqualSpeedVetoRegression: OK (Zandvoort s115 rescued; AI2 frozen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
