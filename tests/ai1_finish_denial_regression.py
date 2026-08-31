#!/usr/bin/env python3
"""Pin the contested-finish denial rescue and its frozen AI2 control."""

import hashlib
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

TARGET = ("hairpin", 68)
CONTROL = (6, 1, [16, 16, 17, 18, 19, 20])
RESCUED = (7, 0, [16, 16, 17, 18, 19, 19, 20])
CONTROL_FINISHERS = [
    (2, 16),
    (3, 16),
    (4, 17),
    (6, 18),
    (7, 19),
    (1, 20),
]
RESCUED_FINISHERS = [
    (2, 16),
    (3, 16),
    (4, 17),
    (6, 18),
    (7, 19),
    (8, 19),
    (1, 20),
]
CONTROL_MOVES = {1: 20, 2: 16, 3: 16, 4: 17, 5: 20, 6: 18, 7: 19, 8: 20}
RESCUED_MOVES = {1: 20, 2: 16, 3: 16, 4: 17, 5: 19, 6: 18, 7: 19, 8: 19}
CONTROL_CRASHES = [(8, 20)]
CONTROL_DECISION = "104 p8 AI2 SE v(7,0)→(8,1) (41,6)→(49,7) ok"
RESCUED_DECISION = "104 p8 AI1 W v(7,0)→(6,0) (41,6)→(47,6) ok"
CONTROL_SHA256 = "c65bdb60c43e7a65e9256e1623850b9da07ba8b6c42dae90c25408e24e5aba48"
RESCUED_SHA256 = "802fef7f56604ece09ab89ae6bf332d5f858dfd18a8d216e119e8ce7d1f452e4"


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


def logged_kinds(text: str, nplayers: int) -> list[str]:
    kinds: list[str | None] = [None] * nplayers
    for line in text.splitlines():
        match = re.match(r"^\d+ p(\d+) (AI1|AI2) ", line)
        if match is None:
            continue
        player = int(match.group(1))
        kind = match.group(2)
        if player < 1 or player > nplayers:
            raise SystemExit(f"finish-denial log has out-of-range player p{player}")
        previous = kinds[player - 1]
        if previous is not None and previous != kind:
            raise SystemExit(
                f"finish-denial p{player} changed kind in one race: {previous} -> {kind}"
            )
        kinds[player - 1] = kind
    if any(kind is None for kind in kinds):
        raise SystemExit(f"finish-denial log is missing player kinds: {kinds}")
    return [kind for kind in kinds if kind is not None]


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    with tempfile.TemporaryDirectory(prefix="finish-denial-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["hairpin"]))  # frozen pre-loop-surgery geometry
        bench_ai.set_nplayers(8)
        for kind in ("AI2", "AI1"):
            bench_ai.set_all_to(kind)
            summary = bench_ai.run_track(TARGET[0], timeout=1200, seed=TARGET[1])
            if summary is None:
                raise SystemExit(f"finish-denial hairpin seed-68 {kind} race failed")
            log_path = Path(bench_ai.LOG)
            if not log_path.is_file():
                raise SystemExit(f"finish-denial hairpin seed-68 {kind} log missing")
            summaries[kind] = summary
            logs[kind] = log_path.read_text(encoding="utf-8")

        mixed_rosters = {
            "MIXED_AI2_LAST": ["AI1"] * 4 + ["AI2"] * 4,
            "MIXED_AI1_LAST": ["AI2"] * 4 + ["AI1"] * 4,
        }
        for label, kinds in mixed_rosters.items():
            bench_ai.set_kinds(kinds)
            summary = bench_ai.run_track(TARGET[0], timeout=1200, seed=TARGET[1])
            if summary is None:
                raise SystemExit(f"finish-denial hairpin seed-68 {label} race failed")
            summaries[label] = summary
            log = Path(bench_ai.LOG).read_text(encoding="utf-8")
            actual_kinds = logged_kinds(log, len(kinds))
            if actual_kinds != kinds:
                raise SystemExit(
                    f"finish-denial {label} roster changed: {actual_kinds}, expected {kinds}"
                )
            logs[label] = log

    control_finishers, control_crashes, control_moves = race_events(logs["AI2"])
    if summaries["AI2"] != CONTROL:
        raise SystemExit(f"finish-denial AI2 control changed: {summaries['AI2']}")
    if control_finishers != CONTROL_FINISHERS:
        raise SystemExit(f"finish-denial AI2 finishers changed: {control_finishers}")
    if control_crashes != CONTROL_CRASHES or control_moves != CONTROL_MOVES:
        raise SystemExit(
            f"finish-denial AI2 events changed: crashes={control_crashes}, moves={control_moves}"
        )
    if CONTROL_DECISION not in logs["AI2"].splitlines():
        raise SystemExit(f"finish-denial AI2 decision missing: {CONTROL_DECISION}")
    control_digest = normalized_sha256(logs["AI2"])
    if control_digest != CONTROL_SHA256:
        raise SystemExit(
            f"finish-denial AI2 trajectory changed: {control_digest}, expected {CONTROL_SHA256}"
        )

    rescued_finishers, rescued_crashes, rescued_moves = race_events(logs["AI1"])
    if summaries["AI1"] != RESCUED:
        raise SystemExit(f"finish-denial AI1 rescue changed: {summaries['AI1']}")
    if rescued_finishers != RESCUED_FINISHERS:
        raise SystemExit(f"finish-denial AI1 finishers changed: {rescued_finishers}")
    if rescued_crashes or rescued_moves != RESCUED_MOVES:
        raise SystemExit(
            f"finish-denial AI1 events changed: crashes={rescued_crashes}, moves={rescued_moves}"
        )
    if RESCUED_DECISION not in logs["AI1"].splitlines():
        raise SystemExit(f"finish-denial AI1 decision missing: {RESCUED_DECISION}")
    rescued_digest = normalized_sha256(logs["AI1"])
    if rescued_digest != RESCUED_SHA256:
        raise SystemExit(
            f"finish-denial AI1 trajectory changed: {rescued_digest}, expected {RESCUED_SHA256}"
        )

    if [event for event in rescued_finishers if event[0] != 8] != CONTROL_FINISHERS:
        raise SystemExit("finish-denial rescue changed an existing finisher's order or moves")
    for player in (1, 2, 3, 4, 6, 7):
        if rescued_moves[player] != CONTROL_MOVES[player]:
            raise SystemExit(f"finish-denial rescue changed existing finisher p{player}")
    if rescued_moves[8] != CONTROL_CRASHES[0][1] - 1:
        raise SystemExit("finish-denial rescue lost the exact one-move crash-to-finish gain")
    if rescued_moves[5] != CONTROL_MOVES[5] - 1:
        raise SystemExit("finish-denial rescue lost the expected earlier-race cutoff for p5")

    mixed_expectations = (
        ("MIXED_AI2_LAST", CONTROL, CONTROL_FINISHERS, CONTROL_CRASHES,
         CONTROL_MOVES, CONTROL_DECISION, CONTROL_SHA256),
        ("MIXED_AI1_LAST", RESCUED, RESCUED_FINISHERS, [],
         RESCUED_MOVES, RESCUED_DECISION, RESCUED_SHA256),
    )
    for label, summary, finishers, crashes, moves, decision, digest in mixed_expectations:
        actual_finishers, actual_crashes, actual_moves = race_events(logs[label])
        if summaries[label] != summary:
            raise SystemExit(f"finish-denial {label} summary changed: {summaries[label]}")
        if (actual_finishers != finishers or actual_crashes != crashes
                or actual_moves != moves):
            raise SystemExit(
                f"finish-denial {label} events changed: finishers={actual_finishers}, "
                f"crashes={actual_crashes}, moves={actual_moves}"
            )
        if decision not in logs[label].splitlines():
            raise SystemExit(f"finish-denial {label} decision missing: {decision}")
        actual_digest = normalized_sha256(logs[label])
        if actual_digest != digest:
            raise SystemExit(
                f"finish-denial {label} trajectory changed: {actual_digest}, expected {digest}"
            )

    print(
        "AI1FinishDenialRegression: OK "
        "(hairpin s68 p8 crash-to-sixth rescue in homogeneous and mixed fields; "
        "AI2 control exact)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
