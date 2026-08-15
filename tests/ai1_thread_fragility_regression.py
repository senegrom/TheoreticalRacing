#!/usr/bin/env python3
"""Pin the Round-98 thread-fragility audit.

Chicane 8-car seed 51 is the definitive rival-side specimen of the
recursion-boundary class: at the last avoidable move the champion's SE
commits to a line that stays alive in every affordable rival world but
threads a single viable candidate on every simulated slot while the real
pack's champion braking seals the lane two rounds later. The audit rejects
alive-but-fully-threaded verdicts in pack traffic and switches to an alive,
non-threaded alternative (here W, the oracle-proven survivor). Before Round
98 this race crashed p1; it must stay crash-free with a full field of
finishers.
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

    with tempfile.TemporaryDirectory(
            prefix="theoretical-racing-ai1-thread-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        bench_ai.set_all_to("AI1")
        result = bench_ai.run_track("chicane", timeout=600, seed=51)

    if result is None:
        raise SystemExit("AI1 chicane seed-51 race failed or produced no complete log")
    # The last live car is placed by elimination without a FINISH log line, so a
    # crash-free 8-car race records 7 finishers. Before Round 98 this race had
    # crashes=1 (p1 dies at move 145 after the m121 commitment).
    finishes, crashes, _ = result
    if crashes != 0 or finishes != 7:
        raise SystemExit(
            "thread-fragility regression: chicane s51 finishes="
            f"{finishes} crashes={crashes} (expected 7/0)"
        )
    print("ai1 thread fragility pin OK: chicane s51 7/0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
