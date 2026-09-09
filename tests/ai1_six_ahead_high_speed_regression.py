#!/usr/bin/env python3
"""Pin the high-speed moderate six-ahead pace frontier and its vetoes."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import finishers, normalized_lines, normalized_sha256, player_moves  # noqa: E402

TARGET = ("spa", 83)
# Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
PROMOTED = (7, 0, [79, 80, 81, 83, 84, 84, 86])
LEGACY = (7, 0, [79, 80, 81, 84, 84, 86, 88])
PROMOTED_FINISHERS = [
    (3, 79),
    (4, 80),
    (5, 81),
    (6, 83),
    (7, 84),
    (8, 84),
    (1, 86),
]
LEGACY_ALL_MOVES = {1: 88, 2: 87, 3: 79, 4: 80, 5: 81, 6: 84, 7: 84, 8: 86}
PROMOTED_ALL_MOVES = {1: 86, 2: 85, 3: 79, 4: 80, 5: 81, 6: 83, 7: 84, 8: 84}
PROMOTED_SHA256 = "462ca020c2815ca6b50e0af10076fe56c8b1b202679eda027fc4b245e794637a"
PROMOTED_DECISION = (
    # Round 229: re-frozen from measurement (the soft caution stack left the score).
    "201 p1 {kind} NW v(1,8)→(0,7) (101,128)→(101,135) ok"
)

# These cases cover every redistribution or slowdown exposed by the historical
# broad six-ahead arm. The final candidate-speed and gain band must leave each
# complete trajectory equal to the champion.
VETO_CASES = {
    ("spa", 27): (
        (7, 0, [78, 79, 81, 82, 84, 85, 86]),
        "a1dfbf0a34021b484805f14ea50f12b6ccc1887311bfb6cfbd8d9197a71d45d0",
    ),
    ("spa", 57): (
        (7, 0, [78, 80, 81, 82, 83, 86, 88]),
        "9067e9d91b179a555a893a15684d1c5f64f48d2f6b81862132a4aa3e87e6c933",
    ),
    ("spa", 12): (
        (7, 0, [78, 80, 81, 84, 84, 85, 86]),
        "a59cfd048f950cd5a4a510c5d7eb24121420b64dafe0dd97daf452422ba6e33d",
    ),
    ("spa", 31): (
        (7, 0, [78, 79, 81, 82, 82, 83, 84]),
        "0bb27e99e78382229716b21e11d058833644c80bdb2904c6402682b55efbe26a",
    ),
    ("spa", 40): (
        (7, 0, [78, 79, 80, 81, 81, 82, 84]),
        "cb9bfc27705040dbbb0725cdd2b802e630920005542e0982a6acf7a58192ccae",
    ),
    ("spa", 47): (
        (7, 0, [78, 80, 81, 82, 84, 85, 87]),
        "b73c9481046b9462f3ecab3759c88af35b72fcdea5974c85f03fccfabcb2c206",
    ),
    ("coil", 5): (
        (7, 0, [58, 58, 59, 59, 60, 62, 62]),
        "f8427669146975630095b98c8b77b0259b62be917e344d7879ebcfbffc7c6657",
    ),
    ("coil", 22): (
        (7, 0, [58, 59, 59, 59, 60, 61, 61]),
        "5822f9dc12715733ab7e46406cf214594be8cf7eec7466c0dfb9c07a572c7c85",
    ),
    ("silverstone", 78): (
        (7, 0, [81, 82, 83, 84, 85, 86, 86]),
        "7fa26b8f8a7b1a43a067446e369e1f4cb87ab1d126be6bdbefb05b7bfc826ed6",
    ),
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    cases = [TARGET, *VETO_CASES]
    with tempfile.TemporaryDirectory(prefix="six-ahead-high-speed-regression-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["silverstone", "spa"]))  # frozen pre-repair geometry
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for track, seed in cases:
                summary = bench_ai.run_track(
                    track, timeout=1200, seed=seed
                )
                if summary is None:
                    raise SystemExit(
                        f"six-ahead high-speed {track} seed-{seed} {kind} race failed"
                    )
                log_path = Path(bench_ai.LOG)
                if not log_path.is_file():
                    raise SystemExit(
                        f"six-ahead high-speed {track} seed-{seed} {kind} log missing"
                    )
                summaries[(kind, track, seed)] = summary
                logs[(kind, track, seed)] = log_path.read_text(
                    encoding="utf-8"
                )

    for kind in ("AI1", "AI2"):
        target_log = logs[(kind, *TARGET)]
        actual = summaries[(kind, *TARGET)]
        if actual != PROMOTED:
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} regression: "
                f"{actual}, expected {PROMOTED}"
            )
        if finishers(target_log) != PROMOTED_FINISHERS:
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} finisher regression: "
                f"{finishers(target_log)}, expected {PROMOTED_FINISHERS}"
            )
        moves = player_moves(target_log)
        if moves != PROMOTED_ALL_MOVES:
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} move regression: "
                f"{moves}, expected {PROMOTED_ALL_MOVES}"
            )
        deltas = [moves[player] - LEGACY_ALL_MOVES[player] for player in sorted(moves)]
        if any(delta > 0 for delta in deltas) or not any(delta < 0 for delta in deltas):
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} lost strict Pareto gain "
                f"over {LEGACY}: {deltas}"
            )
        decision = PROMOTED_DECISION.format(kind=kind)
        if decision not in target_log.splitlines():
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} decision missing: {decision}"
            )
        digest = normalized_sha256(target_log)
        if digest != PROMOTED_SHA256:
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} trajectory regression: "
                f"{digest}, expected {PROMOTED_SHA256}"
            )

    if normalized_lines(logs[("AI1", *TARGET)]) != normalized_lines(
        logs[("AI2", *TARGET)]
    ):
        raise SystemExit("six-ahead high-speed Spa seed-83 promotion is not mirrored")

    for (track, seed), (expected, expected_digest) in VETO_CASES.items():
        for kind in ("AI1", "AI2"):
            actual = summaries[(kind, track, seed)]
            if actual != expected:
                raise SystemExit(
                    f"six-ahead high-speed {track} seed-{seed} {kind} veto regression: "
                    f"{actual}, expected {expected}"
                )
            digest = normalized_sha256(logs[(kind, track, seed)])
            if digest != expected_digest:
                raise SystemExit(
                    f"six-ahead high-speed {track} seed-{seed} {kind} champion "
                    f"trajectory regression: {digest}, expected {expected_digest}"
                )
        if normalized_lines(logs[("AI1", track, seed)]) != normalized_lines(
            logs[("AI2", track, seed)]
        ):
            raise SystemExit(
                f"six-ahead high-speed {track} seed-{seed} veto lost champion identity"
            )

    print(
        "AI1SixAheadHighSpeedRegression: OK "
        "(Spa s83 finisher -2/all-driver -3 mirrored; "
        "nine veto/retention controls pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
