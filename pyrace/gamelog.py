"""Parse a Java game log into (start positions, moves). Shared by
validate_engine.py and extract_data.py.
"""
from __future__ import annotations

import re

_HDR = re.compile(r"^player(\d+) name=\S+ kind=(AI[12]) start=(-?\d+),(-?\d+)")
_MOVE = re.compile(
    r"^(\d+) p(\d+) AI[12] \S+ "
    r"v\((-?\d+),(-?\d+)\)→\((-?\d+),(-?\d+)\) "
    r"\((-?\d+),(-?\d+)\)→\((-?\d+),(-?\d+)\) (\w+)"
)


def parse_log(path: str):
    """Return (starts: {player_num: (x,y)}, moves: list of dicts).
    Each move: pn, x,y, vx,vy (pre), nx,ny, nvx,nvy (post), tag."""
    starts, moves = {}, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = _HDR.match(line)
            if m:
                starts[int(m.group(1))] = (int(m.group(3)), int(m.group(4)))
                continue
            m = _MOVE.match(line)
            if m:
                g = list(map(int, m.groups()[:10]))
                moves.append({
                    "pn": g[1], "vx": g[2], "vy": g[3], "nvx": g[4], "nvy": g[5],
                    "x": g[6], "y": g[7], "nx": g[8], "ny": g[9], "tag": m.group(11),
                })
    return starts, moves
