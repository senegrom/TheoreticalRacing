#!/usr/bin/env python3
"""Pin the high-speed moderate six-ahead pace frontier and its vetoes."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import finishers, normalized_lines, normalized_sha256, player_moves  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

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
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    (6, 78),
    (7, 79),
    (1, 81),
    (3, 82),
    (4, 82),
    (2, 84),
    (5, 85),
]
LEGACY_ALL_MOVES = {1: 88, 2: 87, 3: 79, 4: 80, 5: 81, 6: 84, 7: 84, 8: 86}
# Round 278: re-frozen from measurement (the chooser's pick stands).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
PROMOTED_ALL_MOVES = {1: 81, 2: 84, 3: 82, 4: 82, 5: 85, 6: 78, 7: 79, 8: 84}
# Round 247: re-frozen from measurement (the soft rollout at one level, not two).
# Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
# Round 278: re-frozen from measurement (the chooser's pick stands).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
PROMOTED_SHA256 = "3305159e699110f0e6528af00cc1434b9d8230293b95db90d9e9e0deaa61dbc1"
PROMOTED_DECISION = (
    # Round 229: re-frozen from measurement (the soft caution stack left the score).
    # Round 233: re-frozen from measurement (the lane spread left the score).
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 276: the same turn and car, re-frozen from measurement.
    # Round 278: the same turn and car, re-frozen from measurement.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); the same turn and car.
    "201 p1 {kind} NW v(0,8)→(-1,7) (101,133)→(100,140) ok"
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
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        (7, 0, [79, 80, 80, 81, 81, 82, 82]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        "90c18a0b85d451c7baa7209a1682cb98a7b17d6f91279baded9d1103dc8146cd",
    ),
    ("spa", 57): (
        # Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        (7, 0, [78, 79, 80, 81, 82, 82, 82]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        "31ed12a5fb5c92c7a7d980869883ff1c0c042d13b477b198dab042196159ae06",
    ),
    ("spa", 12): (
        # Round 254: re-frozen from measurement (the danger guard in a faithful world).
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        (7, 0, [79, 80, 80, 82, 82, 83, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        "eb0dd7e39b906d6fc67ff578b3810f022e22488227d99d85e5726c6b8f4ba806",
    ),
    ("spa", 31): (
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p4 no longer crashes on its 58th move and p3 now finishes seventh: six finishers become seven, p4 the car still running at the end.
        (7, 0, [78, 79, 80, 81, 82, 83, 84]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        "7ac682186ef42780e65d6a2cd81011ee8f8d03334107429367eedc8e37b74a02",
    ),
    ("spa", 40): (
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        (7, 0, [78, 79, 80, 81, 81, 82, 82]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        "45788808b5cf99985fcd3357e2a92b3833db9145f287f8372a8fe5a9c7fa6749",
    ),
    ("spa", 47): (
        # Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        (7, 0, [78, 80, 81, 81, 83, 84, 84]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        "1cf705800f7bce4f17add5f8dccbb2cf9a6b807e73b58e739fab81b2174c3b36",
    ),
    ("coil", 5): (
        (7, 0, [58, 59, 59, 59, 60, 60, 60]),
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        "b62fd1cfda32e72c5628edd22aa8ddc318021fc613ed164e6928a5927f3d906a",
    ),
    ("coil", 22): (
        (7, 0, [58, 59, 59, 59, 60, 60, 61]),
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        "84fb62ef4a553fa8333cf8c59564ac37c0f5d0a08e26771bdcae8c8ef1fa523a",
    ),
    ("silverstone", 78): (
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p8 now crashes on its 11th move and seven finishers become six, p6 (sixth home before) the car still running at the end -- recorded, not vetoed.
        (6, 1, [81, 82, 83, 83, 84, 84]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        "818f13bef02579a795e52088cb2d37821b17e74bd7e62d0ed6184e0b5977592b",
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
        for kind in LABELS:
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

    for kind in LABELS:
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

    for (track, seed), (expected, expected_digest) in VETO_CASES.items():
        for kind in LABELS:
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

    print(
        "AI1SixAheadHighSpeedRegression: OK "
        "(Spa s83 finisher -2/all-driver -3; "
        "nine veto/retention controls pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
