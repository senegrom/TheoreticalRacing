#!/usr/bin/env python3
"""Pin the Round-133 vmax overspeed deep check.

Every harvest-25 slow-track crash was one serpentine2 commitment: with
vx=10 on the bottom straight, accelerating to max-axis 11 is a 5-9-round
joint doom (the static reach map holds a solo escape line, but traffic
occupies the escape rows). The deep suppressed world at the certification
cap is the only shipped world that sees it, so the leg re-verdicts
acceleration into the top speed band with scorer-8 alone. Seeds 6 and 35
carry the commitment in different slots (p7 and p6); both races must now
run crash-free under the alternating mixed field.
"""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-vmax-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        bench_ai.set_kinds(["AI1", "AI2"] * 4)
        for seed in (6, 35):
            result = bench_ai.run_track_h2h("serpentine2", timeout=600, seed=seed)
            if result is None:
                raise SystemExit(f"mixed serpentine2 seed-{seed} race failed or produced no log")
            for kind in ("AI1", "AI2"):
                place_sum, finishers, crashes = result[kind]
                if crashes != 0:
                    raise SystemExit(
                        "Round-133 vmax-deep regression: "
                        f"seed {seed} {kind} place_sum={place_sum}, "
                        f"finishers={finishers}, crashes={crashes}"
                    )
    print("AI1 vmax deep pins hold (mixed serpentine2 seeds 6 and 35)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
