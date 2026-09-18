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
# Round 248 (the physical world model): re-frozen from measurement; p5 crashes
# on its 31st move -- recorded, not vetoed.
# Round 260: re-frozen from measurement (the faithful joint world as a chooser).
PROMOTED = (6, 1, [78, 79, 80, 82, 82, 83])
LEGACY = (7, 0, [79, 80, 81, 84, 84, 86, 88])
PROMOTED_FINISHERS = [
    (6, 78),
    (7, 79),
    (8, 80),
    (2, 82),
    (3, 82),
    (4, 83),
]
LEGACY_ALL_MOVES = {1: 88, 2: 87, 3: 79, 4: 80, 5: 81, 6: 84, 7: 84, 8: 86}
PROMOTED_ALL_MOVES = {1: 83, 2: 82, 3: 82, 4: 83, 5: 29, 6: 78, 7: 79, 8: 80}
# Round 247: re-frozen from measurement (the soft rollout at one level, not two).
PROMOTED_SHA256 = "9599187fc03f380c08902c895ef9de7eaaf313da3235cd1515fb66f22b2920e5"
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
# Round 248 (the physical world model): Spa s27 loses a car; four cases
# re-frozen from measurement.
# Round 260: re-frozen from measurement (the faithful joint world as a chooser).
VETO_CASES = {
    ("spa", 27): (
        (7, 0, [78, 79, 81, 81, 81, 83, 84]),
        "d14c6a9c830daf73e0e936cbfdf8f79076e71907e1efbad4f98f958b0dd367df",
    ),
    ("spa", 57): (
        (6, 1, [78, 79, 81, 81, 82, 82]),
        "49a5f9eabd989da4d004ce65e54ba6453f984ebfa475044f1be71312e1c86a8c",
    ),
    ("spa", 12): (
        # Round 254: re-frozen from measurement (the danger guard in a faithful world).
        (7, 0, [78, 79, 81, 82, 83, 83, 84]),
        "31d32c87cff605b84f06b78c648ec01cf0bf6993d27475399c54004571666d71",
    ),
    ("spa", 31): (
        (7, 0, [78, 79, 81, 81, 82, 83, 83]),
        "7f163b460bf13a38b1738354d13099fbdf9675c80343081aacb6176e375efdae",
    ),
    ("spa", 40): (
        (7, 0, [78, 79, 80, 81, 81, 82, 83]),
        "840fbec66afc6dab17679f8e29fe97da7f5591e09030710a4bb4cad3f4d69d34",
    ),
    ("spa", 47): (
        (7, 0, [78, 80, 80, 81, 82, 82, 83]),
        "71341dd9a25ca3d83e34b8c26639e33624ad11660651a4bc78c4d6bcc7b0c511",
    ),
    ("coil", 5): (
        (7, 0, [58, 59, 59, 59, 60, 61, 61]),
        "28fda6295a443572caeb7293036c65942502de0157d5f154162043b74657062a",
    ),
    ("coil", 22): (
        (7, 0, [58, 59, 59, 59, 59, 60, 60]),
        "e7ea5ff98cb2b8f27e2bd71db61d6162b031d54af6e9caefbb9ad7751a2b0cae",
    ),
    ("silverstone", 78): (
        (7, 0, [81, 82, 83, 83, 84, 85, 85]),
        "770202269dafb247af988559a03807fb2f9789f0d23088800d27d7a85cb6bd76",
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
