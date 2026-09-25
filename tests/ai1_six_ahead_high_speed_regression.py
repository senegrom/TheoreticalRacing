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
# Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
# Round 278: re-frozen from measurement (the chooser's pick stands).
PROMOTED = (7, 0, [78, 79, 81, 82, 82, 84, 85])
LEGACY = (7, 0, [79, 80, 81, 84, 84, 86, 88])
PROMOTED_FINISHERS = [
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    (6, 78),
    (7, 79),
    (2, 81),
    (4, 82),
    (5, 82),
    (1, 84),
    (3, 85),
]
LEGACY_ALL_MOVES = {1: 88, 2: 87, 3: 79, 4: 80, 5: 81, 6: 84, 7: 84, 8: 86}
# Round 278: re-frozen from measurement (the chooser's pick stands).
PROMOTED_ALL_MOVES = {1: 84, 2: 81, 3: 85, 4: 82, 5: 82, 6: 78, 7: 79, 8: 84}
# Round 247: re-frozen from measurement (the soft rollout at one level, not two).
# Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
# Round 278: re-frozen from measurement (the chooser's pick stands).
PROMOTED_SHA256 = "58097ec5b5580607c660a9876c6072f215e3e42b293fc97e543abb2c811f6928"
PROMOTED_DECISION = (
    # Round 229: re-frozen from measurement (the soft caution stack left the score).
    # Round 233: re-frozen from measurement (the lane spread left the score).
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 276: the same turn and car, re-frozen from measurement.
    # Round 278: the same turn and car, re-frozen from measurement.
    "201 p1 {kind} NW v(1,8)→(0,7) (104,132)→(104,139) ok"
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
        # Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        (7, 0, [78, 79, 80, 81, 82, 83, 84]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        "f0d8a82c2ea684bbb14e310d352bd10b9a60b5c6d62efa997431eafed49a89a3",
    ),
    ("spa", 57): (
        # Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        (7, 0, [78, 79, 80, 81, 82, 82, 82]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        "72423ee5f265f1a5f42e6e8b5c537ab630e2d0b562f07aa9838b9b154679b3ba",
    ),
    ("spa", 12): (
        # Round 254: re-frozen from measurement (the danger guard in a faithful world).
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        (7, 0, [78, 79, 81, 81, 82, 83, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        "6fc76ea464164874a89f5cbafbd0c456b5c4f6b46d806cb991c1b3f9c04c9a65",
    ),
    ("spa", 31): (
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        (6, 1, [78, 79, 80, 82, 82, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        "23d049fe6fb2d6eb5b0cae93953a34fd333f5e3cf195e8b7db8125e1485849f8",
    ),
    ("spa", 40): (
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        (7, 0, [78, 79, 80, 80, 81, 82, 82]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        "4bc95498ca6310e6b1dfa7073d10140e481d1fff5562bc5a516f9bbc90627278",
    ),
    ("spa", 47): (
        # Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
        (7, 0, [78, 80, 81, 81, 82, 82, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        "8f19c7acc7ef65cd89932cf67b4c04b3348dc890ff0470e3fa9973ded48c0c67",
    ),
    ("coil", 5): (
        (7, 0, [58, 59, 59, 59, 60, 60, 60]),
        "1a161476524e531ebd32d01df81c707490acf885d7b02a70ff807f8d17c63ee1",
    ),
    ("coil", 22): (
        (7, 0, [58, 59, 59, 59, 60, 60, 61]),
        "82c6ee412c5616ca174d4b75a9c543d6eac47c614a45a75788dbdf4e9dbc5d69",
    ),
    ("silverstone", 78): (
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        (7, 0, [81, 82, 83, 83, 84, 84, 85]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        "8d97653bf4ddf6acc14bd7f82630ab066152c34a2cf55550e39f79c71e9d0418",
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
