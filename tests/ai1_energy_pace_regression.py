#!/usr/bin/env python3
from pathlib import Path
import sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai
# Round 231: re-frozen from recorded checkpoint-choice races; the existing
# assertion logic and AI1/AI2 identity checks remain intact.
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
 ("nurburgring",1): (7, 0, [92, 93, 93, 93, 94, 95, 95]),
 # Round 254: re-frozen from measurement (the danger guard in a faithful world).
 ("interlagos",29): (7, 0, [124, 125, 126, 127, 128, 129, 130]),
 ("interlagos",47): (7, 0, [124, 125, 126, 127, 128, 129, 131]),
 ("spa",17): (7, 0, [78, 79, 80, 81, 82, 82, 83]),
 # Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
 ("zandvoort",44): (7, 0, [137, 138, 139, 140, 141, 143, 144]),  # Round 260 (the chooser): whole again.
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
