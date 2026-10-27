#!/usr/bin/env python3
"""Pin the contested-finish denial rescue.

Hairpin seed 68, eight cars: p8 arrives at the flag on a high-energy line a
rival can close, and without the override it crashes at move 104 (its old
frozen AI2 control: 6 finishers, one crash, p8 last). The finish-denial
certificate switches it to a braking escape that survives both the deep
scorer world and the faithful world, and it does not crash. Until the
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
# Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); p8 is
# home sixth of seven, in 17 moves, and p5 seventh, in 18; still seven finishers and no crash.
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); the race
# first plays differently at move 5 (p5's first), and p8 is no longer home: it is the car still running
# at the end, after 17 moves and one move from the line at (70,21), when p7 finishes seventh at move
# 135, so it is classified eighth instead of sixth, as in round 260. p1, the car still running at the
# end before, is home sixth in 18 moves; still seven finishers and no crash.
# Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation
# moves; a rival's forecast crash is no win); the race first plays differently at move 1 (p1's first: it
# now holds still on the grid, NONE), and p8 is home again: seventh, at move 136, in 18 moves. p1 is now
# the car still running at the end, after 18 moves and one move from the line at (70,21), so it is
# classified eighth instead of sixth; p7 is home sixth instead of seventh, in 18 moves as before. The
# same summary: still seven finishers and no crash.
# Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time);
# the race first plays differently at move 14 (p6's second), and p8 is home fifth, at move 133, in 17
# moves (seventh in 18 before). p5, fourth home in 17 moves before, is now the car still running at the
# end, after 18 moves, so it is classified eighth; p1, the car still running at the end before, is home
# seventh in 19 moves, and p6 is home fourth instead of fifth, in 17 moves as before. Still seven
# finishers and no crash.
# Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's
# three stronger forecast moves); the race first plays differently at move 8 (p8's first: NW, not W),
# and p8 is home sixth, at move 137, in 18 moves (fifth at move 133 in 17 before); it brakes at move
# 104 (below). p7 is home fifth instead of sixth, in 18 moves as before; p2, p3 and p4 are still home
# first to third in 16 moves, p6 fourth in 17 and p1 seventh in 19, and p5 is still the car running at
# the end, after 18 moves. Still seven finishers and no crash.
# Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger
# forecast move too); the race first plays differently at move 8 (p8's first: W again, as in rounds 316
# to 328, not NW), and p8 is home fifth again, at move 133, in 17 moves (sixth at move 137 in 18
# before); it steers S at move 104 (below). p7 is home sixth instead of fifth, in 18 moves as before;
# p2, p3 and p4 are still home first to third in 16 moves, p6 fourth in 17 and p1 seventh in 19, and p5
# is still the car running at the end, after 18 moves -- round 316's numbers again, on a race that
# parts from round 316's (as raced through round 328) at move 15 (p7's second). Still seven finishers
# and no crash.
# Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full
# policy in every decision); the race first plays differently at move 31 (p7's fourth: N to (13,21), not
# NW to (12,21)), and p7 and p8 trade places. From (14,17) at v(1,-4), which it reaches at move 39, p7
# races round 330's p8 line move for move, a turn earlier than p8 did, and is home fifth, at move 132, in
# 17 moves (sixth at move 136 in 18 before). p8 holds v(0,-2) at move 32 (NONE, to (13,22), not N to
# (13,21), where p7 now is) and is home sixth, at move 136, in 18 moves (fifth at move 133 in 17 before);
# it accelerates SE at move 104 (below). p2, p3 and p4 are still home first to third in 16 moves, p6
# fourth in 17 and p1 seventh in 19, and p5 is still the car running at the end, after 18 moves, now at
# (74,26), a move from the line (at (71,21) before). The same summary: still seven finishers and no
# crash.
# Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its
# full policy); the race first plays differently at move 8 (p8's first: NW to (14,26), not W to (14,27),
# as in round 329, whose race this one leaves at move 16, p8's second), and p1 and p8 trade places.
# From (16,14) at v(2,-3), which it reaches at move 49, p1 races round 330's p8 line (round 333's p7's)
# move for move and is home sixth, at move 134, in 18 moves (seventh at move 137 in 19 before). From
# (18,10) at v(3,-2), which it reaches at move 56, p8 races round 329's p7 line move for move and is home
# seventh, at move 136, in 18 moves as before (sixth before); it brakes W at move 104 (below). p2, p3 and
# p4 are still home first to third in 16 moves, p6 fourth and p7 fifth in 17, and p5 is still the car
# running at the end, after 18 moves, at (71,21) again, as in round 330, a move from the line (at (74,26)
# before): p8's crossing, the seventh, ends the race, so p5 is classified eighth. Still seven finishers
# and no crash; the last finisher is home in 18 moves, not 19 (the summary of rounds 281, 303 and
# 305/309 again).
RESCUED = (7, 0, [16, 16, 16, 17, 17, 18, 18])
RESCUED_FINISHERS = [(2, 16), (3, 16), (4, 16), (6, 17), (7, 17), (1, 18), (8, 18)]
RESCUED_MOVES = {1: 18, 2: 16, 3: 16, 4: 16, 5: 18, 6: 17, 7: 17, 8: 18}
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
# Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); the
# same turn and car: p8 now steers S from (53,8) there, after braking SW at
# move 88, and brakes SW again at moves 112 and 120.
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); the
# same turn and car: p8 now steers S from (41,6) there, which it reached at move 80 before and at
# move 96 now, and brakes SW at moves 120 and 128.
# Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation
# moves; a rival's forecast crash is no win); the same turn and car: p8 now brakes SW there, v(7,0) to
# (6,1), from (44,6), which it reaches at move 96 (three cells further on than (41,6)), as the original
# rescue braked W, v(7,0) to (6,0); it accelerates SE at move 112, brakes SW at moves 120, 128 and 133
# and finishes at move 136.
# Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time);
# the same turn and car: p8 no longer brakes there; it steers S, v(7,1) to (7,2), from (48,7) -- no
# finish-denial brake, as no landing from v(7,1) is 16 speed2 above (7,2). It is a move ahead of round
# 305/309's line: it reaches (41,6) at v(7,0) at move 88 and steers S from there at move 96 (round 303's
# line, a move earlier), then brakes SW at moves 112, 120 and 128 and finishes at move 133.
# Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's
# three stronger forecast moves); the same turn and car: p8 brakes there, W, v(7,1) to (6,1), from
# (49,9) -- the original rescue's direction (W, v(7,0) to (6,0)), but no finish-denial brake: from
# (49,9) every landing at or above the switch's 64 speed2 (NE, E and SE, all at vx 8 from x 57) runs
# into the outer wall of the hairpin before it can reach the line, so the switch has nothing to
# replace, and W, like NONE, keeps p8 on its fastest line home (five more moves, as raced). p8 runs two
# rows lower than round 316's line and a cell further on: it reaches (42,8) at v(7,0) at move 88 and
# steers S to (49,9) at move 96; after the brake it steers S at move 112, turns SW at moves 120, 128
# and 133 and finishes at move 137.
# Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger
# forecast move too); the same turn and car: p8 steers S there again, v(7,1) to (7,2), from (48,7) --
# round 316's line, and as then no finish-denial brake, as no landing from v(7,1) is 16 speed2 above
# (7,2). p8 takes (13,26) rather than (14,26) at move 16 and from move 32, at (13,21) at v(0,-3), runs
# round 316's line again: it reaches (41,6) at v(7,0) at move 88 and steers S to (48,7) at move 96,
# then brakes SW at moves 112, 120 and 128 and finishes at move 133.
# Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full
# policy in every decision); the same turn and car: p8 now accelerates SE there, v(7,0) to (8,1), from
# (41,6) to (49,7) -- the move the old frozen AI2 control made at this turn (this pin's CONTROL_DECISION
# until round 222, whose p8 crashed on its 20th move), which the rescue replaced with a W brake, v(7,0)
# to (6,0). The switch's gates that the log shows hold for it (65 speed2, five moves from home; p5 at
# (47,6) beside the coast landing (48,6); p1, p5, p6 and p7 within ten cells of (49,7), p6 and p7
# aligned ahead; NONE and SW 16 speed2 or more lower and at most a move slower home -- not W: its
# landing (47,6) is p5's cell), yet p8 keeps SE -- no finish-denial brake -- and the line is not
# closed: p8 brakes SW at moves 112, 120, 128 and 133 and finishes at move 136, and no car crashes. p8
# rejoins round 330's line at (16,14) at v(2,-3) at move 56, a move late, and reaches (41,6) at v(7,0)
# at move 96 (88 before); round 330's S steer from (48,7), pinned here for p8 at move 104, is p7's now,
# at move 103.
# Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its
# full policy); the same turn and car: p8 now brakes W there, v(7,1) to (6,1), from (47,7) to (53,8) --
# the original rescue's direction (W, v(7,0) to (6,0)) and round 329's p7 move at move 103, but no
# finish-denial brake: no live rival is within a cell of the coast landing (54,8) (the nearest, p6, is
# at (56,9)), and every landing at or above the switch's 64 speed2 (NE, E and SE, all at vx 8 from x
# 55) runs into the outer wall of the hairpin before it can reach the line, so the switch has nothing to
# replace. W, like NONE and S, keeps p8 on its fastest line home (five more moves, as raced), and no car
# closes it. p8 reaches (40,6) at v(7,0) at move 88 (round 333's (41,6) at move 96) and steers S to
# (47,7) at move 96 (SE to (48,7) was a move faster alone); after the brake it steers S at move 112,
# brakes SW at moves 120 and 128, steers S at move 133 and finishes at move 136, on p7's cells from
# (59,10) on, a round behind. Round 330's S steer from (48,7), pinned here for p8 at move 104 in rounds
# 316 and 330 and p7's at move 103 in round 333, is p1's now, at move 105.
RESCUED_DECISION = "104 p8 AI W v(7,1)→(6,1) (47,7)→(53,8) ok"
# Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
# Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
# Round 260: re-frozen from measurement (the chooser).
# Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
# Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
# Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
# Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
# Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
# Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
# Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full policy in every decision).
# Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy).
RESCUED_SHA256 = "424ab661a70bcb06a456efaa87b3dfd73372f5ab532d026f04fff3203885141d"


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
        "(hairpin s68 p8 crash-free rescue)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
