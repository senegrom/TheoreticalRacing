#!/usr/bin/env python3
"""Pin Round 117's synchronized six-ahead acceleration after promotion.

Outcome pin, awaiting a decision specimen (2026-11-13). Round 117 admits a
high-energy field acceleration with exactly six rivals ahead when a rival that
has already moved stands beside the landing at the candidate's velocity. On
round 345's grids the race below holds no real switch of the field
acceleration, and a fleet scan found no real switch of round 117's class (six
ahead and a speed-squared gain of 16 or more): the 83 courses other than the
Nordschleife over seeds 1-40, eight AI2 cars, one lap, random starts, 3,320
races, raced by a scratch build that prints the legs of top-level decisions
only. The field acceleration switched 160 real picks in them: 109 of round
106's class, 30 of round 115's, 18 of round 175's and 3 of round 124's. The pin
holds the race's outcome.
"""
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
    # The s5 and s22 controls race in ai1_six_ahead_high_speed_regression, which
    # pins the same races by summary and digest (review, 2026-09-28).
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
    # Round 331: re-frozen from measurement (the relevant rival keeps its three stronger forecast moves beside the second and third rivals').
    # Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full policy in every decision).
    # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy).
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); a new grid and a new race: seven finishers and no crash -- p1 wins on its 58th move, p3 is second on its 59th, p2, p4 and p6 third to fifth on their 60th, and p5 and p7 sixth and seventh on their 61st -- and p8 is the car still running at the end, after 60 moves (the finishers' own moves sum to 419).
    86: (7, 0, [58, 59, 60, 60, 60, 61, 61]),
}
# Round 345: LEGACY_CHAMPION_86 is retired, and with it the round-117 Pareto
# contract and pace-gain checks against it in main(). It was the pre-round-117
# champion's race on Coil seed 86's grid before round 345, the race round 117's
# six-ahead acceleration gained on. Random starts now draw every car's own
# cell, so that race no longer exists, and the legacy policy cannot be raced on
# the new grid. The historical number, for the record:
# LEGACY_CHAMPION_86 = (7, 0, [58, 59, 61, 61, 62, 62, 63])
EXPECTED = {kind: PROMOTED for kind in LABELS}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {kind: {} for kind in LABELS}
    with tempfile.TemporaryDirectory(prefix="round117-regression-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            for seed in (86,):
                actual[kind][seed] = bench_ai.run_track("coil", timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-117 promoted regression: {actual}, expected {EXPECTED}")
    # Round 345: the Pareto contract and the pace gain against
    # LEGACY_CHAMPION_86 are retired (see above); the measured summary is the pin.
    print("AI1SixAheadAccelRegression: OK (Coil s86 promoted; its s5/s22 controls race in the high-speed pin)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
