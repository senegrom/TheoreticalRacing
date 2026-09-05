#!/usr/bin/env python3
"""Validated, resumable fleet runs. See fleet_grid.sh and README.md."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

if __package__:
    from .forensics_common import parse_move
else:
    from forensics_common import parse_move

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic_text(path, text):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def json_text(value):
    return json.dumps(value, sort_keys=True, indent=2) + '\n'


@contextmanager
def directory_lock(out):
    """OS lock, automatically released even if the runner is killed."""
    with (out / '.fleet.lock').open('a+b') as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError('another fleet run is using ' + str(out)) from error
        try:
            yield
        finally:
            if os.name == 'nt':
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def seed_range(text):
    match = re.fullmatch(r'(-?\d+)(?:-(-?\d+))?', text)
    if not match:
        raise ValueError('seeds must be an integer or an inclusive A-B range')
    lo = int(match[1])
    hi = int(match[2]) if match[2] is not None else lo
    if not -(2**63) <= lo <= hi < 2**63:
        raise ValueError('seed range must be ordered and within Java long bounds')
    return lo, hi


def parse_log(path):
    """Reject missing, partial and malformed results; count outcome tokens only."""
    players, ranks, retired = set(), set(), set()
    counters = dict(fin=0, crash=0, timeout=0, moves=0)
    results = False
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        start = re.fullmatch(r'player(\d+) name=.* kind=\S+ start=-?\d+,-?\d+', line)
        if start:
            if results or int(start[1]) in players:
                raise ValueError('duplicate/late player declaration')
            players.add(int(start[1]))
            continue
        if line == '# results':
            if results:
                raise ValueError('duplicate results section')
            results = True
            continue
        move = parse_move(line)
        if move:
            if results or move.player not in players or move.player in retired:
                raise ValueError('invalid move ordering')
            counters['moves'] += 1
            if move.index != counters['moves']:
                raise ValueError('missing or duplicated move')
            key = {'FINISH': 'fin', 'CRASH': 'crash', 'TIMEOUT': 'timeout'}.get(move.status)
            if key:
                counters[key] += 1
                retired.add(move.player)
            continue
        if results:
            rank = re.fullmatch(r'(\d+)\. .*', line)
            if not rank or int(rank[1]) in ranks:
                raise ValueError('malformed results table')
            ranks.add(int(rank[1]))
        elif re.match(r'^\d+ p', line):
            raise ValueError('malformed move')
    expected = set(range(1, len(players) + 1))
    if not players or players != expected or not results or ranks != expected:
        raise ValueError('incomplete results')
    if len(retired) != (len(players) if len(players) == 1 else len(players) - 1):
        raise ValueError('race did not reach a terminal result')
    return counters


def manifest_for(jar, props, java, heap, tracks, lo, hi):
    return {
        'schema': 1, 'runner': digest(Path(__file__)),
        'log_parser': digest(Path(__file__).with_name('forensics_common.py')),
        'jar': digest(jar), 'properties': digest(props),
        'java': str(java), 'java_sha256': digest(java), 'heap': heap,
        'java_environment': {key: hashlib.sha256(os.environ.get(key, '').encode('utf-8')).hexdigest()
                             for key in ('JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS')},
        'seeds': [lo, hi],
        'tracks': {t: digest(jar.parent / 'tracks' / (t + '.track')) for t in tracks},
    }


def completed(out, track, run_id, seeds):
    """Only an atomically published, validated completion marker is resumable."""
    try:
        record = json.loads((out / (track + '.complete.json')).read_text(encoding='utf-8'))
        if record['run_id'] != run_id or record['seeds'] != list(seeds):
            return None
        if not isinstance(record['no_loop'], bool) or len(record['logs']) != len(seeds):
            return None
        for seed, saved in zip(seeds, record['logs']):
            log = out / ('%s_s%d.log' % (track, seed))
            if digest(log) != saved['sha256']:
                return None
            row = parse_log(log)
            if row != saved['counts']:
                return None
        return record
    except (OSError, ValueError, KeyError, TypeError):
        return None


def run_track(out, track, run_id, seeds, java, heap, jar, props, timeout):
    previous = completed(out, track, run_id, seeds)
    if previous is not None:
        return previous
    (out / (track + '.complete.json')).unlink(missing_ok=True)
    (out / (track + '.row')).unlink(missing_ok=True)
    # Fresh attempt paths ensure a failed JVM can never read yesterday's logs.
    with tempfile.TemporaryDirectory(prefix='.' + track + '-', dir=out) as work:
        work = Path(work)
        output = out / (track + '.out')
        command = [str(java), *heap, '-Djava.awt.headless=true', '-jar', str(jar),
                   '--auto', '--track', track, '--props', str(props),
                   '--log', str(work / (track + '.log')),
                   '--seed', '%d-%d' % (seeds.start, seeds.stop - 1)]
        with output.open('w', encoding='utf-8') as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                    timeout=timeout, check=False)
        if result.returncode != 0:
            raise ValueError('%s: Java exited %d (see %s)' % (track, result.returncode, output))
        no_loop = re.search(r'^\[laps\] .* -- laps disabled$',
                            output.read_text(encoding='utf-8', errors='replace'), re.MULTILINE) is not None
        logs = []
        for seed in seeds:
            log = work / ('%s_s%d.log' % (track, seed))
            counts = parse_log(log)
            logs.append({'sha256': digest(log), 'counts': counts})
        for seed in seeds:
            name = '%s_s%d.log' % (track, seed)
            os.replace(work / name, out / name)
        record = dict(run_id=run_id, seeds=list(seeds), no_loop=no_loop, logs=logs)
        atomic_text(out / (track + '.complete.json'), json_text(record))
        return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('seeds', nargs='?', default='1-10')
    parser.add_argument('jobs', nargs='?', type=int, default=os.cpu_count() or 4)
    parser.add_argument('out', nargs='?', default=str(Path(tempfile.gettempdir()) / 'fleet_grid'))
    args = parser.parse_args(argv)
    try:
        lo, hi = seed_range(args.seeds)
        if args.jobs < 1:
            raise ValueError('jobs must be positive')
        timeout = float(os.environ.get('RACING_TIMEOUT', '3600'))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('RACING_TIMEOUT must be a positive finite number of seconds')
        jar = Path(os.environ.get('RACING_JAR', ROOT / 'theoreticRacing.jar')).resolve()
        props = Path(os.environ.get('RACING_PROPS', ROOT / 'tracks/lap_bench.properties')).resolve()
        java_name = os.environ.get('RACING_JAVA', 'java')
        executable = shutil.which(java_name)
        if executable is None:
            raise ValueError('Java executable not found: ' + java_name)
        java = Path(executable).resolve()
        heap = shlex.split(os.environ.get('RACING_HEAP', '-Xmx8g'))
        selected = os.environ.get('RACING_TRACKS', '')
        tracks = sorted(set(filter(None, re.split(r'[,\s]+', selected)))) if selected.strip() else sorted(
            p.stem for p in (jar.parent / 'tracks').glob('*.track'))
        if not tracks or any(not all(c.isalnum() or c in '_-' for c in t) for t in tracks):
            raise ValueError('no tracks selected, or invalid track name')
        manifest = manifest_for(jar, props, java, heap, tracks, lo, hi)
        manifest_text = json_text(manifest)
        run_id = hashlib.sha256(manifest_text.encode('utf-8')).hexdigest()
        out = Path(args.out).resolve()
        out.mkdir(parents=True, exist_ok=True)
        with directory_lock(out):
            path = out / 'manifest.json'
            if path.exists():
                if json.loads(path.read_text(encoding='utf-8')) != manifest:
                    raise ValueError('output manifest differs (build, seeds, profile, tracks or runtime); use a new output directory')
            elif any(p.name != '.fleet.lock' for p in out.iterdir()):
                raise ValueError('nonempty output directory has no manifest; use a new output directory')
            else:
                atomic_text(path, manifest_text)
            seeds = range(lo, hi + 1)
            results, failures = {}, {}
            with ThreadPoolExecutor(max_workers=min(args.jobs, len(tracks))) as pool:
                futures = {pool.submit(run_track, out, t, run_id, seeds, java, heap, jar, props, timeout): t
                           for t in tracks}
                for future in as_completed(futures):
                    track = futures[future]
                    try:
                        results[track] = future.result()
                    except (OSError, ValueError, subprocess.SubprocessError) as error:
                        failures[track] = str(error)
                        print('%s: %s' % (track, error), file=sys.stderr)
            # Detect an input changed while the JVMs were running, not just on resume.
            if manifest_for(jar, props, java, heap, tracks, lo, hi) != manifest:
                for track in tracks:
                    (out / (track + '.complete.json')).unlink(missing_ok=True)
                    (out / (track + '.row')).unlink(missing_ok=True)
                raise ValueError('benchmark inputs changed during the run; results are not valid')
            lines = []
            total = dict(crash=0, timeout=0, moves=0)
            races = 0
            for t in tracks:  # Never glob unrelated/stale result rows into this experiment.
                if t in failures:
                    lines.append(t + ' ERROR\n')
                    continue
                record = results[t]
                rows = []
                if record['no_loop']:
                    rows.append(t + ' NOLOOP\n')
                else:
                    for seed, log in zip(seeds, record['logs']):
                        c = log['counts']
                        rows.append('%s %d fin=%d crash=%d timeout=%d moves=%d\n' %
                                    (t, seed, c['fin'], c['crash'], c['timeout'], c['moves']))
                        races += 1
                        for key in total:
                            total[key] += c[key]
                atomic_text(out / (t + '.row'), ''.join(rows))
                lines.extend(rows)
            atomic_text(out / 'fleet.txt', ''.join(lines))
            print('FLEETDONE seeds=%d-%d races=%d crashes=%d timeouts=%d moves=%d unusable=%d' %
                  (lo, hi, races, total['crash'], total['timeout'], total['moves'], len(failures)))
            print('rows: ' + str(out / 'fleet.txt'))
            return 1 if failures else 0
    except (OSError, ValueError) as error:
        print('fleet: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
