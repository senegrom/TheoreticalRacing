#!/usr/bin/env python3
"""Pin Round 96's synchronized finish-frontier pace gain."""

from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

EXPECTED = {
    6: (7, 0, [58, 59, 59, 60, 61, 62, 62]),
    47: (7, 0, [58, 60, 60, 61, 61, 62, 63]),
    49: (7, 0, [58, 59, 60, 61, 61, 62, 63]),
}
EXPECTED_SEED6_FINISHERS = [
    (1, 58),
    (3, 59),
    (5, 59),
    (4, 60),
    (2, 61),
    (6, 62),
    (7, 62),
]
EXPECTED_DECISION = {
    6: "299 p3 {kind} W v(1,-6)→(0,-6) (65,49)→(65,43) ok",
    47: "298 p2 {kind} SW v(1,-6)→(0,-5) (65,49)→(65,44) ok",
    49: "308 p4 {kind} SW v(1,-5)→(0,-4) (67,49)→(67,45) ok",
}


def finishers(text: str) -> list[tuple[int, int]]:
    moves: dict[int, int] = {}
    result = []
    for line in text.splitlines():
        match = re.match(r"^(\d+) p(\d+) ", line)
        if match is None:
            continue
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if "FINISH" in line:
            result.append((player, moves[player]))
    return result


def normalized_lines(text: str) -> list[str]:
    return [
        line.replace("AI1", "AI").replace("AI2", "AI")
        for line in text.splitlines()
        if line.startswith("player")
        or line.startswith("# turns")
        or line.startswith("# results")
        or (line and line[0].isdigit())
    ]


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    with tempfile.TemporaryDirectory(prefix="ai1-finish-frontier-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for seed in EXPECTED:
                summaries[(kind, seed)] = bench_ai.run_track("coil", timeout=600, seed=seed)
                logs[(kind, seed)] = Path(bench_ai.LOG).read_text(encoding="utf-8")

    for kind in ("AI1", "AI2"):
        for seed, expected in EXPECTED.items():
            actual = summaries[(kind, seed)]
            if actual != expected:
                raise SystemExit(
                    f"Round-96 Coil seed-{seed} {kind} regression: {actual}, expected {expected}"
                )
            decision = EXPECTED_DECISION[seed].format(kind=kind)
            if decision not in logs[(kind, seed)].splitlines():
                raise SystemExit(
                    f"Round-96 Coil seed-{seed} {kind} decision regression: missing {decision}"
                )

        seed6_finishers = finishers(logs[(kind, 6)])
        if seed6_finishers != EXPECTED_SEED6_FINISHERS:
            raise SystemExit(
                f"Round-96 Coil seed-6 {kind} finisher regression: "
                f"{seed6_finishers}, expected {EXPECTED_SEED6_FINISHERS}"
            )

    for seed in EXPECTED:
        if normalized_lines(logs[("AI1", seed)]) != normalized_lines(logs[("AI2", seed)]):
            raise SystemExit(f"Round-96 Coil seed-{seed} champion self-tie lost")

    move_sums = {
        kind: sum(summaries[(kind, 6)][2])
        for kind in ("AI1", "AI2")
    }
    if any(move_sum != 421 or move_sum >= 426 for move_sum in move_sums.values()):
        raise SystemExit(f"Round-96 Coil seed-6 pace gain lost: {move_sums}")

    print(
        "AI1FinishFrontierRegression: OK "
        "(Coil seed 6 self-tie at 421 moves; seeds 47/49 vetoes pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
