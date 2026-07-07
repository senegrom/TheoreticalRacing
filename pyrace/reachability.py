"""Load the exact turnsToFinish reachability map exported by the Java game
(`--dump-reach`). This is the velocity-aware feature distAt lacks: turns to
cross the finish from state (x,y,vx,vy), or BIG if the state is dead
(over-speeding into a wall / no feasible line). Same aliveIdx as RaceGame.
"""
from __future__ import annotations

import os
import subprocess

import numpy as np

JAVA_MAX = 2147483647   # Integer.MAX_VALUE = unreachable/dead
BIG = JAVA_MAX

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
JAR = os.path.join(ROOT, "theoreticRacing.jar")
CACHE = os.path.join(HERE, "data")


class Reach:
    def __init__(self, w: int, h: int, vmax: int, turns: np.ndarray):
        self.w, self.h, self.vmax = w, h, vmax
        self.span = 2 * vmax + 1
        self.turns = turns

    def _idx(self, x: int, y: int, vx: int, vy: int) -> int:
        return ((x * self.h + y) * self.span + (vx + self.vmax)) * self.span + (vy + self.vmax)

    def turns_to_finish(self, x: int, y: int, vx: int, vy: int) -> int:
        if not (0 <= x < self.w and 0 <= y < self.h
                and abs(vx) <= self.vmax and abs(vy) <= self.vmax):
            return BIG
        return int(self.turns[self._idx(x, y, vx, vy)])

    def alive(self, x: int, y: int, vx: int, vy: int) -> bool:
        return self.turns_to_finish(x, y, vx, vy) < BIG


def load_reach(path: str) -> Reach:
    with open(path, "rb") as f:
        hdr = np.frombuffer(f.read(12), dtype="<i4")
        turns = np.frombuffer(f.read(), dtype="<i4")
    return Reach(int(hdr[0]), int(hdr[1]), int(hdr[2]), turns)


def ensure_reach(track_name: str) -> Reach:
    """Dump the track's reachability via Java if not cached, then load it."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"reach_{track_name}.bin")
    if not os.path.isfile(path):
        subprocess.run(["java", "-jar", JAR, "--dump-reach", path, "--track", track_name],
                       capture_output=True, text=True, timeout=300)
    return load_reach(path)
