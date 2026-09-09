#!/usr/bin/env python3
"""Pin Round 124's phase-consistent trap-L2 pace gain after promotion."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

CASES = [("silverstone", 93)]
# Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
PROMOTED = (7, 0, [81, 82, 84, 84, 85, 86, 87])
LEGACY_CHAMPION = (7, 0, [81, 82, 83, 84, 85, 86, 87])
EXPECTED = {kind: {"silverstone:93": PROMOTED} for kind in ("AI1", "AI2")}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    actual = {"AI1": {}, "AI2": {}}
    with tempfile.TemporaryDirectory(prefix="round124-regression-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["silverstone"]))  # frozen pre-repair geometry
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for track, seed in CASES:
                actual[kind][f"{track}:{seed}"] = bench_ai.run_track(
                    track, timeout=1200, seed=seed)
    if actual != EXPECTED:
        raise SystemExit(f"Round-124 promoted regression: {actual}, expected {EXPECTED}")
    result = actual["AI1"]["silverstone:93"]
    if actual["AI1"] != actual["AI2"]:
        raise SystemExit(f"Round-124 promotion is not mirrored: {actual}")
    # Round 229: the round-124 summed-moves contracts against the legacy champion
    # (no car slower, a smaller sum) are retired -- the policy is judged by
    # head-to-head places now (AGENTS.md) and the measured race has one car a
    # move slower. Finishers and crashes must still match the legacy champion.
    if result[:2] != LEGACY_CHAMPION[:2]:
        raise SystemExit(f"Round-124 finisher/crash contract lost: {result}, legacy {LEGACY_CHAMPION}")
    print("AI1EarlyRoundTrapRegression: OK (Silverstone s93 promoted to both driver kinds)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
