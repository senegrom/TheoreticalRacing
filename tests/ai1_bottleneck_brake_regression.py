#!/usr/bin/env python3
"""Pin Round 97's static-bottleneck crash rescue before champion mirroring."""

from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

EXPECTED = {
    "AI1": (7, 0, [139, 140, 141, 142, 143, 144, 146]),
    "AI2": (6, 1, [139, 140, 141, 142, 143, 144]),
}
EXPECTED_DECISION = {
    "AI1": "110 p6 AI1 SW v(3,-8)→(2,-7) (42,35)→(44,28) ok",
    "AI2": "110 p6 AI2 S v(3,-8)→(3,-7) (42,35)→(45,28) ok",
}
EXPECTED_COMMON_FINISHERS = [
    (1, 139),
    (2, 140),
    (3, 141),
    (4, 142),
    (5, 143),
    (7, 144),
]


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


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    with tempfile.TemporaryDirectory(prefix="ai1-bottleneck-brake-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            summaries[kind] = bench_ai.run_track("zandvoort", timeout=900, seed=32)
            logs[kind] = Path(bench_ai.LOG).read_text(encoding="utf-8")

    for kind, expected in EXPECTED.items():
        if summaries[kind] != expected:
            raise SystemExit(
                f"Round-97 Zandvoort seed-32 {kind} regression: "
                f"{summaries[kind]}, expected {expected}"
            )
        if EXPECTED_DECISION[kind] not in logs[kind].splitlines():
            raise SystemExit(
                f"Round-97 Zandvoort seed-32 {kind} decision regression: "
                f"missing {EXPECTED_DECISION[kind]}"
            )

    ai1_finishers = finishers(logs["AI1"])
    ai2_finishers = finishers(logs["AI2"])
    if ai2_finishers != EXPECTED_COMMON_FINISHERS:
        raise SystemExit(
            f"Round-97 frozen champion boundary changed: {ai2_finishers}, "
            f"expected {EXPECTED_COMMON_FINISHERS}"
        )
    if ai1_finishers[:-1] != EXPECTED_COMMON_FINISHERS or ai1_finishers[-1] != (6, 146):
        raise SystemExit(
            f"Round-97 rescue disturbed the established finishers: {ai1_finishers}"
        )

    print(
        "AI1BottleneckBrakeRegression: OK "
        "(Zandvoort seed 32 rescues p6 via the same-TTF transverse brake)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
