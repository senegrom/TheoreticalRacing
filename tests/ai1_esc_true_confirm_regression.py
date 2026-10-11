#!/usr/bin/env python3
"""Pin the Round-107 ESC-route direct true-rival confirm.

Hungaroring 8-car seed 144 is the start-funnel specimen: at move 26 the
champion's SE commitment is alive in every suppressed simulation world
(scorer-5 cap 3, scorer-8 cap 6) and dead only under five rounds of true
rivals at the certification cap. The round-104 cost ladder is blind to it
because its cheap pre-check reads alive; round 107 runs true rivals
directly at the ESC escalation, gated to the exact signature (two threaded
slots, two snug slots, healthy final tier). Before round 107 this race
crashed p2 at move 58; it had to stay crash-free with a full field.

Round 301a' (the pace swap breaks only exact faithful ties): the race is
no longer crash-free. p1, the car still running at the end before, now
crashes on its 44th move (turn 345, in the pack at (62,116)), and p8,
seventh home before, is the car still running at the end, so seven
finishers become six. No car loses a place: the classification is
unchanged, p1 eighth. Recorded, not vetoed (CLAUDE.md): the pin now holds
the measured finishers and crashes.

Round 303 (aware forecasts, the chooser lab's aware promoted): the race is
crash-free again. It first plays differently on p1's 16th move (turn 121);
p1, which crashed on its 44th move in rounds 301a' and 301c (turn 345, in
the pack at (62,116)), now comes through that pack and home seventh on its
117th move (turn 912), so six finishers become seven again. p8, still the
car running at the end, now after 116 moves, drops from seventh to eighth:
p1 takes the place p8 loses, the reverse of the order before round 301a'
(p8 seventh home on its 116th move, p1 eighth). The pin holds the measured
finishers and crashes, the round-107 7/0 again.
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
            prefix="theoretical-racing-ai1-esc-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        bench_ai.set_all_to("AI1")
        result = bench_ai.run_track("hungaroring", timeout=900, seed=144)

    if result is None:
        raise SystemExit("AI1 hungaroring seed-144 race failed or produced no complete log")
    # The last live car is placed by elimination without a FINISH log line, so a
    # crash-free 8-car race records 7 finishers.
    finishes, crashes, _ = result
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); p1, the car
    # still running at the end before, now crashes on its 44th move and seven finishers become six: p8,
    # seventh home on its 116th move before, is now the car still running at the end after 114 moves.
    # The classification is unchanged (p1 eighth) -- recorded, not vetoed.
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); p1, which
    # crashed on its 44th move in rounds 301a' and 301c, now keeps its race and comes home seventh on its
    # 117th, so six finishers become seven again: p8, still the car running at the end, now after 116
    # moves, drops from seventh to eighth -- crash-free again, and that is what is pinned below.
    if crashes != 0 or finishes != 7:
        raise SystemExit(
            "ESC true-confirm regression: hungaroring s144 finishes="
            f"{finishes} crashes={crashes} (expected 7/0)"
        )
    print("ai1 ESC true-confirm pin OK: hungaroring s144 7/0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
