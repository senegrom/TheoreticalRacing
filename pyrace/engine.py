"""Headless race engine — faithful port of tr.logic.RaceGame move resolution.

A `RaceState` holds N cars; `step(accel)` resolves the current car's move the
same way Java `commitMove` does: a finish crossing is checked first and is
unblockable; otherwise an illegal move (outside the corridor, crossing a border,
or landing on another car) crashes the car; otherwise it moves. The game ends
when N-1 of N cars are done.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from track import Track, AI_MAX_SPEED

# the 9 accelerations, Java Direction order is irrelevant to dynamics
ACCELS = [(dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]


def geometry_legal(track, x1, y1, x2, y2) -> bool:
    """Ported RaceGame.isMoveLegalGeometry: destination + ~2-per-unit interior
    samples inside the corridor, and the segment must not cross a border."""
    if not track.in_corridor(x2, y2):
        return False
    dxi, dyi = x2 - x1, y2 - y1
    n = max(2, math.ceil(math.hypot(dxi, dyi) * 2))
    for j in range(1, n):
        if not track.in_corridor(x1 + j * dxi / n, y1 + j * dyi / n):
            return False
    return not track.crosses_border(x1, y1, x2, y2)


@dataclass
class Car:
    x: int
    y: int
    vx: int = 0
    vy: int = 0
    place: int = 0          # 0 = still racing; >0 = final finishing place
    done: bool = False


@dataclass
class RaceState:
    track: Track
    cars: list[Car]
    turn: int = 0                 # index of the car to move next
    finished_first: int = 0       # cars that crossed the finish
    finished_last: int = 0        # cars that crashed
    over: bool = False

    def geometry_legal(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        return geometry_legal(self.track, x1, y1, x2, y2)

    def crashing_car(self, x: int, y: int, mover: int) -> bool:
        for i, c in enumerate(self.cars):
            if i == mover or c.done:
                continue
            if c.x == x and c.y == y:
                return True
        return False

    def is_legal(self, x1, y1, x2, y2, mover) -> bool:
        return self.geometry_legal(x1, y1, x2, y2) and not self.crashing_car(x2, y2, mover)

    def _advance(self) -> None:
        n = len(self.cars)
        if self.finished_first + self.finished_last >= n - (0 if n == 1 else 1):
            for c in self.cars:                       # last car placed by rule
                if c.place == 0:
                    c.place = self.finished_first + 1
                    c.done = True
            self.over = True
            return
        for _ in range(n):
            self.turn = (self.turn + 1) % n
            if not self.cars[self.turn].done:
                return

    def step(self, accel: tuple[int, int]) -> str:
        """Resolve the current car's move. Returns 'finish' | 'crash' | 'ok'."""
        c = self.cars[self.turn]
        nvx, nvy = c.vx + accel[0], c.vy + accel[1]
        nx, ny = c.x + nvx, c.y + nvy
        if self.track.crosses_finish(c.x, c.y, nx, ny):
            self.finished_first += 1
            c.place = self.finished_first
            c.x, c.y, c.vx, c.vy, c.done = nx, ny, nvx, nvy, True
            outcome = "finish"
        elif not self.is_legal(c.x, c.y, nx, ny, self.turn):
            c.place = len(self.cars) - self.finished_last
            self.finished_last += 1
            c.x, c.y, c.vx, c.vy, c.done = nx, ny, nvx, nvy, True
            outcome = "crash"
        else:
            c.x, c.y, c.vx, c.vy = nx, ny, nvx, nvy
            outcome = "ok"
        self._advance()
        return outcome

    def legal_accels(self, mover: int | None = None) -> list[tuple[int, int]]:
        """The accelerations available to the current car that keep |v|<=12
        (a finish crossing is always allowed even if it would exceed budget)."""
        c = self.cars[self.turn if mover is None else mover]
        out = []
        for a in ACCELS:
            nvx, nvy = c.vx + a[0], c.vy + a[1]
            if abs(nvx) > AI_MAX_SPEED or abs(nvy) > AI_MAX_SPEED:
                continue
            out.append(a)
        return out


def run_game(track: Track, starts: list[tuple[int, int]], policies) -> RaceState:
    """Run a full race. `policies[i]` maps (state, car_index) -> accel."""
    state = RaceState(track=track, cars=[Car(x, y) for (x, y) in starts])
    guard = 0
    while not state.over and guard < 100000:
        i = state.turn
        accel = policies[i](state, i)
        state.step(accel)
        guard += 1
    return state
