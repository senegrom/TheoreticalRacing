"""Evaluate the behaviour-cloned policy by actually racing it in the Python
engine, and compare to AI2.9's real numbers on the same track/starts.

For each track: run the Java game (AI2.9) to get the start positions and the
reference finishes/avg-moves, then run an all-clone field in the engine from the
same starts and report finishes / crashes / avg-moves.

Usage: python eval_policy.py [track1 track2 ...]
"""
from __future__ import annotations

import os
import subprocess
import sys

import numpy as np
import torch

from track import Track
from engine import RaceState, Car, ACCELS
from features import compute_dist_map, encode, coast_stoppable, BIG
from gamelog import parse_log
from model import RacePolicy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
JAR = os.path.join(ROOT, "theoreticRacing.jar")
LOG = os.path.join(ROOT, "last_game.log")
PROPS = os.path.join(ROOT, "user.properties")
from extract_data import DEFAULT_TRACKS, set_all_ai1, run_track


def make_policy(model, track, dist, maxd, safe_filter=True):
    def policy(state: RaceState, i: int):
        c = state.cars[i]
        board = [(cc.x, cc.y, cc.vx, cc.vy, cc.done) for cc in state.cars]
        ego, opps, om, am = encode(board, i, track, dist, maxd)
        with torch.no_grad():
            lo = model(torch.tensor(ego[None]), torch.tensor(opps[None]),
                       torch.tensor(om[None]), torch.tensor(am[None]))
        lo = lo[0].numpy()
        if safe_filter:
            # restrict to legal moves whose resulting state can still brake to a
            # stop in the corridor (or crosses the finish) -- prevents the clone
            # from over-speeding into a dead end. Fall back to legal if none.
            safe = np.zeros(len(ACCELS), dtype=np.float32)
            for a_idx, (ax, ay) in enumerate(ACCELS):
                if am[a_idx] == 0:
                    continue
                nvx, nvy = c.vx + ax, c.vy + ay
                nx, ny = c.x + nvx, c.y + nvy
                if track.crosses_finish(c.x, c.y, nx, ny) or coast_stoppable(track, nx, ny, nvx, nvy):
                    safe[a_idx] = 1.0
            mask = safe if safe.any() else am
            lo = np.where(mask > 0, lo, -1e9)
        return ACCELS[int(lo.argmax())]
    return policy


def java_reference(track_name: str):
    _, moves = parse_log(LOG)
    fins = [m for m in moves if m["tag"] == "FINISH"]
    # moves per finisher = the move number index within that player's own moves
    per = {}
    counts = {}
    for m in moves:
        counts[m["pn"]] = counts.get(m["pn"], 0) + 1
        if m["tag"] == "FINISH":
            per[m["pn"]] = counts[m["pn"]]
    avg = np.mean(list(per.values())) if per else 0.0
    crashes = sum(1 for m in moves if m["tag"] == "CRASH")
    return len(per), crashes, avg


def eval_track(model, track_name: str):
    t = Track.load(os.path.join(ROOT, "tracks", f"{track_name}.track"))
    dist = compute_dist_map(t)
    maxd = float(dist[dist < BIG].max()) if (dist < BIG).any() else 1.0
    starts, _ = parse_log(LOG)
    n = max(starts)
    pol = make_policy(model, t, dist, maxd)

    state = RaceState(track=t, cars=[Car(*starts[i + 1]) for i in range(n)])
    moves_of = [0] * n
    fin_moves = []
    guard = 0
    while not state.over and guard < 20000:
        i = state.turn
        moves_of[i] += 1
        out = state.step(pol(state, i))
        if out == "finish":
            fin_moves.append(moves_of[i])
        guard += 1
    return state.finished_first, state.finished_last, (np.mean(fin_moves) if fin_moves else 0.0)


def main() -> int:
    tracks = sys.argv[1:] or DEFAULT_TRACKS
    torch.set_num_threads(1)
    model = RacePolicy()
    model.load_state_dict(torch.load(os.path.join(HERE, "data", "bc_policy.pt")))
    model.eval()

    with open(PROPS, encoding="utf-8") as f:
        backup = f.read()
    print(f"{'track':16} | {'clone f/c mv':>16} | {'AI2.9 f/c mv':>16}")
    print("-" * 58)
    tot = [0, 0, 0.0, 0]
    try:
        with open(PROPS, "w", encoding="utf-8") as f:
            f.write(set_all_ai1(backup))
        for tr in tracks:
            try:
                if not run_track(tr):
                    print(f"{tr:16} | INVALID"); continue
            except subprocess.TimeoutExpired:
                print(f"{tr:16} | TIMEOUT"); continue
            jf, jc, jm = java_reference(tr)
            cf, cc, cm = eval_track(model, tr)
            print(f"{tr:16} | {cf}/{cc} mv={cm:5.1f}    | {jf}/{jc} mv={jm:5.1f}")
            tot[0] += cf; tot[1] += cc; tot[2] += cm; tot[3] += 1
    finally:
        with open(PROPS, "w", encoding="utf-8") as f:
            f.write(backup)
    print("-" * 58)
    print(f"{'TOTAL':16} | clone f={tot[0]} c={tot[1]} mv={tot[2]/max(1,tot[3]):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
