#!/usr/bin/env python3
"""The one label-invariance check (2026-09-27).

Since round 222 the AI1 and AI2 labels run one policy; an experiment is gated
by candidateSlots, never by a label, so the other pins race each case once.
This pin races one eight-car case under an all-AI1 field and an alternating
one, and requires both to be identical, once the labels are erased, to the
all-AI2 race that ai1_six_ahead_high_speed_regression pins: the same profile,
roster and course, so it is not raced twice (review, 2026-09-29).
"""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import normalized_sha256  # noqa: E402
from ai1_six_ahead_high_speed_regression import VETO_CASES  # noqa: E402

CASE = ("coil", 5)
# The frozen all-AI2 race (the champion label) of this case.
REFERENCE = VETO_CASES[CASE][1]
ROSTERS = {
    "all-AI1": ["AI1"] * 8,
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
            logs[label] = normalized_sha256(Path(bench_ai.LOG).read_text(encoding="utf-8"))
    for label, digest in logs.items():
        if digest != REFERENCE:
            raise SystemExit(
                f"label invariance lost: the {label} field races differently on {track} seed {seed} "
                f"({digest}, the all-AI2 race is {REFERENCE})"
            )
    print(
        "AI1LabelInvarianceRegression: OK "
        f"({track} seed {seed}: all-AI1 and alternating fields race as the pinned all-AI2 field)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
