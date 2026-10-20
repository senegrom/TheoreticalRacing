#!/usr/bin/env python3
"""Pin the high-speed moderate six-ahead pace frontier and its vetoes."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import finishers, normalized_lines, normalized_sha256, player_moves  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

TARGET = ("spa", 83)
# Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
# Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
# Round 248 (the physical world model): re-frozen from measurement; p5 crashes
# on its 31st move -- recorded, not vetoed.
# Round 260: re-frozen from measurement (the faithful joint world as a chooser).
# Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
# Round 278: re-frozen from measurement (the chooser's pick stands).
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
# Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
# Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
# Round 310: re-frozen from measurement (the danger-joint-search family deleted); p2 now crashes on its 27th move, at turn 210 ((106,132)→(107,139)), nine turns after the pinned turn-201 decision on the same stretch, and seven finishers become six -- recorded, not vetoed (AGENTS.md).
# Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); p2 no longer crashes on its 27th move (turn 210, now (100,139)→(100,145) ok) and finishes sixth on its 83rd: six finishers become seven again, as before round 310 -- recorded, not vetoed (AGENTS.md).
# Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); seven finishers and no crash as before, the seventh now home on its 84th move (83rd before): p3 and p4 trade fifth and seventh place (see the finisher list below).
PROMOTED = (7, 0, [78, 79, 80, 82, 82, 83, 84])
LEGACY = (7, 0, [79, 80, 81, 84, 84, 86, 88])
PROMOTED_FINISHERS = [
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); seven finishers and no crash as before, but p5 (the car still running at the end before) now finishes fourth on its 81st move and p4 (fifth home before) is the car still running at the end, after 82 moves -- recorded, not vetoed.
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); seven finishers and no crash as before, but p4 (the car still running at the end before) now finishes fifth on its 82nd move and p8 (third home before, on its 80th move) is the car still running at the end, after 82 moves; p1 and p2 now finish third and fourth on their 81st and 82nd moves, p3 sixth and p5 (fourth before) seventh, both on their 83rd -- recorded, not vetoed.
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); seven finishers and no crash as before, but p8 (the car still running at the end before, after 82 moves) now finishes third on its 80th move and p5 (seventh home before, on its 83rd) is the car still running at the end, after 82 moves; p1 now finishes fourth on its 82nd (third on its 81st before), p2 fifth on its 82nd (fourth before), p3 sixth on its 83rd as before and p4 (fifth before, on its 82nd) seventh on its 83rd -- recorded, not vetoed (AGENTS.md).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted); p2 (fifth home before, on its 82nd move) now crashes on its 27th, so six cars finish: p3 fifth on its 82nd (sixth on its 83rd before) and p4 sixth on its 83rd (seventh before); p6, p7, p8 and p1 finish as before and p5 is still the car running at the end, after 82 moves -- recorded, not vetoed (AGENTS.md).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); p2 (crashed on its 27th move before) now finishes sixth on its 83rd, so seven cars finish again and p4 is seventh on its 83rd (sixth before); p6, p7, p8, p1 and p3 finish as before and p5 is still the car running at the end, after 82 moves -- recorded, not vetoed (AGENTS.md).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); seven finishers and no crash as before, but p4 (seventh home before, on its 83rd move) now finishes fifth on its 82nd and p3 (fifth before, on its 82nd) seventh on its 84th; p6, p7, p8, p1 and p2 finish as before and p5 is still the car running at the end, after 83 moves (82 before) -- recorded, not vetoed (AGENTS.md).
    (6, 78),
    (7, 79),
    (8, 80),
    (1, 82),
    (4, 82),
    (2, 83),
    (3, 84),
]
LEGACY_ALL_MOVES = {1: 88, 2: 87, 3: 79, 4: 80, 5: 81, 6: 84, 7: 84, 8: 86}
# Round 278: re-frozen from measurement (the chooser's pick stands).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
# Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
# Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
# Round 310: re-frozen from measurement (the danger-joint-search family deleted); p2's 27 moves end in its crash and p3 is one move faster (83 -> 82).
# Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); p2 no longer crashes and takes 83 moves to its finish (27 -> 83); every other car's count is unchanged.
# Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); p3 takes 84 moves to its finish (82 -> 84), p4 82 (83 -> 82) and p5, still running at the end, makes 83 (82 -> 83); every other car's count is unchanged.
PROMOTED_ALL_MOVES = {1: 82, 2: 83, 3: 84, 4: 82, 5: 83, 6: 78, 7: 79, 8: 80}
# Round 247: re-frozen from measurement (the soft rollout at one level, not two).
# Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
# Round 278: re-frozen from measurement (the chooser's pick stands).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
# Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
# Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
# Round 310: re-frozen from measurement (the danger-joint-search family deleted); identical to the round-305/309 race through turn 169, the first change is p2's 22nd move at turn 170.
# Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); the race differs from the round-310 race from turn 4 on, p4's first move from its start cell (NW instead of N).
# Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); the race differs from the round-316 race from turn 12 on, p4's second move (NE instead of E).
PROMOTED_SHA256 = "78377294e7dbdc310c560db457459ee0c76836304bfec0d7539a64f83ebcb185"
PROMOTED_DECISION = (
    # Round 229: re-frozen from measurement (the soft caution stack left the score).
    # Round 233: re-frozen from measurement (the lane spread left the score).
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 276: the same turn and car, re-frozen from measurement.
    # Round 278: the same turn and car, re-frozen from measurement.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); the same turn and car.
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds); the same turn and car.
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); the same turn and car.
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); the same turn and car.
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); the same turn and car and the same NW acceleration, now from v(0,8) at (101,133) -- round 281's line again.
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); the same turn and car and the same NW acceleration, now from v(1,8) at (104,132) -- round 278's line again.
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); the same turn and car and the same NW acceleration, now from v(0,8) at (101,133) -- round 305/309's line again, which round 310 kept.
    "201 p1 {kind} NW v(0,8)→(-1,7) (101,133)→(100,140) ok"
)

# These cases cover every redistribution or slowdown exposed by the historical
# broad six-ahead arm. The final candidate-speed and gain band must leave each
# complete trajectory equal to the champion.
# Round 247 (the soft rollout at one level, not two): every case re-frozen
# from measurement; Silverstone s78 gets its seventh finisher back.
# Round 248 (the physical world model): Spa s27 loses a car; four cases
# re-frozen from measurement.
# Round 260: re-frozen from measurement (the faithful joint world as a chooser).
VETO_CASES = {
    ("spa", 27): (
        # Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); p1 (the car still running at the end before, after 83 moves) now crashes on its 31st move, at turn 241 ((98,155)→(95,158)), and seven finishers become six; p4 (third home before, on its 81st) is now the car still running at the end, after 82 moves, so p5, p6 and p7 each finish one place higher on the same own move (third and fourth on their 81st, fifth on its 82nd) and p8 sixth on its 82nd (seventh on its 83rd before); p2 and p3 finish as before -- recorded, not vetoed (AGENTS.md).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); still six finishers and one crash, but a different car crashes: p1 no longer crashes on its 31st move (turn 241, now (88,160)→(84,162) ok) and finishes sixth on its 83rd, and p5 (third home before, on its 81st) now crashes on its 47th, at turn 373 ((76,108)→(73,104)); p4 (the car still running at the end before, after 82 moves) now finishes third on its 81st and p8 (sixth home before, on its 82nd) is the car still running at the end, after 82 moves; p7 now finishes fourth on its 81st (fifth on its 82nd before) and p6 fifth on its 82nd (fourth on its 81st before); p2 and p3 finish as before -- recorded, not vetoed (AGENTS.md).
        (6, 1, [79, 80, 81, 81, 82, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); the same classification as before, a different trajectory: every car finishes in the same place on the same own move and p1 is still the car running at the end, after 83 moves.
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted); the same classification as before, a different trajectory: every car finishes in the same place on the same own move and p1 is still the car running at the end, after 83 moves.
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
        "d9c1d8f33cd2ba0891975329cf921d67a3a45827c93abd20d841199a5e6e7bf4",
    ),
    ("spa", 57): (
        # Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); seven finishers and no crash as before, but p3 (fourth home before, on its 81st move) now finishes seventh on its 84th, p2 fourth on its 81st (fifth on its 82nd before) and p4 fifth on its 81st (seventh on its 83rd before); p6, p8, p1 and p7 finish as before and p5 is still the car running at the end, after 83 moves (82 before) -- recorded, not vetoed (AGENTS.md).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted); seven finishers and no crash as before, but p4 now finishes fourth on its 81st move (fifth on its 81st before), p2 fifth on its 82nd (fourth on its 81st before), p3 sixth on its 82nd (seventh on its 84th before) and p7 seventh on its 82nd (sixth before); p6, p8 and p1 finish as before and p5 is still the car running at the end, after 82 moves (83 before) -- recorded, not vetoed (AGENTS.md).
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); seven finishers and no crash as before, but p5 (the car still running at the end before, after 82 moves) now finishes fourth on its 82nd and p7 (seventh home before, on its 82nd) is the car still running at the end, after 83 moves; p1 now finishes second on its 80th (third on its 81st before), p3 third on its 81st (sixth on its 82nd before), p8 fifth on its 82nd (second on its 79th before), p2 sixth on its 83rd (fifth on its 82nd before) and p4 seventh on its 84th (fourth on its 81st before); p6 still wins on its 78th -- recorded, not vetoed (AGENTS.md).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); seven finishers and no crash as before, but p7 (the car still running at the end before, after 83 moves) now finishes seventh on its 83rd and p8 (fifth home before, on its 82nd) is the car still running at the end, after 82 moves; p2 now finishes third on its 81st (sixth on its 83rd before), p3 fourth on its 81st (third before), p4 fifth on its 82nd (seventh on its 84th before) and p5 sixth on its 82nd (fourth before); p6 and p1 finish as before -- recorded, not vetoed (AGENTS.md).
        (7, 0, [78, 80, 81, 81, 82, 82, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
        "0047402d75532d1c91d61543b26dd4ea5ecab0f02dbcb695738bc1b0d746cb5d",
    ),
    ("spa", 12): (
        # Round 254: re-frozen from measurement (the danger guard in a faithful world).
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted); seven finishers and no crash as before, but p1 (the car still running at the end before, after 83 moves) now finishes fifth on its 82nd move and p4 (seventh home before, on its 83rd) is the car still running at the end, after 82 moves; p3 and p5 now finish sixth and seventh, both on their 82nd (fifth and sixth before); p6, p7, p8 and p2 finish as before -- recorded, not vetoed (AGENTS.md).
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); seven finishers and no crash as before, but p4 (the car still running at the end before, after 82 moves) now finishes fourth on its 81st and p5 (seventh home before, on its 82nd) is the car still running at the end, after 82 moves; p6 still wins, one move later, on its 79th; p3 now finishes second on its 80th (sixth on its 82nd before), p7 third on its 80th (second on its 79th before), p8 fifth on its 81st (third on its 80th before), p1 sixth on its 83rd (fifth on its 82nd before) and p2 seventh on its 83rd (fourth on its 81st before) -- recorded, not vetoed (AGENTS.md).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); p5 (the car still running at the end before, after 82 moves) now crashes on its 29th move, at turn 229 ((98,154)→(95,158)), and seven finishers become six; p4 (fourth home before, on its 81st) is now the car still running at the end, after 82 moves; p2 (seventh home before, on its 83rd) now wins on its 78th, p3 is still second, now on its 79th (80th before), p6 (the winner before, on its 79th) third on its 80th, p7 fourth on its 81st (third on its 80th before), p1 fifth on its 82nd (sixth on its 83rd before) and p8 sixth on its 82nd (fifth on its 81st before) -- recorded, not vetoed (AGENTS.md).
        (6, 1, [78, 79, 80, 81, 82, 82]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); the same summary, a different classification: p1 (fourth home before, on its 81st move) is now the car still running at the end, after 83 moves, and p5 (that car before, after 82) finishes sixth on its 82nd; p2 now finishes fourth on its 81st, p3 fifth on its 82nd and p4 seventh on its 83rd (fifth, seventh and sixth before) -- recorded, not vetoed (AGENTS.md).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
        "08d6010daf4f1fd2aff5807f68e268a908d9c00fd4df700cf90672459d74909c",
    ),
    ("spa", 31): (
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p4 no longer crashes on its 58th move and p3 now finishes seventh: six finishers become seven, p4 the car still running at the end.
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); seven finishers as before and p4 still the car running at the end, but p3 now finishes sixth on its 83rd move.
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); seven finishers and no crash as before, but p4 (the car still running at the end before) now finishes sixth on its 82nd move and p5 (seventh home before) is the car still running at the end, after 83 moves; p3 now finishes fifth on its 82nd move and p8 (third before) seventh on its 83rd -- recorded, not vetoed.
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); seven finishers and no crash as before, but p5 (the car still running at the end before, after 83 moves) now finishes fourth on its 81st move and p4 (sixth home before, on its 82nd) is the car still running at the end, after 82 moves; p8 (seventh before, on its 83rd) now finishes third on its 80th, and p1, p2 and p3 (third, fourth and fifth before) fifth, sixth and seventh on their 82nd, 83rd and 83rd -- recorded, not vetoed (AGENTS.md).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted); seven finishers and no crash as before, but p1 now finishes fourth on its 81st move (fifth on its 82nd before), p2 fifth on its 82nd (sixth on its 83rd before) and p5 (fourth before, on its 81st) sixth on its 82nd; p6, p7, p8 and p3 finish as before and p4 is still the car running at the end, after 82 moves -- recorded, not vetoed (AGENTS.md).
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); seven finishers and no crash as before, but p7 (second home before, on its 79th move) is now the car still running at the end, after 83 moves, and p4 (that car before, after 82) finishes seventh on its 84th; p8 now finishes second on its 79th (third on its 80th before), p5 third on its 81st (sixth on its 82nd before), p1 fourth on its 82nd (81st before), p2 fifth on its 83rd (82nd before) and p3 sixth on its 83rd (seventh before); p6 still wins on its 78th -- recorded, not vetoed (AGENTS.md).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); seven finishers and no crash as before, but p7 (the car still running at the end before, after 83 moves) now finishes second on its 79th and p3 (sixth home before, on its 83rd) is the car still running at the end, after 83 moves; p8 now finishes third on its 80th (second on its 79th before), p5 fifth on its 82nd (third on its 81st before), p2 sixth on its 83rd (fifth before) and p4 seventh on its 83rd (84th before); p6 and p1 finish as before -- recorded, not vetoed (AGENTS.md).
        (7, 0, [78, 79, 80, 82, 82, 83, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
        "0e49cfef8c965a0319b957adf817c849d7a9965070c360b1afb4f7f27af4c851",
    ),
    ("spa", 40): (
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); seven finishers and no crash as before, but p2 (second home before, on its 79th move) is now the car still running at the end, after 83 moves, and p8 (that car before, after 81) finishes seventh on its 83rd; p3, p4, p5, p6 and p7 each finish one place higher, p3 second on its 79th and p4 third on its 80th (each one move sooner), and p5 fourth on its 81st, p6 fifth and p7 sixth on their 82nd (each on the same own move as before); p1 still wins on its 78th -- recorded, not vetoed (AGENTS.md).
        (7, 0, [78, 79, 80, 81, 82, 82, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); the same classification as before, a different trajectory: every car finishes in the same place on the same own move and p8 is still the car running at the end, after 81 moves.
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted); the same classification as before, a different trajectory: every car finishes in the same place on the same own move and p8 is still the car running at the end, after 81 moves.
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); the same classification as before, a different trajectory: every car finishes in the same place on the same own move and p2 is still the car running at the end, after 83 moves; the race differs from the round-316 race from turn 6 on, p6's first move from its start cell (NE instead of NONE).
        "c72f14cea7eb66f15f7c0aa8124248d1faa86df8e101e984a76f0e6b0a1e4015",
    ),
    ("spa", 47): (
        # Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); seven finishers and no crash as before, but p6 (the car still running at the end before, after 83 moves) now finishes second on its 80th move and p4 (fifth home before, on its 82nd) is the car still running at the end, after 82 moves; p8 still wins, one move later, on its 79th; p1, p2 and p3 (second, third and fourth before) now finish third, fourth and seventh on their 81st, 82nd and 83rd, p5 fifth and p7 sixth, both on their 82nd (sixth on its 82nd and seventh on its 83rd before) -- recorded, not vetoed (AGENTS.md).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted); seven finishers and no crash as before, but p6 (second home before, on its 80th move) is now the car still running at the end, after 82 moves, and p4 (that car before, after 82) finishes seventh on its 83rd; p1 now finishes second on its 81st (third before), p7 (sixth before, on its 82nd) third on its 81st and p3 sixth on its 83rd (seventh before); p8, p2 and p5 finish as before -- recorded, not vetoed (AGENTS.md).
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); p3 (sixth home before, on its 83rd move) now crashes on its 26th, at turn 203 ((104,134)→(104,141)), and seven finishers become six; p6 (the car still running at the end before, after 82 moves) now finishes fourth on its 81st and p5 (fifth home before, on its 82nd) is the car still running at the end, after 82 moves; p8 still wins, one move sooner, on its 78th, and p1 is still second, on its 80th (81st before); p2 now finishes third on its 81st (fourth on its 82nd before), p4 fifth on its 82nd (seventh on its 83rd before) and p7 sixth on its 82nd (third on its 81st before) -- recorded, not vetoed (AGENTS.md).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); p3 no longer crashes on its 26th move (turn 203, now (102,136)→(101,143) ok) and finishes seventh on its 83rd: six finishers become seven again, as before round 316; p5 (the car still running at the end before, after 82 moves) now finishes fifth on its 82nd and p7 (sixth home before, on its 82nd) is the car still running at the end, after 82 moves; p4 now finishes third on its 81st (fifth on its 82nd before), p2 fourth on its 82nd (third on its 81st before) and p6 sixth on its 82nd (fourth on its 81st before); p8 and p1 finish as before -- recorded, not vetoed (AGENTS.md).
        (7, 0, [78, 80, 81, 82, 82, 82, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
        "73f789cba30419738cfd1201d907806774b68709f9a9ca8825f6eb53b6a2b1b1",
    ),
    ("coil", 5): (
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); seven finishers and no crash as before, but p8 (the car still running at the end before, after 60 moves) now finishes fifth on its 60th and p5 (sixth home before, on its 60th) is the car still running at the end, after 62 moves; p1 still wins on its 58th, p2 is now second on its 59th (fourth on its 60th before), p4 third on its 60th (second on its 59th before), p7 fourth on its 60th (seventh on its 61st before), p3 sixth on its 61st (fifth on its 60th before) and p6 seventh on its 62nd (third on its 59th before) -- recorded, not vetoed (AGENTS.md).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); seven finishers and no crash as before, but p5 (the car still running at the end before, after 62 moves) now finishes fifth on its 60th and p8 (fifth home before, on its 60th) is the car still running at the end, after 59 moves; p3 now finishes third on its 59th (sixth on its 61st before), p4 fourth on its 59th (third on its 60th before), p6 sixth on its 60th (seventh on its 62nd before) and p7 seventh on its 60th (fourth before); p1 and p2 finish as before -- recorded, not vetoed (AGENTS.md).
        (7, 0, [58, 59, 59, 59, 60, 60, 60]),
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); the all-AI1 and alternating races of ai1_label_invariance_regression, which takes this digest as its reference, measured it too.
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); the same summary, a different classification: p8 (sixth home before, on its 60th move) is now the car still running at the end, after 60 moves, and p7 (that car before) finishes seventh on its 61st; p1 still wins on its 58th, p6 (seventh before, on its 61st) now finishes third on its 59th and p2 (second before, on its 59th) fourth on its 60th, and p4, p3 and p5 (third, fourth and fifth before) second, fifth and sixth on their 59th, 60th and 60th as before -- recorded, not vetoed (AGENTS.md). The all-AI1 and alternating races of ai1_label_invariance_regression, which takes this digest as its reference, measured it too.
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); the all-AI1 and alternating races of ai1_label_invariance_regression, which takes this digest as its reference, measured it too.
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); the all-AI1 and alternating races of ai1_label_invariance_regression, which takes this digest as its reference, measured it too.
        "3c01a139194babae1b89fc743e0d1cf1cf463a637f23feefd751b0bd8561ba85",
    ),
    ("coil", 22): (
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); seven finishers and no crash as before, every car in the same place, but two finishers each one move slower: p4 still finishes fourth, now on its 60th move (59th before), and p7 still seventh, now on its 61st (60th before); p8 is still the car running at the end, after 60 moves (59 before); the race is the round-310 race through turn 57, the first change is p2's 8th move at turn 58 -- recorded, not vetoed (AGENTS.md).
        (7, 0, [58, 59, 59, 60, 60, 60, 61]),
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); the same summary, but p7 (the car still running at the end before, after 60 moves) now finishes seventh on its 60th and p8 (seventh home before, on its 60th) is the car still running at the end, after 59 moves -- recorded, not vetoed (AGENTS.md).
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); the same classification as before, a different trajectory: every car finishes in the same place on the same own move and p8 is still the car running at the end, after 60 moves; the race is the round-316 race through turn 69, the first change is p6's 9th move at turn 70 (NONE instead of W).
        "919c06c634693f889c0221ef6f05e58108d7f50a0fe7861b9cdee0e93489adac",
    ),
    ("silverstone", 78): (
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p8 now crashes on its 11th move and seven finishers become six, p6 (sixth home before) the car still running at the end -- recorded, not vetoed.
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); p8 no longer crashes on its 11th move and finishes seventh on its 85th: six finishers become seven again, as before round 281; p6 (the car still running at the end before, after 84 moves) now finishes fifth on its 84th, p7 sixth on its 84th as before, and p5 (fifth home before, on its 84th) is the car still running at the end, after 85 moves -- recorded, not vetoed (AGENTS.md).
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); seven finishers and no crash as before, but p8 (the car still running at the end before, after 84 moves) now finishes fifth on its 84th and p7 (seventh home before, on its 85th) is the car still running at the end, after 85 moves; p5 now finishes sixth on its 85th (fifth on its 84th before) and p6 seventh on its 86th (sixth on its 84th before); p1 to p4 finish as before -- recorded, not vetoed (AGENTS.md).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); p5 (sixth home before, on its 85th move) now crashes on its 75th, at turn 597 ((30,31)→(25,31)), and seven finishers become six; p7 (the car still running at the end before, after 85 moves) now finishes sixth on its 85th and p6 (seventh home before, on its 86th) is the car still running at the end, after 85 moves; p1, p2 and p4 keep their places one move later (first on its 82nd, second on its 83rd, fourth on its 84th), and p3 and p8 finish as before -- recorded, not vetoed (AGENTS.md).
        (6, 1, [82, 83, 83, 84, 84, 85]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds); p8 still crashes on its 11th move and six cars finish, but p6 finishes sixth again and p7 is now the car still running at the end -- recorded, not vetoed.
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); p8 still crashes on its 11th move and six cars finish, but p7 finishes sixth again on its 84th move and p6 is now the car still running at the end, after 84 moves -- recorded, not vetoed.
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); the same classification as before, a different trajectory: p8 still crashes on its 11th move, p7 still finishes sixth on its 84th and p6 is still the car running at the end, after 84 moves -- recorded, not vetoed.
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted); the same summary, a different classification: p5 (the car still running at the end before, after 85 moves) now finishes fifth on its 84th, p6 sixth on its 84th (fifth before) and p7 seventh on its 85th (sixth on its 84th before), and p8 (seventh home before, on its 85th) is the car still running at the end, after 84 moves; p1 to p4 finish as before -- recorded, not vetoed (AGENTS.md).
        # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
        # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
        "bb6eef3d7660a0f66edaff7f51474df66c78444423ab67aaeb7fdd50eae08dee",
    ),
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    cases = [TARGET, *VETO_CASES]
    with tempfile.TemporaryDirectory(prefix="six-ahead-high-speed-regression-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["silverstone", "spa"]))  # frozen pre-repair geometry
        bench_ai.set_nplayers(8)
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            for track, seed in cases:
                summary = bench_ai.run_track(
                    track, timeout=1200, seed=seed
                )
                if summary is None:
                    raise SystemExit(
                        f"six-ahead high-speed {track} seed-{seed} {kind} race failed"
                    )
                log_path = Path(bench_ai.LOG)
                if not log_path.is_file():
                    raise SystemExit(
                        f"six-ahead high-speed {track} seed-{seed} {kind} log missing"
                    )
                summaries[(kind, track, seed)] = summary
                logs[(kind, track, seed)] = log_path.read_text(
                    encoding="utf-8"
                )

    for kind in LABELS:
        target_log = logs[(kind, *TARGET)]
        actual = summaries[(kind, *TARGET)]
        if actual != PROMOTED:
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} regression: "
                f"{actual}, expected {PROMOTED}"
            )
        if finishers(target_log) != PROMOTED_FINISHERS:
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} finisher regression: "
                f"{finishers(target_log)}, expected {PROMOTED_FINISHERS}"
            )
        moves = player_moves(target_log)
        if moves != PROMOTED_ALL_MOVES:
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} move regression: "
                f"{moves}, expected {PROMOTED_ALL_MOVES}"
            )
        # Round 233: the round-117 per-car Pareto contract against the legacy
        # champion is retired -- the policy is judged by head-to-head places
        # (AGENTS.md), and with the lane spread out of the score three cars in
        # this race are slower than the legacy car while the field is faster
        # overall. The measured summary, finisher list, move counts, digest and
        # decision line below all still have to hold.
        deltas = [moves[player] - LEGACY_ALL_MOVES[player] for player in sorted(moves)]
        if not any(delta < 0 for delta in deltas):
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} lost every gain "
                f"over {LEGACY}: {deltas}"
            )
        decision = PROMOTED_DECISION.format(kind=kind)
        if decision not in target_log.splitlines():
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} decision missing: {decision}"
            )
        digest = normalized_sha256(target_log)
        if digest != PROMOTED_SHA256:
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} trajectory regression: "
                f"{digest}, expected {PROMOTED_SHA256}"
            )

    for (track, seed), (expected, expected_digest) in VETO_CASES.items():
        for kind in LABELS:
            actual = summaries[(kind, track, seed)]
            if actual != expected:
                raise SystemExit(
                    f"six-ahead high-speed {track} seed-{seed} {kind} veto regression: "
                    f"{actual}, expected {expected}"
                )
            digest = normalized_sha256(logs[(kind, track, seed)])
            if digest != expected_digest:
                raise SystemExit(
                    f"six-ahead high-speed {track} seed-{seed} {kind} champion "
                    f"trajectory regression: {digest}, expected {expected_digest}"
                )

    print(
        "AI1SixAheadHighSpeedRegression: OK "
        "(Spa s83 finisher -2/all-driver -3; "
        "nine veto/retention controls pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
