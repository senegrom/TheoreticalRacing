#!/usr/bin/env python3
"""Score a mixed field by finishing places: candidate cars against champion cars.

The racecraft rule (CLAUDE.md) is lexicographic: a car's own place first, its
own time second. A fleet grid raced with candidateSlots=1,3,5,7 and another
with candidateSlots=2,4,6,8 puts the candidate in every slot exactly once per
seed, so grid advantage cancels. This reads the race logs of both grids and
reports, per policy, the mean finishing place, race wins, crashes, and the
per-track picture, plus the paired difference over mirrored races.

    python tracks/head_to_head.py <grid dir> [<grid dir> ...]

Every log carries '# candidate-slots a,b,c' (written by the game when the
property is set) and a '# results' section '1. NAME' ... in finishing order.
The unfinished eighth car of an eight-car race holds place 8; a crashed car
holds its crash place.
"""
from __future__ import annotations

import collections
import math
import pathlib
import re
import statistics
import sys

PLAYER = re.compile(r"^player(\d+) name=(\S+) kind=\S+ start=")
RESULT = re.compile(r"^(\d+)\.\s+(\S+)\s*$")
SLOTS = re.compile(r"^# candidate-slots ([0-9,]+)")
MOVE = re.compile(r"^(\d+) p(\d+) \S+ \S+ .*?(ok|CRASH|FINISH|TIMEOUT|LAP \d+/\d+)")


def read(path):
    names, places, slots, crashed = {}, {}, set(), set()
    in_results = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = PLAYER.match(line)
        if m:
            names[m.group(2)] = int(m.group(1))
            continue
        s = SLOTS.match(line)
        if s:
            slots = {int(x) for x in s.group(1).split(",") if x}
            continue
        if line.startswith("# results"):
            in_results = True
            continue
        if in_results:
            r = RESULT.match(line)
            if r and r.group(2) in names:
                places[names[r.group(2)]] = int(r.group(1))
            continue
        mv = MOVE.match(line)
        if mv and mv.group(3) == "CRASH":
            crashed.add(int(mv.group(2)))
    if not names or len(places) != len(names):
        return None
    return places, slots, crashed


def main() -> int:
    races = {}   # (track, seed) -> list of (places, slots, crashed) over the given grids
    for grid in sys.argv[1:]:
        for log in sorted(pathlib.Path(grid).glob("*_s*.log")):
            parsed = read(log)
            if parsed is None or not parsed[1]:
                continue
            track, seed = log.name[:-4].rsplit("_s", 1)
            races.setdefault((track, int(seed)), []).append(parsed)
    if not races:
        print("no mixed-field logs found (is candidateSlots set?)")
        return 1
    cand, champ = [], []
    cand_wins = champ_wins = cand_crash = champ_crash = 0
    per_track = collections.defaultdict(lambda: [[], []])
    paired = []
    for (track, seed), runs in sorted(races.items()):
        diff = []
        for places, slots, crashed in runs:
            c = [p for n, p in places.items() if n in slots]
            h = [p for n, p in places.items() if n not in slots]
            cand += c
            champ += h
            cand_wins += sum(1 for p in c if p == 1)
            champ_wins += sum(1 for p in h if p == 1)
            cand_crash += sum(1 for n in crashed if n in slots)
            champ_crash += sum(1 for n in crashed if n not in slots)
            per_track[track][0] += c
            per_track[track][1] += h
            diff.append(statistics.mean(c) - statistics.mean(h))
        if len(runs) >= 2:
            paired.append(statistics.mean(diff))
    n = len(cand)
    print("%d candidate car-races, %d champion car-races over %d races" % (n, len(champ), sum(len(r) for r in races.values())))
    mc, mh = statistics.mean(cand), statistics.mean(champ)
    print("mean place   candidate %.3f   champion %.3f   (lower is better; 4.500 is a tie in an 8-car field)" % (mc, mh))
    print("race wins    candidate %d   champion %d" % (cand_wins, champ_wins))
    print("crashes      candidate %d   champion %d" % (cand_crash, champ_crash))
    if paired:
        m = statistics.mean(paired)
        se = statistics.pstdev(paired) / math.sqrt(len(paired)) if len(paired) > 1 else float("nan")
        print("mirrored races %d: candidate minus champion mean place %+.3f  (standard error %.3f; negative favours the candidate)"
              % (len(paired), m, se))
    rows = sorted(((statistics.mean(c) - statistics.mean(h), t, len(c)) for t, (c, h) in per_track.items() if c and h))
    print("\ntracks where the candidate gains most (mean place difference, candidate car-races):")
    for d, t, k in rows[:8]:
        print("    %-14s %+.3f  (%d)" % (t, d, k))
    print("tracks where it loses most:")
    for d, t, k in rows[-8:]:
        print("    %-14s %+.3f  (%d)" % (t, d, k))
    better = sum(1 for d, _, _ in rows if d < 0)
    print("\n%d tracks favour the candidate, %d the champion, %d tied" % (better, sum(1 for d, _, _ in rows if d > 0), sum(1 for d, _, _ in rows if d == 0)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
