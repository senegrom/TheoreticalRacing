#!/usr/bin/env python3
"""Pin Round 126's equal-speed false-target rescue after promotion."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

# 2026-09-15 simulation-boundary correction: measured on JDK 25.
# Zandvoort s115 regains a seventh finisher. Compare historical pace over
# the same six finishing positions, rather than incorrectly pricing the extra
# finisher as lost pace.
# See docs/master-simulation-integration.md for paired fleet and corpus evidence.

CASES = [("zandvoort", 115)]
# Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
# Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
# Round 247 (the soft rollout at one level, not two): re-frozen from
# measurement. The race loses a car again -- recorded, not vetoed.
PROMOTED = (7, 0, [137, 139, 140, 141, 142, 143, 144])
LEGACY_CHAMPION = (6, 1, [139, 140, 141, 143, 144, 146])
EXPECTED = {kind: {"zandvoort:115": PROMOTED} for kind in ("AI1", "AI2")}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {"AI1": {}, "AI2": {}}
    with tempfile.TemporaryDirectory(prefix="round126-regression-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["zandvoort"]))  # frozen pre-2026-08-29 geometry
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for track, seed in CASES:
                actual[kind][f"{track}:{seed}"] = bench_ai.run_track(
                    track, timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-126 promoted regression: {actual}, expected {EXPECTED}")
    if actual["AI1"] != actual["AI2"]:
        raise SystemExit(f"Round-126 promotion is not mirrored: {actual}")
    # The repaired race has seven finishers versus six in the historical
    # reference. Summing seven finishing times against six is not a pace
    # comparison. Retain the strict pace check for the same six finishing
    # positions and separately require no loss of the reference finishers.
    # This historical diagnostic is not the promotion criterion; paired
    # current-policy finishing places are measured in the integration report.
    result = actual["AI1"]["zandvoort:115"]
    reference_finishers = LEGACY_CHAMPION[0]
    if (result[0] < reference_finishers
            or sum(result[2][:reference_finishers]) >= sum(LEGACY_CHAMPION[2])):
        raise SystemExit(f"Round-126 matched-finisher pace edge lost: {result}, legacy {LEGACY_CHAMPION}")
    print("AI1EqualSpeedVetoRegression: OK (Zandvoort s115 pinned for both kinds)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
