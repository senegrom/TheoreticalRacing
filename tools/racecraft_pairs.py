#!/usr/bin/env python3
"""Capture disputed decisions, verify full referee controls, label action pairs,
and fit a small held-out pairwise model. No incomplete continuation is a label.

Examples (use a fresh output directory for each stage):
  racecraft_pairs.py capture --jar theoreticRacing.jar --props study.properties \
      --tracks hairpin chicane circle --seeds 41-42 --out /tmp/rc-capture
  racecraft_pairs.py label --capture /tmp/rc-capture --out /tmp/rc-labels
  racecraft_pairs.py train --labels /tmp/rc-labels --holdout-families circle \
      --out /tmp/rc-model

The model is NOT promoted. Use racecraftModel=/tmp/rc-model/model.properties
with paired-shadow first. Fleet wrappers embed the coefficients in their
snapshotted profiles. Training and validation must share an executable and
policy profile but have disjoint whole races and track families.
"""
from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tracks'))
from benchmark_io import read_properties, read_race  # noqa: E402
from forensics_common import DIRNAMES, parse_move, potential_status  # noqa: E402
from racecraft_metrics import family, profile_text  # noqa: E402
from fleet_grid import seed_range  # noqa: E402

FEATURES = 18


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hash_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')


def new_directory(path):
    path = Path(path).resolve()
    path.mkdir(parents=True, exist_ok=False)
    return path


def capture(args):
    out = new_directory(args.out)
    inputs = out / 'inputs'
    (inputs / 'tracks').mkdir(parents=True)
    jar = args.jar.resolve()
    shutil.copy2(jar, inputs / 'theoreticRacing.jar')
    java = Path(shutil.which(args.java) or args.java).resolve()
    lo, hi = seed_range(args.seeds)
    tracks = sorted(set(args.tracks))
    if not tracks or any(not re.fullmatch(r'[A-Za-z0-9_-]+', t) for t in tracks):
        raise ValueError('invalid capture tracks')
    for t in tracks:
        shutil.copy2(jar.parent / 'tracks' / (t + '.track'), inputs / 'tracks' / (t + '.track'))
    manifest = {'schema': 1, 'complete': False, 'jar': digest(jar), 'java': str(java),
                'java_sha256': digest(java), 'heap': shlex.split(args.heap), 'tool': digest(__file__),
                'java_environment': {key: hash_text(os.environ.get(key, '')) for key in
                                     ('JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS')},
                'tracks': {t: digest(inputs / 'tracks' / (t + '.track')) for t in tracks}, 'cases': []}
    for t in tracks:
        for seed in range(lo, hi + 1):
            name = f'{t}_s{seed}'
            case = out / name
            case.mkdir()
            props, log, rows = case / 'profile.properties', case / 'race.log', case / 'decisions.jsonl'
            # Only the output path/limit are added; candidate slots/features stay
            # precisely what the supplied isolated profile requests.
            props.write_text(profile_text(args.props, {'racecraftCapture': str(rows),
                                                       'racecraftCaptureLimit': str(args.limit)}), encoding='ascii')
            before = digest(props)
            with (case / 'stdout.txt').open('w', encoding='utf-8') as stream:
                subprocess.run([str(java), *manifest['heap'], '-Djava.awt.headless=true', '-jar',
                                str(inputs / 'theoreticRacing.jar'), '--auto', '--props', str(props),
                                '--track', t, '--seed', str(seed), '--log', str(log)],
                               cwd=inputs, stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=args.timeout)
            potential_status(t, (case / 'stdout.txt').read_text(encoding='utf-8'))
            read_race(log)
            if digest(props) != before:
                raise ValueError('the captured profile changed during the race')
            if not rows.exists():
                rows.write_text('', encoding='utf-8')
            policy = read_properties(props)
            for key in ('racecraftCapture', 'racecraftCaptureLimit', 'racecraftAudit'):
                policy.pop(key, None)
            identity = hash_text(json.dumps([manifest['jar'], policy, manifest['tracks'][t], seed],
                                            sort_keys=True, separators=(',', ':')))
            manifest['cases'].append({'name': name, 'race_id': identity, 'track': t, 'family': family(t), 'seed': seed,
                                      'files': {p.name: digest(p) for p in (props, log, rows)}})
    if digest(inputs / 'theoreticRacing.jar') != manifest['jar']:
        raise ValueError('capture executable changed')
    manifest['complete'] = True
    save_json(out / 'manifest.json', manifest)
    print(f'Captured {len(manifest["cases"])} complete races in {out}')


class Oracle:
    """Persistent JVM with bounded waits, drained stderr and guaranteed cleanup."""
    def __init__(self, command, track, stderr, timeout):
        self.stderr = open(stderr, 'w', encoding='utf-8')
        self.proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self.stderr, text=True, encoding='utf-8', bufsize=1)
        self.lines = queue.Queue()
        self.track, self.timeout = track, timeout
        def drain():
            try:
                for line in self.proc.stdout:
                    self.lines.put(line)
            finally:
                self.lines.put(None)
        self.reader = threading.Thread(target=drain, daemon=True)
        self.reader.start()

    def ask(self, request):
        self.proc.stdin.write(request + '\n')
        self.proc.stdin.flush()
        # Use a total deadline, not one timeout per progress line.
        import time
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('research oracle response deadline exceeded')
            try:
                line = self.lines.get(timeout=remaining)
            except queue.Empty as error:
                raise TimeoutError('research oracle response deadline exceeded') from error
            if line is None:
                raise RuntimeError('research oracle terminated before answering')
            if line.startswith('[optimal] potential'):
                potential_status(self.track, line)
            if line.startswith('{'):
                answer = json.loads(line)
                if answer.get('schema') != 1 or answer.get('request_id') != hash_text(request):
                    raise ValueError('oracle request binding failed')
                return answer

    def close(self):
        try:
            if self.proc.poll() is None:
                try:
                    self.proc.stdin.write('quit\n')
                    self.proc.stdin.flush()
                    self.proc.wait(timeout=2)
                except (BrokenPipeError, subprocess.TimeoutExpired):
                    self.proc.kill()
                    self.proc.wait()
        finally:
            self.proc.stdin.close()
            self.proc.stdout.close()
            self.stderr.close()
            self.reader.join(timeout=2)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def trace_projection(trace):
    """Ignore display-only gate marks; preserve every physical move and fate."""
    result = []
    for line in trace:
        parts = line.split(':')
        if len(parts) != 6:
            raise ValueError('malformed referee trace')
        result.append(':'.join(parts[:5] + [parts[5].split(',')[2]]))
    return result


def log_projection(log, first_turn):
    result = []
    for line in Path(log).read_text(encoding='utf-8').splitlines():
        m = parse_move(line)
        if m is None or m.index < first_turn:
            continue
        status = 'OK' if m.status == 'ok' else 'LAP' if m.status.startswith('LAP ') else m.status
        place = re.search(r'\bplace=(\d+)\b', m.detail)
        result.append('%d:%d:%d,%d,%d,%d:%d,%d,%d,%d:%s:%d' % (
            m.player - 1, DIRNAMES.index(m.direction), m.x, m.y, m.old_vx, m.old_vy,
            m.new_x, m.new_y, m.new_vx, m.new_vy, status, int(place[1]) if place else 0))
    return result


def validate_tail(tail, row, cars):
    if tail.get('engine') != row['engine'] or tail.get('policy') != row['policy']:
        raise ValueError('counterfactual executable/profile differs from the capture')
    for key in ('places', 'moves', 'outcomes'):
        if not isinstance(tail.get(key), list) or len(tail[key]) != cars:
            raise ValueError('incomplete counterfactual roster')
    if any(type(n) is not int or n < 0 for n in tail['moves']):
        raise ValueError('invalid counterfactual move counts')
    if hash_text('\n'.join(tail['trace'])) != tail['trace_hash']:
        raise ValueError('counterfactual trace digest mismatch')
    if tail['complete']:
        if sorted(tail['places']) != list(range(1, cars + 1)):
            raise ValueError('counterfactual classification is incomplete')
        if any(f not in ('PRIOR', 'FINISH', 'CRASH', 'TIMEOUT', 'SURVIVOR') for f in tail['outcomes']):
            raise ValueError('counterfactual has unresolved terminal fates')


def label(args):
    source = args.capture.resolve()
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema') != 1 or manifest.get('complete') is not True:
        raise ValueError('capture is not complete')
    inputs = source / 'inputs'
    if digest(inputs / 'theoreticRacing.jar') != manifest['jar'] or digest(manifest['java']) != manifest['java_sha256']:
        raise ValueError('capture runtime or executable changed')
    for key, expected in manifest['java_environment'].items():
        if hash_text(os.environ.get(key, '')) != expected:
            raise ValueError('capture Java environment changed')
    out = new_directory(args.out)
    stats = Counter()
    records = []
    identities = set()
    for case in manifest['cases']:
        directory = source / case['name']
        for name, sha in case['files'].items():
            if digest(directory / name) != sha:
                raise ValueError('a captured race/profile/sample changed')
        if digest(inputs / 'tracks' / (case['track'] + '.track')) != manifest['tracks'][case['track']]:
            raise ValueError('capture track changed')
        command = [manifest['java'], *manifest['heap'], '-Djava.awt.headless=true', '-jar', str(inputs / 'theoreticRacing.jar'),
                   '--auto', '--track', case['track'], '--props', str(directory / 'profile.properties'),
                   '--seed', str(case['seed']), '--query-moves', '-', '-']
        with Oracle(command, case['track'], out / (case['name'] + '-oracle.txt'), args.timeout) as oracle:
            rows = [json.loads(line) for line in (directory / 'decisions.jsonl').read_text(encoding='utf-8').splitlines()]
            for row in rows[:args.limit]:
                if row.get('schema') != 1 or hash_text(row['state']) != row['state_id']:
                    raise ValueError('capture state binding failed')
                if row['state_id'] in identities:
                    stats['duplicate_states'] += 1
                    continue
                identities.add(row['state_id'])
                header = row['state'].split(';')[0].split(',')
                seat, turn, count = int(header[1]), int(header[2]), row['state'].count(';')
                request = f'tail3|{args.max_events}|-1|{row["state"]}'
                control = oracle.ask(request)
                validate_tail(control, row, count)
                stats['controls'] += 1
                if not control['complete']:
                    stats['incomplete_controls'] += 1
                    continue
                if trace_projection(control['trace']) != log_projection(directory / 'race.log', turn + 1):
                    raise ValueError(f'configured control does not reproduce the captured suffix: {case["name"]} turn {turn + 1}')
                stats['exact_controls'] += 1
                tails = {}
                for candidate in row['candidates']:
                    action = candidate['action']
                    if action == row['executed']:
                        tail = control
                    else:
                        tail = oracle.ask(f'tail3|{args.max_events}|{action}|{row["state"]}')
                        validate_tail(tail, row, count)
                    stats['candidate_tails'] += 1
                    if not tail['complete']:
                        stats['incomplete_candidate_tails'] += 1
                        continue
                    tails[action] = tail
                for a, b in combinations(row['candidates'], 2):
                    # Initial deployed model acts on exact primary ties only.
                    if a['verdict'] < 0 or a['verdict'] != b['verdict'] or a['action'] not in tails or b['action'] not in tails:
                        continue
                    ta, tb = tails[a['action']], tails[b['action']]
                    record = {key: case[key] for key in ('race_id', 'track', 'family', 'seed')}
                    record.update(schema=1, engine=row['engine'], policy=row['policy'], state_id=row['state_id'], seat=seat,
                                  a=a, b=b, place_a=ta['places'][seat], place_b=tb['places'][seat],
                                  moves_a=ta['moves'][seat], moves_b=tb['moves'][seat],
                                  fate_a=ta['outcomes'][seat], fate_b=tb['outcomes'][seat],
                                  request_a=ta['request_id'], request_b=tb['request_id'])
                    records.append(record)
                    stats['pairs'] += 1
                # Retain all outcomes, including defeats, physical crashes and timeouts.
                save_json(out / (row['state_id'] + '.json'), {'capture': row, 'control': control, 'tails': tails})
    with (out / 'pairs.jsonl').open('w', encoding='utf-8') as stream:
        for row in records:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
    save_json(out / 'manifest.json', {'schema': 1, 'complete': True, 'source_manifest': digest(source / 'manifest.json'),
                                    'pairs': digest(out / 'pairs.jsonl'), 'tool': digest(__file__), 'stats': dict(stats)})
    print(json.dumps(dict(stats), indent=2))


def ridge(rows, targets, penalty):
    """Positive ridge system, pivoted elimination; no extra dependency required."""
    n = FEATURES
    matrix = [[(penalty if i == j else 0.0) + sum(x[i] * x[j] for x in rows)
               for j in range(n)] + [sum(x[i] * y for x, y in zip(rows, targets))] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda i: abs(matrix[i][col]))
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        scale = matrix[col][col]
        if not math.isfinite(scale) or abs(scale) < 1e-15:
            raise ValueError('ill-conditioned paired regression')
        matrix[col] = [v / scale for v in matrix[col]]
        for i in range(n):
            if i != col:
                factor = matrix[i][col]
                matrix[i] = [a - factor * b for a, b in zip(matrix[i], matrix[col])]
    return [matrix[i][-1] for i in range(n)]


def validate_pair(row):
    if row.get('schema') != 1 or row['family'] != family(row['track']):
        raise ValueError('invalid pair schema/family')
    for key in ('engine', 'policy', 'state_id', 'race_id'):
        if not re.fullmatch('[0-9a-f]{64}', row[key]):
            raise ValueError('invalid pair provenance')
    for arm in ('a', 'b'):
        x = row[arm]['features']
        if len(x) != FEATURES or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1e6 for v in x):
            raise ValueError('invalid paired features')
        if type(row[arm]['action']) is not int or not 0 <= row[arm]['action'] < 9:
            raise ValueError('invalid paired action')
        if type(row['place_' + arm]) is not int or not 1 <= row['place_' + arm] <= 9:
            raise ValueError('invalid paired place')
        if type(row['moves_' + arm]) is not int or row['moves_' + arm] < 0:
            raise ValueError('invalid paired time')
        if row['fate_' + arm] not in ('FINISH', 'CRASH', 'TIMEOUT', 'SURVIVOR'):
            raise ValueError('unresolved mover cannot be a training label')
    if row['a']['action'] == row['b']['action'] or row['a']['verdict'] < 0 or row['a']['verdict'] != row['b']['verdict']:
        raise ValueError('model training requires two distinct, exactly tied actions')


def fit(pairs, holdout, penalty=1.0):
    if not math.isfinite(penalty) or penalty <= 0:
        raise ValueError('ridge penalty must be positive and finite')
    for row in pairs:
        validate_pair(row)
    if not pairs or len({(r['engine'], r['policy']) for r in pairs}) != 1:
        raise ValueError('train one executable/profile at a time')
    identities = [(r['state_id'], *sorted((r['a']['action'], r['b']['action']))) for r in pairs]
    if len(set(identities)) != len(identities):
        raise ValueError('duplicate training pairs')
    training = [r for r in pairs if r['family'] not in holdout]
    validation = [r for r in pairs if r['family'] in holdout]
    if not training or not validation:
        raise ValueError('both training and held-out families are required')
    if {r['race_id'] for r in training} & {r['race_id'] for r in validation}:
        raise ValueError('a whole race leaked across training and validation')
    points = [r[arm]['features'] for r in training for arm in ('a', 'b')]
    mean = [statistics.mean(x[i] for x in points) for i in range(FEATURES)]
    scale = [max(1e-6, statistics.pstdev(x[i] for x in points)) for i in range(FEATURES)]
    low = [min(x[i] for x in points) for i in range(FEATURES)]
    high = [max(x[i] for x in points) for i in range(FEATURES)]
    def delta(r):
        return [(a - b) / s for a, b, s in zip(r['a']['features'], r['b']['features'], scale)]
    x = [delta(r) for r in training]
    place = ridge(x, [r['place_a'] - r['place_b'] for r in training], penalty)
    timed = [r for r in training if r['place_a'] == r['place_b'] and r['fate_a'] == r['fate_b'] == 'FINISH']
    time = ridge([delta(r) for r in timed], [r['moves_a'] - r['moves_b'] - 1000 *
                 (r['a']['features'][4] - r['b']['features'][4]) for r in timed], penalty) if timed else [0.] * FEATURES
    model = dict(mean=mean, scale=scale, low=low, high=high, place=place, time=time)
    stats = Counter(training_pairs=len(training), time_training_pairs=len(timed), validation_pairs=len(validation))
    for r in validation:
        supported = all(l - 1e-10 <= v <= h + 1e-10 for arm in ('a', 'b')
                        for v, l, h in zip(r[arm]['features'], low, high))
        if not supported:
            stats['out_of_domain_pairs'] += 1
            continue
        d = delta(r)
        predicted = (sum(a * b for a, b in zip(place, d)),
                     1000 * (r['a']['features'][4] - r['b']['features'][4]) + sum(a * b for a, b in zip(time, d)))
        choose_a = predicted <= (0, 0)
        selected = r['place_a'] if choose_a else r['place_b']
        stats['supported_pairs'] += 1
        stats['place_regret'] += selected - min(r['place_a'], r['place_b'])
        stats['place_errors'] += selected > min(r['place_a'], r['place_b'])
        if r['place_a'] == r['place_b'] and r['fate_a'] == r['fate_b'] == 'FINISH':
            stats['equal_place_time_regret'] += (r['moves_a'] if choose_a else r['moves_b']) - min(r['moves_a'], r['moves_b'])
    return model, dict(stats)


def train(args):
    labels = args.labels.resolve()
    manifest = json.loads((labels / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('complete') is not True or manifest.get('schema') != 1 or digest(labels / 'pairs.jsonl') != manifest['pairs']:
        raise ValueError('labels are incomplete or changed')
    pairs = [json.loads(line) for line in (labels / 'pairs.jsonl').read_text(encoding='utf-8').splitlines()]
    model, stats = fit(pairs, set(args.holdout_families), args.ridge)
    out = new_directory(args.out)
    props = {'schema': 'paired-ridge-1', 'engine': pairs[0]['engine'], 'policy': pairs[0]['policy']}
    props.update({k: ','.join(format(v, '.17g') for v in values) for k, values in model.items()})
    (out / 'model.properties').write_text(''.join(f'{k}={v}\n' for k, v in sorted(props.items())), encoding='ascii')
    save_json(out / 'validation.json', {'schema': 1, 'promoted': False, 'labels_manifest': digest(labels / 'manifest.json'),
                                      'model': digest(out / 'model.properties'), 'tool': digest(__file__),
                                      'holdout_families': sorted(args.holdout_families), 'ridge': args.ridge,
                                      'training_races': sorted({r['race_id'] for r in pairs if r['family'] not in args.holdout_families}),
                                      'validation_races': sorted({r['race_id'] for r in pairs if r['family'] in args.holdout_families}),
                                      'stats': stats})
    print(json.dumps(stats, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    c = commands.add_parser('capture')
    c.add_argument('--jar', required=True, type=Path)
    c.add_argument('--props', required=True, type=Path)
    c.add_argument('--tracks', required=True, nargs='+')
    c.add_argument('--seeds', default='41')
    c.add_argument('--heap', default='-Xmx4g')
    c.add_argument('--java', default='java')
    c.add_argument('--limit', default=32, type=int)
    c.add_argument('--timeout', default=600, type=float)
    c.add_argument('--out', required=True, type=Path)
    c.set_defaults(run=capture)
    l = commands.add_parser('label')
    l.add_argument('--capture', required=True, type=Path)
    l.add_argument('--out', required=True, type=Path)
    l.add_argument('--limit', default=32, type=int)
    l.add_argument('--max-events', default=20000, type=int)
    l.add_argument('--timeout', default=600, type=float)
    l.set_defaults(run=label)
    t = commands.add_parser('train')
    t.add_argument('--labels', required=True, type=Path)
    t.add_argument('--out', required=True, type=Path)
    t.add_argument('--holdout-families', required=True, nargs='+')
    t.add_argument('--ridge', default=1., type=float)
    t.set_defaults(run=train)
    args = parser.parse_args(argv)
    if hasattr(args, 'limit') and args.limit < 1:
        parser.error('--limit must be positive')
    if hasattr(args, 'timeout') and (not math.isfinite(args.timeout) or args.timeout <= 0):
        parser.error('--timeout must be positive and finite')
    try:
        args.run(args)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'racecraft pairs: {error}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
