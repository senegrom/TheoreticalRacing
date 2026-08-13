"""Fully-isolated bench stage runner: props + log live in the scratchpad
(LOCAL disk, not OneDrive) to dodge sync-lock contention on the repo dir.

Usage: bench_iso.py MODE [SEED0] [track1 track2 ...]
  MODE: 8car | h2h | 4car | 2car | slow    (SEED0: first of 5 seeds, default 1)
  With explicit tracks, benches only those (chunked runs under the
  background-task lifetime cap; totals summed across chunks afterwards).
"""
import importlib.util
import os
import shutil
import sys
import tempfile

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Props/logs must live OFF any cloud-synced directory (OneDrive rewrites
# wedge long benches); default to the system temp dir.
S = os.environ.get('RACING_WORK_DIR', tempfile.gettempdir())

spec = importlib.util.spec_from_file_location('bench_ai', os.path.join(REPO, 'tracks', 'bench_ai.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def main(argv):
    if not argv:
        raise SystemExit('usage: bench_iso.py MODE [SEED0] [track1 track2 ...]')
    mode = argv[0]
    seed0 = int(argv[1]) if len(argv) > 1 else 1
    tracks_arg = argv[2:] or None

    m.PROPS = os.path.join(S, 'iso_%s.properties' % mode)
    m.LOG = os.path.join(S, 'iso_%s.log' % mode)
    user = os.path.join(REPO, 'user.properties')
    base = user if os.path.exists(user) else os.path.join(REPO, 'tracks', 'bench.properties')
    shutil.copy(base, m.PROPS)
    original_set_nplayers = m.set_nplayers
    try:
        if mode == 'slow':
            m.SEEDS = [None]
            return m.bench(tracks_arg or m.SLOW_TRACKS)

        tracks = tracks_arg or m.DEFAULT_TRACKS
        m.SEEDS = list(range(seed0, seed0 + 5))
        print('# seeds %s tracks %s' % (m.SEEDS, tracks))
        if mode == '8car':
            return m.bench(tracks)
        if mode == 'h2h':
            return m.bench_field(tracks, 8, 4, 'h2h')
        if mode == '4car':
            original = m.set_nplayers

            def force(_n, setter=original):
                setter(4)
            m.set_nplayers = force
            return m.bench(tracks)
        if mode == '2car':
            original = m.set_nplayers

            def force2(_n, setter=original):
                setter(2)
            m.set_nplayers = force2
            return m.bench(tracks)
        raise SystemExit('unknown mode ' + mode)
    finally:
        m.set_nplayers = original_set_nplayers
        for path in (m.PROPS, m.LOG):
            if os.path.exists(path):
                os.remove(path)


if __name__ == '__main__':
    raise SystemExit(0 if main(sys.argv[1:]) else 1)
