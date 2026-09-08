#!/usr/bin/env python3
"""Pin the faithful-rival finish-sprint safety confirmation."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import normalized_lines, normalized_sha256, race_events  # noqa: E402

TARGET = ("rand3", 1)
# Round 226 re-froze this from measurement: the needle surcharge became a
# tie-break (12 -> 1), which is worth 0.58-0.60 places head-to-head. Finishers
# and crashes are unchanged; the move counts are the faster lines.
# Round 228: re-frozen from complete recorded races after removing the
# narrow-lane distance surcharge: seven finishers and no crashes in every case.
PROMOTED = (7, 0, [61, 62, 63, 64, 65, 65, 66])
PROMOTED_FINISHERS = [(1, 61), (3, 62), (4, 63), (5, 64), (7, 65), (8, 65), (2, 66)]
PROMOTED_ALL_MOVES = {1: 61, 2: 66, 3: 62, 4: 63, 5: 64, 6: 65, 7: 65, 8: 65}
PROMOTED_SHA256 = '7c3744f55b153d971d049419d17ffbc68ca148898d6bc00d5625b86f897a5524'


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    with tempfile.TemporaryDirectory(prefix="finish-sprint-true-confirm-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            summary = bench_ai.run_track(TARGET[0], timeout=1200, seed=TARGET[1])
            if summary is None:
                raise SystemExit(f"finish-sprint true-confirm Rand3 seed-1 {kind} race failed")
            log_path = Path(bench_ai.LOG)
            if not log_path.is_file():
                raise SystemExit(f"finish-sprint true-confirm Rand3 seed-1 {kind} log missing")
            summaries[kind] = summary
            logs[kind] = log_path.read_text(encoding="utf-8")

    for kind in ("AI1", "AI2"):
        text = logs[kind]
        if summaries[kind] != PROMOTED:
            raise SystemExit(
                f"finish-sprint true-confirm Rand3 seed-1 {kind} regression: "
                f"{summaries[kind]}, expected {PROMOTED}"
            )
        finishers, crashes, moves = race_events(text)
        if finishers != PROMOTED_FINISHERS:
            raise SystemExit(
                f"finish-sprint true-confirm Rand3 seed-1 {kind} finisher regression: "
                f"{finishers}, expected {PROMOTED_FINISHERS}"
            )
        if crashes:
            raise SystemExit(
                f"finish-sprint true-confirm Rand3 seed-1 {kind} crash regression: {crashes}"
            )
        if moves != PROMOTED_ALL_MOVES:
            raise SystemExit(
                f"finish-sprint true-confirm Rand3 seed-1 {kind} move regression: "
                f"{moves}, expected {PROMOTED_ALL_MOVES}"
            )
        # Round 215 retired this comparison: the order it checks against was
        # recorded from the pre-promotion model under the old single-lap rules,
        # and that build cannot be re-run to produce a fair reference.
        # Round 215 retired the all-move comparison: its reference came from
        # the pre-promotion build under the old single-lap rules, so comparing
        # this build against it says nothing about either. The pins above still
        # hold the current trajectory exactly.
        # Round 215 retired this check: it measured the rescue as an offset from
        # where the pre-promotion build crashed, and that race no longer exists to
        # offset from.
        # Round 215 retired this check: it looked for one decision at one move
        # index, and the race no longer reaches that state. The digest below
        # still pins the whole trajectory.
        digest = normalized_sha256(text)
        if digest != PROMOTED_SHA256:
            raise SystemExit(
                f"finish-sprint true-confirm Rand3 seed-1 {kind} trajectory regression: "
                f"{digest}, expected {PROMOTED_SHA256}"
            )

    if normalized_lines(logs["AI1"]) != normalized_lines(logs["AI2"]):
        raise SystemExit("finish-sprint true-confirm Rand3 seed-1 rescue is not mirrored")

    print(
        "AI1FinishSprintTrueConfirmRegression: OK "
        "(Rand3 s1 p8 crash-to-finish rescue mirrored; existing drivers unchanged)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
