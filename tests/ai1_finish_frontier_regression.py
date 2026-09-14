#!/usr/bin/env python3
"""Pin Round 96's synchronized finish-frontier pace gain."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import finishers, normalized_lines  # noqa: E402

EXPECTED = {
    # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    6: (7, 0, [58, 59, 59, 60, 60, 60, 61]),
    # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
    47: (7, 0, [58, 59, 60, 61, 61, 61, 62]),
    49: (7, 0, [58, 59, 60, 60, 61, 61, 61]),
}
EXPECTED_SEED6_FINISHERS = [
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    (1, 58),
    (2, 59),
    (4, 59),
    (3, 60),
    (5, 60),
    (8, 60),
    (6, 61),
]
EXPECTED_DECISION = {
    # Round 229: re-frozen from measurement (the soft caution stack left the score).
    # Round 233: re-frozen from measurement (the lane spread left the score).
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    6: "299 p3 {kind} NW v(1,-5)→(0,-6) (65,53)→(65,47) ok",
    47: "298 p2 {kind} SW v(1,-6)→(0,-5) (65,47)→(65,42) ok",
    49: "308 p4 {kind} W v(1,-6)→(0,-6) (65,48)→(65,42) ok",
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    with tempfile.TemporaryDirectory(prefix="ai1-finish-frontier-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for seed in EXPECTED:
                summaries[(kind, seed)] = bench_ai.run_track("coil", timeout=600, seed=seed)
                logs[(kind, seed)] = Path(bench_ai.LOG).read_text(encoding="utf-8")

    for kind in ("AI1", "AI2"):
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

    for seed in EXPECTED:
        if normalized_lines(logs[("AI1", seed)]) != normalized_lines(logs[("AI2", seed)]):
            raise SystemExit(f"Round-96 Coil seed-{seed} champion self-tie lost")

    move_sums = {
        kind: sum(summaries[(kind, 6)][2])
        for kind in ("AI1", "AI2")
    }
    # Round 229: 418 is the re-frozen seed-6 sum (the soft caution stack left the score).
    # Round 247: 417 (the soft rollout at one level, not two).
    if any(move_sum != 417 or move_sum >= 426 for move_sum in move_sums.values()):
        raise SystemExit(f"Round-96 Coil seed-6 pace gain lost: {move_sums}")

    print(
        "AI1FinishFrontierRegression: OK "
        "(Coil seed 6 self-tie at 417 moves; seeds 47/49 vetoes pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
