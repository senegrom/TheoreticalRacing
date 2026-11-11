#!/usr/bin/env python3
"""Pin Round 96's synchronized finish-frontier pace gain.

Round 345: that gain (Coil seed 6, 426 -> 421 finisher moves) was measured
against the policy before round 96 on the grid before round 345. Random
starts are now each car's own draw from the seed's SplitMix64 stream, so
seeds 6, 47 and 49 race from new grids; the pin holds the champion's new
races there and one finish-frontier column decision in each
(EXPECTED_DECISION).
"""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import finishers, normalized_lines  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

EXPECTED = {
    # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
    # Round 331: re-frozen from measurement (the relevant rival keeps its three stronger forecast moves beside the second and third rivals'); no crash, p5 and p6 each one own move faster, in 60 (61 before), p7 (the car still running at the end before, after 60 own moves) now finishes in 61, and p8 (home in 60 before) is the car still running at the end, after 60 own moves -- the list of rounds 328 and 329 again (sum 418 -> 417); the classification is under EXPECTED_SEED6_FINISHERS.
    # Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full policy in every decision); no crash, p5 and p6 each one own move slower, in 61 (60 before), p8 (the car still running at the end before, after 60 own moves) now finishes in 60, and p7 (home in 61 before) is the car still running at the end, after 60 own moves -- the list of round 330 again (sum 417 -> 418); the classification is under EXPECTED_SEED6_FINISHERS.
    # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy); no crash, p5 and p6 each one own move faster, in 60 (61 before), p7 (the car still running at the end before, after 60 own moves) now finishes in 61, and p8 (home in 60 before) is the car still running at the end, after 60 own moves -- the list of rounds 328, 329 and 331 again (sum 418 -> 417); the classification is under EXPECTED_SEED6_FINISHERS.
    # Round 345: measured (random starts: each car's own draw from the seed's SplitMix64 stream); seed 6 starts from a new grid and is a new race, with the same summary: no crash, p1 finishes first in 58, p2 and p4 second and third in 59, p3, p5 and p6 fourth to sixth in 60 and p7 seventh in 61, and p8 is the car still running at the end, after 60 own moves (sum 417); the classification is under EXPECTED_SEED6_FINISHERS.
    6: (7, 0, [58, 59, 59, 60, 60, 60, 61]),
    # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
    # Round 260: re-frozen from measurement (the faithful joint world as a chooser).
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); the same seven finish, no crash, p3, p6 and p7 each one own move faster (sum 418 -> 415).
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); the same seven finish, no crash, p5 one own move faster, in 59, and p2, p3 and p6 each one own move slower, in 60, 60 and 61 (sum 415 -> 417).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); no crash, p1 (first home in 58 before) is now the car still running at the end, p8 (the car still running at the end before) now finishes seventh in 60 own moves, p2 and p6 each finish two own moves faster, first in 58 and fourth in 59, p3 one faster, second in 59, and p5 one slower, fifth in 60 (sum 417 -> 415).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); the same seven finish, no crash, p1 still the car running at the end, and p6 one own move slower, fifth in 60 (fourth in 59 before), so p5 is fourth, in 60 as before (sum 415 -> 416).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); the same seven finish, no crash, p1 still the car running at the end (after 60 own moves), and p6 one own move faster, fourth in 59 (fifth in 60 before), so p5 is fifth, in 60 as before -- round 316's classification again (sum 416 -> 415).
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too); no crash, p1 (the car still running at the end before, after 60 own moves) now finishes fifth in 61, p7 fourth in 60 (sixth in 60 before), p4 one own move slower, third in 60 (third in 59 before), p5 one slower, sixth in 61 (fifth in 60 before), p6 two slower, seventh in 61 (fourth in 59 before), and p8 (seventh home in 60 before) is the car still running at the end, after 60 own moves; p2 and p3 finish first and second as before, in 58 and 59 (sum 415 -> 420).
    # Round 331: re-frozen from measurement (the relevant rival keeps its three stronger forecast moves beside the second and third rivals'); no crash, p7 one own move faster, third in 59 (fourth in 60 before), p6 one faster, fourth in 60 (seventh in 61 before), p4 one slower, fifth in 61 (third in 60 before), p8 (the car still running at the end before, after 60 own moves) now finishes seventh in 61, and p1 (fifth home in 61 before) is the car still running at the end, after 61 own moves; p2, p3 and p5 finish first, second and sixth as before, in 58, 59 and 61 (sum 420 -> 419).
    # Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full policy in every decision); no crash, the race is round 331's through move 357: p4 one own move faster, third in 60 (fifth in 61 before), p7 one slower, fourth in 60 (third in 59 before), p6 two slower, seventh in 62 (fourth in 60 before), so p5 and p8 are fifth and sixth, in 61 as before (sixth and seventh before), and p1 is still the car running at the end, after 62 own moves (61 before); p2 and p3 finish first and second as before, in 58 and 59 (sum 419 -> 421).
    # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy); no crash, p6 one own move faster, sixth in 61 (seventh in 62 before), so p8 is seventh, in 61 as before (sixth before), and p1 is still the car running at the end, after 61 own moves (62 before); p2, p3, p4, p7 and p5 finish first to fifth as before, in 58, 59, 60, 60 and 61 -- the list of round 330 again (sum 421 -> 420).
    # Round 335: re-frozen from measurement (every rival but the relevant one plays its first two forecast moves by its full policy); no crash, the race is round 334's through move 36: p5 (fifth home in 61 before) is now the car still running at the end, after 62 own moves, so p6 is fifth, in 61 as before (sixth before); p1 (the car still running at the end before, after 61 own moves) now finishes sixth in 62, and p8 one own move slower, seventh in 62 (61 before); p2, p3, p4 and p7 finish first to fourth as before, in 58, 59, 60 and 60 (sum 420 -> 422).
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); seed 47 starts from a new grid and is a new race: no crash, p1 finishes first in 58, p2 second in 59, p3 and p6 third and fourth in 60 and p4, p5 and p7 fifth to seventh in 61, and p8 is the car still running at the end, after 60 own moves (sum 420).
    47: (7, 0, [58, 59, 60, 60, 61, 61, 61]),
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); no crash, p8 (the car still running at the end before) now finishes third in 59 own moves, p7 (sixth home in 60 before) is the car still running at the end, and p3 and p6 each finish one own move slower, in 60 and 61 (sum 417 -> 418).
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); no crash, p7 (the car still running at the end before) now finishes seventh in 61 own moves, p8 (third home in 59 before) is the car still running at the end, and p3, p5 and p6 each finish one own move faster, in 59, 60 and 60 (sum 418 -> 417).
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); the same seven finish in the same order, no crash, p8 still the car running at the end, and p6 one own move slower, in 61 (sum 417 -> 418).
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); the same seven finish in the same order, no crash, p8 still the car running at the end, and p6 one own move faster, in 60 (sum 418 -> 417).
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); no crash, p8 (the car still running at the end before) now finishes sixth in 60 own moves, p6 (sixth home in 60 before) two own moves slower, seventh in 62, and p7 (seventh home in 61 before) is the car still running at the end, after 61 own moves; p1 to p5 finish as before (sum 417 -> 418).
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves); no crash, p6 (seventh home in 62 before) two own moves faster, sixth in 60, p7 (the car still running at the end before) now finishes seventh in 61 own moves, and p8 (sixth home in 60 before) is the car still running at the end, after 60 own moves; p1 to p5 finish as before -- round 326's classification again (sum 418 -> 417).
    # Round 330: measured (a third rival in contact with the mover plays one stronger forecast move too); the same summary, a different classification: no crash, p8 (the car still running at the end before, after 60 own moves) now finishes sixth in 60, p6 one own move slower, seventh in 61 (sixth in 60 before), and p7 (seventh home in 61 before) is the car still running at the end, after 60 own moves; p1 to p5 finish as before (sum 417, unchanged).
    # Round 331: measured (the relevant rival keeps its three stronger forecast moves beside the second and third rivals'); the same summary, a different classification: no crash, p6 one own move faster, sixth in 60 (seventh in 61 before), p8 one slower, seventh in 61 (sixth in 60 before), and p7 is still the car running at the end, after 61 own moves (60 before); p1 to p5 finish as before (sum 417, unchanged).
    # Round 333: measured (the mover's aware forecast plays eight own moves by its full policy in every decision); the same summary, a different classification: no crash, p8 one own move faster, sixth in 60 (seventh in 61 before), p6 one slower, seventh in 61 (sixth in 60 before), and p7 is still the car running at the end, after 60 own moves (61 before); p1 to p5 finish as before -- round 330's classification again (sum 417, unchanged).
    # Round 334: measured (every other live rival plays its first forecast move by its full policy); the same summary, a different classification: no crash, p7 (the car still running at the end before, after 60 own moves) now finishes sixth in 60, and p8 (sixth home in 60 before) is the car still running at the end, after 60 own moves; p1 to p5 finish as before, and p6 is seventh in 61 as before (sum 417, unchanged).
    # Round 343: re-frozen from measurement (a rival whose simulated move finishes leaves the score's simulated round); no crash, p7 now finishes fourth in 60 (sixth in 60 before), p3 one own move slower, third in 60 (59 before), and p4 and p5 each one slower, fifth and sixth in 61 (fourth and fifth in 60 before); p1, p2 and p6 finish as before, first in 58, second in 59 and seventh in 61, and p8 is still the car running at the end, after 60 own moves; the race is the round-342 race through turn 381, the first change is p6's 48th move at turn 382 (S instead of SE), after the pinned line at move 308, which stands (sum 417 -> 420).
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); seed 49 starts from a new grid and is a new race: no crash, p1 finishes first in 58, p2 second in 59, p4 third in 60 and p5, p6, p7 and p8 fourth to seventh in 61, and p3 is the car still running at the end, after 61 own moves (sum 421).
    49: (7, 0, [58, 59, 60, 61, 61, 61, 61]),
}
EXPECTED_SEED6_FINISHERS = [
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 260: re-frozen from measurement; the seed-6 sum is unchanged at 417.
    # Round 274: re-frozen from measurement (rank first); the sum is 420 now.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); no crash, p2 now finishes second in 59 own moves (classified last before) and p8 is the car still running at the end; the sum is 419 now.
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); no crash, p3, p4 and p6 each finish one own move faster, in 59, 60 and 60, p5 one slower, seventh in 61, p8 (the car still running at the end before) now finishes sixth in 60 own moves and p7 (fifth home in 60 before) is the car still running at the end; the sum is 417 now.
    # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); no crash, p4 finishes one own move faster, third in 59, and p3, p6 and p8 each one slower, fourth in 60 and sixth and seventh in 61; p5 is home fifth instead of seventh, in 61 as before, and p7 is still the car running at the end; the sum is 419 now.
    # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too); no crash, p3 finishes one own move faster, second in 59 (fourth in 60 before), p5 and p6 each one faster, fourth and fifth in 60 (fifth and sixth in 61 before), p7 (the car still running at the end before) now finishes sixth in 61 own moves, and p2 (second home in 59 before) is the car still running at the end; p1, p4 and p8 finish as before, first in 58, third in 59 and seventh in 61; the sum is 418 now.
    # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); the same seven finish in the same order, no crash, p7 one own move faster, sixth in 60 (61 before), and p2 still the car running at the end, after 61 own moves; the sum is 417 now.
    # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves); no crash, p2 (the car still running at the end before, after 61 own moves) now finishes second in 59, p3 one own move slower, fourth in 60 (second in 59 before), p8 one faster, sixth in 60 (seventh in 61 before), p6 one slower, seventh in 61 (fifth in 60 before), and p7 (sixth home in 60 before) is the car still running at the end, after 60 own moves; p1 and p4 finish as before, first in 58 and third in 59, and p5 is fifth, in 60 as before (fourth before); the sum is unchanged at 417.
    # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too); no crash, p5 one own move slower, sixth in 61 (fifth in 60 before), so p8 is fifth, in 60 as before (sixth before); p1, p2, p4, p3 and p6 finish as before, first in 58, second and third in 59, fourth in 60 and seventh in 61, and p7 is still the car running at the end, after 60 own moves; the sum is 418 now.
    # Round 331: re-frozen from measurement (the relevant rival keeps its three stronger forecast moves beside the second and third rivals'); no crash, p5 and p6 each one own move faster, fifth and sixth in 60 (sixth and seventh in 61 before), p7 (the car still running at the end before, after 60 own moves) now finishes seventh in 61, and p8 (fifth home in 60 before) is the car still running at the end, after 60 own moves; p1, p2, p4 and p3 finish as before, first in 58, second and third in 59 and fourth in 60; the sum is 417 now.
    # Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full policy in every decision); no crash, p8 (the car still running at the end before, after 60 own moves) now finishes fifth in 60, p5 and p6 each one own move slower, sixth and seventh in 61 (fifth and sixth in 60 before), and p7 (seventh home in 61 before) is the car still running at the end, after 60 own moves -- round 330's classification again; p1, p2, p4 and p3 finish as before, first in 58, second and third in 59 and fourth in 60; the sum is 418 now.
    # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy); no crash, p5 and p6 each one own move faster, fifth and sixth in 60 (sixth and seventh in 61 before), p7 (the car still running at the end before, after 60 own moves) now finishes seventh in 61, and p8 (fifth home in 60 before) is the car still running at the end, after 60 own moves -- round 331's classification again; p1, p2, p4 and p3 finish as before, first in 58, second and third in 59 and fourth in 60; the sum is 417 now.
    # Round 335: re-frozen from measurement (every rival but the relevant one plays its first two forecast moves by its full policy); the same summary, a different classification: no crash, p8 (the car still running at the end before, after 60 own moves) now finishes third in 59, p4 one own move slower, fifth in 60 (third in 59 before), p5 one slower, seventh in 61 (fifth in 60 before), and p7 (seventh home in 61 before) is the car still running at the end, after 60 own moves; p1, p2, p3 and p6 finish as before, first in 58, second in 59, fourth in 60 and sixth in 60; the sum is unchanged at 417.
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); seed 6 is a new race from a new grid: no crash, p1 finishes first in 58, p2 and p4 second and third in 59, p3, p5 and p6 fourth to sixth in 60 and p7 seventh in 61, and p8 is the car still running at the end, after 60 own moves; the sum is 417.
    (1, 58),
    (2, 59),
    (4, 59),
    (3, 60),
    (5, 60),
    (6, 60),
    (7, 61),
]
EXPECTED_DECISION = {
    # Round 229: re-frozen from measurement (the soft caution stack left the score).
    # Round 233: re-frozen from measurement (the lane spread left the score).
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 260: the same turn and car, re-frozen from measurement.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 303: the same turns and cars, re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); s6's p3 brakes SW as before, three cells further east (round 260's line), s49's p4 now reaches (66,47) at v(1,-5) and plays W to (0,-5); s47 unchanged.
    # Round 305/309: the same turns and cars, re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); s49's p4 still plays W from v(1,-5) to (0,-5), one cell further west: it coasts at move 292 and reaches (65,47) at move 300 instead of (66,47); s6 and s47 unchanged.
    # Round 316: the same turns and cars, re-frozen from measurement (the chooser ranks its forecasts by projected place, then time); s6's p3 brakes SW as before, two cells further west: it reaches (66,47) at move 291 instead of (68,47); s47's p2 now reaches the column a move earlier, (65,49) at v(1,-6) at move 282, and at move 290 plays W there, to (0,-6) and (65,43) -- from the very state at which round 96 pinned its SW veto, it now plays the W that round 96 pinned as seed 6's gain -- and brakes SW from (65,43) at move 298; the old line's SW from (65,47) is p3's now, at move 299; s49 unchanged.
    # Round 326: the same turns and cars, re-frozen from measurement (every chooser call ranks by projected place, nested ones too); s6's p3 no longer brakes at move 299: it reaches (65,48) at v(1,-6) at move 291, one cell west and one south of round 316's (66,47), and plays W there, to (0,-6) and (65,42) -- the W that round 96 pinned as seed 6's gain and the W-then-SW pair s47's p2 plays at moves 290 and 298, each from (65,49), one cell further south -- and brakes SW from (65,42) at move 307; s47 and s49 unchanged.
    # Round 328: the same turns and cars, re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy); s6's p3 brakes at move 299 again: it reaches (65,47) at v(1,-6) at move 291, one cell north of round 326's (65,48), and brakes SW there, to (0,-5) and (65,42) -- the very line rounds 233-234 and 281-301a' pinned at this turn -- then plays W from (65,42) at move 307, to (-1,-5) and (64,37), where round 326's line also stood after that move; the W that round 96 pinned as seed 6's gain, from (65,49) at v(1,-6) to (65,43), is the winner p1's, at move 289, as in round 326; s47 and s49 unchanged.
    # Round 329: the same turns and cars, re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves); s6's p3 still brakes SW at move 299, one cell further east: it reaches (66,47) at v(1,-6) at move 291 instead of (65,47) and brakes there, to (0,-5) and (66,42) -- round 316's line again -- then plays W from (66,42) at move 307, to (-1,-5) and (65,37); the W that round 96 pinned as seed 6's gain, from (65,49) at v(1,-6) to (65,43), is still the winner p1's, at move 289; s47 and s49 unchanged.
    # Round 330: the same turns and cars, re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too); s49's p4 reaches v(1,-5) a move earlier and brakes from it: it plays W at move 292 (it coasted there before), from (63,56) at v(2,-5), to (1,-5) and (64,51), and brakes SW at move 300, from (64,51), to (0,-4) and (64,47) -- the very velocity change, v(1,-5) to (0,-4), that round 96 pinned as s49's veto, at move 308 from (67,49) -- then at move 308, from (64,47) at v(0,-4), one cell west of round 329's (65,47) at v(1,-5), plays NW, to (-1,-5) and (63,42); it finishes fourth in 60 as before; s6 and s47 unchanged.
    # Round 331: the same turns and cars, re-frozen from measurement (the relevant rival keeps its three stronger forecast moves beside the second and third rivals'); s49's p4 races round 329's line again, move for move: it leaves round 330's line at move 260, coasts at move 292 again, from (62,57) at v(2,-5) to (64,52), plays W at move 300, to (1,-5) and (65,47), and at move 308 plays W from (65,47) at v(1,-5), to (0,-5) and (65,42) -- the line rounds 305/309 to 329 pinned at this turn; it finishes fourth in 60 as before, and the velocity change round 96 pinned as s49's veto, v(1,-5) to (0,-4), is p7's now, at move 319 from (68,45); s6's p3 still brakes SW at move 299, from (66,47) at v(1,-6), to (0,-5) and (66,42), as in rounds 329 and 330 -- the velocity change, v(1,-6) to (0,-5), of round 96's s47 SW veto -- and the W that round 96 pinned as seed 6's gain, from (65,49) at v(1,-6) to (65,43), is still the winner p1's, at move 289; s47 unchanged.
    # Round 333: the same turns and cars, measured (the mover's aware forecast plays eight own moves by its full policy in every decision); the three pinned lines stand: s6's p3 races round 331's line move for move and still brakes SW at move 299, and the winner p1 still plays round 96's seed-6 gain W at move 289; s47's race is round 331's through move 357, so p2's SW at move 298 stands; s49's p4 leaves round 331's line only at move 356 and still plays W at move 308, from (65,47) at v(1,-5). The velocity change round 96 pinned as s49's veto, v(1,-5) to (0,-4), is in none of the three races now: s49's p7 leaves round 331's line at move 63 and at move 319 plays SW from (64,43) at v(0,-6), to (-1,-5) and (63,38); round 96's own s47 line, SW from (65,49) at v(1,-6) to (0,-5) and (65,44), is s49's p8's now, at move 304.
    # Round 334: the same turns and cars, measured (every other live rival plays its first forecast move by its full policy); the three pinned lines stand: s6's p3 leaves round 333's line at move 43 and rejoins it at move 235, so it still reaches (66,47) at v(1,-6) at move 291 and brakes SW at move 299, and the winner p1 races round 333's line move for move and still plays round 96's seed-6 gain W at move 289; s47's p2 races round 333's line move for move, so its SW at move 298 stands; s49's p4 races round 331's line again, move for move (it left it at move 356 under round 333), and still plays W at move 308, from (65,47) at v(1,-5). The velocity change round 96 pinned as s49's veto, v(1,-5) to (0,-4), is still in none of the three races, and round 96's own s47 line, SW from (65,49) at v(1,-6) to (0,-5) and (65,44) -- s49's p8's at move 304 under round 333 -- is in none of them now either: s49's p8 leaves round 333's line at move 72 and at move 304 plays W from (63,55) at v(2,-6), to (1,-6) and (64,49).
    # Round 335: the same turns and cars, measured (every rival but the relevant one plays its first two forecast moves by its full policy); the three pinned lines stand: s6's p3 leaves round 334's line at move 43 and rejoins it at move 235, so it still reaches (66,47) at v(1,-6) at move 291 and brakes SW at move 299, and the winner p1 races round 334's line move for move and still plays round 96's seed-6 gain W at move 289; s47's p2 races round 334's line move for move, so its SW at move 298 stands; s49's race is round 334's move for move, so p4's W at move 308, from (65,47) at v(1,-5), stands. The velocity change round 96 pinned as s49's veto, v(1,-5) to (0,-4), is in one of the three races again: s47's p5 plays it at move 317, SW from (69,50) to (69,46); round 96's own s47 line, SW from (65,49) at v(1,-6) to (0,-5) and (65,44), is still in none of them.
    # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); three new races from new grids, so each line is chosen afresh from its own race by the decision it shows, not by its turn. s6's line is in the new race: p3 (fourth home in 60) reaches (66,47) at v(1,-6) at move 291 and at move 299, its 38th own move, brakes SW to (0,-5) and (66,42) -- the velocity change of round 96's s47 veto -- one move after p2 played round 96's own s6 gain, W from (65,49) at v(1,-6) to (0,-6) and (65,43) (the winner p1 played it at move 289), with p4 alongside at (64,48) at the same v(1,-6), which brakes SW to (64,43) at move 300. s47's new line is p5's brake at move 309: p5 (sixth home in 61) reaches (66,47) at v(1,-6) at move 301 and at move 309, its 39th own move, brakes SW to (0,-5) and (66,42) -- round 96's s47 veto velocity change -- in a formation of four cars at v(1,-6): p4, one column west and two rows behind, has just played round 96's s6 gain (move 308, W from (65,49) to (0,-6) and (65,43)), and p7, at (68,47) on p5's row, and p8, at (68,52), brake SW in turn at moves 311 and 312; round 343's s47 move, SW from (65,43) at v(0,-6) to (-1,-5) and (64,38) after that W, is the winner p1's at move 297 and p4's at move 316. s49's new line is p5's W at move 309, the move rounds 305/309 to 343 (all but round 330) pinned here, from the same state: p5 (fourth home in 61) reaches (65,47) at v(1,-5) at move 301 and at move 309, its 39th own move, plays W to (0,-5) and (65,42), keeping the vertical speed that round 96's s49 veto shed (SW to (0,-4)), in the middle of a four-car stack -- p7 one cell ahead at (65,46) at v(1,-7), p6 one cell behind at (65,48) and p8 diagonally behind at (64,48), both at v(1,-6) -- after which p6 and p7 brake SW (moves 310 and 311) and p8 plays round 96's s6 gain velocity change, W to (0,-6), at move 312. Round 96's own s47 line, SW from (65,49) at v(1,-6) to (0,-5) and (65,44), and its s49 veto velocity change, v(1,-5) to (0,-4), are in none of the three races. None of these lines, nor round 343's, has the formation the round-96 rule needs before it may fire -- a car that moved earlier in the round, one cell away and alongside, at the mover's exact velocity -- so the lines pin the column decisions that rule was written for, not the rule firing.
    6: "299 p3 {kind} SW v(1,-6)→(0,-5) (66,47)→(66,42) ok",
    47: "309 p5 {kind} SW v(1,-6)→(0,-5) (66,47)→(66,42) ok",
    49: "309 p5 {kind} W v(1,-5)→(0,-5) (65,47)→(65,42) ok",
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    with tempfile.TemporaryDirectory(prefix="ai1-finish-frontier-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            for seed in EXPECTED:
                summaries[(kind, seed)] = bench_ai.run_track("coil", timeout=600, seed=seed)
                logs[(kind, seed)] = Path(bench_ai.LOG).read_text(encoding="utf-8")

    for kind in LABELS:
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

    move_sums = {
        kind: sum(summaries[(kind, 6)][2])
        for kind in LABELS
    }
    # Round 229: 418 is the re-frozen seed-6 sum (the soft caution stack left the score).
    # Round 247: 417 (the soft rollout at one level, not two).
    # Round 274: 420 (rank first), measured; still below the pre-frontier 426.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 303: 419 (aware forecasts, the chooser lab's aware promoted), measured; still below the pre-frontier 426.
    # Round 305/309: 417 (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win), measured; still below the pre-frontier 426.
    # Round 316: 419 (the chooser ranks its forecasts by projected place, then time), measured; still below the pre-frontier 426.
    # Round 326: 418 (every chooser call ranks by projected place, nested ones too), measured; still below the pre-frontier 426.
    # Round 328: 417 (aware's relevant rival plays its first three forecast moves by its full policy), measured; still below the pre-frontier 426.
    # Round 330: 418 (a third rival in contact with the mover plays one stronger forecast move too), measured; still below the pre-frontier 426.
    # Round 331: 417 (the relevant rival keeps its three stronger forecast moves beside the second and third rivals'), measured; still below the pre-frontier 426.
    # Round 333: 418 (the mover's aware forecast plays eight own moves by its full policy in every decision), measured; still below the pre-frontier 426.
    # Round 334: 417 (every other live rival plays its first forecast move by its full policy), measured; still below the pre-frontier 426.
    # Round 345: 417 (random starts: each car's own draw from the seed's SplitMix64 stream), measured: seed 6 is a new race and 417 is its own sum (58 + 59 + 59 + 60 + 60 + 60 + 61), an equality with no margin that moves with the race, as it has since round 96. The pre-frontier 426 does not: it was the seed-6 sum of the policy before round 96 (round 96: [58,60,61,61,61,62,63] -> [58,59,59,60,61,62,62], 426 -> 421), raced on the grid before round 345, and that policy cannot race the new grid, so the comparison with it is retired (the condition was `move_sum != 417 or move_sum >= 426`).
    if any(move_sum != 417 for move_sum in move_sums.values()):
        raise SystemExit(f"Round-96 Coil seed-6 pace gain lost: {move_sums}")

    # Round 345: the message said 'seeds 47/49 vetoes pinned'; round 96's veto moves are in none of the new races
    # (EXPECTED_DECISION), so the message names what is pinned.
    print(
        "AI1FinishFrontierRegression: OK "
        "(Coil seed 6 at 417 moves; one finish-frontier column decision pinned in each of seeds 6, 47 and 49)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
