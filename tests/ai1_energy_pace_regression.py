#!/usr/bin/env python3
from pathlib import Path
import sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai
# Round 231: re-frozen from recorded checkpoint-choice races; the existing
# assertion logic remains intact. (Its AI1/AI2 identity checks retired on
# 2026-09-27: one policy under both labels, pinned by ai1_label_invariance.)
# Round 247 (the soft rollout at one level, not two): Zandvoort s44 lost a
# car -- recorded, not vetoed (AGENTS.md); round 248 (the physical world
# model) gives it back. Every case pins its measured (finishers, crashes,
# finisher moves).
EXPECTED = {
 # Round 228: measured raw-distance policy, seven finishers and no crashes.
 # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
 # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
 # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
 # Round 260: re-frozen from measurement (the faithful joint world as a chooser).
 # Round 278: re-frozen from measurement (the chooser's pick stands).
 # Round 291: re-frozen from measurement (the grid rule at the finish, finishing without the potential, crossings that do not finish, no field-cost veto).
 # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
 # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
 # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
 # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
 # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
 # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
 # Round 316: re-frozen from measurement (the chooser ranks its forecasts by projected place, then time).
 # Round 326: re-frozen from measurement (every chooser call ranks by projected place, nested ones too).
 # Round 328: re-frozen from measurement (aware's relevant rival plays its first three forecast moves by its full policy).
 # Round 329: re-frozen from measurement (a second rival in contact with the mover plays one of aware's three stronger forecast moves).
 # Round 330: re-frozen from measurement (a third rival in contact with the mover plays one stronger forecast move too).
 # Round 331: re-frozen from measurement (the relevant rival keeps its three stronger forecast moves beside the second and third rivals').
 # Round 333: re-frozen from measurement (the mover's aware forecast plays eight own moves by its full policy in every decision).
 # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy); p1 still wins, one own move faster (91 -> 90); p3 (fifth home on its 95th before) is second on its 91st, p7 (fourth on its 94th) third on its 92nd, p4 (sixth on its 95th) fourth on its 94th, p5 (seventh on its 96th) fifth on its 95th, p8 (the car still running at the end before, after 95 moves) sixth on its 95th and p6 (third on its 93rd) seventh on its 96th; p2, second home on its 92nd before, is the car still running at the end, after 96 moves (it reaches (95,39) on its 96th, where it was on its 90th before) -- seven finishers and no crash. The race parts from round 333's on move 5 (p5's 1st).
 # Round 335: re-frozen from measurement (every rival but the relevant one plays its first two forecast moves by its full policy).
 # Round 336: re-frozen from measurement (gates are ordinary landings wherever the exact potential prices them).
 # Round 341: re-frozen from measurement (the score's rival twin plays the rival's own gate rules).
 # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); Nurburgring s1 is a new race from a new grid: seven finishers and no crash -- p1 to p4 come home first to fourth on their 90th to 93rd own moves, p8 fifth on its 94th, and p5 and p6 sixth and seventh, each on its 96th, and p7 is the car still running at the end, after 95 moves.
 ("nurburgring",1): (7, 0, [90, 91, 92, 93, 94, 96, 96]),
 # Round 254: re-frozen from measurement (the danger guard in a faithful world).
 # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); p7 now crashes on its 56th move -- recorded, not vetoed (AGENTS.md).
 # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); p7 no longer crashes on its 56th move and finishes seventh on its 130th -- recorded, not vetoed (AGENTS.md).
 # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy); p1 to p4 still come home first to fourth on their 124th to 127th; p5, seventh home on its 131st before, is fifth on its 128th, p6, the car still running at the end before (after 130 moves), sixth on its 129th and p7, fifth home on its 128th before, seventh on its 130th; p8, sixth home on its 129th before, is the car still running at the end, after 129 moves -- seven finishers and no crash, the seventh home one own move sooner (131 -> 130), the numbers of rounds 305/309 to 332 again. The race parts from round 333's on move 61 (p5's 8th).
 # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); Interlagos s29 is a new race from a new grid: seven finishers and no crash -- p1 wins on its 124th own move, p2 is second on its 125th, p4 third on its 126th, p5 fourth on its 127th, p6 fifth on its 128th, and p7 and p8 sixth and seventh, each on its 129th, and p3 is the car still running at the end, after 129 moves.
 ("interlagos",29): (7, 0, [124, 125, 126, 127, 128, 129, 129]),  # Round 305/309: whole again.
 # Interlagos s47 races in ai1_private_slack_regression, which pins the same
 # race by summary and digest (the labels race alike; review, 2026-09-28).
 # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
 # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
 # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
 # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
 # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
 # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy); p3, the car still running at the end before (after 83 moves), now wins on its 78th and p2, the winner on its 79th before, comes home seventh on its 84th; p5 to p8 move up a place each, to second to fifth on their 79th to 82nd (third to sixth on their 81st, 81st, 81st and 82nd before), p1 to sixth on its 83rd (seventh on its 84th before), and p4, second home on its 80th before, is the car still running at the end, after 83 moves -- seven finishers and no crash. The race parts from round 333's on move 15 (p7's 2nd).
 # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); Spa s17 is a new race from a new grid, and it loses a car: p7 crashes on its 30th move, at turn 239, NW from (96,157) at v(-2,4) to (93,160), in the hairpin at the bottom of the course, at the foot of the long run south -- it stood on a vertex of the outer wall, where every landing leaves the track. It had come there on its 29th move (turn 231, N from (98,153) at v(-2,5)), when its one landing inside the wall, (95,157) at v(-3,4), was held by p3 (there since turn 227). Six finishers: p1 wins on its 79th own move, p5 is second on its 80th, p2 third on its 81st, p3 and p4 fourth and fifth, each on its 82nd, and p6 sixth on its 83rd, and p8 is the car still running at the end, after 82 moves -- recorded, not vetoed (AGENTS.md).
 ("spa",17): (6, 1, [79, 80, 81, 82, 82, 83]),  # Round 345: loses a car.
 # Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
 # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p6 now crashes on its 19th move -- recorded, not vetoed.
 # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); p6 no longer crashes on its 19th move and finishes third on its 139th -- recorded, not vetoed (AGENTS.md).
 # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
 # Round 334: re-frozen from measurement (every other live rival plays its first forecast move by its full policy); p2, sixth home on its 143rd move before, now crashes on its 39th (move 306, in the hairpin at the foot of the run down from the top of the course: it came to (39,71) at v(-3,2) on its 37th, move 290, and on its 38th, move 298, its two landings that did not lead into the wall, (37,72) and (37,73), were held by p1 (since move 297, the move before) and p6 (since move 294), so it held v(-3,2) to (36,73), from where every landing left the track; it steered into (32,74)) -- six finishers. p4 to p7 still come home first to fourth on their 137th to 140th and p1 fifth on its 142nd; p3, the car still running at the end before (after 143 moves), comes home sixth on its 143rd, and p8, seventh home on its 143rd before, is the car still running at the end, after 142 moves -- recorded, not vetoed (AGENTS.md). The race parts from round 333's on move 75 (p3's 10th).
 # Round 345: re-frozen from measurement (random starts: each car's own draw from the seed's SplitMix64 stream); Zandvoort s44 is a new race from a new grid, and whole: seven finishers and no crash -- p7 wins on its 137th own move, p8 is second on its 138th, p1 third on its 140th, p2 fourth on its 141st, p3 fifth on its 142nd, and p4 and p5 sixth and seventh, each on its 143rd, and p6 is the car still running at the end, after 142 moves.
 ("zandvoort",44): (7, 0, [137, 138, 140, 141, 142, 143, 143]),  # Round 334: loses a car again. Round 345: whole, on a new grid.
}
def main():
 with tempfile.TemporaryDirectory(prefix="ai1-energy-") as d:
  bench_ai.configure_runtime(d)
  import fixture_install
  bench_ai.JAR = str(fixture_install.install(d, ["interlagos", "nurburgring", "zandvoort", "spa"]))  # frozen pre-2026-08-29 geometry
  bench_ai.set_nplayers(8); bench_ai.set_all_to("AI1")
  for (track,seed), expected in EXPECTED.items():
   result=bench_ai.run_track(track,timeout=900,seed=seed)
   if result is None: raise SystemExit(f"invalid {track} {seed}")
   f,c,moves=result
   if (f,c,moves)!=expected: raise SystemExit(f"{track} {seed}: {(f,c,moves)}, expected {expected}")
 print("AI1EnergyPaceRegression: OK")
if __name__ == "__main__": main()
