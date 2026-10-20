#!/usr/bin/env python3
"""Pin Round 115's low-energy field acceleration after promotion."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

PROMOTED = {
    # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
    # Round 233: re-frozen from measurement (the lane spread left the score).
    # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 260: re-frozen from measurement (the faithful joint world as a chooser).
    # Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
    # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes).
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); no crash, p8 (the car still running at the end before) now finishes fifth in 60 own moves, p7 (sixth home in 60 before) is the car still running at the end, and p6 finishes one own move slower, seventh in 61 (sum 417 -> 418).
    1: (7, 0, [58, 59, 59, 60, 60, 61, 61]),
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); no crash, p8 (the car still running at the end before) now finishes seventh in 61 own moves, p7 (seventh home in 61 before) is the car still running at the end, p3 finishes two own moves slower, sixth in 61, and p5 one slower, fourth in 60 (sum 416 -> 419).
    38: (7, 0, [58, 59, 60, 60, 60, 61, 61]),
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); p7, seventh home in 60 moves before, now crashes on its 50th move and seven finishers become six, p4 (fifth home before) the car still running at the end -- recorded, not vetoed.
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); p7 no longer crashes on its 50th move and p4, the car still running at the end before, now finishes fourth in 60 moves: six finishers become seven, p7 the car still running at the end -- crash-free again, and that is what is pinned.
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); still crash-free: p7, the car still running at the end before, now finishes fifth in 60 moves, p8 (sixth home in 60 moves before) the car still running at the end.
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); still crash-free, the same seven finish and p8 is still the car running at the end: p2, p3, p4 and p5 each finish one own move faster, second to fifth in 59, 59, 60 and 60, p7 one slower, seventh in 61, and p6 (second home in 59 before) two slower, sixth in 61 (sum 419 -> 418).
    106: (7, 0, [58, 59, 59, 60, 60, 61, 61]),
}
# Seed 106 was the round-115 coast control, pinned equal to the legacy
# champion; re-freezes moved it, so EXPECTED alone pins it now (review,
# 2026-09-29: the old alias compared it with itself).
LEGACY_CHAMPION = {
    1: (7, 0, [58, 59, 60, 62, 62, 63, 63]),
    38: (7, 0, [58, 59, 61, 61, 62, 62, 63]),
}
EXPECTED = {kind: PROMOTED for kind in LABELS}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {kind: {} for kind in LABELS}
    with tempfile.TemporaryDirectory(prefix="round115-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            for seed in (1, 38, 106):
                actual[kind][seed] = bench_ai.run_track("coil", timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-115 promoted regression: {actual}, expected {EXPECTED}")
    for seed in (1, 38):
        result, legacy = actual[LABELS[0]][seed], LEGACY_CHAMPION[seed]
        if result[:2] != legacy[:2] or any(a > b for a, b in zip(result[2], legacy[2])):
            raise SystemExit(f"Round-115 Pareto contract lost on seed {seed}: {result}, {legacy}")
        if sum(result[2]) >= sum(legacy[2]):
            raise SystemExit(f"Round-115 pace gain lost on seed {seed}: {result}, {legacy}")
    print("AI1GraduatedFieldAccelRegression: OK (Coil s1/s38 promoted; s106 frozen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
