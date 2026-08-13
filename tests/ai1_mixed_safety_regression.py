#!/usr/bin/env python3
"""Pin the Round-78 heterogeneous-field safety boundary."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    # The unrestricted fast two-exit proof accelerated an AI1 car in this
    # heterogeneous field and caused a different AI1 car to crash 66 global
    # moves later. Keeping fast mixed-field candidates on the wider three-exit
    # certificate makes the race match the crash-free pre-private-lane policy.
    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-mixed-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        bench_ai.set_kinds(["AI2"] * 4 + ["AI1"] * 4)
        result = bench_ai.run_track_h2h("lemans", timeout=600, seed=2)

    if result is None:
        raise SystemExit("AI1 mixed Le Mans seed-2 race failed or produced no complete log")
    for kind in ("AI1", "AI2"):
        place_sum, finishers, crashes = result[kind]
        if finishers != 4 or crashes != 0:
            raise SystemExit(
                "AI1 mixed-field safety regression: "
                f"{kind} place_sum={place_sum}, finishers={finishers}, crashes={crashes}"
            )

    print(
        "AI1MixedSafetyRegression: OK "
        f"(AI1 places={result['AI1'][0]}, AI2 places={result['AI2'][0]}, crashes=0/0)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
