#!/usr/bin/env python3
"""Pin the faithful-rival finish-sprint safety confirmation.

Outcome pin, awaiting a decision specimen (2026-11-13). Round 176 drops a
finish-sprint candidate that is five or more map turns from the finish and
leaves one safe successor when a five-round forecast against faithful rivals
kills it. On round 345's grids the race below holds no real decision of the
sprint or of any pace override, and a fleet scan found the veto dropping a
candidate in no real decision: the 83 courses other than the Nordschleife over
seeds 1-40, eight AI2 cars, one lap, random starts, 3,320 races, raced by a
scratch build that prints the legs of top-level decisions only. The scan shows
a drop, not a veto that ran and passed, so it does not say how often the veto
was asked. The finish sprint took 130 real moves in them, 111 within 15 map
turns of the finish and 19 in round 94's band of 16 to 20. The pin holds the
race's outcome and trajectory.
"""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import normalized_lines, normalized_sha256, race_events  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

TARGET = ("rand3", 1)
# Round 226 re-froze this from measurement: the needle surcharge became a
# tie-break (12 -> 1), which is worth 0.58-0.60 places head-to-head. Finishers
# and crashes are unchanged; the move counts are the faster lines.
# Round 228: re-frozen from complete recorded races after removing the
# narrow-lane distance surcharge: seven finishers and no crashes in every case.
# Round 231: re-frozen from recorded checkpoint-choice races; the existing
# assertion logic and AI1/AI2 identity checks remain intact.
# Every case below retains seven finishers and zero crashes.
# Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
# Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
# Round 247: re-frozen from measurement (the soft rollout at one level, not two).
# Round 248: re-frozen from measurement (the physical world model: occupancy with lap state, rollouts that stop with the last survivor, blockades replayed).
# Round 260: re-frozen from measurement (the faithful joint world as a chooser).
# Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
# Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
# Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
# Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
# Round 336: re-frozen from measurement (gates are ordinary landings wherever the exact potential prices them).
PROMOTED = (7, 0, [60, 61, 61, 62, 62, 62, 63])
# Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
# Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); a new grid and a new race, seven finishers and no crash: p1 wins on its 60th own move, p2 and p3 are second and third on their 61st, p4, p5 and p6 fourth to sixth on their 62nd and p7 seventh on its 63rd, and p8 is the car still running at the end, after 62 moves, at (141,113) at v(2,-5), a move from the line (p5 crossed from that cell at that speed, NW to (142,107), at move 489). The summary above, PROMOTED, is this race's summary as it stands.
PROMOTED_FINISHERS = [(1, 60), (2, 61), (3, 61), (4, 62), (5, 62), (6, 62), (7, 63)]
# Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); the race of the note above PROMOTED_FINISHERS: the seven finishers' own moves, and p8's 62, the car still running at the end.
PROMOTED_ALL_MOVES = {1: 60, 2: 61, 3: 61, 4: 62, 5: 62, 6: 62, 7: 63, 8: 62}
# Round 237: re-frozen from measurement (every car takes the two-move duel proof).
# Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
# Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy).
# Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
# Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full policy in every decision).
# Round 335: re-frozen from measurement (every rival but the relevant one plays its first two forecast moves by its full policy).
# Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); the race of the note above PROMOTED_FINISHERS.
PROMOTED_SHA256 = 'b9b6b54ee9ec6f0bac9e136534e41d2f5a403c5d3ba8267c6ea26762bbb94a7a'


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    with tempfile.TemporaryDirectory(prefix="finish-sprint-true-confirm-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            summary = bench_ai.run_track(TARGET[0], timeout=1200, seed=TARGET[1])
            if summary is None:
                raise SystemExit(f"finish-sprint true-confirm Rand3 seed-1 {kind} race failed")
            log_path = Path(bench_ai.LOG)
            if not log_path.is_file():
                raise SystemExit(f"finish-sprint true-confirm Rand3 seed-1 {kind} log missing")
            summaries[kind] = summary
            logs[kind] = log_path.read_text(encoding="utf-8")

    for kind in LABELS:
        text = logs[kind]
        if summaries[kind] != PROMOTED:
            raise SystemExit(
                f"finish-sprint true-confirm Rand3 seed-1 {kind} regression: "
                f"{summaries[kind]}, expected {PROMOTED}"
            )
        finishers, crashes, moves = race_events(text)
        if finishers != PROMOTED_FINISHERS:
            raise SystemExit(
                f"finish-sprint true-confirm Rand3 seed-1 {kind} finisher regression: "
                f"{finishers}, expected {PROMOTED_FINISHERS}"
            )
        if crashes:
            raise SystemExit(
                f"finish-sprint true-confirm Rand3 seed-1 {kind} crash regression: {crashes}"
            )
        if moves != PROMOTED_ALL_MOVES:
            raise SystemExit(
                f"finish-sprint true-confirm Rand3 seed-1 {kind} move regression: "
                f"{moves}, expected {PROMOTED_ALL_MOVES}"
            )
        # Round 215 retired this comparison: the order it checks against was
        # recorded from the pre-promotion model under the old single-lap rules,
        # and that build cannot be re-run to produce a fair reference.
        # Round 215 retired the all-move comparison: its reference came from
        # the pre-promotion build under the old single-lap rules, so comparing
        # this build against it says nothing about either. The pins above still
        # hold the current trajectory exactly.
        # Round 215 retired this check: it measured the rescue as an offset from
        # where the pre-promotion build crashed, and that race no longer exists to
        # offset from.
        # Round 215 retired this check: it looked for one decision at one move
        # index, and the race no longer reaches that state. The digest below
        # still pins the whole trajectory.
        digest = normalized_sha256(text)
        if digest != PROMOTED_SHA256:
            raise SystemExit(
                f"finish-sprint true-confirm Rand3 seed-1 {kind} trajectory regression: "
                f"{digest}, expected {PROMOTED_SHA256}"
            )

    # Round 345: the message named the race before round 345 (p8 home, round 176's crash-to-finish
    # rescue, unchecked since round 215); in the new race p8 is the car still running at the end.
    print(
        "AI1FinishSprintTrueConfirmRegression: OK "
        "(Rand3 s1: seven finishers, no crash, every move count and the trajectory pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
