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
# Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
PROMOTED = (7, 0, [78, 79, 81, 82, 82, 84, 85])
LEGACY = (7, 0, [79, 80, 81, 84, 84, 86, 88])
PROMOTED_FINISHERS = [
    (6, 78),
    (7, 79),
    (2, 81),
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    (5, 82),
    (8, 82),
    (1, 84),
    (4, 85),
]
LEGACY_ALL_MOVES = {1: 88, 2: 87, 3: 79, 4: 80, 5: 81, 6: 84, 7: 84, 8: 86}
PROMOTED_ALL_MOVES = {1: 84, 2: 81, 3: 85, 4: 85, 5: 82, 6: 78, 7: 79, 8: 82}
# Round 247: re-frozen from measurement (the soft rollout at one level, not two).
PROMOTED_SHA256 = "a9e5e26b76afa435c16189a5c051ca209a1199cd0f5a0c87327c93ccaad59f61"
PROMOTED_DECISION = (
    # Round 229: re-frozen from measurement (the soft caution stack left the score).
    # Round 233: re-frozen from measurement (the lane spread left the score).
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    "201 p1 {kind} NW v(0,8)→(-1,7) (101,132)→(100,139) ok"
)

# These cases cover every redistribution or slowdown exposed by the historical
# broad six-ahead arm. The final candidate-speed and gain band must leave each
# complete trajectory equal to the champion.
# Round 247 (the soft rollout at one level, not two): every case re-frozen
# from measurement; Silverstone s78 gets its seventh finisher back.
VETO_CASES = {
    ("spa", 27): (
        (7, 0, [79, 80, 82, 82, 83, 83, 85]),
        "2cdea6c13502bf538d10c7a0ced83d5293e6d64eb9df187d5a011ff6c2001bad",
    ),
    ("spa", 57): (
        (7, 0, [78, 80, 81, 83, 83, 84, 84]),
        "5a4adcd881337ba2ead3e276569a3f384f9f0e737707264e7e5d1ee197337f29",
    ),
    ("spa", 12): (
        (7, 0, [78, 79, 81, 81, 82, 83, 84]),
        "81550b7b506cbaaf4b1746a0edbac70af08dd07e66d85c9794de2daa22ea97ba",
    ),
    ("spa", 31): (
        (7, 0, [78, 79, 81, 81, 82, 84, 84]),
        "02a02c4a9e76366f1284e28218fce2f1c5118d35ddb553eb43af46f7c07b741c",
    ),
    ("spa", 40): (
        (7, 0, [78, 79, 80, 81, 83, 83, 84]),
        "05cd3a0dbae19360e0f7daa7ba1edfa74cac292b6305fc2ffc02ef0221deb1af",
    ),
    ("spa", 47): (
        (7, 0, [78, 80, 81, 81, 82, 83, 84]),
        "8ada5e4d0b77406e10ef7e9ba9a55de7908469ed24709623502bca61bc823bf6",
    ),
    ("coil", 5): (
        (7, 0, [58, 59, 60, 60, 61, 61, 62]),
        "9207750748733019482321e3c0bb415c5d83a67f38cbe78572544854838f05c2",
    ),
    ("coil", 22): (
        (7, 0, [58, 59, 60, 61, 61, 62, 62]),
        "30d2c987de19d18144d638e4d366df4cb7fffb22c55ba1015a4419dbf31796d8",
    ),
    ("silverstone", 78): (
        (7, 0, [81, 82, 83, 83, 84, 84, 86]),
        "e4d3c6305222993d18c4ce0e095ecdb57c2481b03c34d43f93c3b292adc0bea3",
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
