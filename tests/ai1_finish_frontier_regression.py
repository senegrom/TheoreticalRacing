#!/usr/bin/env python3
"""Pin Round 96's synchronized finish-frontier pace gain."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import finishers, normalized_lines  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

EXPECTED = {
    # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
    6: (7, 0, [58, 59, 60, 60, 60, 61, 61]),
    # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
    # Round 260: re-frozen from measurement (the faithful joint world as a chooser).
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); the same seven finish, no crash, p3, p6 and p7 each one own move faster (sum 418 -> 415).
    47: (7, 0, [58, 59, 59, 59, 60, 60, 60]),
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); no crash, p8 (the car still running at the end before) now finishes third in 59 own moves, p7 (sixth home in 60 before) is the car still running at the end, and p3 and p6 each finish one own move slower, in 60 and 61 (sum 417 -> 418).
    49: (7, 0, [58, 59, 59, 60, 60, 61, 61]),
}
EXPECTED_SEED6_FINISHERS = [
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 260: re-frozen from measurement; the seed-6 sum is unchanged at 417.
    # Round 274: re-frozen from measurement (rank first); the sum is 420 now.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); no crash, p2 now finishes second in 59 own moves (classified last before) and p8 is the car still running at the end; the sum is 419 now.
    (1, 58),
    (2, 59),
    (3, 60),
    (5, 60),
    (7, 60),
    (4, 61),
    (6, 61),
]
EXPECTED_DECISION = {
    # Round 229: re-frozen from measurement (the soft caution stack left the score).
    # Round 233: re-frozen from measurement (the lane spread left the score).
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 260: the same turn and car, re-frozen from measurement.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 303: the same turns and cars, re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); s6's p3 brakes SW as before, three cells further east (round 260's line), s49's p4 now reaches (66,47) at v(1,-5) and plays W to (0,-5); s47 unchanged.
    6: "299 p3 {kind} SW v(1,-6)→(0,-5) (68,47)→(68,42) ok",
    47: "298 p2 {kind} SW v(1,-6)→(0,-5) (65,47)→(65,42) ok",
    49: "308 p4 {kind} W v(1,-5)→(0,-5) (66,47)→(66,42) ok",
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    with tempfile.TemporaryDirectory(prefix="ai1-finish-frontier-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            for seed in EXPECTED:
                summaries[(kind, seed)] = bench_ai.run_track("coil", timeout=600, seed=seed)
                logs[(kind, seed)] = Path(bench_ai.LOG).read_text(encoding="utf-8")

    for kind in LABELS:
        for seed, expected in EXPECTED.items():
            actual = summaries[(kind, seed)]
            if actual != expected:
                raise SystemExit(
                    f"Round-96 Coil seed-{seed} {kind} regression: {actual}, expected {expected}"
                )
            decision = EXPECTED_DECISION[seed].format(kind=kind)
            if decision not in logs[(kind, seed)].splitlines():
                raise SystemExit(
                    f"Round-96 Coil seed-{seed} {kind} decision regression: missing {decision}"
                )

        seed6_finishers = finishers(logs[(kind, 6)])
        if seed6_finishers != EXPECTED_SEED6_FINISHERS:
            raise SystemExit(
                f"Round-96 Coil seed-6 {kind} finisher regression: "
                f"{seed6_finishers}, expected {EXPECTED_SEED6_FINISHERS}"
            )

    move_sums = {
        kind: sum(summaries[(kind, 6)][2])
        for kind in LABELS
    }
    # Round 229: 418 is the re-frozen seed-6 sum (the soft caution stack left the score).
    # Round 247: 417 (the soft rollout at one level, not two).
    # Round 274: 420 (rank first), measured; still below the pre-frontier 426.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 303: 419 (aware forecasts, the chooser lab's aware promoted), measured; still below the pre-frontier 426.
    if any(move_sum != 419 or move_sum >= 426 for move_sum in move_sums.values()):
        raise SystemExit(f"Round-96 Coil seed-6 pace gain lost: {move_sums}")

    print(
        "AI1FinishFrontierRegression: OK "
        "(Coil seed 6 at 419 moves; seeds 47/49 vetoes pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
