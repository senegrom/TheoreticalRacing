"""Feature encoding for the learned policy.

A decision is (board state, mover, track). We encode it as:
  - ego vector: the mover's own velocity / position / progress  [EGO_DIM]
  - opponent tokens: one per other car, relative state           [MAX_OPP, OPP_DIM]
  - opponent mask: which opponent slots are real                 [MAX_OPP]
  - action mask: which of the 9 accelerations are legal moves    [N_ACTIONS]

`dist_map` (ported from RaceGame.computeDistMap) is the 8-connected BFS distance
from the finish through the corridor — the key "how far to go" progress signal,
so the net does not have to relearn navigation.
"""
from __future__ import annotations

from collections import deque

import numpy as np

from track import Track, AI_MAX_SPEED
from engine import RaceState, Car, ACCELS, geometry_legal


def _sgn(v: int) -> int:
    return (v > 0) - (v < 0)


def coast_stoppable(track: Track, x: int, y: int, vx: int, vy: int, target: int = 0) -> bool:
    """Can the car brake down to a manageable corner speed (both |v| components
    <= target) from (x,y,vx,vy) without leaving the corridor? A cheap proxy for
    AI2.9's alive/feasibility check -- the braking signal distAt lacks. target=0
    means brake to a full stop (strict); target~2-3 allows carrying speed
    through corners the way AI2.9 does, so the clone isn't over-cautious. A
    finish crossing counts as a safe escape."""
    px, py, cvx, cvy = x, y, vx, vy
    for _ in range(2 * AI_MAX_SPEED + 2):
        if abs(cvx) <= target and abs(cvy) <= target:
            return True
        cvx -= _sgn(cvx)
        cvy -= _sgn(cvy)
        nx, ny = px + cvx, py + cvy
        if track.crosses_finish(px, py, nx, ny):
            return True
        if not geometry_legal(track, px, py, nx, ny):
            return False
        px, py = nx, ny
    return True

MAX_CARS = 8
MAX_OPP = MAX_CARS - 1
EGO_DIM = 7               # +1: ego turns_to_finish
OPP_DIM = 7
N_ACTIONS = len(ACCELS)   # 9
BIG = 1 << 30
JAVA_MAX = 2147483647     # unreachable/dead in the reachability map


def compute_dist_map(track: Track) -> np.ndarray:
    """8-connected BFS from the finish line through corridor cells. Returns a
    (w, h) int array of steps-to-finish (BIG where unreachable)."""
    w, h = track.grid_x + 1, track.grid_y + 1
    dist = np.full((w, h), BIG, dtype=np.int32)
    (fx1, fy1), (fx2, fy2) = track.finish
    q = deque()
    samples = int(np.ceil(np.hypot(fx2 - fx1, fy2 - fy1) * 2)) + 1
    for i in range(samples + 1):
        t = i / samples
        x = int(round(fx1 + t * (fx2 - fx1)))
        y = int(round(fy1 + t * (fy2 - fy1)))
        if 0 <= x < w and 0 <= y < h and dist[x, y] == BIG:
            dist[x, y] = 0
            q.append((x, y))
    while q:
        x, y = q.popleft()
        d = dist[x, y]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and dist[nx, ny] == BIG and track.in_corridor(nx, ny):
                    dist[nx, ny] = d + 1
                    q.append((nx, ny))
    return dist


def dist_at(dist: np.ndarray, x: int, y: int) -> int:
    if 0 <= x < dist.shape[0] and 0 <= y < dist.shape[1]:
        return int(dist[x, y])
    return BIG


def encode(cars: list[tuple], mover: int, track: Track, dist: np.ndarray, maxd: float,
           reach, maxt: float):
    """cars: list of (x, y, vx, vy, done). Returns numpy arrays:
       ego [EGO_DIM], opps [MAX_OPP, OPP_DIM], opp_mask [MAX_OPP],
       act_mask [N_ACTIONS] (legal), succ_turns [N_ACTIONS] (normalized
       turns_to_finish of each move's result; 1.0 = dead), alive_mask
       [N_ACTIONS] (result is alive / on a feasible line)."""
    gx, gy = track.grid_x, track.grid_y
    x, y, vx, vy, _ = cars[mover]
    ego_d = dist_at(dist, x, y)
    ego_t = reach.turns_to_finish(x, y, vx, vy)
    ego = np.array([
        vx / AI_MAX_SPEED, vy / AI_MAX_SPEED,
        np.hypot(vx, vy) / AI_MAX_SPEED,
        x / gx, y / gy,
        min(ego_d, maxd) / maxd,
        1.0 if ego_t >= JAVA_MAX else min(ego_t, maxt) / maxt,
    ], dtype=np.float32)

    opps = np.zeros((MAX_OPP, OPP_DIM), dtype=np.float32)
    opp_mask = np.zeros(MAX_OPP, dtype=np.float32)
    j = 0
    for i, (ox, oy, ovx, ovy, odone) in enumerate(cars):
        if i == mover or j >= MAX_OPP:
            continue
        od = dist_at(dist, ox, oy)
        opps[j] = [
            (ox - x) / gx, (oy - y) / gy,
            (ovx - vx) / AI_MAX_SPEED, (ovy - vy) / AI_MAX_SPEED,
            (min(od, maxd) - min(ego_d, maxd)) / maxd,
            1.0 if odone else 0.0,
            1.0,   # present
        ]
        opp_mask[j] = 1.0
        j += 1

    # per-action: legality, the result's turns_to_finish (the key signal), and
    # whether the result is alive (on a feasible line). A finishing move is the
    # best possible (turns 0); a dead successor keeps succ_turns=1.0.
    st = RaceState(track=track, cars=[Car(*c) for c in cars], turn=mover)
    act_mask = np.zeros(N_ACTIONS, dtype=np.float32)
    succ_turns = np.ones(N_ACTIONS, dtype=np.float32)
    alive_mask = np.zeros(N_ACTIONS, dtype=np.float32)
    for a_idx, (ax, ay) in enumerate(ACCELS):
        nvx, nvy = vx + ax, vy + ay
        if abs(nvx) > AI_MAX_SPEED or abs(nvy) > AI_MAX_SPEED:
            continue
        nx, ny = x + nvx, y + nvy
        crosses = track.crosses_finish(x, y, nx, ny)
        if not (crosses or st.is_legal(x, y, nx, ny, mover)):
            continue
        act_mask[a_idx] = 1.0
        if crosses:
            succ_turns[a_idx] = 0.0
            alive_mask[a_idx] = 1.0
        else:
            tt = reach.turns_to_finish(nx, ny, nvx, nvy)
            if tt < JAVA_MAX:
                succ_turns[a_idx] = min(tt, maxt) / maxt
                alive_mask[a_idx] = 1.0
    return ego, opps, opp_mask, act_mask, succ_turns, alive_mask


def accel_index(dx: int, dy: int) -> int:
    return ACCELS.index((dx, dy))
