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
PROMOTED = (7, 0, [137, 138, 139, 141, 142, 143, 144])
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
    # pinned the pace edge once more; round 300a gives the race its seventh
    # finisher back and the original contract holds again.
    result = actual[LABELS[0]]["zandvoort:115"]
    if not (result[0] > LEGACY_CHAMPION[0] and result[1] < LEGACY_CHAMPION[1]):
        raise SystemExit(f"Round-126 safety contract lost: {result}, legacy {LEGACY_CHAMPION}")
    print("AI1EqualSpeedVetoRegression: OK (Zandvoort s115 rescue holds)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
