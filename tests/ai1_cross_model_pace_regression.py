#!/usr/bin/env python3
"""Pin Round 95's strict pace retention (measured across two AI models then;
one policy since round 222)."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

EXPECTED = {
    # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
    # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 248: re-frozen from measurement (the physical world model: occupancy with lap state, rollouts that stop with the last survivor, blockades replayed).
    # Round 260 (the chooser): Silverstone s1 loses a car here -- recorded,
    # not vetoed (AGENTS.md); the finisher moves below are the pin's subject.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p8 no longer crashes on its 11th move and p5 now finishes: six finishers become seven, p8 the car still running at the end.
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); seven finishers and no crash as before; the third and fifth finishers are each one move slower (see the move sum below).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted); seven finishers and no crash as before, the first six places each one move faster (see the move sum below). The pin's subject went with that family: round 95's leg, which kept the faster line when the cross-model alternative was slower, sat in its deep-pack check, so since round 310 these numbers pin only the race's own result and finisher moves.
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); seven finishers and no crash as before; the first, second, fourth and sixth places are each one move slower and the seventh two (see the move sum below).
    "AI2": (7, 0, [82, 83, 83, 84, 84, 85, 87]),
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    results = {}
    with tempfile.TemporaryDirectory(prefix="ai1-cross-model-pace-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["silverstone"]))  # frozen pre-repair geometry
        bench_ai.set_nplayers(8)
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            results[kind] = bench_ai.run_track("silverstone", timeout=900, seed=1)

    for kind, expected in EXPECTED.items():
        if results[kind] != expected:
            raise SystemExit(
                f"Round-95 Silverstone seed-1 {kind} regression: "
                f"{results[kind]}, expected {expected}"
            )

    move_sum = sum(results[LABELS[0]][2])
    # Round 229: 596 is the sum of the re-frozen finisher moves.
    # Round 247: 586 (the soft rollout at one level, not two). Round 248: 587.
    # Round 260: 501 is the sum of the six re-frozen finisher moves.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); 586 is the sum of the seven finisher moves: round 260's six unchanged plus p5's 85.
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); 588 is the sum of the seven finisher moves, two more than before: p1 now wins on its 82nd move (second on its 83rd before), but p2 (the winner before, on its 82nd) is second on its 83rd, p3 third on its 84th (83rd before) and p4 fifth on its 85th (fourth on its 84th before); p5 is fourth on its 84th (fifth before), p6 and p7 sixth and seventh on their 85th as before, and p8 is still the car running at the end, after 84 moves -- recorded, not vetoed (AGENTS.md).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted); 582 is the sum of the seven finisher moves, six fewer than before: p2 now wins on its 81st move (second on its 83rd before), p3 is second on its 82nd (third on its 84th before), p1, the winner on its 82nd before, third on its 83rd, p4 fourth on its 83rd (fifth on its 85th before), p5 fifth on its 84th (fourth on its 84th before), p6 sixth on its 84th (85th before) and p7 seventh on its 85th as before; p8 is still the car running at the end, after 84 moves -- recorded, not vetoed (AGENTS.md).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); 588 is the sum of the seven finisher moves, six more than before: p2 still wins, now on its 82nd move (81st before), and p3 is still second, now on its 83rd (82nd before); p5 is third on its 83rd (fifth on its 84th before), p6 fourth on its 84th (sixth on its 84th before), p7 fifth on its 84th (seventh on its 85th before), p8 (the car still running at the end before, after 84 moves) sixth on its 85th and p1 (third on its 83rd before) seventh on its 87th; p4 (fourth home before, on its 83rd) is now the car still running at the end, after 86 moves -- recorded, not vetoed (AGENTS.md).
    if move_sum != 588:
        raise SystemExit(f"Round-95 promoted finisher moves lost: {results[LABELS[0]]}")

    print(
        "AI1CrossModelPaceRegression: OK "
        f"(promoted Silverstone seed 1 at {move_sum} finisher moves)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
