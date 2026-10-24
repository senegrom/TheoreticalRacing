#!/usr/bin/env python3
"""Pin Round 126's equal-speed false-target rescue after promotion."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

CASES = [("zandvoort", 115)]
# Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
# Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
# Round 247 (the soft rollout at one level, not two): re-frozen from
# measurement. The race loses a car again -- recorded, not vetoed.
# Round 248 (the physical world model): whole again, re-frozen from measurement.
# Round 254: re-frozen from measurement (the danger guard in a faithful world).
# Round 260: re-frozen from measurement (the faithful joint world as a chooser).
# Round 278: re-frozen from measurement (the chooser's pick stands).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p5 now crashes on its 19th move and seven finishers become six -- recorded, not vetoed.
# Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout); p5, lost on its 19th move since round 281, now finishes sixth on its 143rd move and six finishers become seven, with no crash.
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
# Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
# Round 310: the round-126 equal-speed veto went with the danger-joint-search family; the pinned outcome is unchanged under the promoted champion (measured), so the pin now guards that outcome.
# Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
# Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
# Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy).
# Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
# Round 331: re-frozen from measurement (the relevant rival keeps its three stronger forecast moves beside the second and third rivals'); p7, fifth home on its 141st move before, now crashes on its 19th, move 151, at the top-of-course hairpin: from (59,4) at v(2,-3) every landing is beyond the outer wall, and it goes NW to (60,0). On its 15th, move 119, its one landing from (48,22) at v(4,-6) that could still stop for the hairpin, (51,17) at v(3,-5), was held by p1 (there since move 113), and it went W to (51,16) at v(3,-6). p7 leaves its old line on its 4th, move 31 (it holds v(2,-3) where it turned NW before), and comes into the hairpin about a move ahead of its old line, in the pack. Seven finishers become six: p8 moves up to fifth on its 141st (sixth on its 142nd before) and p1 to sixth on its 143rd (seventh on its 144th before); p2 is still the car running at the end, now after 142 moves (143 before), and p3 to p6 still come home first to fourth on their 137th to 140th. The race parts from round 330's on move 20 (p4's 3rd) -- recorded, not vetoed (AGENTS.md).
PROMOTED = (6, 1, [137, 138, 139, 140, 141, 143])
LEGACY_CHAMPION = (6, 1, [139, 140, 141, 143, 144, 146])
EXPECTED = {kind: {"zandvoort:115": PROMOTED} for kind in LABELS}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {kind: {} for kind in LABELS}
    with tempfile.TemporaryDirectory(prefix="round126-regression-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["zandvoort"]))  # frozen pre-2026-08-29 geometry
        bench_ai.set_nplayers(8)
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            for track, seed in CASES:
                actual[kind][f"{track}:{seed}"] = bench_ai.run_track(
                    track, timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-126 promoted regression: {actual}, expected {EXPECTED}")
    # Round 247 retired the round-126 finisher/crash contract against the legacy
    # champion and pinned the pace edge instead; round 248's physical world model
    # gave the race its seventh finisher back and the contract returned. Round 281
    # lost that car again (six finishers and one crash, like the legacy car) and
    # pinned the pace edge once more; round 300a gave the race its seventh
    # finisher back and the original contract returned, holding through round
    # 330. Round 331 loses that car again (six finishers and one crash, like the
    # legacy car, fifteen finisher moves faster), and the rule records a crash
    # rather than vetoing it (CLAUDE.md): the measured race above is the pin, and
    # the pace edge over the legacy car still has to hold, as in rounds 247 and 281.
    result = actual[LABELS[0]]["zandvoort:115"]
    if sum(result[2]) >= sum(LEGACY_CHAMPION[2]):
        raise SystemExit(f"Round-126 pace edge lost: {result}, legacy {LEGACY_CHAMPION}")
    print("AI1EqualSpeedVetoRegression: OK (Zandvoort s115 pinned, with the pace edge over the legacy car)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
