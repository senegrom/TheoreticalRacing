#!/usr/bin/env python3
from pathlib import Path
import sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai
EXPECTED = {
 ("nurburgring",1): [92, 95, 98, 100, 100, 101, 103],
 ("interlagos",29): [126, 132, 136, 138, 139, 141, 142],
 ("interlagos",47): [128, 134, 135, 137, 138, 139, 140],
 ("spa",17): [78,80,82,83,84,84,86],
 ("zandvoort",44): [139,140,141,142,143,144,146],
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
   if (f,c,moves)!=(7,0,expected): raise SystemExit(f"{track} {seed}: {(f,c,moves)}")
 print("AI1EnergyPaceRegression: OK")
if __name__ == "__main__": main()
