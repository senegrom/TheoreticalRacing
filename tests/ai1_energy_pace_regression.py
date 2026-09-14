#!/usr/bin/env python3
from pathlib import Path
import sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai
# Round 231: re-frozen from recorded checkpoint-choice races; the existing
# assertion logic and AI1/AI2 identity checks remain intact.
# Round 247 (the soft rollout at one level, not two): Zandvoort s44 loses a
# car -- recorded, not vetoed (AGENTS.md); every case now pins its measured
# (finishers, crashes, finisher moves).
EXPECTED = {
 # Round 228: measured raw-distance policy, seven finishers and no crashes.
 # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
 # Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
 # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
 ("nurburgring",1): (7, 0, [91, 92, 92, 93, 93, 95, 96]),
 ("interlagos",29): (7, 0, [124, 126, 126, 128, 130, 130, 131]),
 ("interlagos",47): (7, 0, [124, 126, 127, 129, 129, 130, 132]),
 ("spa",17): (7, 0, [78, 79, 80, 81, 82, 83, 85]),
 ("zandvoort",44): (6, 1, [137, 139, 140, 141, 142, 144]),
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
