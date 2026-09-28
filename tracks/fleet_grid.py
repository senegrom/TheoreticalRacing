#!/usr/bin/env python3
"""Validated, resumable fleet runs. See fleet_grid.sh and README.md."""
from __future__ import annotations

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import contextlib
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading

if __package__:
    from .forensics_common import parse_move, potential_status
    from .benchmark_io import comparison_profile
else:
    from forensics_common import parse_move, potential_status
    from benchmark_io import comparison_profile

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
        start = re.fullmatch(
            r'player(\d+) name=.* kind=\S+ start=-?\d+,-?\d+(?: vel=-?\d+,-?\d+ gate=\d)?', line)
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


class Jvms:
    """The grid's running JVMs. An interrupted grid stops them, and no track
    starts after that: a Ctrl+C used to wait for every queued track to race,
    and a SIGTERM left the running JVMs behind (review, 2026-09-28)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.running = set()
        self.stopped = False

    def run(self, command, stream, timeout):
        with self.lock:
            if self.stopped:
                raise ValueError('the grid was interrupted before this track started')
            process = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
            self.running.add(process)
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise
        finally:
            with self.lock:
                self.running.discard(process)

    def stop(self):
        with self.lock:
            self.stopped = True
            running = list(self.running)
        for process in running:
            with contextlib.suppress(OSError):
                process.terminate()
        for process in running:
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(OSError):
                    process.kill()


def physical_memory():
    """Installed memory in bytes, or None when the platform will not say."""
    try:
        return os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    except (AttributeError, ValueError, OSError):
        pass
    if os.name == 'nt':
        import ctypes

        class Status(ctypes.Structure):
            _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                        ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
        status = Status()
        status.dwLength = ctypes.sizeof(Status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.ullTotalPhys
    return None


def heap_bytes(heap):
    """The -Xmx among these JVM options, in bytes; None when there is none."""
    for option in heap:
        m = re.fullmatch(r'-Xmx(\d+)([kKmMgGtT]?)', option)
        if m:
            return int(m.group(1)) << {'': 0, 'k': 10, 'm': 20, 'g': 30, 't': 40}[m.group(2).lower()]
    return None


def default_jobs(heap, memory=None, cpus=None):
    """Parallel JVMs that fit: each may reach its -Xmx plus about a quarter more
    off the heap. The old default, one per CPU at -Xmx8g, overcommitted any
    machine with under ten GB per core -- the ledger records 15 JVMs exhausting
    30 GB (review, 2026-09-28). An explicit jobs argument always wins."""
    cpus = cpus or os.cpu_count() or 4
    memory = physical_memory() if memory is None else memory
    if not memory:
        return max(1, min(cpus, 4))
    per_jvm = heap_bytes(heap) or memory // 4  # without -Xmx the JVM takes a quarter
    return max(1, min(cpus, int(memory // (per_jvm * 5 // 4))))


INPUTS = '.inputs'


def snapshot_inputs(out, manifest, jar, props, tracks):
    """Race from private copies of the jar, the profile and the courses. The
    revalidations see the originals only when a track completes: an input changed
    and restored in between would have raced tracks unseen (review, 2026-09-28).
    The copies must hash to the manifest, so nothing changed before they were made."""
    root = out / INPUTS
    shutil.rmtree(root, ignore_errors=True)
    (root / 'tracks').mkdir(parents=True)
    run_jar, run_props = root / jar.name, root / ('profile' + props.suffix)
    shutil.copyfile(jar, run_jar)
    shutil.copyfile(props, run_props)
    for track in tracks:
        shutil.copyfile(jar.parent / 'tracks' / (track + '.track'), root / 'tracks' / (track + '.track'))
    if not snapshot_matches(manifest, run_jar, run_props, tracks):
        raise ValueError('benchmark inputs changed while the run started; results would not be valid')
    return run_jar, run_props


def snapshot_matches(manifest, run_jar, run_props, tracks):
    """The private copies still hash to the manifest (nothing wrote into them)."""
    try:
        return (digest(run_jar) == manifest['jar'] and digest(run_props) == manifest['properties']
                and all(digest(run_jar.parent / 'tracks' / (t + '.track')) == manifest['tracks'][t]
                        for t in tracks))
    except OSError:
        return False


def revoke_publication(out, tracks):
    """Remove every resumable marker, row and the report of this output."""
    for track in tracks:
        (out / (track + '.complete.json')).unlink(missing_ok=True)
        (out / (track + '.row')).unlink(missing_ok=True)
    (out / 'fleet.txt').unlink(missing_ok=True)


def manifest_for(jar, props, java, heap, tracks, lo, hi):
    return {
        'schema': 2, 'runner': digest(Path(__file__)),
        'comparison': comparison_profile(props),
        'benchmark_parser': digest(Path(__file__).with_name('benchmark_io.py')),
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
        # A marker from before the potential was checked proves nothing about it.
        if record['potential'] not in ('built', 'capped', None):
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


def run_track(out, track, run_id, seeds, java, heap, jar, props, timeout, jvms):
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
            returncode = jvms.run(command, stream, timeout)
        if returncode != 0:
            raise ValueError('%s: Java exited %d (see %s)' % (track, returncode, output))
        text = output.read_text(encoding='utf-8', errors='replace')
        no_loop = re.search(r'^\[laps\] .* -- laps disabled$', text, re.MULTILINE) is not None
        potential = potential_status(track, text)
        logs = []
        for seed in seeds:
            log = work / ('%s_s%d.log' % (track, seed))
            counts = parse_log(log)
            logs.append({'sha256': digest(log), 'counts': counts})
        for seed in seeds:
            name = '%s_s%d.log' % (track, seed)
            os.replace(work / name, out / name)
        record = dict(run_id=run_id, seeds=list(seeds), no_loop=no_loop, potential=potential, logs=logs)
        # main publishes resumable completion only after input revalidation.
        return record


def _terminated(signum, frame):
    raise KeyboardInterrupt('SIGTERM')


def main(argv=None):
    """A SIGTERM (a queue runner's kill) interrupts the grid like Ctrl+C."""
    if threading.current_thread() is not threading.main_thread():
        return grid(argv)
    previous = signal.signal(signal.SIGTERM, _terminated)
    try:
        return grid(argv)
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_DFL if previous is None else previous)


def grid(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('seeds', nargs='?', default='1-10')
    parser.add_argument('jobs', nargs='?', type=int, default=None)
    parser.add_argument('out', nargs='?', default=str(Path(tempfile.gettempdir()) / 'fleet_grid'))
    args = parser.parse_args(argv)
    try:
        lo, hi = seed_range(args.seeds)
        if args.jobs is not None and args.jobs < 1:
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
        jobs = args.jobs if args.jobs is not None else default_jobs(heap)
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
            run_jar, run_props = snapshot_inputs(out, manifest, jar, props, tracks)

            def intact():
                # The originals, as the manifest promises, and the copies raced.
                return (manifest_for(jar, props, java, heap, tracks, lo, hi) == manifest
                        and snapshot_matches(manifest, run_jar, run_props, tracks))

            results, failures = {}, {}
            unverified = False
            jvms = Jvms()
            pool = ThreadPoolExecutor(max_workers=min(jobs, len(tracks)))
            try:
                futures = {pool.submit(run_track, out, t, run_id, seeds, java, heap, run_jar, run_props,
                                       timeout, jvms): t
                           for t in tracks}
                pending = set(futures)
                while pending:
                    # Polled: a blocked wait holds Ctrl+C on Windows until a track ends.
                    done, pending = wait(pending, timeout=1.0, return_when=FIRST_COMPLETED)
                    for future in sorted(done, key=futures.get):
                        track = futures[future]
                        try:
                            results[track] = future.result()
                        except (OSError, ValueError, subprocess.SubprocessError) as error:
                            failures[track] = str(error)
                            print('%s: %s' % (track, error), file=sys.stderr)
                            continue
                        # Publish this track's marker once the inputs are revalidated,
                        # so a runner killed later in the grid resumes without racing
                        # it again (review, 2026-09-27). A revalidation that fails or
                        # cannot be read makes the whole run unverified: nothing more
                        # is published and the final check revokes everything.
                        if unverified:
                            continue
                        try:
                            unverified = not intact()
                        except (OSError, ValueError):
                            unverified = True
                        if not unverified:
                            atomic_text(out / (track + '.complete.json'), json_text(results[track]))
            except BaseException:
                # Interrupted (Ctrl+C, SIGTERM): no queued track starts, the running
                # JVMs are stopped, and every marker already validated stays
                # resumable -- a resume must present the same manifest anyway.
                pool.shutdown(wait=False, cancel_futures=True)
                jvms.stop()
                pool.shutdown(wait=True)
                raise
            pool.shutdown(wait=True)
            # A missing/malformed input is just as invalid as a changed hash: leave
            # neither resumable markers nor an old report behind. An interruption
            # proves nothing about the inputs and revokes nothing.
            try:
                inputs_valid = not unverified and intact()
            except (OSError, ValueError):
                revoke_publication(out, tracks)
                raise
            if not inputs_valid:
                revoke_publication(out, tracks)
                raise ValueError('benchmark inputs changed during the run; results are not valid')
            lines = []
            total = dict(crash=0, timeout=0, moves=0)
            races = 0
            for t in tracks:  # Never glob unrelated/stale result rows into this experiment.
                if t in failures:
                    lines.append(t + ' ERROR\n')
                    continue
                record = results[t]
                atomic_text(out / (t + '.complete.json'), json_text(record))
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
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('fleet: interrupted; the tracks already validated resume without racing again', file=sys.stderr)
        raise SystemExit(130)
