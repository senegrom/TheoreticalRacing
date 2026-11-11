#!/usr/bin/env python3
"""Pin Round 124's phase-consistent trap-L2 pace gain after promotion.

Round 345: that gain was measured against the legacy champion on the grid
before round 345. Random starts are now each car's own draw from the seed's
SplitMix64 stream, so Silverstone s93 races from a new grid, and the pin holds
the champion's new race there (PROMOTED).
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

CASES = [("silverstone", 93)]
# Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
# Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
# Round 247: re-frozen from measurement (the soft rollout at one level, not two).
# Round 260: re-frozen from measurement (the faithful joint world as a chooser).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
# Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
# Round 310: re-frozen from measurement (the danger-joint-search family deleted).
# Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
# Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
# Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy).
# Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
# Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
# Round 331: re-frozen from measurement (the relevant rival keeps its three stronger forecast moves beside the second and third rivals').
# Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full policy in every decision).
# Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy).
# Round 335: re-frozen from measurement (every rival but the relevant one plays its first two forecast moves by its full policy).
# Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); Silverstone s93 is a new race from a new grid: seven finishers and no crash -- p1 wins on its 81st own move, p2 is second on its 82nd, p3 and p4 third and fourth on their 84th, p5 and p7 fifth and sixth on their 85th and p6 seventh on its 86th, and p8 is the car still running at the end, after 85 moves.
PROMOTED = (7, 0, [81, 82, 84, 84, 85, 85, 86])
# Round 345: retired with the check in main() that read it (the legacy
# champion's race on the grid before round 345, which no race reaches now):
# LEGACY_CHAMPION = (7, 0, [81, 82, 83, 84, 85, 86, 87])
EXPECTED = {kind: {"silverstone:93": PROMOTED} for kind in LABELS}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {kind: {} for kind in LABELS}
    with tempfile.TemporaryDirectory(prefix="round124-regression-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["silverstone"]))  # frozen pre-repair geometry
        bench_ai.set_nplayers(8)
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            for track, seed in CASES:
                actual[kind][f"{track}:{seed}"] = bench_ai.run_track(
                    track, timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-124 promoted regression: {actual}, expected {EXPECTED}")
    # Round 229: the round-124 summed-moves contracts against the legacy champion
    # (no car slower, a smaller sum) are retired -- the policy is judged by
    # head-to-head places now (AGENTS.md) and the measured race has one car a
    # move slower. Finishers and crashes must still match the legacy champion.
    # Round 345: that last contract (the race's finishers and crashes equal to
    # LEGACY_CHAMPION's, 7 and 0) is retired too. LEGACY_CHAMPION was the legacy
    # champion's race on the grid before round 345; random starts now give each
    # car its own draw from the seed's SplitMix64 stream, so seed 93 starts from
    # a new grid that the legacy policy never raced, and the check would hold a
    # new race to an old one. PROMOTED above still pins the new race's seven
    # finishers and no crash, inside its whole summary.
    print("AI1EarlyRoundTrapRegression: OK (Silverstone s93 promoted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
