#!/usr/bin/env python3
"""Pin immediate-finish precedence over a superficially winning endgame seal.

The champion takes the guaranteed crossing on every board. Until the
2026-09-04 promotion the precedence was AI1-only and this pin froze AI2
forgoing it with two or three rivals as the control; the kinds are one policy
now, so each board is asked once.
"""

from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import Oracle  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

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
        roots = {}
        for nplayers, board in ROOT_BOARDS.items():
            bench_ai.set_nplayers(nplayers)
            roots[nplayers] = ask(LABELS[0], [(0, board)])[0]

        bench_ai.set_nplayers(3)
        boxed_rival, later_finisher = ask(
            LABELS[0],
            [(1, AFTER_SEAL), (2, AFTER_RIVAL_CRASH)],
        )

    finish_mask = "XXAXXAXFF"
    for nplayers in ROOT_BOARDS:
        if roots[nplayers] != (0, 1, finish_mask):
            raise SystemExit(
                f"immediate-finish {nplayers}-player champion did not take S: "
                f"{roots[nplayers]}"
            )
    if boxed_rival != (-1, -1, "XXXXXBXXB"):
        raise SystemExit(f"immediate-finish causal rival crash changed: {boxed_rival}")
    if later_finisher != (-1, 1, "XBAXAAFFF"):
        raise SystemExit(f"immediate-finish later rival finish changed: {later_finisher}")

    print(
        "AI1ImmediateFinishRegression: OK "
        "(the champion takes guaranteed first with 1-3 live rivals)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
