#!/usr/bin/env python3
"""Pin immediate-finish precedence over a superficially winning endgame seal."""

from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import Oracle  # noqa: E402

TRACK = "sprint"
# sprint left the fleet (2026-08-29): the pin races a PRIVATE install --
# a jar copy beside the frozen fixture track -- so its byte-frozen boards
# and masks stay valid forever, independent of the live tracks/ folder.
FIXTURE_JAR = None
ROOT_BOARD = [
    (32, 10, -4, 9, 0),
    (28, 20, 0, -3, 0),
    (29, 17, 0, 2, 0),
]
ROOT_BOARDS = {
    2: ROOT_BOARD[:2],
    3: ROOT_BOARD,
    # Stationary, road-live and far from the finish pocket (mask AAAAAAAAA).
    4: ROOT_BOARD + [(20, 5, 0, 0, 0)],
}
AFTER_SEAL = [
    (29, 18, -3, 8, 0),
    (28, 20, 0, -3, 0),
    (29, 17, 0, 2, 0),
]
AFTER_RIVAL_CRASH = [
    (29, 18, -3, 8, 0),
    (28, 20, 0, -3, 99),
    (29, 17, 0, 2, 0),
]


def ask(kind: str, queries: list[tuple[int, list[tuple[int, int, int, int, int]]]]):
    bench_ai.set_all_to(kind)
    oracle = Oracle(TRACK, FIXTURE_JAR or Path(bench_ai.JAR), bench_ai.PROPS)
    try:
        return [oracle.ask(mover, board) for mover, board in queries]
    finally:
        oracle.close()


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    with tempfile.TemporaryDirectory(prefix="immediate-finish-") as directory:
        bench_ai.configure_runtime(directory)
        global FIXTURE_JAR
        install = Path(directory)
        FIXTURE_JAR = install / "theoreticRacing.jar"
        shutil.copyfile(bench_ai.JAR, FIXTURE_JAR)
        (install / "tracks").mkdir(exist_ok=True)
        shutil.copyfile(ROOT / "tests" / "fixtures" / "sprint.track",
                        install / "tracks" / "sprint.track")
        ai1 = {}
        ai2 = {}
        for nplayers, board in ROOT_BOARDS.items():
            bench_ai.set_nplayers(nplayers)
            ai1[nplayers] = ask("AI1", [(0, board)])[0]
            ai2[nplayers] = ask("AI2", [(0, board)])[0]

        bench_ai.set_nplayers(3)
        boxed_rival, later_finisher = ask(
            "AI2",
            [(1, AFTER_SEAL), (2, AFTER_RIVAL_CRASH)],
        )

    finish_mask = "XXAXXAXFF"
    for nplayers in ROOT_BOARDS:
        if ai1[nplayers] != (0, 1, finish_mask):
            raise SystemExit(
                f"immediate-finish {nplayers}-player AI1 did not take S: "
                f"{ai1[nplayers]}"
            )
    expected_ai2 = {
        2: (0, 1, finish_mask),
        3: (1, -1, finish_mask),
        4: (1, -1, finish_mask),
    }
    if ai2 != expected_ai2:
        raise SystemExit(
            f"immediate-finish frozen AI2 field boundary changed: {ai2}"
        )
    if boxed_rival != (-1, -1, "XXXXXBXXB"):
        raise SystemExit(f"immediate-finish causal rival crash changed: {boxed_rival}")
    if later_finisher != (-1, 1, "XBAXAAFFF"):
        raise SystemExit(f"immediate-finish later rival finish changed: {later_finisher}")

    print(
        "AI1ImmediateFinishRegression: OK "
        "(AI1 takes guaranteed first with 1-3 live rivals; frozen AI2 "
        "forgoes it with 2-3 rivals)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
