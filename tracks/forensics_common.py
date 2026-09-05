"""Shared primitives for the campaign forensic tools.

The standalone forensic scripts all consume the same race-log grammar,
reachability dump, and interactive move-oracle protocol, and the
regression pins all hash the same normalized projection of a log.
Keeping those formats here prevents small parser and process-lifecycle
differences from changing an investigation's result.
"""

from pathlib import Path
import hashlib
import re
import struct
import subprocess
import sys
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
    r"\((-?\d+),(-?\d+)\)\S\((-?\d+),(-?\d+)\) "
    r"(ok|CRASH|FINISH|TIMEOUT|LAP \d+/\d+)(.*)$"
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
    detail: str = ""


def parse_move(line):
    """Parse one behavior-bearing move line, or return ``None``.

    ``status`` is the outcome word (``ok``, ``CRASH``, ``FINISH``, ``TIMEOUT``
    or ``LAP n/m``) and ``detail`` whatever the game appended to it, such as
    `` place=8`` or a checkpoint mark.
    """
    match = MOVE_LINE.match(line)
    if match is None:
        return None
    return LogMove(
        int(match.group(1)), int(match.group(2)), match.group(3),
        int(match.group(4)), int(match.group(5)),
        int(match.group(6)), int(match.group(7)),
        int(match.group(8)), int(match.group(9)),
        int(match.group(10)), int(match.group(11)), match.group(12),
        match.group(13),
    )


def normalized_lines(text: str) -> list[str]:
    """Project a race log onto its behavior-bearing lines, kind labels erased.

    The regression pins freeze SHA-256 digests over exactly this projection,
    so the line predicate, its order, and the AI1-then-AI2 replacement order
    must stay as they are.
    """
    return [
        line.replace("AI1", "AI").replace("AI2", "AI")
        for line in text.splitlines()
        if line.startswith("player")
        or line.startswith("# turns")
        or line.startswith("# results")
        or (line and line[0].isdigit())
    ]


def normalized_sha256(text: str) -> str:
    """Digest of ``normalized_lines`` joined by newlines, as the pins store it."""
    return hashlib.sha256("\n".join(normalized_lines(text)).encode("utf-8")).hexdigest()


def race_events(
    text: str,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]], dict[int, int]]:
    """Return ``(finishers, crashes, moves)`` for one race log.

    ``finishers`` and ``crashes`` list ``(player, own_move_count)`` in log
    order; ``moves`` maps every player to its total move count.
    """
    moves: dict[int, int] = {}
    finishers: list[tuple[int, int]] = []
    crashes: list[tuple[int, int]] = []
    for line in text.splitlines():
        match = re.match(r"^(\d+) p(\d+) ", line)
        if match is None:
            continue
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if "FINISH" in line:
            finishers.append((player, moves[player]))
        if "CRASH" in line:
            crashes.append((player, moves[player]))
    return finishers, crashes, moves


def finishers(text: str) -> list[tuple[int, int]]:
    """``(player, own_move_count)`` for every finisher, in log order."""
    return race_events(text)[0]


def player_moves(text: str) -> dict[int, int]:
    """Every player's total move count."""
    return race_events(text)[2]


class Reach:
    """Read-only view of a ``--dump-reach`` little-endian binary."""

    HEADER = struct.Struct("<iii")
    VALUE = struct.Struct("<i")

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
        self._payload = memoryview(self._data)[self.HEADER.size:]

    def turns(self, x, y, vx, vy):
        if not (0 <= x < self.w and 0 <= y < self.h):
            return None
        if abs(vx) > self.vmax or abs(vy) > self.vmax:
            return None
        index = (
            ((x * self.h + y) * self.span + (vx + self.vmax)) * self.span
            + (vy + self.vmax)
        )
        value = self.VALUE.unpack_from(self._payload, index * self.VALUE.size)[0]
        return None if value == INF else value


def log_player_count(log):
    """Infer the active field size from a game log's player declarations."""
    count = 0
    with open(log, encoding="utf-8", errors="replace") as lines:
        for line in lines:
            start = START_LINE.match(line)
            if start is not None:
                count = max(count, int(start.group(1)))
    if count == 0:
        raise ValueError("log has no player declarations: %s" % log)
    return count


class ReplayBoard(list):
    """A complete oracle board plus its race clock/profile. Legacy callers may
    still use five-field cars; full replay explicitly requests seven fields."""

    def __init__(self, cars=(), *, laps=1, turns=0, complete=False):
        super().__init__(cars)
        self.laps = laps
        self.turns = turns
        self.complete = complete

    def copy(self):
        return ReplayBoard(self, laps=self.laps, turns=self.turns, complete=self.complete)


class Transition(NamedTuple):
    status: str
    lap: int
    gate: int
    checkpoints: int


class CandidateMask(str):
    def __new__(cls, value, transitions, laps):
        result = super().__new__(cls, value)
        result.transitions = tuple(transitions)
        result.laps = laps
        return result


def parse_v2_answer(line, laps):
    parts = line.strip().split(';')
    if len(parts) != 4 or parts[0] != 'v2':
        raise ValueError('malformed V2 oracle answer')
    direction = tuple(int(v) for v in parts[1].split(','))
    if direction not in DIRS or not re.fullmatch(r'[FXBDAT]{9}', parts[2]):
        raise ValueError('invalid V2 oracle direction/mask')
    transitions = []
    for symbol, token in zip(parts[2], parts[3].split('|')):
        fields = token.split(',')
        if len(fields) != 4:
            raise ValueError('malformed V2 transition')
        status, lap, gate, checkpoints = fields
        t = Transition(status, int(lap), int(gate), int(checkpoints))
        allowed = {'F': ('FINISH',), 'X': ('CRASH',), 'B': ('CRASH',),
                   'T': ('TIMEOUT',), 'A': ('OK', 'LAP'), 'D': ('OK', 'LAP')}
        if status not in allowed[symbol] or not (0 <= t.lap <= laps and 0 <= t.gate <= 2
                                                and 0 <= t.checkpoints <= 3):
            raise ValueError('inconsistent V2 transition')
        transitions.append(t)
    if len(transitions) != 9 or len(parts[3].split('|')) != 9:
        raise ValueError('V2 answer must contain exactly nine transitions')
    return direction[0], direction[1], CandidateMask(parts[2], transitions, laps)


def reconstruct_board(log, target, player_count=8, *, complete=False):
    """Return the board immediately before global move ``target``.

    The result is ``(cars, mover, real_moves)``.  Each car is
    ``(x, y, vx, vy, fate)``, or with complete=True additionally ``lap, gate``.
    Fate is 0 for live, 90 for finished or timed out, and 99 for crashed. ``mover`` is zero-based; ``real_moves`` contains parsed
    log moves from the target onward.
    """
    cars = [None] * player_count
    laps = 1
    mover = None
    real_moves = []

    with open(log, encoding="utf-8", errors="replace") as lines:
        for line in lines:
            if line.startswith('# laps '):
                laps = int(line.split()[2])
                if laps > 1 and not complete:
                    raise ValueError('multi-lap replay requires complete=True (use oracle_roll)')
            start = START_LINE.match(line)
            if start is not None:
                player = int(start.group(1))
                if 1 <= player <= player_count:
                    cars[player - 1] = [
                        int(start.group(2)), int(start.group(3)), 0, 0, 0
                    ] + ([0, 1] if complete else [])
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
            progress = cars[index][5:] if complete else []
            if complete:
                if 'cp1' in move.detail.split():
                    progress[1] = 2
                if 'cp2' in move.detail.split():
                    progress[1] = 0
                if move.status.startswith('LAP '):
                    lap, total = map(int, move.status.split()[1].split('/'))
                    if total != laps:
                        raise ValueError('log lap event disagrees with its profile')
                    progress = [lap, 1]
                cars[index][5:] = progress
            if move.status == "CRASH":
                cars[index][4] = 99
            elif move.status in ("FINISH", "TIMEOUT"):
                cars[index][4] = 90
            else:
                cars[index] = [
                    move.new_x, move.new_y, move.new_vx, move.new_vy, 0
                ] + progress
            if complete and move.status in ('CRASH', 'FINISH', 'TIMEOUT'):
                cars[index][:4] = [-100000, -100000, 0, 0]

    if mover is None:
        raise ValueError("move %d was not found in %s" % (target, log))
    if any(car is None for car in cars):
        raise ValueError("log does not initialize all %d players" % player_count)
    return ReplayBoard((tuple(car) for car in cars), laps=laps, turns=target - 1,
                       complete=complete), mover, real_moves


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
        complete = isinstance(cars, ReplayBoard) and cars.complete
        header = ('v2,%d,%d,%d' % (mover, cars.turns, cars.laps)) if complete else str(mover)
        expected = 7 if complete else 5
        if any(len(car) != expected for car in cars):
            raise ValueError('oracle board has incomplete or mixed-version car states')
        query = header + ';' + ';'.join(','.join(str(v) for v in car) for car in cars)
        self.proc.stdin.write(query + "\n")
        self.proc.stdin.flush()
        self.asks += 1
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("oracle died while answering query")
            if line.startswith('v2;'):
                if not complete:
                    raise ValueError('unexpected V2 reply to a legacy query')
                return parse_v2_answer(line, cars.laps)
            answer = ORACLE_ANSWER.fullmatch(line.strip())
            if answer is not None:
                if complete:
                    raise ValueError('legacy oracle cannot replay complete lap state')
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


def configure_console(line_buffering=None):
    """Make behavior-bearing Unicode log lines printable on Windows."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="replace", line_buffering=line_buffering)
