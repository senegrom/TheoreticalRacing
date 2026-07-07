"""Generate behaviour-cloning data: run AI2.9 (the frozen champion) on each
track, replay the log, and encode every (board state -> chosen move) decision.

The game is deterministic, so one trajectory per track. Output: data/bc_data.npz
with stacked feature arrays + integer action labels.

Usage: python extract_data.py [track1 track2 ...]
"""
from __future__ import annotations

import os
import subprocess
import sys

import numpy as np

from track import Track
from features import compute_dist_map, encode, accel_index, BIG, EGO_DIM, OPP_DIM, MAX_OPP, N_ACTIONS
from gamelog import parse_log

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
JAR = os.path.join(ROOT, "theoreticRacing.jar")
LOG = os.path.join(ROOT, "last_game.log")
PROPS = os.path.join(ROOT, "user.properties")

DEFAULT_TRACKS = [
    "silverstone", "monza", "spa", "monaco", "spielberg", "nurburgring", "lemans",
    "interlagos", "zandvoort", "hungaroring", "the_long_loop", "sprint", "hairpin",
    "triangle", "chicane", "bigoval", "curve", "zigzag", "coil", "slalom", "gear",
]


def set_all_ai1(text: str) -> str:
    import re
    return re.sub(r"(player[1-8]Kind=)AI[12]", r"\g<1>AI1", text)


def run_track(track: str) -> bool:
    r = subprocess.run(["java", "-jar", JAR, "--auto", "--track", track],
                       capture_output=True, text=True, timeout=300)
    return "Aborting" not in r.stdout


def extract_track(track_name: str):
    """Replay one track's log -> list of (ego, opps, opp_mask, act_mask, action)."""
    t = Track.load(os.path.join(ROOT, "tracks", f"{track_name}.track"))
    dist = compute_dist_map(t)
    maxd = float(dist[dist < BIG].max()) if (dist < BIG).any() else 1.0
    starts, moves = parse_log(LOG)
    n = max(starts)
    cars = [[*starts[i + 1], 0, 0, False] for i in range(n)]   # x,y,vx,vy,done
    out = []
    for mv in moves:
        mover = mv["pn"] - 1
        c = cars[mover]
        c[0], c[1], c[2], c[3] = mv["x"], mv["y"], mv["vx"], mv["vy"]
        if mv["tag"] in ("ok", "FINISH"):     # imitate successful choices only
            board = [tuple(cc) for cc in cars]
            ax, ay = mv["nvx"] - mv["vx"], mv["nvy"] - mv["vy"]
            ego, opps, om, am = encode(board, mover, t, dist, maxd)
            out.append((ego, opps, om, am, accel_index(ax, ay)))
        c[0], c[1], c[2], c[3] = mv["nx"], mv["ny"], mv["nvx"], mv["nvy"]
        if mv["tag"] in ("FINISH", "CRASH"):
            c[4] = True
    return out


def main() -> int:
    tracks = sys.argv[1:] or DEFAULT_TRACKS
    with open(PROPS, encoding="utf-8") as f:
        backup = f.read()
    records = []
    try:
        with open(PROPS, "w", encoding="utf-8") as f:
            f.write(set_all_ai1(backup))
        for tr in tracks:
            try:
                if not run_track(tr):
                    print(f"  {tr}: INVALID"); continue
            except subprocess.TimeoutExpired:
                print(f"  {tr}: TIMEOUT"); continue
            recs = extract_track(tr)
            records.extend(recs)
            print(f"  {tr}: {len(recs)} examples")
    finally:
        with open(PROPS, "w", encoding="utf-8") as f:
            f.write(backup)

    if not records:
        print("no data"); return 1
    ego = np.stack([r[0] for r in records])
    opps = np.stack([r[1] for r in records])
    om = np.stack([r[2] for r in records])
    am = np.stack([r[3] for r in records])
    act = np.array([r[4] for r in records], dtype=np.int64)
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    path = os.path.join(HERE, "data", "bc_data.npz")
    np.savez_compressed(path, ego=ego, opps=opps, opp_mask=om, act_mask=am, action=act)
    print(f"\nsaved {len(records)} examples -> {path}")
    print(f"  ego {ego.shape} opps {opps.shape} act_mask {am.shape} action {act.shape}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
