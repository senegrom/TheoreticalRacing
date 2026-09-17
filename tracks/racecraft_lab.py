#!/usr/bin/env python3
"""Counterfactual place experiments and a small identity-free pairwise ranker.

collect: freeze one real log/profile, replay it, vary the first action, then
         run the frozen champion to classification for every legal alternative.
train:   pairwise logistic ranking, with explicit disjoint validation families.
evaluate: untouched-family counterfactual ranking, NOT a deployed-policy fleet.
profile: embed an experiment/model in a new manifest-bound profile for the
         existing promotion_pair.py runner. Never modifies an input file.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
from typing import Any

if __package__:
    from .benchmark_io import configured_players, read_properties, read_race, update_properties
    from .forensics_common import DIRNAMES, DIRS, Oracle, ReplayBoard, parse_move, reconstruct_board
    from .oracle_roll import apply_move, race_finished, verify
    from .promotion_pair import require_plain_java_environment
else:
    from benchmark_io import configured_players, read_properties, read_race, update_properties
    from forensics_common import DIRNAMES, DIRS, Oracle, ReplayBoard, parse_move, reconstruct_board
    from oracle_roll import apply_move, race_finished, verify
    from promotion_pair import require_plain_java_environment

FEATURES = ('speed_inf', 'speed_squared', 'acceleration', 'legal_exits', 'map_alive',
            'remaining_events', 'solo_turns', 'direct_rivals', 'indirect_rivals',
            'contested_exits', 'nearest_distance', 'terminal')
EXPERIMENTS = {'interaction', 'refresh', 'opportunity', 'encounter', 'learned'}
ROOT = Path(__file__).resolve().parents[1]
HEX = re.compile(r'[0-9a-f]{64}')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def write_new(path: Path, value: str) -> None:
    with path.open('x', encoding='utf-8', newline='\n') as f:
        f.write(value)


class LabOracle(Oracle):
    """Explicit heap/runtime and a whole-session deadline, including blocked reads."""
    def __init__(self, track: str, jar: Path, props: Path, java: Path, heap: str,
                 seed: int, timeout: float, stderr: Path):
        self.asks = 0
        self.errors = stderr.open('x', encoding='utf-8')
        try:
            self.proc = subprocess.Popen([str(java), heap, '-jar', str(jar), '--auto',
                                          '--track', track, '--props', str(props), '--seed', str(seed),
                                          '--query-moves', '-', '-'], stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, stderr=self.errors, text=True,
                                         encoding='utf-8', bufsize=1)
        except BaseException:
            self.errors.close()
            raise
        self.timer = threading.Timer(timeout, self.proc.kill)
        self.timer.daemon = True
        self.timer.start()

    def features(self, mover: int, cars: ReplayBoard) -> list[list[float] | None]:
        if not cars.complete or any(len(c) != 7 for c in cars):
            raise ValueError('features require complete V2 progress')
        assert self.proc.stdin is not None and self.proc.stdout is not None
        request = 'lab2,%d,%d,%d;' % (mover, cars.turns, cars.laps)
        self.proc.stdin.write(request + ';'.join(','.join(map(str, c)) for c in cars) + '\n')
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError('oracle died/deadline expired during features')
            if not line.startswith('lab2;'):
                continue
            fields = line.strip().split(';')
            if len(fields) != 3 or fields[1] != '1':
                raise ValueError('incompatible feature schema')
            rows = fields[2].split('|')
            if len(rows) != 9:
                raise ValueError('incomplete feature response')
            result = [None if row == '-' else list(map(float, row.split(','))) for row in rows]
            for row in result:
                if row is not None:
                    check_features(row)
            return result

    def close(self):
        self.timer.cancel()
        try:
            super().close()
        finally:
            self.errors.close()


def check_features(f: Any, features=FEATURES) -> None:
    if (not isinstance(f, list) or len(f) != len(features)
            or any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not math.isfinite(v) or abs(v) > 1.0000001 for v in f)):
        raise ValueError('invalid v1 features')


def prefix_classification(log: Path, target: int, players: int) -> tuple[dict[int, int], int, int]:
    placed: dict[int, int] = {}
    first = last = 0
    for line in log.read_text(encoding='utf-8').splitlines():
        move = parse_move(line)
        if move is None or move.index >= target:
            continue
        if move.status == 'FINISH':
            first += 1
            placed[move.player - 1] = first
        elif move.status in ('CRASH', 'TIMEOUT'):
            placed[move.player - 1] = players - last
            last += 1
    return placed, first, last


def continue_action(oracle: Oracle, initial: ReplayBoard, focal: int, action: int,
                    placed: dict[int, int], first: int, last: int, max_moves: int,
                    trace: Any) -> dict[str, Any]:
    """Exact classification accounting around the V2 referee. Censor rather than
    invent an outcome when the finite collection budget cannot finish a race."""
    cars = initial.copy()
    classifications = dict(placed)
    own_moves = [0] * len(cars)
    mover, committed = focal, 0
    trace.write(encoded({'initial': list(cars), 'turns': cars.turns, 'laps': cars.laps,
                         'focal': focal, 'first_action': DIRNAMES[action], 'placed': placed}) + '\n')
    while not race_finished(cars):
        if committed >= max_moves:
            return {'complete': False, 'place': None, 'own_moves': None, 'committed': committed}
        if cars[mover][4] != 0:
            mover = (mover + 1) % len(cars)
            continue
        dx, dy, mask = oracle.ask(mover, cars)
        if committed == 0:
            dx, dy = DIRS[action]
        transition = mask.transitions[DIRS.index((dx, dy))]
        cars, fate = apply_move(cars, mover, dx, dy, mask)
        committed += 1
        own_moves[mover] += 1
        if fate == 'FINISH':
            first += 1
            classifications[mover] = first
        elif fate in ('CRASH', 'TIMEOUT'):
            classifications[mover] = len(cars) - last
            last += 1
        trace.write(encoded({'turn': cars.turns, 'mover': mover, 'action': DIRNAMES[DIRS.index((dx, dy))],
                             'transition': list(transition), 'fate': fate}) + '\n')
        mover = (mover + 1) % len(cars)
    for i, car in enumerate(cars):
        if car[4] == 0:
            classifications[i] = first + 1
    if set(classifications) != set(range(len(cars))) or set(classifications.values()) != set(range(1, len(cars) + 1)):
        raise ValueError('counterfactual classification is incomplete or duplicated')
    return {'complete': True, 'place': classifications[focal], 'own_moves': own_moves[focal],
            'committed': committed, 'classification': [classifications[i] for i in range(len(cars))]}


def collect(args: argparse.Namespace) -> None:
    require_plain_java_environment()
    if not re.fullmatch(r'-Xmx[1-9][0-9]*[kKmMgG]', args.heap):
        raise ValueError('supply one explicit --heap=-Xmx8g')
    args.family = args.family.strip().casefold()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.track) or not args.family:
        raise ValueError('valid track and an explicit track-family label are required')
    if not math.isfinite(args.timeout) or min(args.stride, args.limit, args.max_moves, args.timeout) <= 0:
        raise ValueError('collection limits must be positive')
    java_name = shutil.which(args.java)
    if not java_name:
        raise ValueError('Java executable not found')
    java, jar, log, props = Path(java_name).resolve(), args.jar.resolve(), args.log.resolve(), args.props.resolve()
    course = jar.parent / 'tracks' / (args.track + '.track')
    race = read_race(log)
    roster = configured_players(props)
    if race.players != roster or any(kind == 'HUMAN' for _, kind in roster.values()):
        raise ValueError('source profile must match the logged all-AI roster')
    settings = read_properties(props)
    if settings.get('candidateSlots', '').strip() or settings.get('racecraft.experiments', '').strip() or race.slots:
        raise ValueError('collect from an unmodified champion profile and log, not a candidate')
    if int(settings.get('laps', '1')) != int(race.profile['laps']):
        raise ValueError('profile/log lap count differs')
    # Freeze dependencies before any JVM work. Snapshots and retained full traces
    # are sufficient to distinguish changed inputs from changed policy outcomes.
    inputs = [jar, log, props, course, java] + sorted((ROOT / 'tracks').glob('*.py'))
    hashes = {str(p): digest(p) for p in inputs}
    version = subprocess.run([str(java), '-version'], text=True, capture_output=True,
                             check=True, timeout=30).stderr.strip()
    identity = {'schema': 1, 'features': list(FEATURES), 'family': args.family,
                'track': args.track, 'course_sha256': hashes[str(course)], 'race_sha256': hashes[str(log)], 'seed': args.seed,
                'heap': args.heap, 'java': version, 'inputs': hashes, 'source': str(log),
                'selection': {'stride': args.stride, 'limit': args.limit, 'moves': args.moves},
                'max_moves': args.max_moves, 'timeout': args.timeout}
    args.out.mkdir(parents=True, exist_ok=False)
    out = args.out.resolve()
    shutil.copyfile(log, out / 'source.log')
    shutil.copyfile(props, out / 'profile.properties')
    shutil.copyfile(course, out / 'course.track')
    write_new(out / 'manifest.pending.json', encoded(identity) + '\n')
    rows: list[dict[str, Any]] = []
    with LabOracle(args.track, jar, out / 'profile.properties', java, args.heap, args.seed,
                   args.timeout, out / 'oracle.stderr') as oracle:
        initial, mover, moves = reconstruct_board(log, 1, len(roster), complete=True)
        with (out / 'source-replay.txt').open('x', encoding='utf-8') as replay, contextlib.redirect_stdout(replay):
            if not verify(oracle, initial, mover, moves, len(moves)):
                raise ValueError('frozen profile does not replay the source race exactly')
        targets = ([int(s) for s in args.moves.split(',')] if args.moves
                   else [m.index for m in moves[::args.stride]][:args.limit])
        valid_targets = {m.index for m in moves}
        if not targets or len(set(targets)) != len(targets) or any(t not in valid_targets for t in targets):
            raise ValueError('select unique existing move indices')
        for target in targets:
            board, focal, _ = reconstruct_board(log, target, len(roster), complete=True)
            dx, dy, mask = oracle.ask(focal, board)
            features = oracle.features(focal, board)
            baseline = DIRS.index((dx, dy))
            # Do not condition sampling on crashes, rank or whether the champion
            # survived. A no-legal-move state is retained with an empty action set.
            placed, first, last = prefix_classification(log, target, len(roster))
            actions = []
            for i, f in enumerate(features):
                if f is None:
                    continue
                if mask.transitions[i].status not in ('OK', 'LAP', 'FINISH'):
                    raise ValueError('features/referee disagree about a legal action')
                name = '%06d-%s.jsonl' % (target, DIRNAMES[i])
                with (out / name).open('x', encoding='utf-8') as trace:
                    result = continue_action(oracle, board, focal, i, placed, first, last, args.max_moves, trace)
                actions.append({'direction': DIRNAMES[i], 'features': f, 'outcome': result,
                                'trace': name, 'trace_sha256': digest(out / name)})
            row = {'id': hashes[str(log)] + ':' + str(target), 'race_sha256': hashes[str(log)],
                   'family': args.family, 'track': args.track, 'course_sha256': hashes[str(course)], 'move': target, 'focal': focal,
                   'players': len(roster), 'baseline': DIRNAMES[baseline], 'actions': actions}
            rows.append(row)
            with (out / 'rows.pending.jsonl').open('a', encoding='utf-8') as f:
                f.write(encoded(row) + '\n')
            print('move %d: %d alternatives, %d complete' %
                  (target, len(actions), sum(a['outcome']['complete'] for a in actions)), flush=True)
    require_plain_java_environment()
    if any(digest(Path(p)) != h for p, h in hashes.items()) or digest(out / 'profile.properties') != hashes[str(props)]:
        raise ValueError('collection inputs changed; pending rows are not valid evidence')
    # No successful dataset marker exists until every input and output is bound.
    identity['rows_sha256'] = digest(out / 'rows.pending.jsonl')
    identity['samples'] = len(rows)
    identity['censored_samples'] = sum(any(not a['outcome']['complete'] for a in r['actions']) for r in rows)
    (out / 'rows.pending.jsonl').rename(out / 'rows.jsonl')
    write_new(out / 'manifest.json', encoded(identity) + '\n')
    (out / 'manifest.pending.json').unlink()
    print('Published counterfactual dataset (not a fleet promotion):', out)


def load_datasets(paths: list[Path], *, features=FEATURES, schema=1) -> tuple[list[dict[str, Any]], list[str]]:
    rows, manifests, seen = [], [], set()
    for directory in paths:
        manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
        data = directory / 'rows.jsonl'
        if manifest.get('schema') != schema or manifest.get('features') != list(features) or digest(data) != manifest.get('rows_sha256'):
            raise ValueError('dataset schema/hash mismatch')
        manifests.append(digest(directory / 'manifest.json'))
        local_rows = [json.loads(s) for s in data.read_text(encoding='utf-8').splitlines()]
        if len(local_rows) != manifest.get('samples'):
            raise ValueError('sample count mismatch')
        for row in local_rows:
            if row['id'] in seen:
                raise ValueError('duplicate decision sample')
            seen.add(row['id'])
            if (row['family'] != manifest['family'] or row['race_sha256'] != manifest['race_sha256']
                    or row['course_sha256'] != manifest['course_sha256']):
                raise ValueError('sample provenance differs from manifest')
            n = row['players']
            if not isinstance(n, int) or not 1 <= n <= 9:
                raise ValueError('bad field size')
            names = set()
            for a in row['actions']:
                if a['direction'] not in DIRNAMES or a['direction'] in names:
                    raise ValueError('invalid/duplicate direction')
                names.add(a['direction'])
                check_features(a['features'], features)
                result = a['outcome']
                if result.get('complete') is True:
                    if (type(result.get('place')) is not int or not 1 <= result['place'] <= n
                            or type(result.get('own_moves')) is not int or result['own_moves'] < 1):
                        raise ValueError('invalid complete outcome')
                elif result.get('complete') is not False or result.get('place') is not None:
                    raise ValueError('invalid censored outcome')
                trace = a.get('trace', '')
                if Path(trace).name != trace or not trace:
                    raise ValueError('trace path must be a basename')
                if digest(directory / trace) != a.get('trace_sha256'):
                    raise ValueError('counterfactual trace hash differs')
            rows.append(row)
    return rows, manifests


def usable(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Censor the WHOLE decision if one alternative is unknown. Never train on
    # only the easy subset of actions in a hard state.
    return [r for r in rows if len(r['actions']) >= 2 and all(a['outcome']['complete'] for a in r['actions'])
            and r['baseline'] in {a['direction'] for a in r['actions']}]


def key(action: dict[str, Any]) -> tuple[int, int]:
    result = action['outcome']
    return result['place'], result['own_moves']


def separation(train: list[dict[str, Any]], holdout: list[dict[str, Any]]) -> None:
    for field in ('id', 'race_sha256', 'family', 'course_sha256'):
        if {r[field] for r in train} & {r[field] for r in holdout}:
            raise ValueError('data leakage: overlapping ' + field)


def fit(rows: list[dict[str, Any]], epochs: int, rate: float, l2: float) -> list[float]:
    if epochs < 1 or not 0 < rate <= 1 or not math.isfinite(l2) or l2 < 0:
        raise ValueError('invalid training hyperparameters')
    pairs = []
    for r in sorted(usable(rows), key=lambda v: v['id']):
        actions = r['actions']
        for i, a in enumerate(actions):
            for b in actions[i + 1:]:
                if key(a) == key(b):
                    continue
                # Score LOWER is better. Logistic P(a better b) uses score(b)-score(a).
                pairs.append(([y - x for x, y in zip(a['features'], b['features'])], float(key(a) < key(b))))
    if not pairs:
        raise ValueError('no complete non-tied pairwise examples to learn from')
    weights = [0.0] * len(FEATURES)
    for epoch in range(epochs):
        gradient = [l2 * w for w in weights]
        for delta, target in pairs:
            z = max(-40.0, min(40.0, sum(w * x for w, x in zip(weights, delta))))
            error = 1 / (1 + math.exp(-z)) - target
            for i, x in enumerate(delta):
                gradient[i] += error * x / len(pairs)
        step = rate / math.sqrt(1 + epoch / 10)
        weights = [w - step * g for w, g in zip(weights, gradient)]
    return weights


def report(rows: list[dict[str, Any]], weights: list[float], margin: float) -> dict[str, Any]:
    selected = usable(rows)
    if not selected:
        raise ValueError('no complete comparative decisions')
    deltas, time_deltas, switches = [], [], 0
    for row in selected:
        baseline = next(a for a in row['actions'] if a['direction'] == row['baseline'])
        score = lambda a: sum(w * x for w, x in zip(weights, a['features']))
        best = baseline
        for action in sorted(row['actions'], key=lambda a: DIRNAMES.index(a['direction'])):
            if score(action) < score(best):
                best = action
        if score(baseline) - score(best) <= margin:
            best = baseline
        switches += best != baseline
        deltas.append(key(best)[0] - key(baseline)[0])
        if key(best)[0] == key(baseline)[0]:
            time_deltas.append(key(best)[1] - key(baseline)[1])
    return {'decisions': len(selected), 'excluded_decisions': len(rows) - len(selected), 'switches': switches,
            'mean_counterfactual_place_delta': sum(deltas) / len(deltas),
            'mean_time_delta_at_equal_place': sum(time_deltas) / len(time_deltas) if time_deltas else None,
            'scope': 'one-action counterfactuals under a frozen policy; not deployed-policy performance'}


def train(args: argparse.Namespace) -> None:
    training, manifests = load_datasets(args.train)
    validation, val_manifests = load_datasets(args.validation)
    separation(training, validation)
    weights = fit(training, args.epochs, args.rate, args.l2)
    model = {'version': 1, 'features': list(FEATURES), 'weights': weights, 'margin': args.margin,
             'trainingSha256': hashlib.sha256(encoded(sorted(manifests)).encode()).hexdigest(),
             'trainingFamilies': sorted({r['family'] for r in training}),
             'trainingRaces': sorted({r['race_sha256'] for r in training}),
             'trainingCourses': sorted({r['course_sha256'] for r in training}),
             'validationFamilies': sorted({r['family'] for r in validation}),
             'validationRaces': sorted({r['race_sha256'] for r in validation}),
             'validationCourses': sorted({r['course_sha256'] for r in validation}),
             'trainingDatasets': manifests, 'validationDatasets': val_manifests,
             'hyperparameters': {'epochs': args.epochs, 'rate': args.rate, 'l2': args.l2},
             'validation': report(validation, weights, args.margin)}
    validate_model(model)
    write_new(args.out, encoded(model) + '\n')
    print(json.dumps(model['validation'], indent=2))


def validate_model(model: dict[str, Any]) -> None:
    if (not isinstance(model, dict) or type(model.get('version')) is not int
            or model.get('version') != 1 or model.get('features') != list(FEATURES)
            or not isinstance(model.get('trainingSha256'), str)
            or not HEX.fullmatch(model['trainingSha256'])
            or not isinstance(model.get('weights'), list)
            or len(model['weights']) != len(FEATURES)
            or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1e6 for v in model['weights'])
            or type(model.get('margin')) not in (int, float) or not math.isfinite(model['margin'])
            or not 0 <= model['margin'] <= 100):
        raise ValueError('invalid model artifact')


def evaluate(args: argparse.Namespace) -> None:
    model = json.loads(args.model.read_text(encoding='utf-8'))
    validate_model(model)
    rows, manifests = load_datasets(args.data)
    for field, names in (('family', ('trainingFamilies', 'validationFamilies')),
                         ('race_sha256', ('trainingRaces', 'validationRaces')),
                         ('course_sha256', ('trainingCourses', 'validationCourses'))):
        used = {v for name in names for v in model[name]}
        if {r[field] for r in rows} & used:
            raise ValueError('evaluation is not an untouched holdout: ' + field)
    result = report(rows, model['weights'], model['margin'])
    result.update(model_sha256=digest(args.model), datasets=manifests)
    write_new(args.out, encoded(result) + '\n')
    print(json.dumps(result, indent=2))


def profile(args: argparse.Namespace) -> None:
    flags = args.experiments.split(',')
    if not flags or len(flags) != len(set(flags)) or any(f not in EXPERIMENTS for f in flags):
        raise ValueError('select comma-separated interaction,refresh,opportunity,encounter,learned')
    if not (1 <= args.rounds <= 4 and 0 <= args.extra_rounds <= 3 and 0 <= args.budget <= 512
            and 0 <= args.extension_budget <= 512 and 1 <= args.alternatives <= 8):
        raise ValueError('profile search limits out of range')
    read_properties(args.base)
    settings = {'candidateSlots': '', 'racecraft.experiments': ','.join(flags),
                'racecraft.rounds': str(args.rounds), 'racecraft.extraRounds': str(args.extra_rounds),
                'racecraft.policyBudget': str(args.budget), 'racecraft.extensionBudget': str(args.extension_budget), 'racecraft.alternatives': str(args.alternatives)}
    if 'learned' in flags:
        if args.model is None:
            raise ValueError('learned mode requires a trained --model, no placeholder weights are provided')
        model = json.loads(args.model.read_text(encoding='utf-8'))
        validate_model(model)
        settings.update({'racecraft.model.' + k: str(model[k]) for k in ('version', 'margin', 'trainingSha256')})
        settings['racecraft.model.features'] = ','.join(FEATURES)
        settings['racecraft.model.weights'] = ','.join(repr(w) for w in model['weights'])
    with args.out.open('xb') as f:
        f.write(args.base.read_bytes())
    try:
        update_properties(args.out, settings)
    except BaseException:
        args.out.unlink(missing_ok=True)
        raise
    print('Created', args.out, '(candidateSlots left empty; promotion_pair.py supplies complementary cohorts)')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    c = commands.add_parser('collect')
    for name in ('log', 'props', 'out'):
        c.add_argument('--' + name, required=True, type=Path)
    c.add_argument('--jar', type=Path, default=ROOT / 'theoreticRacing.jar')
    c.add_argument('--track', required=True)
    c.add_argument('--family', required=True, help='explicit geometry-family grouping for leakage checks')
    c.add_argument('--java', default='java'); c.add_argument('--heap', default='-Xmx8g')
    c.add_argument('--seed', type=int, default=1)
    c.add_argument('--moves', help='explicit comma-separated log indices, otherwise deterministic stride')
    c.add_argument('--stride', type=int, default=25); c.add_argument('--limit', type=int, default=20)
    c.add_argument('--max-moves', type=int, default=10000); c.add_argument('--timeout', type=float, default=3600)
    c.set_defaults(func=collect)
    t = commands.add_parser('train')
    t.add_argument('--train', nargs='+', type=Path, required=True)
    t.add_argument('--validation', nargs='+', type=Path, required=True)
    t.add_argument('--out', type=Path, required=True); t.add_argument('--epochs', type=int, default=200)
    t.add_argument('--rate', type=float, default=.5); t.add_argument('--l2', type=float, default=.001)
    t.add_argument('--margin', type=float, default=.05); t.set_defaults(func=train)
    e = commands.add_parser('evaluate')
    e.add_argument('--model', type=Path, required=True); e.add_argument('--data', nargs='+', type=Path, required=True)
    e.add_argument('--out', type=Path, required=True); e.set_defaults(func=evaluate)
    p = commands.add_parser('profile')
    p.add_argument('--base', type=Path, default=ROOT / 'tracks/lap_bench.properties')
    p.add_argument('--out', type=Path, required=True); p.add_argument('--experiments', required=True)
    p.add_argument('--model', type=Path); p.add_argument('--rounds', type=int, default=2)
    p.add_argument('--extra-rounds', type=int, default=1); p.add_argument('--budget', type=int, default=96)
    p.add_argument('--alternatives', type=int, default=2)
    p.add_argument('--extension-budget', type=int, default=64); p.set_defaults(func=profile)
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        print('racecraft lab:', error, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
