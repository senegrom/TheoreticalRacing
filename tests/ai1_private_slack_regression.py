#!/usr/bin/env python3
"""Pin the exact-private score-slack pace frontier and its identity vetoes."""

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

HUNGARORING_SEED = 12
# Round 228: re-frozen from complete recorded races after removing the
# narrow-lane distance surcharge: seven finishers and no crashes in every case.
# Round 231: re-frozen from recorded checkpoint-choice races; the existing
# assertion logic and AI1/AI2 identity checks remain intact.
# Every case below retains seven finishers and zero crashes.
# Round 233 (the lane spread left the score, -0.65 places): every case
# re-frozen from measurement; Hungaroring s40 is whole again (seven
# finishers, no crash), Le Mans s2 still loses p4.
# Round 229 (the soft caution stack left the score, -0.82 places head-to-head):
# every case re-frozen from measurement (E:/tmp-claude/refreeze_survey.py slack).
# Hungaroring s40 now has six finishers and p8 crashes on its 33rd move, under
# both labels -- recorded, not vetoed (AGENTS.md); the other cases keep seven
# finishers and no crashes.
# Round 232 (the kinematic confirm): re-frozen from measurement. Le Mans s2 and
# Monaco s35 lose a car here (p1 dies alone at Le Mans, p1 on its 60th move at
# Monaco) while the fleet cuts crashes by two fifths in the same races and the
# bounded-field Le Mans s29 pin gets its seventh finisher back; recorded, not
# vetoed (AGENTS.md).
# Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
# Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
# Round 248 (the physical world model): re-frozen from measurement; p2 crashes
# on its 30th move -- recorded, not vetoed.
# Round 260 (the faithful joint world as a chooser): Hungaroring s12 is
# whole again -- p2 no longer dies on its 30th move, seven finishers.
# Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds); p2 crashes again, now on its 28th move (six finishers) -- recorded, not vetoed.
# Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); a car that crashed there now finishes (p2, lost on its 28th move since round 292b, is seventh on its 129th move).
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
# Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); p2 crashes again (seventh home before, on its 128th move), now on its 45th, at turn 354 ((59,117)->(61,118)), and seven finishers become six: p1 (sixth before, on its 127th) now finishes fifth on its 126th and p8 (fifth before, on its 125th) sixth on its 127th; p3, p4, p6 and p7 finish as before and p5 is still the car running at the end, after 127 moves -- recorded, not vetoed (AGENTS.md).
# Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); six finishers and one crash as before, but p8 (sixth before, on its 127th move) now finishes fifth on its 125th and p1 (fifth before, on its 126th) sixth on its 127th -- the first six of rounds 303 to 310 again, each on the same own move; p2 still crashes on its 45th, at turn 354 ((59,117)->(61,118)), p3, p4, p6 and p7 finish as before and p5 is still the car running at the end, after 126 moves (127 before) -- recorded, not vetoed (AGENTS.md).
# Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves); Hungaroring s12 is whole again (a car short since round 316): p2, lost on its 45th move since round 316, now finishes seventh on its 128th, so six finishers become seven; p5 is still the car running at the end, after 127 moves (126 before), and p1, p3, p4, p6, p7 and p8 finish as before -- the whole classification of rounds 303 to 310 again, each car on the same own move, on a new trajectory (the race leaves round 328's at p6's 2nd move, turn 14); recorded, not vetoed (AGENTS.md).
# Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too); Hungaroring s12 loses a car again (whole since round 329): p5 (the car still running at the end before, after 127 moves) now crashes on its 46th move, at turn 365 ((60,117)->(62,118)) -- one cell east of p2's crash in rounds 316 to 328 (on its 45th, at turn 354 ((59,117)->(61,118))), at the same velocity -- and seven finishers become six; p2 (seventh home before, on its 128th) is the car still running at the end, after 126 moves, and p1, p3, p4, p6, p7 and p8 finish as before -- the six finishers of rounds 326 and 328 again, each in the same place on the same own move, but the car lost is now p5 (p2 then, on its 45th) and the car running at the end p2 (p5 then, after 126 moves), on a new trajectory (the race leaves round 329's at p2's 1st move, turn 2); recorded, not vetoed (AGENTS.md).
HUNGARORING_PROMOTED = (6, 1, [121, 122, 123, 124, 125, 127])
HUNGARORING_PROMOTED_FINISHERS = [(3, 121), (4, 122), (6, 123), (7, 124), (8, 125), (1, 127)]
HUNGARORING_ALL_MOVES = {
    "AI2": {1: 127, 2: 126, 3: 121, 4: 122, 5: 46, 6: 123, 7: 124, 8: 125},
}
HUNGARORING_NORMALIZED_SHA256 = (
    # Round 237: re-frozen from measurement (every car takes the two-move duel proof).
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 248: re-frozen from measurement (the physical world model).
    # Round 254: re-frozen from measurement (the danger guard in a faithful world).
    # Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); the same classification as before, a different trajectory from p8's 7th move at turn 56: every car finishes in the same place on the same own move, p2 still crashes on its 45th, at turn 354 ((59,117)->(61,118)), and p5 is still the car running at the end, after 126 moves.
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
    'f5202993f68a018a7403b1d1bf645058fc43cd05f9a4fa510ab0e6ee86817ad5'
)

# Each case pins one false-positive class from the broader score-slack screens:
# identity swap, order redistribution, coasting, far-TTF field drift, braking,
# short-phase overlap, distant-field drift, high-energy redistribution, and a
# steering-reversal finisher swap. The final rule must leave every complete
# trajectory equal to the current champion.
# Round 260: re-frozen from measurement (the faithful joint world as a chooser).
VETO_CASES = {
    # Round 226 (the needle tie-break): re-frozen from measurement.
    # Round 254 (the danger guard in a faithful world): Le Mans s2 loses a
    # car, Hungaroring s40 is whole again; four cases re-frozen from measurement.
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 296 (landings priced with the checkpoints they collect paid): Le Mans s2
    # keeps the car it has lost since round 254 and Interlagos s47 loses one (p2 on
    # its 57th move); six cases re-frozen from measurement -- recorded, not vetoed
    # (AGENTS.md).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); Spa s1 loses a car (p7 now crashes on its 28th move) -- recorded, not vetoed.
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted); seven finishers and no crash as before, but p5 now finishes fourth on its 69th move (fifth on its 71st before), p6 fifth on its 70th (sixth on its 72nd before), p8 (fourth before, on its 69th) sixth on its 70th and p7 seventh on its 71st (73rd before); p2, p3 and p4 finish as before and p1 is still the car running at the end, after 71 moves (73 before) -- the round-303 classification again, on a new trajectory; recorded, not vetoed (AGENTS.md).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); seven finishers and no crash as before, but p8 (sixth before, on its 70th move) now finishes fourth on its 69th, p5 (fourth before, on its 69th) fifth on its 71st, p6 (fifth before, on its 70th) sixth on its 72nd and p7 seventh on its 72nd (71st before); p2, p3 and p4 finish as before and p1 is still the car running at the end, after 72 moves (71 before) -- the round-305/309 finishing order again, on a new trajectory (p7 then finished on its 73rd and p1 ran 73 moves); recorded, not vetoed (AGENTS.md).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); Le Mans s2 loses a car (whole since round 296): p7 (seventh home before, on its 72nd move) now crashes on its 54th, at turn 431 ((21,136)->(18,132)), and seven finishers become six; p8 now finishes fourth on its 68th (69th before), p5 fifth on its 69th (71st before) and p6 sixth on its 70th (72nd before); p2, p3 and p4 finish as before and p1 is still the car running at the end, after 70 moves (72 before) -- recorded, not vetoed (AGENTS.md).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); Le Mans s2 is whole again (a car short since round 326): p7, lost on its 54th move in round 326, is the car still running at the end, after 71 moves, and p1 (the car still running at the end before, after 70 moves) finishes seventh on its 72nd, so seven finishers again; p5 (fifth before, on its 69th) now finishes fourth on its 69th and p8 (fourth before, on its 68th) fifth on its 69th; p2, p3, p4 and p6 finish as before -- recorded, not vetoed (AGENTS.md).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves); seven finishers and no crash as before, but p7 (the car still running at the end before, after 71 moves) now finishes seventh on its 71st and p1 (seventh before, on its 72nd) is the car still running at the end, after 71 moves; p2, p3, p4, p5, p6 and p8 finish as before -- recorded, not vetoed (AGENTS.md).
    ("lemans", 2): (7, 0, [66, 67, 68, 69, 69, 70, 71]),
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds); a car that crashed there now finishes (p7, lost on its 28th move since round 281, is sixth on its 82nd move).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted); seven finishers and no crash as before, but p6 now finishes fifth on its 81st move (82nd before) and p7 (the car still running at the end before, after 82 moves) sixth on its 82nd, and p8 (sixth home before, on its 82nd) is the car still running at the end, after 82 moves; p1, p3, p4, p5 and p2 finish as before -- recorded, not vetoed (AGENTS.md).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); seven finishers and no crash as before, but p5 (fourth before, on its 81st move) now finishes third on its 80th, p6 fourth on its 81st (fifth before, on its 81st), p7 fifth on its 81st (sixth on its 82nd before), p8 (the car still running at the end before, after 82 moves) sixth on its 82nd and p2 seventh on its 84th (83rd before); p4 (third before, on its 80th) is the car still running at the end, after 83 moves, and p1 and p3 finish as before -- recorded, not vetoed (AGENTS.md).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); seven finishers and no crash as before, but p4 (the car still running at the end before, after 83 moves) now finishes third on its 80th, p5 fourth on its 81st (third on its 80th before), p6 fifth on its 82nd (fourth on its 81st before), p7 sixth on its 82nd (fifth on its 81st before) and p8 seventh on its 83rd (sixth on its 82nd before); p2 (seventh home before, on its 84th) is the car still running at the end, after 83 moves, and p1 and p3 finish as before -- recorded, not vetoed (AGENTS.md).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); seven finishers and no crash as before, but p6 (fifth before, on its 82nd move) now finishes fourth on its 81st, p5 (fourth before, on its 81st) fifth on its 82nd and p8 seventh on its 82nd (83rd before); p1, p3, p4 and p7 finish as before and p2 is still the car running at the end, after 82 moves (83 before) -- recorded, not vetoed (AGENTS.md).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves); seven finishers and no crash as before, but p5 (fifth before, on its 82nd move) now finishes fourth on its 81st, p6 (fourth before, on its 81st) fifth on its 81st, p8 (seventh before, on its 82nd) sixth on its 82nd and p2 (the car still running at the end before, after 82 moves) seventh on its 83rd; p7 (sixth before, on its 82nd) is the car still running at the end, after 82 moves, and p1, p3 and p4 finish as before -- the round-310 summary again (p7 then sixth on its 82nd and p8 the car running at the end, after 82 moves); recorded, not vetoed (AGENTS.md).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too); seven finishers and no crash as before, but p6 (fifth before, on its 81st move) now finishes fourth on its 81st, p5 (fourth before, on its 81st) fifth on its 82nd and p7 (the car still running at the end before, after 82 moves) sixth on its 82nd; p8 (sixth before, on its 82nd) is the car still running at the end, after 82 moves, and p1, p2, p3 and p4 finish as before -- the round-326 summary again, from a different classification; recorded, not vetoed (AGENTS.md).
    ("spa", 1): (7, 0, [78, 79, 80, 81, 82, 82, 83]),
    # Round 234: re-frozen from measurement (the seal guard left the decision).
    # Round 247 (the soft rollout at one level, not two): every case below
    # re-frozen from measurement. Hungaroring s40 is whole again; Zandvoort
    # s34 loses a car. Recorded, not vetoed (AGENTS.md).
    # Round 248 (the physical world model): Hungaroring s40 loses a car again
    # and Zandvoort s34 is whole again; six cases re-frozen from measurement.
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); seven finishers and no crash as before, but p6 (the car still running at the end before, after 127 moves) now finishes fourth on its 124th, p7 fifth on its 125th (fourth on its 124th before), p8 sixth on its 126th (fifth on its 125th before) and p2 seventh on its 128th (sixth on its 127th before); p3 (seventh home before, on its 128th) is the car still running at the end, after 127 moves, and p1, p4 and p5 finish as before -- recorded, not vetoed (AGENTS.md).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); Hungaroring s40 loses a car (whole since round 254): p3 (the car still running at the end before, after 127 moves) now crashes on its 45th move, at turn 355 ((59,117)->(61,118)) -- the cells, velocity and own move of p2's crash in the seed-12 race -- and seven finishers become six; p2 (seventh home before, on its 128th) is the car still running at the end, after 126 moves, and p1, p4, p5, p6, p7 and p8 finish as before -- recorded, not vetoed (AGENTS.md).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); Hungaroring s40 is whole again (a car short since round 326): p3, lost on its 45th move in round 326, is the car still running at the end, after 127 moves, and p2 (the car still running at the end before, after 126 moves) finishes seventh on its 128th, so seven finishers again; p1, p4, p5, p6, p7 and p8 finish as before -- the round-316 classification again, on a new trajectory; recorded, not vetoed (AGENTS.md).
    ("hungaroring", 40): (7, 0, [121, 122, 123, 124, 125, 126, 128]),
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); a car that crashed there now finishes (p2, lost on its 57th move since round 296, is second on its 125th move).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted); seven finishers and no crash as before, but p1 to p7 now finish in number order: p2 (seventh home before, on its 131st move) second on its 125th, p3 (the car still running at the end before, after 130 moves) third on its 126th, and p4, p5, p6 and p7 (second to fifth before, on their 125th to 128th) fourth to seventh on their 127th, 128th, 129th and 129th; p8 (sixth before, on its 129th) is the car still running at the end, after 128 moves, and p1 still wins on its 124th -- recorded, not vetoed (AGENTS.md).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); seven finishers and no crash as before, but p4, p5 and p6 (fourth to sixth before, on their 127th to 129th) now finish second to fourth on their 125th, 126th and 127th, p8 (the car still running at the end before, after 128 moves) fifth on its 128th, p2 (second before, on its 125th) sixth on its 130th and p3 (third before, on its 126th) seventh on its 131st; p7 (seventh home before, on its 129th) is the car still running at the end, after 130 moves, and p1 still wins on its 124th -- recorded, not vetoed (AGENTS.md).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); seven finishers and no crash as before, but p7 (the car still running at the end before, after 130 moves) now finishes fifth on its 128th, p8 sixth on its 129th (fifth on its 128th before) and p2 seventh on its 131st (sixth on its 130th before); p3 (seventh home before, on its 131st) is the car still running at the end, after 130 moves, and p1, p4, p5 and p6 finish as before -- the round-305/309 classification again, on a new trajectory; recorded, not vetoed (AGENTS.md).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); seven finishers and no crash as before, but p3 (the car still running at the end before, after 130 moves) now finishes seventh on its 130th and p2 (seventh home before, on its 131st) is the car still running at the end, after 130 moves; p1, p4, p5, p6, p7 and p8 finish as before -- recorded, not vetoed (AGENTS.md).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves); Interlagos s47 loses a car (whole since round 281): p2 (the car still running at the end before, after 130 moves) now crashes on its 35th move, at turn 274 ((52,41)->(48,44)), and seven finishers become six; p3 (seventh home before, on its 130th) is the car still running at the end, after 129 moves, and p1, p4, p5, p6, p7 and p8 finish as before -- the round-296 summary again, but p2 now crashes on its 35th move (its 57th then); recorded, not vetoed (AGENTS.md).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too); Interlagos s47 is whole again (a car short since round 329): p2, lost on its 35th move in round 329, now finishes seventh on its 131st, so six finishers become seven; p3 is still the car running at the end, after 130 moves (129 before), and p1, p4, p5, p6, p7 and p8 finish as before -- the round-326 classification again, each car on the same own move, on a new trajectory; recorded, not vetoed (AGENTS.md).
    ("interlagos", 47): (7, 0, [124, 125, 126, 127, 128, 129, 131]),
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); seven finishers and no crash as before, but p6 now finishes fifth on its 80th move (sixth on its 79th before), p7 sixth on its 81st (seventh on its 79th before) and p8 (the car still running at the end before, after 78 moves) seventh on its 81st; p5 (fifth before, on its 79th) is the car still running at the end, after 81 moves, and p1, p2, p3 and p4 finish as before -- recorded, not vetoed (AGENTS.md).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); seven finishers and no crash as before, but p5 (the car still running at the end before, after 81 moves) now finishes fifth on its 79th, p6 sixth on its 79th (fifth on its 80th before) and p7 seventh on its 80th (sixth on its 81st before); p8 (seventh home before, on its 81st) is the car still running at the end, after 79 moves, and p1, p2, p3 and p4 finish as before -- p1 to p7 home in number order again, as in round 316 (p7 then on its 79th); recorded, not vetoed (AGENTS.md).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves); seven finishers and no crash as before, but p7 now finishes seventh on its 79th move (80th before) and p8 is still the car running at the end, after 78 moves (79 before); p1 to p6 finish as before -- the classification of rounds 305/309 to 316 again (p1 to p7 home in number order, p7 on its 79th), on a new trajectory; recorded, not vetoed (AGENTS.md).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too); seven finishers and no crash as before, but p5 (fifth before, on its 79th move) now finishes fourth on its 79th, p6 (sixth before, on its 79th) fifth on its 80th, p4 (fourth before, on its 79th) sixth on its 81st and p7 seventh on its 81st (79th before); p8 is still the car running at the end, after 80 moves (78 before), and p1, p2 and p3 finish as before -- the round-326 summary again, from a different classification; recorded, not vetoed (AGENTS.md).
    ("monza", 30): (7, 0, [77, 78, 79, 79, 80, 81, 81]),
    # Round 224 moved this race: still seven finishers and no crash, but the
    # car that misses out changes (car 7 finished before, car 1 finishes now)
    # and the last five finishers each take a few moves longer.
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p8 now crashes on its 18th move -- recorded, not vetoed.
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout); a car that crashed there now finishes (p6, lost on its 18th move since round 292b, is seventh on its 120th move).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted); seven finishers and no crash as before, but p3, p5, p6 and p7 keep the first four places, each one own move sooner (on their 112th to 115th), p8 (seventh home before, on its 120th) now finishes fifth on its 116th, p1 (the car still running at the end before, after 120 moves) sixth on its 118th and p2 (fifth before, on its 118th) seventh on its 119th, and p4 (sixth before, on its 119th) is the car still running at the end, after 118 moves -- recorded, not vetoed (AGENTS.md).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); seven finishers and no crash as before, but p2 (seventh home before, on its 119th move) now finishes second on its 114th and p4 (the car still running at the end before, after 118 moves) third on its 115th; p5, p6, p7 and p8 (second to fifth before, on their 113th to 116th) finish fourth to seventh, each three own moves later (on their 116th to 119th), and p1 (sixth before, on its 118th) is the car still running at the end, after 119 moves; p3 still wins on its 112th -- recorded, not vetoed (AGENTS.md).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); Monaco s35 loses a car (whole since round 300a): p1 (the car still running at the end before, after 119 moves) now crashes on its 18th move, at turn 137 ((103,5)->(105,1)) -- the own move on which p8 (round 281) and p6 (round 292b) were lost here -- and seven finishers become six; p8 (seventh home before, on its 119th) is the car still running at the end, after 117 moves, and p2, p3, p4, p5, p6 and p7 finish as before -- recorded, not vetoed (AGENTS.md).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves); Monaco s35 loses another car (a car short since round 328): p1, lost on its 18th move in round 328, now finishes fifth on its 117th, but p4 (third before, on its 115th move) now crashes on its 20th, at turn 156 ((108,4)->(109,2)), and p7 (sixth before, on its 118th) on its 20th too, at turn 159 ((106,3)->(107,3)) -- the corner where p1 was lost in round 328 -- so six finishers become five; p5 (fourth before, on its 116th) now finishes second on its 113th, p6 (fifth before, on its 117th) third on its 114th and p8 (the car still running at the end before, after 117 moves) fourth on its 115th; p2 (second before, on its 114th) is the car still running at the end, after 116 moves, and p3 still wins on its 112th -- recorded, not vetoed (AGENTS.md).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too); Monaco s35 gets a car back (two short since round 329): p4, lost on its 20th move in round 329, now finishes sixth on its 118th and p7, lost on its 20th too, is the car still running at the end, after 117 moves, but p1 (fifth before, on its 117th) now crashes on its 69th, at turn 545 ((12,109)->(11,113)), so two crashes become one and five finishers become six; p2 (the car still running at the end before, after 116 moves) now finishes fifth on its 117th, and p3, p5, p6 and p8 finish as before -- recorded, not vetoed (AGENTS.md).
    ("monaco", 35): (6, 1, [112, 113, 114, 115, 117, 118]),
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted); Zandvoort s34 loses a car: p6 (seventh home before, on its 144th move) now crashes on its 33rd, at turn 262 ((51,62)->(48,66)), and seven finishers become six; p7 (the car still running at the end before, after 143 moves) now finishes fifth on its 141st, p8 sixth on its 142nd (fifth on its 141st before), and p1 (sixth home before, on its 143rd) is the car still running at the end, after 142 moves; p2, p3, p4 and p5 finish as before -- recorded, not vetoed (AGENTS.md).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); Zandvoort s34 is whole again: p6, lost on its 33rd move since round 310, is the car still running at the end, after 142 moves, and p1 (the car still running at the end before, after 142 moves) finishes seventh on its 143rd, so seven finishers again; p2, p3, p4, p5, p7 and p8 finish as before -- recorded, not vetoed (AGENTS.md).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); Zandvoort s34 loses a car again (whole since round 316): p6 (the car still running at the end before, after 142 moves) now crashes on its 19th move, at turn 150 ((59,5)->(61,1)), and seven finishers become six; p1 (seventh home before, on its 143rd) is the car still running at the end, after 142 moves, and p2, p3, p4, p5, p7 and p8 finish as before -- the round-310 classification again, but p6 now crashes on its 19th move (its 33rd then); recorded, not vetoed (AGENTS.md).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); Zandvoort s34 is whole again (a car short since round 326): p6, lost on its 19th move in round 326, now finishes third on its 139th, so seven finishers again; p7 (fifth before, on its 141st) finishes fourth on its 140th, p1 (the car still running at the end before, after 142 moves) fifth on its 142nd, p4 (third before, on its 139th) sixth on its 143rd and p5 (fourth before, on its 140th) seventh on its 144th; p8 (sixth home before, on its 142nd) is the car still running at the end, after 143 moves, and p2 and p3 finish as before -- recorded, not vetoed (AGENTS.md).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves); seven finishers and no crash as before, but p4 (sixth before, on its 143rd move) now finishes third on its 139th, p5 (seventh before, on its 144th) fourth on its 140th, p6 (third before, on its 139th) fifth on its 141st, p7 (fourth before, on its 140th) sixth on its 142nd and p1 (fifth before, on its 142nd) seventh on its 143rd; p8 is still the car running at the end, after 142 moves (143 before), and p2 and p3 finish as before -- p2 to p7 home in number order, the round-316 summary again from a different classification; recorded, not vetoed (AGENTS.md).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too); Zandvoort s34 loses a car again (whole since round 328): p7 (sixth before, on its 142nd move) now crashes on its 18th, at turn 143 ((57,5)->(59,1)) -- two cells west of p6's crash in round 326 (on its 19th, at turn 150 ((59,5)->(61,1))), at the same velocity -- and seven finishers become six; p8 (the car still running at the end before, after 142 moves) now finishes sixth on its 142nd and p1 (seventh before, on its 143rd) is the car still running at the end, after 142 moves; p2, p3, p4, p5 and p6 finish as before -- the round-326 classification again with p6 and p7 swapped (p7 then fifth on its 141st, p6 lost on its 19th); recorded, not vetoed (AGENTS.md).
    ("zandvoort", 34): (6, 1, [137, 138, 139, 140, 141, 142]),
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); seven finishers and no crash as before, but p2 and p4 (third and fourth before) now finish second and third, on their 79th as before, p5 (the car still running at the end before, after 80 moves) fourth on its 80th, p6 fifth on its 80th (79th before), p7 sixth on its 80th (seventh before) and p3 (second before, on its 78th) seventh on its 81st; p8 (sixth before, on its 79th) is the car still running at the end, after 80 moves, and p1 still wins on its 78th -- recorded, not vetoed (AGENTS.md).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); seven finishers and no crash as before, but p8 (the car still running at the end before, after 80 moves) now wins on its 78th, p1 (the winner before, on its 78th) finishes second on its 80th, p2 third on its 80th (second on its 79th before), p3 fourth on its 80th (seventh on its 81st before), p4 fifth on its 80th (third on its 79th before), p5 sixth on its 80th (fourth before) and p7 seventh on its 80th (sixth before); p6 (fifth before, on its 80th) is the car still running at the end, after 80 moves -- recorded, not vetoed (AGENTS.md).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); seven finishers and no crash as before, but p4 (fifth before, on its 80th move) now wins on its 78th, p3 (fourth before, on its 80th) finishes second on its 79th, p5 (sixth before, on its 80th) third on its 79th, p2 (third before, on its 80th) fourth on its 80th, p6 (the car still running at the end before, after 80 moves) fifth on its 80th, p8 (the winner before, on its 78th) sixth on its 80th and p7 seventh on its 81st (80th before); p1 (second before, on its 80th) is the car still running at the end, after 81 moves -- the round-316 summary again, from a different classification; recorded, not vetoed (AGENTS.md).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves); seven finishers and no crash as before, but p2 (fourth before, on its 80th move) now wins on its 78th, p1 (the car still running at the end before, after 81 moves) finishes third on its 80th, p4 (the winner before, on its 78th) fourth on its 80th, p5 (third before, on its 79th) fifth on its 80th, p6 (fifth before, on its 80th) sixth on its 80th and p7 seventh on its 80th (81st before); p8 (sixth before, on its 80th) is the car still running at the end, after 79 moves, and p3 finishes second on its 79th as before -- recorded, not vetoed (AGENTS.md).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too); seven finishers and no crash as before, but p1 (third before, on its 80th move) now wins on its 78th, p3 finishes second on its 78th (79th before), p2 (the winner before, on its 78th) third on its 79th, p4 fourth on its 79th (80th before), p6 (sixth before, on its 80th) fifth on its 79th, p7 (seventh before, on its 80th) sixth on its 80th and p5 (fifth before, on its 80th) seventh on its 81st; p8 is still the car running at the end, after 80 moves (79 before) -- recorded, not vetoed (AGENTS.md).
    ("monza", 145): (7, 0, [78, 78, 79, 79, 79, 80, 81]),
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); seven finishers and no crash as before, but p8 (seventh before, on its 103rd move) now finishes sixth on its 103rd and p6 (sixth before, on its 103rd) seventh on its 104th; p1 to p5 finish as before and p7 is still the car running at the end, after 103 moves -- recorded, not vetoed (AGENTS.md).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves); seven finishers and no crash as before, but p2 (seventh before, on its 104th move) now finishes second on its 103rd, p4 (the car still running at the end before, after 103 moves) third on its 103rd, p5 fourth on its 103rd (third before), p6 fifth on its 103rd (fourth before), p3 (second before, on its 103rd) sixth on its 104th and p7 (fifth before, on its 103rd) seventh on its 104th; p8 (sixth before, on its 103rd) is the car still running at the end, after 103 moves, and p1 still wins on its 103rd -- recorded, not vetoed (AGENTS.md).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too); seven finishers and no crash as before, but p2 (second before, on its 103rd move) now wins on its 103rd, p3 (sixth before, on its 104th) finishes second on its 103rd, p7 (seventh before, on its 104th) third on its 103rd, p8 (the car still running at the end before, after 103 moves) fourth on its 103rd, p4 (third before, on its 103rd) fifth on its 104th, p5 (fourth before, on its 103rd) sixth on its 104th and p6 (fifth before, on its 103rd) seventh on its 104th; p1 (the winner before, on its 103rd) is the car still running at the end, after 104 moves -- recorded, not vetoed (AGENTS.md).
    ("serpentine", 38): (7, 0, [103, 103, 103, 103, 104, 104, 104]),
}
VETO_NORMALIZED_SHA256 = {
    # Round 224 (rival predictor in its own lap frame): trajectory only.
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too); the same classification as before, a different trajectory from p4's 39th move at turn 308: every car finishes in the same place on the same own move and p1 is still the car running at the end, after 71 moves.
    ("lemans", 2): 'ee1557f72135e18dde735c3c6e65bd9d02daa2e3bae764dffd3475fb7d43ec1e',
    # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
    ("spa", 1): 'a58cb913c1a7f63a5c75625c9bbacf38d4eb0934d0bcf57d0600110058d0ff31',
    # Round 224: same finishing order and same per-car move counts, new route.
    # Round 234: re-frozen from measurement (the seal guard left the decision).
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted); the same classification as before, a different trajectory: every car finishes in the same place on the same own move and p6 is still the car running at the end, after 127 moves.
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves); the same classification as before, a different trajectory from p7's 3rd move at turn 23: every car finishes in the same place on the same own move and p3 is still the car running at the end, after 127 moves.
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too); the same classification as before, a different trajectory from p2's 7th move at turn 50: every car finishes in the same place on the same own move and p3 is still the car running at the end, after 127 moves.
    ("hungaroring", 40): '843f1148b2d221ecaab9f92385bcc9928a8df791d0154b9a3d03c337f9777794',
    # Round 224: same finishing order and same per-car move counts, new route.
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 291: re-frozen from measurement (the grid rule at the finish, finishing without the potential, crossings that do not finish, no field-cost veto).
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
    ("interlagos", 47): '982c9b4a1a62a8acc634487ff3781291134493dc6acc8f3963f62268f64986b3',
    # Referee correction: turn 647 p5 N replaces an illegal NW finish;
    # every earlier move, race total and finishing place is unchanged.
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
    ("monza", 30): 'c89c6e51b5ce70ad7dedde95bd2ec3f4604858dd5a74216ca5da8e97b61ac850',
    # Round 224, the one case that changes its result: still seven finishers,
    # but car 1 finishes seventh where car 7 used to, and the race is nine
    # moves longer. The fleet cleared the change on 1460 races either side
    # (no crash moved, +19 and +133 moves in 1.85M).
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds); the crash on the 18th move is now p6's, and p8, lost there since round 281, finishes sixth -- recorded, not vetoed.
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); the same classification as before, a different trajectory from p4's 5th move at turn 36: every car finishes in the same place on the same own move and p1 is still the car running at the end, after 119 moves.
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
    ("monaco", 35): '0ecd117763f57c6a9f640fe3ac127753df2672a8b4d8d0eae42a9e588cc42a24',
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted); identical to the round-305/309 race until p7's 11th move at turn 87.
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
    ("zandvoort", 34): '74c3206d1d358d9b99f87336ce192d2901732638241b677246a7127e0dee4dd1',
    # Same illegal finishing vector at turn 640; legal N preserves all counters.
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
    ("monza", 145): '531b51a7c390f54ac206bb375f6dac72ae9fb98d416ef64e6c0d2ad19214fa89',
    # Reject p3's wall-overlap finish at turn 819: its last two approach moves
    # and p6's nearby response move, but the full field's outcome counters do not.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); the same summary, a different race from p5's 56th move at turn 445: p8 (the car still running at the end before, after 102 moves) now finishes seventh on its 103rd and p7 (seventh home before, on its 103rd) is the car still running at the end, after 103 moves.
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); the same summary, a different race from p7's 11th move at turn 87: p3 (third before), p5 (fifth before), p6 (seventh before, on its 104th) and p7 (the car still running at the end before, after 103 moves) now finish second to fifth, each on its 103rd move, p8 sixth on its 103rd as before and p2 (second before, on its 103rd) seventh on its 104th; p4 (fourth before, on its 103rd) is the car still running at the end, after 103 moves, and p1 still wins on its 103rd.
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
    ("serpentine", 38): '7d22ef658a8e207b899b9bbc5a5300c1312064b744b99cd8a72968c103c949a2',
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    cases = [("hungaroring", HUNGARORING_SEED), *VETO_CASES]
    with tempfile.TemporaryDirectory(prefix="ai1-private-slack-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["hungaroring", "interlagos", "lemans", "monaco", "zandvoort", "spa", "monza"]))  # frozen pre-2026-08-29 geometry
        bench_ai.set_nplayers(8)
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            for track, seed in cases:
                summaries[(kind, track, seed)] = bench_ai.run_track(
                    track, timeout=1200, seed=seed
                )
                logs[(kind, track, seed)] = Path(bench_ai.LOG).read_text(
                    encoding="utf-8"
                )

    for kind in LABELS:
        actual = summaries[(kind, "hungaroring", HUNGARORING_SEED)]
        if actual != HUNGARORING_PROMOTED:
            raise SystemExit(
                f"private-slack Hungaroring seed-12 {kind} regression: "
                f"{actual}, expected {HUNGARORING_PROMOTED}"
            )

    actual_finishers = {
        kind: finishers(logs[(kind, "hungaroring", HUNGARORING_SEED)])
        for kind in LABELS
    }
    expected_finishers = {
        "AI2": HUNGARORING_PROMOTED_FINISHERS,
    }
    if actual_finishers != expected_finishers:
        raise SystemExit(
            "private-slack Hungaroring seed-12 finisher regression: "
            f"{actual_finishers}, expected {expected_finishers}"
        )
    actual_moves = {
        kind: player_moves(logs[(kind, "hungaroring", HUNGARORING_SEED)])
        for kind in LABELS
    }
    if actual_moves != HUNGARORING_ALL_MOVES:
        raise SystemExit(
            "private-slack Hungaroring seed-12 complete move-count regression: "
            f"{actual_moves}, expected {HUNGARORING_ALL_MOVES}"
        )
    # Round 215 retired the all-move comparison: its reference came from the
    # pre-promotion build under the old single-lap rules. Under checkpoints on
    # every race both builds drive different races, so a Pareto comparison
    # between them measures the rule change, not the policy.
    # Round 215 retired this check: it pinned one decision by the exact log line
    # it appears on, and with checkpoints on every race the car is somewhere else
    # by that move. The move-count pins above still hold the whole field.
    for kind in LABELS:
        digest = normalized_sha256(logs[(kind, "hungaroring", HUNGARORING_SEED)])
        if digest != HUNGARORING_NORMALIZED_SHA256:
            raise SystemExit(
                f"private-slack Hungaroring seed-12 {kind} trajectory regression: "
                f"{digest}, expected {HUNGARORING_NORMALIZED_SHA256}"
            )

    for (track, seed), expected in VETO_CASES.items():
        for kind in LABELS:
            actual = summaries[(kind, track, seed)]
            if actual != expected:
                raise SystemExit(
                    f"private-slack {track} seed-{seed} {kind} veto regression: "
                    f"{actual}, expected {expected}"
                )
            # Round 215 retired this check: it looked for one veto at one move
            # index, and the race no longer reaches that state. The digest below
            # still pins the whole trajectory.
            digest = normalized_sha256(logs[(kind, track, seed)])
            expected_digest = VETO_NORMALIZED_SHA256[(track, seed)]
            if digest != expected_digest:
                raise SystemExit(
                    f"private-slack {track} seed-{seed} {kind} champion-trajectory "
                    f"regression: {digest}, expected {expected_digest}"
                )

    print(
        "AI1PrivateSlackRegression: OK "
        "(Hungaroring s12 strict -1; nine false-positive classes vetoed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
