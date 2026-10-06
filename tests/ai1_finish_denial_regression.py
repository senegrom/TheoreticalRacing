#!/usr/bin/env python3
"""Pin the contested-finish denial rescue.

Hairpin seed 68, eight cars: p8 arrives at the flag on a high-energy line a
rival can close, and without the override it crashes at move 104 (its old
frozen AI2 control: 6 finishers, one crash, p8 last). The finish-denial
certificate switches it to a braking escape that survives both the deep
scorer world and the faithful world, and it finishes. Until the
2026-09-04 promotion that arm was AI1-only and this pin froze the AI2 crash
as a control. Both kinds now run one policy, so since 2026-09-27 the pin
races the all-AI2 roster once; ai1_label_invariance_regression checks that
the labels race alike.
"""

from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import normalized_lines, normalized_sha256, race_events  # noqa: E402

TARGET = ("hairpin", 68)
# Round 247 (the soft rollout at one level, not two): re-frozen from
# measurement; still seven finishers and no crash, p8 home in 18 moves.
# Round 260 (the faithful joint world as a chooser): re-frozen from
# measurement. The rescue holds -- p8 is home in 17 moves and no roster
# crashes -- on a faster race: eighteen moves for the last car, not nineteen.
# Round 274 (rank first): re-frozen from measurement. p8 now crosses the line
# in 17 moves as the sixth finisher instead of being classified last, and p1
# is the car classified behind; still seven finishers and no crash.
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p8 is
# home seventh of seven, in 18 moves; still seven finishers and no crash.
RESCUED = (7, 0, [16, 16, 16, 17, 17, 18, 18])
RESCUED_FINISHERS = [(2, 16), (3, 16), (4, 16), (5, 17), (7, 17), (6, 18), (8, 18)]
RESCUED_MOVES = {1: 18, 2: 16, 3: 16, 4: 16, 5: 17, 6: 18, 7: 17, 8: 18}
# The rescue decision with the kind label normalized, as normalized_lines does.
# Round 233 (the lane spread left the score): p8 reaches (47,6) a move earlier
# now, so move 104 is the step after the rescue rather than the rescue itself;
# re-frozen from measurement, with the trajectory digest below unchanged in role.
# Round 247: re-frozen from measurement (the soft rollout at one level, not two).
# Round 260: the same turn and car, re-frozen from measurement.
# Round 274: the same turn and car, re-frozen from measurement (rank first).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); the
# same turn and car: p8 now accelerates SE from (40,6) there, and its braking
# SW comes at move 112.
RESCUED_DECISION = "104 p8 AI SE v(7,0)→(8,1) (40,6)→(48,7) ok"
# Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
# Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
# Round 260: re-frozen from measurement (the chooser).
# Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
RESCUED_SHA256 = "b71867850cc67bd2466ad3037fd1282e2fd49b65cfd1cbc748e8b20255dbfd8b"


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

    # One roster: both labels run one policy since round 222, so the three
    # relabeled rosters raced the same race again (ai1_label_invariance_regression
    # checks that once for every pin; 2026-09-27).
    rosters = {
        "AI2": ["AI2"] * 8,
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
        "(hairpin s68 p8 crash-to-finish rescue)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
