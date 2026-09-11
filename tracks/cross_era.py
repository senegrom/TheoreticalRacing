"""Cross-era exhibition on non-checkpoint, single-lap courses.

Usage: cross_era.py track1,track2,... seed1,seed2,...

NEW_JAR is the current build; OLD_JAR selects a preserved historic JAR. Track
files resolve beside each JAR. RACING_WORK_DIR holds era_AI1.properties and
era_AI2.properties, each with an eight-AI roster. Every track/seed is mirrored.
The current oracle is the referee; the old oracle supplies only its own moves.

The legacy five-field protocol cannot carry checkpoint or lap progress. Such
courses, multi-lap profiles and scattered starts are rejected, not approximated.
Use both policies in one modern binary and head_to_head.py for those races.
A search horizon is not a finish: any incomplete race fails the entire report.
"""
from contextlib import ExitStack
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

if __package__:
    from .benchmark_io import configured_players, read_properties, read_race
    from .fleet_grid import digest
    from .forensics_common import DIRS, Oracle, START_LINE
else:
    from benchmark_io import configured_players, read_properties, read_race
    from fleet_grid import digest
    from forensics_common import DIRS, Oracle, START_LINE

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
S = os.environ.get('RACING_WORK_DIR', HERE)
NEW_JAR = os.path.join(ROOT, 'theoreticRacing.jar')
OLD_JAR = os.environ.get('OLD_JAR', os.path.join(ROOT, 'era60.jar'))


def experiment_identity(tracks):
    """Validate both era inputs, then snapshot them before/after the whole grid.

    Policy binaries and AI-kind labels may differ. Course bytes and all other
    properties must match; legacy queries cannot reconcile different profiles.
    Raw file hashes also detect changes hidden by last-wins properties parsing.
    """
    identity = {'jars': {}, 'properties': {}, 'tracks': {}}
    profiles = []
    for era, jar, props_name in (('new', NEW_JAR, 'era_AI2.properties'),
                                 ('old', OLD_JAR, 'era_AI1.properties')):
        jar = Path(jar).resolve()
        props_path = Path(S, props_name).resolve()
        identity['jars'][era] = (str(jar), digest(jar))
        identity['properties'][era] = (str(props_path), digest(props_path))
        players = configured_players(props_path)
        if len(players) != 8 or any(kind == 'HUMAN' for _, kind in players.values()):
            raise ValueError('both cross-era profiles require an eight-AI roster')
        profile = read_properties(props_path)
        for n in range(1, 10):
            profile.pop('player%dKind' % n, None)
        profiles.append(profile)
        identity['tracks'][era] = {}
        for track in tracks:
            if not re.fullmatch(r'[A-Za-z0-9_-]+', track):
                raise ValueError('invalid track name: ' + track)
            identity['tracks'][era][track] = digest(jar.parent / 'tracks' / (track + '.track'))
    if profiles[0] != profiles[1]:
        raise ValueError('cross-era profiles differ beyond AI-kind labels')
    if identity['tracks']['new'] != identity['tracks']['old']:
        raise ValueError('cross-era track data differ between the two installations')
    java = shutil.which('java')
    if java is None:
        raise ValueError('Java executable not found')
    identity['java'] = (str(Path(java).resolve()), digest(java))
    identity['java_options'] = {key: os.environ.get(key, '') for key in
                                ('JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS')}
    return identity


def start_positions(track, seed):
    """Extract numbered starts only from this invocation's completed race."""
    props = os.path.join(S, 'era_AI2.properties')
    # Never reuse cross_start_<track>_<seed>.log: a failed process must have no
    # previous output to fall back to, and concurrent invocations stay isolated.
    with tempfile.TemporaryDirectory(prefix='racing-cross-start-') as directory:
        log = Path(directory) / 'start.log'
        result = subprocess.run(
            ['java', '-jar', NEW_JAR, '--auto', '--track', track,
             '--props', props, '--seed', str(seed), '--log', str(log)],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=300, check=True,
        )
        race = read_race(log, configured_players(props))
        if len(race.players) != 8 or any(kind == 'HUMAN' for _, kind in race.players.values()):
            raise ValueError('cross-era requires an eight-AI roster')
        text = log.read_text(encoding='utf-8')
        if (race.profile['laps'] != '1' or race.profile['start-placement'] == 'scatter'
                or re.search(r'^\[laps\] gate geometry:', result.stdout, re.MULTILINE)
                or re.search(r' (?:cp1|cp2)(?: |$)', text, re.MULTILINE)):
            raise ValueError('legacy cross-era queries cannot carry checkpoint/lap or scattered-start state')
        starts = {}
        for line in text.splitlines():
            match = START_LINE.fullmatch(line)
            if match:
                if int(match[4] or 0) or int(match[5] or 0):
                    raise ValueError('legacy cross-era requires stationary starts')
                starts[int(match[1])] = (int(match[2]), int(match[3]))
        if set(starts) != set(race.players) or len(set(starts.values())) != 8:
            raise ValueError('incomplete or overlapping cross-era starts')
        return [starts[n] for n in sorted(starts)]


def classify(new_o, old_o, starts, new_slots, *, max_rounds=400):
    """Live-referee place ordering, with current-engine legality for both eras."""
    if (len(starts) != 8 or len(set(starts)) != 8 or max_rounds < 1
            or len(new_slots) != 4 or not set(new_slots) <= set(range(8))):
        raise ValueError('cross-era requires eight distinct starts, four new slots and a positive horizon')
    cars = [[x, y, 0, 0, 0] for x, y in starts]
    places = [0] * 8
    finished = crashed = 0
    for _ in range(max_rounds):
        for i in range(8):
            if cars[i][4] != 0:
                continue
            is_new = i in new_slots
            dx, dy, mask = (new_o if is_new else old_o).ask(i, cars)
            ref_mask = mask if is_new else new_o.ask(i, cars)[2]
            if not re.fullmatch(r'[FXBDA]{9}', ref_mask):
                raise ValueError('invalid legacy referee mask')
            outcome = ref_mask[DIRS.index((dx, dy))]
            if outcome == 'F':
                finished += 1
                places[i] = finished
                cars[i] = [-100000, -100000, 0, 0, 90]
            elif outcome in 'XB':
                places[i] = 8 - crashed
                crashed += 1
                cars[i] = [-100000, -100000, 0, 0, 99]
            else:
                x, y, vx, vy, _ = cars[i]
                nvx, nvy = vx + dx, vy + dy
                cars[i] = [x + nvx, y + nvy, nvx, nvy, 0]
            # The referee ends immediately after the seventh retirement, not
            # after the remaining slots have had a chance to crash or finish.
            if finished + crashed == 7:
                survivor = next(n for n, car in enumerate(cars) if car[4] == 0)
                places[survivor] = finished + 1
                cars[survivor][4] = 90
                return places, [car[4] for car in cars]
    raise ValueError('cross-era race incomplete after %d rounds; no classification' % max_rounds)


def race(track, seed, new_slots, *, max_rounds=400):
    starts = start_positions(track, seed)
    with ExitStack() as cleanup:
        new_o = Oracle(track, NEW_JAR, os.path.join(S, 'era_AI2.properties'))
        cleanup.callback(new_o.close)
        old_o = Oracle(track, OLD_JAR, os.path.join(S, 'era_AI1.properties'))
        cleanup.callback(old_o.close)
        return classify(new_o, old_o, starts, new_slots, max_rounds=max_rounds)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if len(args) > 2:
            raise ValueError('usage: cross_era.py track1,track2,... seed1,seed2,...')
        tracks = args[0].split(',') if args else ['hairpin']
        seeds = [int(s) for s in args[1].split(',')] if len(args) > 1 else [1]
        if (not tracks or any(not re.fullmatch(r'[A-Za-z0-9_-]+', t) for t in tracks)
                or len(set(tracks)) != len(tracks) or not seeds or len(set(seeds)) != len(seeds)):
            raise ValueError('tracks and seeds must be nonempty and unique')
        identity = experiment_identity(tracks)
        totals = {'new': [0, 0, 0], 'old': [0, 0, 0]}
        rows = []
        for track in tracks:
            for seed in seeds:
                for swap in (False, True):
                    new_slots = {0, 2, 4, 6} if not swap else {1, 3, 5, 7}
                    places, fates = race(track, seed, new_slots)
                    rows.append('%s s%d swap=%d  NEW places=%s  OLD places=%s' % (
                        track, seed, swap, sorted(places[i] for i in new_slots),
                        sorted(places[i] for i in range(8) if i not in new_slots)))
                    for i, place in enumerate(places):
                        total = totals['new' if i in new_slots else 'old']
                        total[0] += place
                        total[1] += 1
                        total[2] += fates[i] == 99
        if experiment_identity(tracks) != identity:
            raise ValueError('cross-era inputs changed during the comparison; no report')
        # Nothing is reported as a performance result unless every pair finished.
        print('\n'.join(rows))
        print('=' * 60)
        for label, key, jar in (('NEW', 'new', NEW_JAR), ('OLD', 'old', OLD_JAR)):
            places, count, crashes = totals[key]
            print('%s (%s): mean place %.3f  crashes %d' %
                  (label, Path(jar).name, places / count, crashes))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        detail = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
        print('cross-era: ' + detail, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
