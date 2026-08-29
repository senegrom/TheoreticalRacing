#!/usr/bin/env python3
"""Pin Round 126's equal-speed false-target rescue after promotion."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

CASES = [("zandvoort", 115)]
PROMOTED = (7, 0, [139, 140, 141, 142, 143, 144, 145])
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
    result = actual["AI1"]["zandvoort:115"]
    if not (result[0] > LEGACY_CHAMPION[0] and result[1] < LEGACY_CHAMPION[1]):
        raise SystemExit(f"Round-126 safety contract lost: {result}, legacy {LEGACY_CHAMPION}")
    print("AI1EqualSpeedVetoRegression: OK (Zandvoort s115 rescue promoted to both kinds)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
