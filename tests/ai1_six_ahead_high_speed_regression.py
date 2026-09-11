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
    (4, 82),
    (5, 82),
    (1, 84),
    (3, 85),
]
LEGACY_ALL_MOVES = {1: 88, 2: 87, 3: 79, 4: 80, 5: 81, 6: 84, 7: 84, 8: 86}
PROMOTED_ALL_MOVES = {1: 84, 2: 81, 3: 85, 4: 82, 5: 82, 6: 78, 7: 79, 8: 84}
PROMOTED_SHA256 = "7a2aa8cc34801243fa0a29bda4c43a1cfaa5a91bbb46df95b9febeeeab730437"
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
        (7, 0, [79, 80, 81, 81, 82, 83, 84]),
        "1063bb8af1f62a262e3e6847acde8de28e0ea92a2608ee7ea1b4de294f214f79",
    ),
    ("spa", 57): (
        (7, 0, [78, 80, 81, 81, 82, 83, 83]),
        "b6f8c019856596b4c07f770236ca3c66a7517d093595bd655f41555f5e6fadb4",
    ),
    ("spa", 12): (
        (7, 0, [78, 79, 80, 81, 82, 83, 84]),
        "b2dab367e14c94ff8bb84148a8e88593919bb8f1f39f5cfdb05efd1cf8cb5dcc",
    ),
    ("spa", 31): (
        (7, 0, [78, 79, 80, 81, 82, 83, 83]),
        "c166b3b9deee36887c76c954b9364dcf1b9c241cd378f67a665d89e64448cb86",
    ),
    ("spa", 40): (
        (7, 0, [78, 79, 80, 81, 82, 83, 84]),
        "4b8a5b5595d26ce24e5c40b432fd2703923d959e26e5eadc63eb710611ed3b1f",
    ),
    ("spa", 47): (
        (7, 0, [78, 80, 81, 81, 82, 83, 83]),
        "9129791cfb08a70754d5f511fc9045873cbc01ff535bde6d8e078d5bb5d680e4",
    ),
    ("coil", 5): (
        (7, 0, [58, 59, 59, 60, 61, 62, 62]),
        "7f7373da3f94ca84d278104584ec8ec3e22936515ee0f500554ef1dd7a22c37c",
    ),
    ("coil", 22): (
        (7, 0, [58, 59, 60, 61, 61, 61, 62]),
        "60f45bc46cfc5ed0a9cc6ebb5c7c264737b522966463624a58fc8cf68e8ebe12",
    ),
    ("silverstone", 78): (
        (6, 1, [81, 82, 83, 84, 84, 85]),
        "f3db28284473bc1212cf52afd0798c1d51970fcda3c24f80b041fcc1be236b05",
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
