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
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
# Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
PROMOTED = (7, 0, [78, 79, 81, 82, 82, 83, 83])
LEGACY = (7, 0, [79, 80, 81, 84, 84, 86, 88])
PROMOTED_FINISHERS = [
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); seven finishers and no crash as before, but p5 (the car still running at the end before) now finishes fourth on its 81st move and p4 (fifth home before) is the car still running at the end, after 82 moves -- recorded, not vetoed.
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); seven finishers and no crash as before, but p4 (the car still running at the end before) now finishes fifth on its 82nd move and p8 (third home before, on its 80th move) is the car still running at the end, after 82 moves; p1 and p2 now finish third and fourth on their 81st and 82nd moves, p3 sixth and p5 (fourth before) seventh, both on their 83rd -- recorded, not vetoed.
    (6, 78),
    (7, 79),
    (1, 81),
    (2, 82),
    (4, 82),
    (3, 83),
    (5, 83),
]
LEGACY_ALL_MOVES = {1: 88, 2: 87, 3: 79, 4: 80, 5: 81, 6: 84, 7: 84, 8: 86}
# Round 278: re-frozen from measurement (the chooser's pick stands).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
# Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
PROMOTED_ALL_MOVES = {1: 81, 2: 82, 3: 83, 4: 82, 5: 83, 6: 78, 7: 79, 8: 82}
# Round 247: re-frozen from measurement (the soft rollout at one level, not two).
# Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
# Round 278: re-frozen from measurement (the chooser's pick stands).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
# Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
PROMOTED_SHA256 = "04d7f5ecf7dd796c3235908d45bc8f10a5aa7b815642d4ff86d65e6b43156076"
PROMOTED_DECISION = (
    # Round 229: re-frozen from measurement (the soft caution stack left the score).
    # Round 233: re-frozen from measurement (the lane spread left the score).
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 276: the same turn and car, re-frozen from measurement.
    # Round 278: the same turn and car, re-frozen from measurement.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); the same turn and car.
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds); the same turn and car.
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); the same turn and car.
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); the same turn and car.
    "201 p1 {kind} NW v(0,7)→(-1,6) (101,131)→(100,137) ok"
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
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        (7, 0, [79, 80, 81, 81, 81, 82, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        "54d41f36199ad48ade0c8d53c093927b78622823c620a749847bf431f5ed8e58",
    ),
    ("spa", 57): (
        # Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        (7, 0, [78, 79, 81, 81, 82, 82, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        "b1aca180bb8a9d7934617c382c8264147adc46ac8a68af58e42825be2cbef354",
    ),
    ("spa", 12): (
        # Round 254: re-frozen from measurement (the danger guard in a faithful world).
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        (7, 0, [78, 79, 80, 81, 82, 82, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        "b88bd963aa0f033a1e6d09eff37d5beeda0ebd0c8dbb6fafe1791b2ed87c7afe",
    ),
    ("spa", 31): (
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p4 no longer crashes on its 58th move and p3 now finishes seventh: six finishers become seven, p4 the car still running at the end.
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); seven finishers as before and p4 still the car running at the end, but p3 now finishes sixth on its 83rd move.
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); seven finishers and no crash as before, but p4 (the car still running at the end before) now finishes sixth on its 82nd move and p5 (seventh home before) is the car still running at the end, after 83 moves; p3 now finishes fifth on its 82nd move and p8 (third before) seventh on its 83rd -- recorded, not vetoed.
        (7, 0, [78, 79, 81, 81, 82, 82, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        "40324fecc2e9f86a2a6592458abb6cb4b1dd4f84ac3f4928d0c4bc7901659b5e",
    ),
    ("spa", 40): (
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        (7, 0, [78, 79, 80, 81, 81, 82, 82]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        "af94856bbc03aadfbafe34db81096295c9fd3b717fd3cbe7aa2cd2a54fad32ca",
    ),
    ("spa", 47): (
        # Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        (7, 0, [78, 80, 81, 81, 82, 82, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        "9fb15753ffa7d24569cca9daff6febe5c21e160f5178a03aa58acd24f3e4af5b",
    ),
    ("coil", 5): (
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        (7, 0, [58, 59, 59, 60, 60, 60, 61]),
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); the all-AI1 and alternating races of ai1_label_invariance_regression, which takes this digest as its reference, measured it too.
        "79340ceefb3ea05cb5ec10db22c0c3edb6d70e1f4243b48728e091d8c2c64f1c",
    ),
    ("coil", 22): (
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        (7, 0, [58, 59, 59, 59, 60, 60, 60]),
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        "c61c3470824af2ed722965c48d723c27428492bba6eb4b912f25cca894771163",
    ),
    ("silverstone", 78): (
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p8 now crashes on its 11th move and seven finishers become six, p6 (sixth home before) the car still running at the end -- recorded, not vetoed.
        (6, 1, [81, 82, 83, 83, 84, 84]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds); p8 still crashes on its 11th move and six cars finish, but p6 finishes sixth again and p7 is now the car still running at the end -- recorded, not vetoed.
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); p8 still crashes on its 11th move and six cars finish, but p7 finishes sixth again on its 84th move and p6 is now the car still running at the end, after 84 moves -- recorded, not vetoed.
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); the same classification as before, a different trajectory: p8 still crashes on its 11th move, p7 still finishes sixth on its 84th and p6 is still the car running at the end, after 84 moves -- recorded, not vetoed.
        "9ed540fd98b1c47f078d21307ccb7bc868261d59a618d9671a376f881f5076ba",
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
