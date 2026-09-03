#!/usr/bin/env python3
"""Pin the exact-axial vmax narrow-ridge rescue and frozen AI2 control."""

import hashlib
from itertools import zip_longest
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

TARGET = ("rand3", 103)
CONTROL = (6, 1, [59, 60, 61, 62, 62, 63])
RESCUED = (7, 0, [59, 60, 61, 62, 62, 63, 63])
CONTROL_FINISHERS = [(1, 59), (2, 60), (4, 61), (5, 62), (7, 62), (6, 63)]
RESCUED_FINISHERS = CONTROL_FINISHERS + [(8, 63)]
CONTROL_MOVES = {1: 59, 2: 60, 3: 63, 4: 61, 5: 62, 6: 63, 7: 62, 8: 62}
RESCUED_MOVES = {1: 59, 2: 60, 3: 63, 4: 61, 5: 62, 6: 63, 7: 62, 8: 63}
CONTROL_RESULTS = ["A", "B", "D", "E", "G", "F", "C", "H"]
RESCUED_RESULTS = ["A", "B", "D", "E", "G", "F", "H", "C"]
CONTROL_ACTIONS = 492
RESCUED_ACTIONS = 493
CONTROL_CRASHES = [(8, 62)]
CONTROL_DECISION = "440 p8 AI2 NONE v(11,0)→(11,0) (88,130)→(99,130) ok"
RESCUED_DECISION = "440 p8 AI1 NW v(11,0)→(10,-1) (88,130)→(98,129) ok"
CONTROL_CRASH = "490 p8 AI2 W v(5,-3)→(4,-3) (144,117)→(148,114) CRASH place=8"
RESCUED_FINISH = "493 p8 AI1 NW v(4,-4)→(3,-5) (144,117)→(147,112) FINISH place=7"
FIRST_DIFFERENCE_LINE = 449
CONTROL_NORMALIZED_DECISION = CONTROL_DECISION.replace("AI2", "AI")
RESCUED_NORMALIZED_DECISION = RESCUED_DECISION.replace("AI1", "AI")
CONTROL_SHA256 = "038204d0a4609e4c5ecd8b4628c8883abe703cf0444bed725019ff2fe6c44434"
RESCUED_SHA256 = "4657016f6e56554c85566c383273c3a442af517f7eee341d242550b0ffdae392"


def race_events(
    text: str,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]], dict[int, int], int]:
    moves: dict[int, int] = {}
    finishers: list[tuple[int, int]] = []
    crashes: list[tuple[int, int]] = []
    actions = 0
    for line in text.splitlines():
        match = re.match(r"^(\d+) p(\d+) ", line)
        if match is None:
            continue
        actions += 1
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if "FINISH" in line:
            finishers.append((player, moves[player]))
        if "CRASH" in line:
            crashes.append((player, moves[player]))
    return finishers, crashes, moves, actions


def result_order(text: str) -> list[str]:
    lines = text.splitlines()
    try:
        start = lines.index("# results") + 1
    except ValueError as exc:
        raise SystemExit("vmax narrow-ridge result block missing") from exc
    results = []
    for line in lines[start:]:
        match = re.fullmatch(r"\d+\. (.+)", line)
        if match is not None:
            results.append(match.group(1))
    return results


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


def first_difference(left: list[str], right: list[str]) -> tuple[int, str | None, str | None]:
    for index, (left_line, right_line) in enumerate(
        zip_longest(left, right), start=1
    ):
        if left_line != right_line:
            return index, left_line, right_line
    return 0, None, None


# RETIRED in round 215. This pin compared a control race in which p8 crashes at
# a narrow ridge with a rescued race in which the promoted policy saves it. With
# checkpoints on every race and the finish-wall rule, the control race no longer
# crashes at all -- both kinds now finish seven cars with none lost -- so there
# is no rescue to detect and nothing for the comparison to mean. The constants
# above are kept as the record of what the scenario used to look like. The
# behaviour it guarded (a car surviving a narrow ridge at speed) is covered by
# the 730-race fleet grid and the fresh-seed slice.


def main() -> int:
    print("AI1VmaxNarrowRidgeRegression: RETIRED (see the note above)")
    return 0


def _retired_main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    with tempfile.TemporaryDirectory(prefix="vmax-narrow-ridge-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI2", "AI1"):
            bench_ai.set_all_to(kind)
            summary = bench_ai.run_track(TARGET[0], timeout=1200, seed=TARGET[1])
            if summary is None:
                raise SystemExit(f"vmax narrow-ridge rand3 seed-103 {kind} race failed")
            log_path = Path(bench_ai.LOG)
            if not log_path.is_file():
                raise SystemExit(f"vmax narrow-ridge rand3 seed-103 {kind} log missing")
            summaries[kind] = summary
            logs[kind] = log_path.read_text(encoding="utf-8")

    expectations = (
        (
            "AI2", CONTROL, CONTROL_FINISHERS, CONTROL_CRASHES, CONTROL_MOVES,
            CONTROL_ACTIONS, CONTROL_RESULTS, CONTROL_DECISION, CONTROL_SHA256,
        ),
        (
            "AI1", RESCUED, RESCUED_FINISHERS, [], RESCUED_MOVES,
            RESCUED_ACTIONS, RESCUED_RESULTS, RESCUED_DECISION, RESCUED_SHA256,
        ),
    )
    evidence = {}
    for kind, summary, finishers, crashes, moves, actions, results, decision, digest in expectations:
        actual_finishers, actual_crashes, actual_moves, actual_actions = race_events(logs[kind])
        evidence[kind] = (actual_finishers, actual_crashes, actual_moves, actual_actions)
        if summaries[kind] != summary:
            raise SystemExit(f"vmax narrow-ridge {kind} summary changed: {summaries[kind]}")
        if (actual_finishers != finishers or actual_crashes != crashes
                or actual_moves != moves or actual_actions != actions):
            raise SystemExit(
                f"vmax narrow-ridge {kind} events changed: finishers={actual_finishers}, "
                f"crashes={actual_crashes}, moves={actual_moves}, actions={actual_actions}"
            )
        actual_results = result_order(logs[kind])
        if actual_results != results:
            raise SystemExit(f"vmax narrow-ridge {kind} results changed: {actual_results}")
        if decision not in logs[kind].splitlines():
            raise SystemExit(f"vmax narrow-ridge {kind} decision missing: {decision}")
        actual_digest = normalized_sha256(logs[kind])
        if actual_digest != digest:
            raise SystemExit(
                f"vmax narrow-ridge {kind} trajectory changed: {actual_digest}, expected {digest}"
            )

    if CONTROL_CRASH not in logs["AI2"].splitlines():
        raise SystemExit(f"vmax narrow-ridge AI2 crash missing: {CONTROL_CRASH}")
    if RESCUED_FINISH not in logs["AI1"].splitlines():
        raise SystemExit(f"vmax narrow-ridge AI1 finish missing: {RESCUED_FINISH}")

    difference = first_difference(normalized_lines(logs["AI1"]), normalized_lines(logs["AI2"]))
    expected_difference = (
        FIRST_DIFFERENCE_LINE, RESCUED_NORMALIZED_DECISION, CONTROL_NORMALIZED_DECISION,
    )
    if difference != expected_difference:
        raise SystemExit(
            f"vmax narrow-ridge first divergence changed: {difference}, "
            f"expected {expected_difference}"
        )

    rescued_finishers, _, rescued_moves, _ = evidence["AI1"]
    control_finishers, _, control_moves, _ = evidence["AI2"]
    if rescued_finishers[:-1] != control_finishers:
        raise SystemExit("vmax narrow-ridge rescue changed the existing six finishers")
    for player, _ in control_finishers:
        if rescued_moves[player] != control_moves[player]:
            raise SystemExit(f"vmax narrow-ridge rescue changed existing finisher p{player}")
    if rescued_moves[8] != control_moves[8] + 1:
        raise SystemExit("vmax narrow-ridge rescue lost the exact crash-to-finish move gain")

    print(
        "AI1VmaxNarrowRidgeRegression: OK "
        "(rand3 s103 p8 exact axial-vmax crash-to-seventh rescue; AI2 control exact)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
