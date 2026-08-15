#!/usr/bin/env python3
"""Pin Round 101 guarded-field gains and its finite-horizon counterexamples."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

EXPECTED = {
    ("coil", 9): (7, 0, [58, 59, 60, 61, 61, 62, 62]),
    ("silverstone", 56): (7, 0, [81, 82, 83, 84, 85, 85, 86]),
    ("spa", 57): (7, 0, [78, 80, 81, 84, 85, 86, 87]),
    ("interlagos", 26): (7, 0, [122, 123, 124, 126, 127, 128, 129]),
    ("interlagos", 38): (7, 0, [122, 123, 124, 125, 126, 127, 128]),
    ("interlagos", 40): (7, 0, [122, 123, 124, 125, 127, 129, 130]),
    ("interlagos", 54): (7, 0, [122, 123, 124, 125, 126, 127, 128]),
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    with tempfile.TemporaryDirectory(prefix="ai1-guarded-field-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        bench_ai.set_all_to("AI1")
        for (track, seed), expected in EXPECTED.items():
            result = bench_ai.run_track(track, timeout=900, seed=seed)
            if result != expected:
                raise SystemExit(
                    f"Round-101 guarded-field regression {track} seed {seed}: "
                    f"{result}, expected {expected}"
                )
    print("AI1GuardedFieldPaceRegression: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
