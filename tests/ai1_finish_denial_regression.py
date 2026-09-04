#!/usr/bin/env python3
"""Pin the contested-finish denial rescue, now for both kinds.

Hairpin seed 68, eight cars: p8 arrives at the flag on a high-energy line a
rival can close, and without the override it crashes at move 104 (its old
frozen AI2 control: 6 finishers, one crash, p8 last). The finish-denial
certificate switches it to a braking escape that survives both the deep
scorer world and the faithful world, and it finishes sixth. Until the
2026-09-04 promotion that arm was AI1-only and this pin froze the AI2 crash
as a control; both kinds now run one policy, so every roster -- all-AI2,
all-AI1 and the two mixed halves -- must drive the same rescued race, byte
for byte once the kind labels are normalized away.
"""

import hashlib
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

TARGET = ("hairpin", 68)
RESCUED = (7, 0, [16, 16, 17, 18, 19, 19, 20])
RESCUED_FINISHERS = [
    (2, 16),
    (3, 16),
    (4, 17),
    (6, 18),
    (7, 19),
    (8, 19),
    (1, 20),
]
RESCUED_MOVES = {1: 20, 2: 16, 3: 16, 4: 17, 5: 19, 6: 18, 7: 19, 8: 19}
# The rescue decision with the kind label normalized, as normalized_lines does.
RESCUED_DECISION = "104 p8 AI W v(7,0)→(6,0) (41,6)→(47,6) ok"
RESCUED_SHA256 = "802fef7f56604ece09ab89ae6bf332d5f858dfd18a8d216e119e8ce7d1f452e4"


def race_events(
    text: str,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]], dict[int, int]]:
    moves: dict[int, int] = {}
    finishers: list[tuple[int, int]] = []
    crashes: list[tuple[int, int]] = []
    for line in text.splitlines():
        match = re.match(r"^(\d+) p(\d+) ", line)
        if match is None:
            continue
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if "FINISH" in line:
            finishers.append((player, moves[player]))
        if "CRASH" in line:
            crashes.append((player, moves[player]))
    return finishers, crashes, moves


def normalized_lines(text: str) -> list[str]:
    return [
        line.replace("AI1", "AI").replace("AI2", "AI")
        for line in text.splitlines()
        if line.startswith("player")
        or line.startswith("# turns")
        or line.startswith("# results")
        or (line and line[0].isdigit())
    ]


def normalized_sha256(text: str) -> str:
    return hashlib.sha256("\n".join(normalized_lines(text)).encode("utf-8")).hexdigest()


def logged_kinds(text: str, nplayers: int) -> list[str]:
    kinds: list[str | None] = [None] * nplayers
    for line in text.splitlines():
        match = re.match(r"^\d+ p(\d+) (AI1|AI2) ", line)
        if match is None:
            continue
        player = int(match.group(1))
        kind = match.group(2)
        if player < 1 or player > nplayers:
            raise SystemExit(f"finish-denial log has out-of-range player p{player}")
        previous = kinds[player - 1]
        if previous is not None and previous != kind:
            raise SystemExit(
                f"finish-denial p{player} changed kind in one race: {previous} -> {kind}"
            )
        kinds[player - 1] = kind
    if any(kind is None for kind in kinds):
        raise SystemExit(f"finish-denial log is missing player kinds: {kinds}")
    return [kind for kind in kinds if kind is not None]


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    rosters = {
        "AI2": ["AI2"] * 8,
        "AI1": ["AI1"] * 8,
        "MIXED_AI2_LAST": ["AI1"] * 4 + ["AI2"] * 4,
        "MIXED_AI1_LAST": ["AI2"] * 4 + ["AI1"] * 4,
    }
    summaries = {}
    logs = {}
    with tempfile.TemporaryDirectory(prefix="finish-denial-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for label, kinds in rosters.items():
            bench_ai.set_kinds(kinds)
            summary = bench_ai.run_track(TARGET[0], timeout=1200, seed=TARGET[1])
            if summary is None:
                raise SystemExit(f"finish-denial hairpin seed-68 {label} race failed")
            log_path = Path(bench_ai.LOG)
            if not log_path.is_file():
                raise SystemExit(f"finish-denial hairpin seed-68 {label} log missing")
            log = log_path.read_text(encoding="utf-8")
            actual_kinds = logged_kinds(log, len(kinds))
            if actual_kinds != kinds:
                raise SystemExit(
                    f"finish-denial {label} roster changed: {actual_kinds}, expected {kinds}"
                )
            summaries[label] = summary
            logs[label] = log

    for label in rosters:
        finishers, crashes, moves = race_events(logs[label])
        if summaries[label] != RESCUED:
            raise SystemExit(f"finish-denial {label} summary changed: {summaries[label]}")
        if finishers != RESCUED_FINISHERS:
            raise SystemExit(f"finish-denial {label} finishers changed: {finishers}")
        if crashes or moves != RESCUED_MOVES:
            raise SystemExit(
                f"finish-denial {label} events changed: crashes={crashes}, moves={moves}"
            )
        if RESCUED_DECISION not in normalized_lines(logs[label]):
            raise SystemExit(f"finish-denial {label} decision missing: {RESCUED_DECISION}")
        digest = normalized_sha256(logs[label])
        if digest != RESCUED_SHA256:
            raise SystemExit(
                f"finish-denial {label} trajectory changed: {digest}, expected {RESCUED_SHA256}"
            )

    print(
        "AI1FinishDenialRegression: OK "
        "(hairpin s68 p8 crash-to-sixth rescue, identical for every roster of both kinds)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
