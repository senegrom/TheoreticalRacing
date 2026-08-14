#!/usr/bin/env python3
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai

EXPECTED = {
    ("chicane", 51): {
        "AI1": (7, 0, [19, 20, 20, 21, 21, 21, 22]),
        "AI2": (6, 1, [19, 20, 20, 21, 21, 21]),
    },
    ("zandvoort", 32): {
        "AI1": (7, 0, [139, 140, 141, 142, 143, 144, 146]),
        "AI2": (6, 1, [139, 140, 141, 142, 143, 144]),
    },
}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ai1-policy-layer-") as work_dir:
        bench_ai.configure_runtime(work_dir)
        bench_ai.set_nplayers(8)
        for (track, seed), policies in EXPECTED.items():
            for policy, expected in policies.items():
                bench_ai.set_all_to(policy)
                result = bench_ai.run_track(track, timeout=900, seed=seed)
                if result is None:
                    raise SystemExit(f"invalid {track} seed {seed} {policy}")
                if result != expected:
                    raise SystemExit(
                        f"{track} seed {seed} {policy}: expected {expected}, got {result}"
                    )
    print("AI1PolicyLayerRegression: OK")


if __name__ == "__main__":
    main()
