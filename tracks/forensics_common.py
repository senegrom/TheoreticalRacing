"""Shared primitives for the campaign forensic tools.

The standalone forensic scripts all consume the same race-log grammar,
reachability dump, and interactive move-oracle protocol.  Keeping those
formats here prevents small parser and process-lifecycle differences from
changing an investigation's result.
"""

from pathlib import Path
import re
import struct
import subprocess
from typing import NamedTuple


INF = 2147483647
DIRS = [
    (-1, -1), (0, -1), (1, -1),
    (-1, 0), (0, 0), (1, 0),
    (-1, 1), (0, 1), (1, 1),
]
DIRNAMES = ["NW", "N", "NE", "W", "NONE", "E", "SW", "S", "SE"]

MOVE_LINE = re.compile(
    r"^(\d+) p(\d+) \S+ (\S+) v\((-?\d+),(-?\d+)\)\S\((-?\d+),(-?\d+)\) "
    r"\((-?\d+),(-?\d+)\)\S\((-?\d+),(-?\d+)\) (ok|CRASH|FINISH)"
)
START_LINE = re.compile(r"^player(\d+) name=.*? kind=\S+ start=(\d+),(\d+)")
ORACLE_ANSWER = re.compile(r"^(-?\d+),(-?\d+);([FXBDA]{9})$")


class LogMove(NamedTuple):
    index: int
    player: int
    direction: str
    old_vx: int
    old_vy: int
    new_vx: int
    new_vy: int
    x: int
    y: int
    new_x: int
    new_y: int
    status: str


def parse_move(line):
    """Parse one behavior-bearing move line, or return ``None``."""
    match = MOVE_LINE.match(line)
    if match is None:
        return None
    return LogMove(
        int(match.group(1)), int(match.group(2)), match.group(3),
        int(match.group(4)), int(match.group(5)),
        int(match.group(6)), int(match.group(7)),
        int(match.group(8)), int(match.group(9)),
        int(match.group(10)), int(match.group(11)), match.group(12),
    )


class Reach:
    """Read-only view of a ``--dump-reach`` little-endian binary."""

    HEADER = struct.Struct("<iii")

    def __init__(self, path):
        self._data = Path(path).read_bytes()
        if len(self._data) < self.HEADER.size:
            raise ValueError("reachability dump is shorter than its header")

        self.w, self.h, self.vmax = self.HEADER.unpack_from(self._data)
        if self.w <= 0 or self.h <= 0 or self.vmax < 0:
            raise ValueError("reachability dump has invalid dimensions")
        self.span = 2 * self.vmax + 1
        entries = self.w * self.h * self.span * self.span
        expected_size = self.HEADER.size + entries * 4
        if len(self._data) != expected_size:
            raise ValueError(
                "reachability dump size mismatch: expected %d bytes, found %d"
                % (expected_size, len(self._data))
            )
        self.arr = memoryview(self._data)[self.HEADER.size:].cast("i")

    def turns(self, x, y, vx, vy):
        if not (0 <= x < self.w and 0 <= y < self.h):
            return None
        if abs(vx) > self.vmax or abs(vy) > self.vmax:
            return None
        index = (
            ((x * self.h + y) * self.span + (vx + self.vmax)) * self.span
            + (vy + self.vmax)
        )
        value = self.arr[index]
        return None if value == INF else value


def reconstruct_board(log, target, player_count=8):
    """Return the board immediately before global move ``target``.

    The result is ``(cars, mover, real_moves)``.  Each car is
    ``(x, y, vx, vy, fate)``, where fate is 0 for live, 90 for finished, and
    99 for crashed. ``mover`` is zero-based; ``real_moves`` contains parsed
    log moves from the target onward.
    """
    cars = [None] * player_count
    mover = None
    real_moves = []

    with open(log, encoding="utf-8", errors="replace") as lines:
        for line in lines:
            start = START_LINE.match(line)
            if start is not None:
                player = int(start.group(1))
                if 1 <= player <= player_count:
                    cars[player - 1] = [
                        int(start.group(2)), int(start.group(3)), 0, 0, 0
                    ]
                continue

            move = parse_move(line)
            if move is None:
                continue
            if move.index >= target:
                real_moves.append(move)
                if move.index == target and mover is None:
                    mover = move.player - 1
                continue

            index = move.player - 1
            if not (0 <= index < player_count) or cars[index] is None:
                raise ValueError("move references an uninitialized player")
            if move.status == "CRASH":
                cars[index][4] = 99
            elif move.status == "FINISH":
                cars[index][4] = 90
            else:
                cars[index] = [
                    move.new_x, move.new_y, move.new_vx, move.new_vy, 0
                ]

    if mover is None:
        raise ValueError("move %d was not found in %s" % (target, log))
    if any(car is None for car in cars):
        raise ValueError("log does not initialize all %d players" % player_count)
    return [tuple(car) for car in cars], mover, real_moves


class Oracle:
    """Persistent adapter for the game's ``--query-moves`` protocol."""

    def __init__(self, track, jar, properties, seed=1):
        self.proc = subprocess.Popen(
            [
                "java", "-jar", str(jar), "--auto", "--track", track,
                "--props", str(properties), "--seed", str(seed),
                "--query-moves", "-", "-",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self.asks = 0

    def ask(self, mover, cars):
        """Return ``(dx, dy, mask)`` for a zero-based mover and car board."""
        if self.proc.stdin is None or self.proc.stdout is None:
            raise RuntimeError("oracle pipes are unavailable")
        query = str(mover) + ";" + ";".join(
            "%d,%d,%d,%d,%d" % tuple(car) for car in cars
        )
        self.proc.stdin.write(query + "\n")
        self.proc.stdin.flush()
        self.asks += 1
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("oracle died while answering query")
            answer = ORACLE_ANSWER.fullmatch(line.strip())
            if answer is not None:
                return int(answer.group(1)), int(answer.group(2)), answer.group(3)

    def close(self):
        if self.proc.poll() is not None:
            return
        try:
            if self.proc.stdin is not None:
                self.proc.stdin.write("quit\n")
                self.proc.stdin.flush()
            self.proc.wait(timeout=2)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            try:
                self.proc.terminate()
            except OSError:
                return
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
