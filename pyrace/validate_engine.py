"""Replay a Java game log through the Python engine and check every move's
verdict (ok / crash / finish) matches Java. This validates that track.py +
engine.py reproduce the Java physics.

Usage:
  python validate_engine.py <track_name> [log_path]
e.g.
  python validate_engine.py sprint ../last_game.log
"""
from __future__ import annotations

import re
import sys
import os

from track import Track
from engine import RaceState, Car

HERE = os.path.dirname(os.path.abspath(__file__))

HDR = re.compile(r"^player(\d+) name=\S+ kind=AI[12] start=(-?\d+),(-?\d+)")
MOVE = re.compile(
    r"^(\d+) p(\d+) AI[12] \S+ "
    r"v\((-?\d+),(-?\d+)\)→\((-?\d+),(-?\d+)\) "
    r"\((-?\d+),(-?\d+)\)→\((-?\d+),(-?\d+)\) (\w+)"
)


def java_outcome(tag: str) -> str:
    return {"ok": "ok", "FINISH": "finish", "CRASH": "crash"}[tag]


def main() -> int:
    track_name = sys.argv[1] if len(sys.argv) > 1 else "sprint"
    log_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "last_game.log")
    track = Track.load(os.path.join(HERE, "..", "tracks", f"{track_name}.track"))

    starts: dict[int, tuple[int, int]] = {}
    moves = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            m = HDR.match(line)
            if m:
                starts[int(m.group(1))] = (int(m.group(2)), int(m.group(3)))
                continue
            m = MOVE.match(line)
            if m:
                g = list(map(int, m.groups()[:10]))
                moves.append({
                    "pn": g[1], "vx": g[2], "vy": g[3], "nvx": g[4], "nvy": g[5],
                    "x": g[6], "y": g[7], "nx": g[8], "ny": g[9], "tag": m.group(11),
                })

    n = max(starts)
    state = RaceState(track=track, cars=[Car(*starts[i + 1]) for i in range(n)])

    ok = mismatch = 0
    mismatches = []
    for mv in moves:
        mover = mv["pn"] - 1
        # sync mover's pre-move state to the log (guards against drift)
        c = state.cars[mover]
        c.x, c.y, c.vx, c.vy = mv["x"], mv["y"], mv["vx"], mv["vy"]
        x1, y1, nx, ny = mv["x"], mv["y"], mv["nx"], mv["ny"]

        if track.crosses_finish(x1, y1, nx, ny):
            mine = "finish"
        elif not state.is_legal(x1, y1, nx, ny, mover):
            mine = "crash"
        else:
            mine = "ok"

        want = java_outcome(mv["tag"])
        if mine == want:
            ok += 1
        else:
            mismatch += 1
            if len(mismatches) < 15:
                mismatches.append(
                    f"  p{mv['pn']} ({x1},{y1})->({nx},{ny}) v({mv['vx']},{mv['vy']})->"
                    f"({mv['nvx']},{mv['nvy']}): java={want} python={mine}")

        # apply to state
        c.x, c.y, c.vx, c.vy = nx, ny, mv["nvx"], mv["nvy"]
        if want in ("finish", "crash"):
            c.done = True

    total = ok + mismatch
    print(f"track={track_name}  moves={total}  match={ok}  mismatch={mismatch}  "
          f"({100.0 * ok / max(1, total):.1f}%)")
    for line in mismatches:
        print(line)
    return 0 if mismatch == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
