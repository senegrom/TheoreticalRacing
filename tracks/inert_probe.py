"""Cheapest possible go/no-go for any AI1-only change: does it FIRE at all?

Runs an all-AI1 field and an all-AI2 field on the same track+seed and diffs
the move logs. Identical logs => the change is byte-inert (revert, don't
bench). Divergence => it fires; count where and how far. Also the standard
promotion self-tie: after mirroring AI1 into AI2, every race must be
move-identical.

Runs strictly sequentially (serialization law: never two
reachability-heavy JVMs at once). Props/logs go to RACING_WORK_DIR
(default: this script's directory); the base properties come from the
repo's local user.properties if present, else tracks/bench.properties.

Usage: inert_probe.py [track ...]   (default: the 5 traffic sinks)
       PROBE_SEEDS=6,7,8 to pick seeds (default 1,2,3)
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
WORK = os.environ.get('RACING_WORK_DIR', HERE)
JAR = os.path.join(REPO, 'theoreticRacing.jar')
_USER_PROPS = os.path.join(REPO, 'user.properties')
SRC_PROPS = _USER_PROPS if os.path.exists(_USER_PROPS) else os.path.join(HERE, 'bench.properties')
SINKS = ['lemans', 'sprint', 'triangle', 'hairpin', 'monaco']
SEEDS = [int(s) for s in os.environ.get('PROBE_SEEDS', '1,2,3').split(',')]

MOVE = re.compile(r'^(\d+) p(\d+) ')
# move lines embed the AI kind ("1 p1 AI1 NONE v(0,0)->..."), which differs
# trivially between the two runs -- normalize it out before diffing.
KIND = re.compile(r'^(\d+ p\d+ )AI[12] ')


def make_props(kind):
    with open(SRC_PROPS, encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'(player[1-8]Kind=)(AI[12]|HUMAN)', r'\1' + kind, text)
    text = re.sub(r'nPlayers=\d+', 'nPlayers=8', text)
    path = os.path.join(WORK, 'inert_%s.properties' % kind)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return path


def run(kind, props, track, seed):
    log = os.path.join(WORK, 'inert_%s_%s_s%d.log' % (kind, track, seed))
    if os.path.exists(log):
        os.remove(log)
    subprocess.run(['java', '-jar', JAR, '--auto', '--track', track,
                    '--props', props, '--log', log, '--seed', str(seed)],
                   capture_output=True, timeout=600)
    if not os.path.exists(log):
        return None
    with open(log, encoding='utf-8', errors='replace') as f:
        return [KIND.sub(r'\1', ln.rstrip('\n')) for ln in f if MOVE.match(ln)]


def main():
    tracks = sys.argv[1:] or SINKS
    p1, p2 = make_props('AI1'), make_props('AI2')
    total_div = 0
    for track in tracks:
        for seed in SEEDS:
            a = run('AI1', p1, track, seed)
            b = run('AI2', p2, track, seed)
            if a is None or b is None:
                print('%-10s s%d  RUN FAILED' % (track, seed))
                continue
            if a == b:
                print('%-10s s%d  INERT (%d moves identical)' % (track, seed, len(a)))
                continue
            first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
            total_div += 1
            print('%-10s s%d  DIVERGES at move %d/%d  (AI1 %d moves, AI2 %d moves)'
                  % (track, seed, first, min(len(a), len(b)), len(a), len(b)))
            if first < len(a) and first < len(b):
                print('      AI1: %s' % a[first])
                print('      AI2: %s' % b[first])
    print('\n%d/%d race(s) diverge' % (total_div, len(tracks) * len(SEEDS)))


main()
