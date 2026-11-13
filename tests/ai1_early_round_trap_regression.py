#!/usr/bin/env python3
"""Pin Round 124's phase-consistent trap-L2 pace gain after promotion.

Round 345: that gain was measured against the legacy champion on the grid
before round 345. Random starts are now each car's own draw from the seed's
SplitMix64 stream, so Silverstone s93 races from a new grid, and the pin holds
the champion's new race there (PROMOTED).

Decision specimen (2026-11-13): that new race holds no round-124 decision (its
one real switch of the field acceleration is of round 175's class), so the pin
also races one that does, Hungaroring seed 8 (SPECIMEN below).
"""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402
import decision_specimen  # noqa: E402

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
# Decision specimen (2026-11-13). A fleet scan (the 83 courses other than the Nordschleife over seeds 1-40, eight AI2
# cars, one lap, random starts: 3,320 races; a scratch build that prints the legs of top-level decisions only) found
# the field acceleration switching a real pick onto a trapped landing, which only round 124's admission allows, in
# three races: Hungaroring s8 and s30 and Hybrid14 s31. Each of the three is also a moderate gain (11, 11 and 13),
# which round 115's admission carries. In Hungaroring s8 on the live track (the staged-pace pin's Hungaroring s8 is
# another race, on the frozen fixture) at turn 585 p1, the round's first mover, on its 74th of 116 moves, stands at
# (113,25) with v(3,6) and five live rivals ahead by the override's own test ((rival - mover) . velocity > 0): p3 at
# (113,27), p7 at (115,32), p2 at (116,38), p5 at (116,40) and p6 at (118,48). Its pick is NW to v(2,5), 29 speed2,
# and the override switches it to W, v(2,6), 40 speed2, one map turn faster (42 to 41), onto a landing with two safe
# successors (trap 0.5). The race has seven finishers and no crash: p6 wins on its 111th move, p2, p5, p7, p1, p3 and
# p4 follow on their 113th, 114th, 115th, 116th, 117th and 118th, and p8 is the car still running at the end, after
# 117 moves (921 turns). With the trap admission off in top-level decisions only, a twin scratch build races the same
# race through turn 584 and plays NW at turn 585.
SPECIMEN = decision_specimen.Specimen(
    "hungaroring", 8, (7, 0, [111, 113, 114, 115, 116, 117, 118]),
    "0a54cd25c98afba66f2cbc7d0c6557cb019a58cb2155fc37b2bd51ec9582c248",
    "585 p1 AI W v(3,6)→(2,6) (113,25)→(115,31) ok",
)


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
    decision_specimen.check("round-124", SPECIMEN)
    print("AI1EarlyRoundTrapRegression: OK (Silverstone s93 promoted; decision specimen pinned on Hungaroring s8)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
