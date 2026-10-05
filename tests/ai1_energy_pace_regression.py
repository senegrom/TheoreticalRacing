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
 ("nurburgring",1): (7, 0, [91, 92, 92, 93, 93, 94, 95]),
 # Round 254: re-frozen from measurement (the danger guard in a faithful world).
 ("interlagos",29): (7, 0, [124, 125, 126, 127, 128, 129, 130]),
 # Interlagos s47 races in ai1_private_slack_regression, which pins the same
 # race by summary and digest (the labels race alike; review, 2026-09-28).
 # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
 # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
 ("spa",17): (7, 0, [78, 79, 80, 81, 81, 81, 82]),
 # Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
 # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p6 now crashes on its 19th move -- recorded, not vetoed.
 ("zandvoort",44): (6, 1, [137, 138, 139, 141, 142, 143]),  # Round 281: loses a car again.
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
