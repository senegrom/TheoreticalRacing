#!/usr/bin/env python3
"""Race-running helpers for the champion regression pins.

configure_runtime() points a pin at an isolated copy of bench.properties;
set_all_to/set_kinds/set_nplayers edit its roster; run_track races one course
and returns the self-play counters, run_track_h2h the per-label places.

The AI1-vs-AI2 benchmark this file used to run (and its baseline cache and
command line) was retired on 2026-09-27: since round 222 both labels run the
same policy, so it compared the champion with itself. Measure a candidate
with tracks/fleet_grid.py and the mirrored screen instead.
"""

import os
from pathlib import Path
import shutil
import subprocess
import sys

if __package__:
    from .benchmark_io import configured_players, read_race, update_properties
else:
    # A pin may load this file by path rather than as a package.
    if str(Path(__file__).resolve().parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
    from benchmark_io import configured_players, read_race, update_properties

ROOT = Path(__file__).resolve().parents[1]
JAR = str(ROOT / 'theoreticRacing.jar')
LOG = ''
PROPS = ''


def configure_runtime(directory):
    """Point mutable benchmark files at an isolated runtime directory."""
    global LOG, PROPS
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    LOG = str(directory / 'last_game.log')
    PROPS = str(directory / 'bench.properties')
    shutil.copyfile(ROOT / 'tracks' / 'bench.properties', PROPS)


def require_runtime():
    if not PROPS or not LOG:
        raise RuntimeError('benchmark runtime is not configured')


def require_roster(kinds, label='benchmark'):
    players = configured_players(PROPS)
    if [kind for _, kind in players.values()] != list(kinds):
        raise ValueError(label + ' roster differs from the requested assignment')


def set_all_to(kind):
    """Assign every active slot, including slots absent from the source profile."""
    require_runtime()
    set_kinds([kind] * len(configured_players(PROPS)))


def set_kinds(kinds):
    """Assign the complete active roster by decoded Java-properties keys."""
    require_runtime()
    kinds = list(kinds)
    if not 1 <= len(kinds) <= 9 or any(kind not in ('AI1', 'AI2') for kind in kinds):
        raise ValueError('benchmark requires 1-9 AI1/AI2 controllers')
    if len(configured_players(PROPS)) != len(kinds):
        raise ValueError('benchmark field size differs from the requested assignment')
    update_properties(PROPS, {'player%dKind' % n: kind
                              for n, kind in enumerate(kinds, 1)})
    require_roster(kinds)


def set_nplayers(n):
    """Set the active field size and reject a profile that clamps it away."""
    require_runtime()
    if type(n) is not int or not 1 <= n <= 9:
        raise ValueError('benchmark requires a field size from 1 to 9')
    update_properties(PROPS, {'nPlayers': str(n)})
    if len(configured_players(PROPS)) != n:
        raise ValueError('benchmark field size differs from the requested assignment (check maxPlayers)')


def parse_race_log(path, expected_players=None):
    """Return finishes/crashes/finisher moves only for a complete classification."""
    try:
        return read_race(path, expected_players).self_play()
    except (OSError, ValueError):
        return None


def run_track(track, timeout=240, seed=None):
    require_runtime()
    cmd = ['java', '-Djava.awt.headless=true', '-jar', JAR, '--auto', '--track', track, '--props', PROPS, '--log', LOG]
    if seed is not None:
        cmd += ['--seed', str(seed)]
    if os.path.exists(LOG):
        os.remove(LOG)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 or 'Aborting' in r.stdout:
        if r.stderr.strip():
            print(r.stderr.rstrip(), file=sys.stderr)
        return None
    return parse_race_log(LOG, configured_players(PROPS))


def run_track_h2h(track, timeout=240, seed=None):
    """Run one race with the current PROPS kinds. Returns
    {kind: (sum_places, count, crashes)} or None if invalid."""
    require_runtime()
    cmd = ['java', '-Djava.awt.headless=true', '-jar', JAR, '--auto', '--track', track, '--props', PROPS, '--log', LOG]
    if seed is not None:
        cmd += ['--seed', str(seed)]
    if os.path.exists(LOG):
        os.remove(LOG)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 or 'Aborting' in r.stdout or not os.path.exists(LOG):
        if r.stderr.strip():
            print(r.stderr.rstrip(), file=sys.stderr)
        return None
    try:
        race = read_race(LOG, configured_players(PROPS))
        out = {}
        for kind in ('AI1', 'AI2'):
            numbers = [n for n, (_, k) in race.players.items() if k == kind]
            if not numbers:
                raise ValueError('mixed benchmark requires both AI cohorts')
            out[kind] = (sum(race.places[n] for n in numbers), len(numbers),
                         sum(n in race.crashed for n in numbers))
        return out
    except (OSError, ValueError) as error:
        print('benchmark log: ' + str(error), file=sys.stderr)
        return None
