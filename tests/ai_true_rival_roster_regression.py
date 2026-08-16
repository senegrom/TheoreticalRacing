#!/usr/bin/env python3
"""Pin Round 103's full-roster true-confirmation safety boundaries."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

EXPECTED = {
    ("zigzag", 76): (7, 0, [65, 65, 65, 66, 67, 67, 68]),
    ("hungaroring", 63): (7, 0, [118, 121, 122, 124, 127, 128, 129]),
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    results = {}
    with tempfile.TemporaryDirectory(prefix="true-rival-roster-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for case in EXPECTED:
                track, seed = case
                results[(kind, case)] = bench_ai.run_track(
                    track, timeout=1200, seed=seed
                )

    for kind in ("AI1", "AI2"):
        for case, expected in EXPECTED.items():
            actual = results[(kind, case)]
            if actual != expected:
                raise SystemExit(
                    f"Round-103 {kind} {case[0]} seed-{case[1]} regression: "
                    f"{actual}, expected {expected}"
                )
    for case in EXPECTED:
        if results[("AI1", case)] != results[("AI2", case)]:
            raise SystemExit(
                f"Round-103 target parity lost at {case}: {results}"
            )

    print("AITrueRivalRosterRegression: OK "
          "(Zigzag 76 and Hungaroring 63 safety boundaries pinned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
