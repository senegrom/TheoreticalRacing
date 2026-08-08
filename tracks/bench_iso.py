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

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Props/logs must live OFF any cloud-synced directory (OneDrive rewrites
# wedge long benches); default to the system temp dir.
S = os.environ.get('RACING_WORK_DIR', tempfile.gettempdir())

spec = importlib.util.spec_from_file_location('bench_ai', os.path.join(REPO, 'tracks', 'bench_ai.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

MODE = sys.argv[1]
SEED0 = int(sys.argv[2]) if len(sys.argv) > 2 else 1
TRACKS = sys.argv[3:] or None

m.PROPS = os.path.join(S, 'iso_%s.properties' % MODE)
m.LOG = os.path.join(S, 'iso_%s.log' % MODE)
_user = os.path.join(REPO, 'user.properties')
_base = _user if os.path.exists(_user) else os.path.join(REPO, 'tracks', 'bench.properties')
shutil.copy(_base, m.PROPS)
try:
    if MODE == 'slow':
        m.SEEDS = [None]
        m.bench(TRACKS or m.SLOW_TRACKS)
    else:
        tracks = TRACKS or m.DEFAULT_TRACKS
        m.SEEDS = list(range(SEED0, SEED0 + 5))
        print('# seeds %s tracks %s' % (m.SEEDS, tracks))
        if MODE == '8car':
            m.bench(tracks)
        elif MODE == 'h2h':
            m.bench_field(tracks, 8, 4, 'h2h')
        elif MODE == '4car':
            orig = m.set_nplayers

            def force(n, _o=orig):
                _o(4)
            m.set_nplayers = force
            m.bench(tracks)
        elif MODE == '2car':
            orig = m.set_nplayers

            def force2(n, _o=orig):
                _o(2)
            m.set_nplayers = force2
            m.bench(tracks)
        else:
            raise SystemExit('unknown mode ' + MODE)
finally:
    for p in (m.PROPS, m.LOG):
        if os.path.exists(p):
            os.remove(p)
