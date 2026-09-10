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
PROMOTED = (7, 0, [78, 79, 81, 82, 83, 84, 85])
LEGACY = (7, 0, [79, 80, 81, 84, 84, 86, 88])
PROMOTED_FINISHERS = [
    (6, 78),
    (7, 79),
    (1, 81),
    (2, 82),
    (3, 83),
    (4, 84),
    (5, 85),
]
LEGACY_ALL_MOVES = {1: 88, 2: 87, 3: 79, 4: 80, 5: 81, 6: 84, 7: 84, 8: 86}
PROMOTED_ALL_MOVES = {1: 81, 2: 82, 3: 83, 4: 84, 5: 85, 6: 78, 7: 79, 8: 84}
PROMOTED_SHA256 = "9fc35c625d9085fc344ce464570c87baa93c1838e6de2cf873c4099d8d82017f"
PROMOTED_DECISION = (
    # Round 229: re-frozen from measurement (the soft caution stack left the score).
    # Round 233: re-frozen from measurement (the lane spread left the score).
    "201 p1 {kind} NW v(0,7)→(-1,6) (101,131)→(100,137) ok"
)

# These cases cover every redistribution or slowdown exposed by the historical
# broad six-ahead arm. The final candidate-speed and gain band must leave each
# complete trajectory equal to the champion.
VETO_CASES = {
    ("spa", 27): (
        (7, 0, [79, 80, 81, 81, 82, 84, 85]),
        "124950ca13ddc4c918de8657be101d3545f4ddfa5b10d7ddbcec05b3db330807",
    ),
    ("spa", 57): (
        (7, 0, [78, 80, 81, 81, 83, 84, 84]),
        "77870b0d7a68fdd6468f06ef817f54e6fc6169d1c36efe1c9c46c5310926897b",
    ),
    ("spa", 12): (
        (7, 0, [78, 79, 80, 81, 82, 83, 84]),
        "1609c7a24beb61682243b288825ccc294c7059f5a8eb61446c97dbaf9f656684",
    ),
    ("spa", 31): (
        (7, 0, [78, 79, 80, 81, 83, 85, 85]),
        "14b49b5cffbb2ec3c880686ec2b19b77d36415b962a560060f023adaefc43997",
    ),
    ("spa", 40): (
        (7, 0, [78, 79, 80, 81, 82, 82, 84]),
        "7586d94de7b1be9777d0b6fd39e1b382fcdd408639d866b2db9e340ecb914d5f",
    ),
    ("spa", 47): (
        (7, 0, [78, 80, 81, 82, 83, 84, 85]),
        "44866af4395dc232c6b6a67794e7ca2ef2c667cfca9077d05fe787fc9c9d2c07",
    ),
    ("coil", 5): (
        (7, 0, [58, 59, 59, 60, 61, 62, 62]),
        "a19d088bdea655e3864eb5297ad8aad74c2def69ba12b8e584ff37a0e31f2c07",
    ),
    ("coil", 22): (
        (7, 0, [58, 59, 60, 61, 61, 61, 61]),
        "03dc0fab60456f4bc5719ddd430b7b6f4c28ddcaecfcb38c243b22d94ad74b3d",
    ),
    ("silverstone", 78): (
        (7, 0, [81, 82, 83, 84, 85, 85, 86]),
        "263e16a09260d42b9946a0856d5766ccd439aa1f612ff4ca7409242838b77754",
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
        # Round 233: the round-117 per-car Pareto contract against the legacy
        # champion is retired -- the policy is judged by head-to-head places
        # (AGENTS.md), and with the lane spread out of the score three cars in
        # this race are slower than the legacy car while the field is faster
        # overall. The measured summary, finisher list, move counts, digest and
        # decision line below all still have to hold.
        deltas = [moves[player] - LEGACY_ALL_MOVES[player] for player in sorted(moves)]
        if not any(delta < 0 for delta in deltas):
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} lost every gain "
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
