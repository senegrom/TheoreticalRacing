#!/usr/bin/env python3
"""The one label-invariance check (2026-09-27).

Since round 222 the AI1 and AI2 labels run one policy; an experiment is gated
by candidateSlots, never by a label, so the other pins race each case once.
This pin races one eight-car case under an all-AI1 field, an all-AI2 field and
an alternating one, and requires the three races to be identical once the
labels are erased.
"""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import normalized_lines  # noqa: E402

CASE = ("coil", 5)
ROSTERS = {
    "all-AI1": ["AI1"] * 8,
    "all-AI2": ["AI2"] * 8,
    "alternating": ["AI1", "AI2"] * 4,
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    track, seed = CASE
    logs = {}
    with tempfile.TemporaryDirectory(prefix="ai1-label-invariance-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for label, kinds in ROSTERS.items():
            bench_ai.set_kinds(kinds)
            if bench_ai.run_track(track, timeout=1200, seed=seed) is None:
                raise SystemExit(f"label invariance {track} seed-{seed} {label} race failed")
            logs[label] = normalized_lines(Path(bench_ai.LOG).read_text(encoding="utf-8"))
    reference = logs["all-AI2"]
    for label, lines in logs.items():
        if lines != reference:
            raise SystemExit(
                f"label invariance lost: the {label} field races differently on {track} seed {seed}"
            )
    print(
        "AI1LabelInvarianceRegression: OK "
        f"({track} seed {seed}: all-AI1, all-AI2 and alternating fields race identically)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
