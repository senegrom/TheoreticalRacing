"""Cross-era exhibition referee: race the champions of any two commits.

Build an era jar from a historic commit, then race it against the current
champion through dual --query-moves oracles -- each era's brain answers only
for its own four cars on a shared board; the CURRENT jar's candidate mask is
the rulebook (rules are era-invariant).

Era jar recipe (example, round-60 champion at commit 886fab9):
  git archive 886fab9 src | tar -x -C /tmp/era
  find /tmp/era/src -name '*.java' | sort > /tmp/era/srcs.txt
  javac --release 25 -encoding UTF-8 -d /tmp/era/classes @/tmp/era/srcs.txt
  jar --create --file era60.jar --main-class tr.main.Main -C /tmp/era/classes .
Place the era jar in the repo root (track files resolve against the jar's
directory) and set OLD_JAR below or via the OLD_JAR environment variable.

Usage: cross_era.py track1,track2,... seed1,seed2,...
Each (track, seed) runs twice with grid slots swapped so grid advantage
cancels; the report gives mean place and crashes per era.

First result on record (round 109 vs round 60, 24 races, 6 tracks):
NEW 4.438 vs OLD 4.562 mean place, both crash-free -- the edge lives
entirely on tracks where overtaking exists.
"""
import os, sys
sys.path.insert(0, 'E:/OneDrive/Coding/Java/theoreticRacing/tracks')
from forensics_common import DIRS, Oracle

ROOT = 'E:/OneDrive/Coding/Java/theoreticRacing'
S = os.environ.get('RACING_WORK_DIR', os.path.dirname(os.path.abspath(__file__)))
NEW_JAR = ROOT + '/theoreticRacing.jar'
OLD_JAR = os.environ.get('OLD_JAR', ROOT + '/era60.jar')

def start_positions(track, seed):
    """Ask the new jar for a real race's initial board by parsing a 0-move log?
    Simpler: run one race with --seed and read the start= lines from its log."""
    import subprocess
    log = os.path.join(S, 'cross_start_%s_%d.log' % (track, seed))
    subprocess.run(['java', '-jar', NEW_JAR, '--auto', '--track', track,
                    '--props', os.path.join(S, 'era_AI2.properties'),
                    '--seed', str(seed), '--log', log],
                   capture_output=True, timeout=300)
    starts = []
    import re
    for ln in open(log, encoding='utf-8', errors='replace'):
        m = re.match(r'^player(\d+) name=.*start=(\d+),(\d+)', ln)
        if m:
            starts.append((int(m.group(2)), int(m.group(3))))
    return starts

def race(track, seed, new_slots):
    starts = start_positions(track, seed)
    assert len(starts) == 8, starts
    cars = [[x, y, 0, 0, 0] for x, y in starts]
    new_o = Oracle(track, NEW_JAR, os.path.join(S, 'era_AI2.properties'))
    old_o = Oracle(track, OLD_JAR, os.path.join(S, 'era_AI1.properties'))
    place = [0] * 8
    next_place = 1
    turns = 0
    try:
        while turns < 400:
            turns += 1
            for i in range(8):
                if cars[i][4] != 0:
                    continue
                is_new = i in new_slots
                dx, dy, mask = (new_o if is_new else old_o).ask(i, cars)
                ref_mask = mask if is_new else new_o.ask(i, cars)[2]
                ci = DIRS.index((dx, dy))
                c = ref_mask[ci]
                x, y, vx, vy, _ = cars[i]
                if c == 'F':
                    cars[i][4] = 90
                    place[i] = next_place; next_place += 1
                    continue
                if c in 'XB':
                    cars[i][4] = 99
                    continue
                nvx, nvy = vx + dx, vy + dy
                cars[i] = [x + nvx, y + nvy, nvx, nvy, 0]
            live = [i for i in range(8) if cars[i][4] == 0]
            if len(live) <= 1:
                for i in live:
                    cars[i][4] = 90
                    place[i] = next_place; next_place += 1
                break
    finally:
        new_o.close(); old_o.close()
    # Crashed cars share the tail places (by crash order ~ position: give max place).
    for i in range(8):
        if place[i] == 0:
            place[i] = 8 if cars[i][4] == 99 else next_place
    return place, [cars[i][4] for i in range(8)]

def main():
    tracks = sys.argv[1].split(',') if len(sys.argv) > 1 else ['monza']
    seeds = [int(s) for s in sys.argv[2].split(',')] if len(sys.argv) > 2 else [1]
    tot_new, tot_old, n_new, n_old, crash_new, crash_old = 0, 0, 0, 0, 0, 0
    for track in tracks:
        for seed in seeds:
            for swap in (False, True):
                new_slots = {0, 2, 4, 6} if not swap else {1, 3, 5, 7}
                place, fate = race(track, seed, new_slots)
                np_, op_ = [], []
                for i in range(8):
                    (np_ if i in new_slots else op_).append(place[i])
                    if fate[i] == 99:
                        if i in new_slots: crash_new += 1
                        else: crash_old += 1
                tot_new += sum(np_); n_new += 4
                tot_old += sum(op_); n_old += 4
                print('%s s%d swap=%d  NEW places=%s  OLD places=%s' % (
                    track, seed, swap, sorted(np_), sorted(op_)))
    print('=' * 60)
    print('NEW (r109 champion): mean place %.3f  crashes %d' % (tot_new / n_new, crash_new))
    print('OLD (r60 champion):  mean place %.3f  crashes %d' % (tot_old / n_old, crash_old))

if __name__ == '__main__':
    main()
