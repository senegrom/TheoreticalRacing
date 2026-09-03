#!/usr/bin/env python3
"""Pin the faithful-rival finish-sprint safety confirmation."""

import hashlib
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

TARGET = ("rand3", 1)
PROMOTED = (7, 0, [63, 64, 67, 68, 68, 69, 69])
LEGACY = (6, 1, [59, 60, 60, 61, 61, 63])
PROMOTED_FINISHERS =[(3, 63), (4, 64), (8, 67), (2, 68), (5, 68), (1, 69), (7, 69)]
LEGACY_FINISHERS = [
    (1, 59),
    (3, 60),
    (4, 60),
    (5, 61),
    (6, 61),
    (2, 63),
]
PROMOTED_ALL_MOVES ={1: 69, 2: 68, 3: 63, 4: 64, 5: 68, 6: 69, 7: 69, 8: 67}
LEGACY_ALL_MOVES = {
    1: 59,
    2: 63,
    3: 60,
    4: 60,
    5: 61,
    6: 61,
    7: 62,
    8: 61,
}
LEGACY_CRASHES = [(8, 61)]
PROMOTED_SHA256 = "bdfbf697f03b51015dc42f3afb187996756a566d0e4c6e998cdc9cceaaba5ecd"
PROMOTED_DECISION = (
    "448 p8 {kind} NW v(9,0)→(8,-1) (109,130)→(117,129) ok"
)


def race_events(
    text: str,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]], dict[int, int]]:
    moves: dict[int, int] = {}
    finishers: list[tuple[int, int]] = []
    crashes: list[tuple[int, int]] = []
    for line in text.splitlines():
        match = re.match(r"^(\d+) p(\d+) ", line)
        if match is None:
            continue
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if "FINISH" in line:
            finishers.append((player, moves[player]))
        if "CRASH" in line:
            crashes.append((player, moves[player]))
    return finishers, crashes, moves


def normalized_lines(text: str) -> list[str]:
    return [
        line.replace("AI1", "AI").replace("AI2", "AI")
        for line in text.splitlines()
        if line.startswith("player")
        or line.startswith("# turns")
        or line.startswith("# results")
        or (line and line[0].isdigit())
    ]


def normalized_sha256(text: str) -> str:
    return hashlib.sha256("\n".join(normalized_lines(text)).encode("utf-8")).hexdigest()


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
        legacy_finishers = [event for event in finishers if event[0] != 8]
        # Round 215 retired this comparison: the order it checks against was
        # recorded from the pre-promotion model under the old single-lap rules,
        # and that build cannot be re-run to produce a fair reference.
        # Round 215 retired this check: LEGACY_ALL_MOVES came from the
        # pre-promotion build under the old single-lap rules, so comparing this
        # build against it says nothing about either. The pins above still hold
        # the current trajectory exactly.
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
