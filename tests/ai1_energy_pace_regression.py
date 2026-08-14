#!/usr/bin/env python3
"""Pin the Round-90 proof-gated high-energy pace boundaries."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

EXPECTED = {
    ("nurburgring", 1): [90, 91, 94, 95, 95, 96, 97],
    ("interlagos", 29): [122, 123, 124, 126, 128, 129, 130],
    ("interlagos", 47): [122, 123, 125, 126, 127, 128, 130],
    ("spa", 17): [78, 80, 82, 83, 84, 84, 86],
    ("zandvoort", 44): [139, 140, 141, 142, 143, 144, 146],
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-energy-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        bench_ai.set_all_to("AI1")
        for (track, seed), expected_moves in EXPECTED.items():
            result = bench_ai.run_track(track, timeout=900, seed=seed)
            if result is None:
                raise SystemExit(f"AI1 {track} seed-{seed} race failed or produced no complete log")
            finishes, crashes, finish_moves = result
            if (finishes, crashes, finish_moves) != (7, 0, expected_moves):
                raise SystemExit(
                    f"AI1 {track} seed-{seed} high-energy regression: "
                    f"{(finishes, crashes, finish_moves)} != {(7, 0, expected_moves)}"
                )

    print("AI1EnergyPaceRegression: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
