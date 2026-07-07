"""Load a .track file and derive its racing geometry.

Ported from tr.logic.RaceGame#buildTrackGeometry / makeStartZone /
computeFinishForward. A track is two border polylines; from them we derive the
finish line + racing direction, the start zone band, and the corridor polygon
used for move-legality tests.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union

START_ZONE_WIDTH = 2.0   # RaceGame.startZoneWidth
AI_MAX_SPEED = 12        # RaceGame.AI_MAX_SPEED
_TOL = 0.5               # approximation of getToleranceExpandedShape's stroke


def _parse_points(s: str) -> list[tuple[int, int]]:
    pts = []
    for pair in s.split(";"):
        pair = pair.strip()
        if not pair:
            continue
        xy = pair.split(",")
        if len(xy) != 2:
            continue
        pts.append((int(xy[0]), int(xy[1])))
    return pts


@dataclass
class Track:
    name: str
    grid_x: int
    grid_y: int
    left: list[tuple[int, int]]
    right: list[tuple[int, int]]

    # derived
    finish: tuple[tuple[int, int], tuple[int, int]] = field(default=None)
    finish_fwd: tuple[float, float] = field(default=None)
    start_line: tuple[tuple[int, int], tuple[int, int]] = field(default=None)
    _allowed: Polygon = field(default=None, repr=False)
    _left_ls: LineString = field(default=None, repr=False)
    _right_ls: LineString = field(default=None, repr=False)
    _finish_ls: LineString = field(default=None, repr=False)

    @classmethod
    def load(cls, path: str) -> "Track":
        name, gx, gy, left, right = "", 0, 0, [], []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("name="):
                    name = line[5:]
                elif line.startswith("gameX="):
                    gx = int(line[6:])
                elif line.startswith("gameY="):
                    gy = int(line[6:])
                elif line.startswith("trackLeft="):
                    left = _parse_points(line[len("trackLeft="):])
                elif line.startswith("trackRight="):
                    right = _parse_points(line[len("trackRight="):])
        t = cls(name=name, grid_x=gx, grid_y=gy, left=left, right=right)
        t._derive()
        return t

    def _derive(self) -> None:
        fL, fR = self.left[-1], self.right[-1]
        sL, sR = self.left[0], self.right[0]
        self.finish = (fL, fR)
        self.start_line = (sL, sR)
        self._finish_ls = LineString([fL, fR])

        # racing direction = avg of last left+right border segments
        hx = hy = 0.0
        if len(self.left) >= 2:
            p = self.left[-2]
            hx += fL[0] - p[0]; hy += fL[1] - p[1]
        if len(self.right) >= 2:
            p = self.right[-2]
            hx += fR[0] - p[0]; hy += fR[1] - p[1]
        if hx == 0 and hy == 0:            # fallback: finish-line normal
            hx = -(fR[1] - fL[1]); hy = fR[0] - fL[0]
        n = math.hypot(hx, hy)
        self.finish_fwd = (0.0, 0.0) if n == 0 else (hx / n, hy / n)

        # corridor polygon = left forward + right reversed, closed
        corridor = Polygon(self.left + self.right[::-1])
        if not corridor.is_valid:
            corridor = corridor.buffer(0)
        # start zone band off the start line (makeStartZone)
        ln = math.hypot(sR[0] - sL[0], sR[1] - sL[1]) or 1.0
        dx = (sL[1] - sR[1]) * START_ZONE_WIDTH / ln
        dy = (sR[0] - sL[0]) * START_ZONE_WIDTH / ln
        zone = Polygon([(sL[0], sL[1]), (sR[0], sR[1]),
                        (sR[0] + dx, sR[1] + dy), (sL[0] + dx, sL[1] + dy)])
        self._allowed = unary_union([corridor, zone]).buffer(_TOL)
        self._left_ls = LineString(self.left)
        self._right_ls = LineString(self.right)

    # -------- legality primitives (used by engine.py) --------

    def in_corridor(self, x: float, y: float) -> bool:
        return self._allowed.contains(Point(x, y)) or self._allowed.touches(Point(x, y))

    def crosses_border(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        seg = LineString([(x1, y1), (x2, y2)])
        return seg.crosses(self._left_ls) or seg.crosses(self._right_ls)

    def crosses_finish(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        seg = LineString([(x1, y1), (x2, y2)])
        if not seg.intersects(self._finish_ls):
            return False
        fdx, fdy = self.finish_fwd
        return (x2 - x1) * fdx + (y2 - y1) * fdy > 0
