#!/usr/bin/env python3
"""Round-260 chooser research: teacher collection, distillation, execution audits
and complete one/two-action counterfactuals. All results are model/experiment-
conditional; none is a universal tactical certificate or a policy promotion.
"""
from __future__ import annotations

import argparse
import contextlib
from collections import Counter
import hashlib
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
    from .benchmark_io import candidate_slots, configured_players, read_properties, read_race, update_properties
    from .forensics_common import DIRS, DIRNAMES, ReplayBoard, parse_move, parse_v2_answer, reconstruct_board
    from .oracle_roll import apply_move, race_finished
    from .promotion_pair import require_plain_java_environment
else:
    from benchmark_io import candidate_slots, configured_players, read_properties, read_race, update_properties
    from forensics_common import DIRS, DIRNAMES, ReplayBoard, parse_move, parse_v2_answer, reconstruct_board
    from oracle_roll import apply_move, race_finished
    from promotion_pair import require_plain_java_environment

ROOT = Path(__file__).resolve().parents[1]
FLAGS = {'aware', 'setup', 'terminal', 'student', 'assist', 'legacy-guarded', 'legacy-unchecked'}
LEGACY_FEATURES = 'speed_inf,speed_squared,acceleration,legal_exits,map_alive,remaining_events,solo_turns,direct_rivals,indirect_rivals,contested_exits,nearest_distance,terminal'.split(',')
FEATURES = LEGACY_FEATURES + 'closing_motion,relative_route,route_known,rival_moves_first,response_delta,rival_exits,field_size'.split(',')
INF = 2147483647


def encoded(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, data: Any) -> None:
    with path.open('x', encoding='utf-8', newline='\n') as f:
        f.write(encoded(data) + '\n')


def hashes(paths) -> dict[str, str]:
    return {str(p.resolve()): digest(p) for p in paths}


def unchanged(original: dict[str, str]) -> None:
    for name, value in original.items():
        if digest(Path(name)) != value:
            raise ValueError('input changed: ' + name)


def verify_geometry(race, course: Path, settings: dict[str, str]) -> None:
    """Bind logged boundaries/grid/laps, not just the human-readable track name."""
    track = read_properties(course)
    if int(race.profile['laps']) != int(settings.get('laps', '1')):
        raise ValueError('source lap rules differ from the profile')
    grid = f"{int(track['gameX'])}x{int(track['gameY'])}"
    if race.profile.get('grid') != grid:
        raise ValueError('source grid differs from course')
    def points(text):
        return tuple(tuple(map(int, point.strip().split(','))) for point in text.strip().split(';'))
    for key in ('trackLeft', 'trackRight'):
        if points(race.profile[key]) != points(track[key]):
            raise ValueError('source boundaries differ from course: ' + key)


def snapshot_identity(directory: Path, names) -> dict[str, str]:
    return {name: digest(directory / name) for name in names}


def verify_snapshots(directory: Path, expected: dict[str, str]) -> None:
    if not expected or any(Path(name).name != name for name in expected):
        raise ValueError('invalid snapshot manifest')
    for name, value in expected.items():
        if digest(directory / name) != value:
            raise ValueError('retained snapshot changed: ' + name)


class State:
    """Classification wrapper around the existing authoritative V2 transitions."""
    def __init__(self, cars: ReplayBoard, first=0, last=0):
        self.cars, self.first, self.last = cars.copy(), first, last

    def copy(self):
        return State(self.cars, self.first, self.last)

    def header(self, mover: int, command='v3') -> str:
        return f'{command},{mover},{self.cars.turns},{self.cars.laps},{self.first},{self.last};' + ';'.join(','.join(map(str, c)) for c in self.cars)

    def step(self, mover: int, dx: int, dy: int, mask) -> str:
        if race_finished(self.cars) or self.cars[mover][4]:
            raise ValueError('action after retirement/classification')
        self.cars, fate = apply_move(self.cars, mover, dx, dy, mask)
        rank = 0
        if fate == 'FINISH':
            self.first += 1
            rank = self.first
        elif fate in ('CRASH', 'TIMEOUT'):
            rank = len(self.cars) - self.last
            self.last += 1
        if rank:
            c = list(self.cars[mover]); c[4] = rank; self.cars[mover] = tuple(c)
        # Keep the survivor live until the caller records final classification.
        # A further query is forbidden by race_finished; no phantom turn is made.
        return fate

    def places(self):
        if not race_finished(self.cars):
            raise ValueError('unfinished classification')
        result = [c[4] if c[4] else self.first + 1 for c in self.cars]
        if sorted(result) != list(range(1, len(result) + 1)):
            raise ValueError('duplicate or missing place')
        return result


def at(log: Path, move: int, players: int) -> tuple[State, int, list]:
    cars, mover, moves = reconstruct_board(log, move, players, complete=True)
    first = last = 0
    for line in log.read_text(encoding='utf-8').splitlines():
        m = parse_move(line)
        if m is None or m.index >= move:
            continue
        rank = 0
        if m.status == 'FINISH':
            first += 1; rank = first
        elif m.status in ('CRASH', 'TIMEOUT'):
            rank = players - last; last += 1
        if rank:
            c = list(cars[m.player - 1]); c[4] = rank; cars[m.player - 1] = tuple(c)
    return State(cars, first, last), mover, moves


class Oracle:
    def __init__(self, java: Path, heap: str, jar: Path, props: Path, track: str, seed: int,
                 timeout: float, stderr: Path, protocol="v3"):
        self.protocol = protocol
        self.errors = stderr.open('x', encoding='utf-8')
        try:
            self.proc = subprocess.Popen([str(java), heap, '-jar', str(jar), '--auto', '--track', track,
                                          '--props', str(props), '--seed', str(seed), '--query-moves', '-', '-'],
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.errors,
                                         encoding='utf-8', text=True, bufsize=1)
        except BaseException:
            self.errors.close(); raise
        self.timer = threading.Timer(timeout, self.proc.kill); self.timer.daemon = True; self.timer.start()

    def request(self, state: State, mover: int, probe=False):
        assert self.proc.stdin and self.proc.stdout
        if probe and self.protocol != 'v3': raise ValueError('teacher diagnostics require V3')
        query = state.header(mover, 'chooser3' if probe else 'v3')
        if self.protocol == 'v2':
            query = f'v2,{mover},{state.cars.turns},{state.cars.laps};' + query.split(';', 1)[1]
        self.proc.stdin.write(query + '\n'); self.proc.stdin.flush()
        prefix = 'chooser3;' if probe else 'v2;'
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError('oracle stopped or exceeded whole-session deadline')
            if line.startswith(prefix):
                return json.loads(line[len(prefix):]) if probe else parse_v2_answer(line, state.cars.laps)

    def close(self):
        self.timer.cancel()
        try:
            if self.proc.poll() is None and self.proc.stdin:
                try: self.proc.stdin.write('quit\n'); self.proc.stdin.flush()
                except (BrokenPipeError, OSError): pass
            try: self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired: self.proc.kill(); self.proc.wait(timeout=10)
        finally:
            if self.proc.stdin: self.proc.stdin.close()
            if self.proc.stdout: self.proc.stdout.close()
            self.errors.close()

    def __enter__(self): return self
    def __exit__(self, *_): self.close()


def runtime(args) -> Path:
    require_plain_java_environment()
    java = shutil.which(args.java)
    if not java or not re.fullmatch(r'-Xmx[1-9][0-9]*[kKmMgG]', args.heap):
        raise ValueError('a Java executable and one explicit heap are required')
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        raise ValueError('timeout must be finite and positive')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.track):
        raise ValueError('invalid track name')
    return Path(java).resolve()


def verify_source(oracle: Oracle, log: Path, players: int) -> int:
    state, mover, moves = at(log, 1, players)
    checked = 0
    while not race_finished(state.cars):
        if checked >= len(moves): raise ValueError('incomplete source race')
        if state.cars[mover][4]: mover = (mover + 1) % players; continue
        observed = moves[checked]; before = state.cars[mover]
        dx, dy, mask = oracle.request(state, mover)
        fate = state.step(mover, dx, dy, mask)
        expected = (observed.x, observed.y, observed.old_vx, observed.old_vy)
        if (tuple(before[:4]) != expected or observed.player != mover + 1 or observed.index != state.cars.turns
                or observed.direction != DIRNAMES[DIRS.index((dx, dy))] or observed.status != fate
                or observed.new_x != before[0] + before[2] + dx or observed.new_y != before[1] + before[3] + dy):
            raise ValueError(f'source policy replay diverged at {observed.index}')
        transition = mask.transitions[DIRS.index((dx, dy))]
        observed_cp = (1 if 'cp1' in observed.detail.split() else 0) | (2 if 'cp2' in observed.detail.split() else 0)
        if fate == 'ok' and transition.checkpoints != observed_cp:
            raise ValueError('checkpoint replay diverged')
        checked += 1; mover = (mover + 1) % players
    if checked != len(moves): raise ValueError('source has moves after terminal classification')
    state.places()
    return checked


def collect(args):
    java = runtime(args)
    if not args.family.strip() or args.stride < 1 or args.limit < 1:
        raise ValueError('family and positive sampling limits required')
    jar, props, log = args.jar.resolve(), args.props.resolve(), args.log.resolve()
    course = jar.parent / 'tracks' / (args.track + '.track')
    race = read_race(log); roster = configured_players(props)
    if race.players != roster or race.slots != candidate_slots(read_properties(props).get('candidateSlots', '')) or any(kind == 'HUMAN' for _, kind in roster.values()):
        raise ValueError('source roster/profile does not match')
    verify_geometry(race, course, read_properties(props))
    inputs = hashes([jar, props, log, course, java] + sorted((ROOT / 'tracks').glob('*.py')))
    args.out.mkdir(parents=True, exist_ok=False)
    pending = args.out / 'pending.json'
    write_new(pending, {'operation': 'collect', 'inputs': inputs})
    source_props = args.out / 'source.properties'; shutil.copyfile(props, source_props)
    shutil.copyfile(log, args.out / 'source.log'); shutil.copyfile(course, args.out / 'course.track')
    teacher_props = args.out / 'teacher.properties'; shutil.copyfile(props, teacher_props)
    update_properties(teacher_props, {'candidateSlots': '', 'chooser.experiments': '', 'chooser.audit': 'false'})
    snapshots = snapshot_identity(args.out, ['source.properties', 'teacher.properties', 'source.log', 'course.track'])
    version = subprocess.run([str(java), '-version'], capture_output=True, text=True, check=True, timeout=30).stderr
    identity = {'schema': 1, 'teacher': digest(jar), 'teacher_profile': digest(teacher_props), 'source_profile': digest(props),
                'source_race': digest(log), 'family': args.family.strip().casefold(), 'geometry': digest(course),
                'feature_schema': FEATURES, 'java': version.strip(), 'heap': args.heap, 'seed': args.seed,
                'target': 'round260-chooser-verdict-order', 'inputs': inputs, 'snapshots': snapshots}
    with Oracle(java, args.heap, jar, source_props, args.track, args.seed, args.timeout, args.out / 'source.stderr') as source:
        identity['verified_moves'] = verify_source(source, log, len(roster))
    moves = [parse_move(line) for line in log.read_text(encoding='utf-8').splitlines()]
    moves = [m for m in moves if m is not None]
    wanted = [int(v) for v in args.moves.split(',')] if args.moves else [m.index for m in moves][::args.stride][:args.limit]
    if not wanted or len(set(wanted)) != len(wanted) or any(v not in {m.index for m in moves} for v in wanted):
        raise ValueError('requested decision indices invalid/duplicated')
    identity['selection'] = wanted
    rows_path = args.out / 'rows.pending.jsonl'
    with rows_path.open('x', encoding='utf-8') as output, Oracle(java, args.heap, jar, teacher_props, args.track,
                args.seed, args.timeout, args.out / 'teacher.stderr') as teacher:
        for turn in wanted:
            state, focal, _ = at(log, turn, len(roster))
            audit = teacher.request(state, focal, probe=True)
            record = {'id': hashlib.sha256(f'{identity["source_race"]}:{turn}'.encode()).hexdigest(),
                      'race': identity['source_race'], 'family': identity['family'], 'geometry': identity['geometry'],
                      'teacher': identity['teacher'], 'teacher_profile': identity['teacher_profile'], 'audit': audit}
            output.write(encoded(record) + '\n'); output.flush()
    unchanged(inputs)
    verify_snapshots(args.out, snapshots)
    rows_path.rename(args.out / 'rows.jsonl')
    identity['rows_sha256'] = digest(args.out / 'rows.jsonl')
    write_new(args.out / 'manifest.json', identity); pending.unlink()
    print(encoded({'decisions': len(wanted), 'verified_moves': identity['verified_moves'], 'out': str(args.out)}))


def load(paths: list[Path]):
    rows, manifests, ids = [], [], set()
    for directory in paths:
        if (directory / 'pending.json').exists(): raise ValueError('unfinished dataset')
        manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
        if manifest.get('schema') != 1 or manifest.get('feature_schema') != FEATURES:
            raise ValueError('incompatible dataset')
        if digest(directory / 'rows.jsonl') != manifest.get('rows_sha256'):
            raise ValueError('dataset digest mismatch')
        verify_snapshots(directory, manifest.get('snapshots', {}))
        manifests.append(digest(directory / 'manifest.json'))
        for line in (directory / 'rows.jsonl').read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            if row['id'] in ids: raise ValueError('duplicate source decision')
            ids.add(row['id'])
            for key, name in [('race', 'source_race'), ('geometry', 'geometry'), ('family', 'family'), ('teacher', 'teacher'), ('teacher_profile', 'teacher_profile')]:
                if row[key] != manifest[name]: raise ValueError('row identity differs from manifest')
            for f in row['audit']['features'].values():
                if not isinstance(f, list) or len(f) != 19 or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1.000001 for v in f):
                    raise ValueError('invalid numeric feature')
            rows.append(row)
    return rows, manifests


def separate(a, b):
    for key in ('id', 'race', 'family', 'geometry'):
        if {r[key] for r in a} & {r[key] for r in b}: raise ValueError('data leakage: ' + key)


def teacher_actions(row):
    audit = row['audit']; features = audit['features']; result = []
    for r in audit['teacher']:
        value = r['outcome']['verdict']
        if value == INF or r['action'] not in features: return []
        result.append((r['action'], features[r['action']], value))
    return result


def teacher_key(value):
    return (value < 0, max(0, value))


def fit(rows, epochs: int, rate: float, l2: float):
    if not 1 <= epochs <= 10000 or not math.isfinite(rate) or not 0 < rate <= 1 or not math.isfinite(l2) or l2 < 0:
        raise ValueError('invalid training parameters')
    pairs = []
    for row in sorted(rows, key=lambda r: r['id']):
        actions = teacher_actions(row)
        for i, (_, a, va) in enumerate(actions):
            for _, b, vb in actions[i + 1:]:
                if teacher_key(va) == teacher_key(vb): continue
                pairs.append(([y - x for x, y in zip(a, b)], float(teacher_key(va) < teacher_key(vb))))
    if not pairs: raise ValueError('no unequal teacher comparisons')
    weights = [0.0] * len(FEATURES)
    for epoch in range(epochs):
        grad = [l2 * w for w in weights]
        for delta, target in pairs:
            z = max(-40, min(40, sum(w * x for w, x in zip(weights, delta))))
            error = 1 / (1 + math.exp(-z)) - target
            for i, x in enumerate(delta): grad[i] += error * x / len(pairs)
        step = rate / math.sqrt(1 + epoch / 10)
        weights = [w - step * v for w, v in zip(weights, grad)]
    return weights


def model_report(rows, weights, margin):
    matched = switches = failures = n = 0; regrets = []
    for row in rows:
        actions = teacher_actions(row)
        if len(actions) < 2: continue
        # Student has the score-only baseline BEFORE the chooser, not its teacher's answer.
        initial = next((a for a in actions if a[0] == row['audit']['scoreChoice']), None)
        if initial is None: continue
        score = lambda a: sum(w * x for w, x in zip(weights, a[1]))
        pick = min(actions, key=score)
        if score(initial) - score(pick) <= margin: pick = initial
        best = min(actions, key=lambda a: teacher_key(a[2]))
        n += 1; switches += pick[0] != initial[0]; matched += teacher_key(pick[2]) == teacher_key(best[2])
        failures += pick[2] < 0 <= best[2]
        if pick[2] >= 0 and best[2] >= 0: regrets.append(pick[2] - best[2])
    return {'decisions': n, 'equal_teacher_value': matched, 'switches_from_scorer': switches,
            'teacher_death_errors': failures, 'mean_teacher_time_regret_on_live': sum(regrets) / len(regrets) if regrets else None,
            'scope': 'teacher forecast regret, not actual finishing-place or deployment performance'}


def validate_model(model):
    if (not isinstance(model, dict) or model.get('version') != 'chooser-distill-v1' or model.get('features') != FEATURES
            or not re.fullmatch('[0-9a-f]{64}', str(model.get('trainingSha256', '')))
            or not isinstance(model.get('weights'), list) or len(model['weights']) != 19
            or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1e6 for v in model['weights'])
            or type(model.get('margin')) not in (int, float) or not math.isfinite(model['margin']) or not 0 <= model['margin'] <= 100):
        raise ValueError('invalid student model')
    for key in ('training', 'validation'):
        if not isinstance(model.get(key), dict) or any(not isinstance(model[key].get(f), list) for f in ('race', 'family', 'geometry')):
            raise ValueError('model missing split provenance')


def train(args):
    a, am = load(args.train); b, bm = load(args.validation); separate(a, b)
    if len({r['teacher'] for r in a + b}) != 1: raise ValueError('teacher implementations differ')
    weights = fit(a, args.epochs, args.rate, args.l2)
    model = {'version': 'chooser-distill-v1', 'features': FEATURES, 'weights': weights, 'margin': args.margin,
             'trainingSha256': hashlib.sha256(encoded(sorted(am)).encode()).hexdigest(),
             'teacher': sorted({r['teacher'] for r in a}), 'trainingDatasets': am, 'validationDatasets': bm,
             'training': {k: sorted({r[k] for r in a}) for k in ('race', 'family', 'geometry')},
             'validation': {k: sorted({r[k] for r in b}) for k in ('race', 'family', 'geometry')},
             'parameters': {'epochs': args.epochs, 'rate': args.rate, 'l2': args.l2}}
    validate_model(model); model['report'] = model_report(b, weights, args.margin)
    write_new(args.out, model); print(encoded(model['report']))


def evaluate(args):
    model = json.loads(args.model.read_text(encoding='utf-8')); validate_model(model)
    rows, manifests = load(args.data)
    if {r['teacher'] for r in rows} != set(model['teacher']):
        raise ValueError('evaluation teacher differs from the model teacher')
    for k in ('race', 'family', 'geometry'):
        if {r[k] for r in rows} & set(model['training'][k] + model['validation'][k]): raise ValueError('evaluation overlaps ' + k)
    result = model_report(rows, model['weights'], model['margin'])
    result.update(model_sha256=digest(args.model), datasets=manifests)
    write_new(args.out, result); print(encoded(result))


def profile(args):
    flags = args.experiments.split(',') if args.experiments else []
    if len(set(flags)) != len(flags) or any(f not in FLAGS for f in flags): raise ValueError('invalid flags')
    if ('aware' in flags and 'student' in flags) or (any(f.startswith('legacy-') for f in flags) and len(flags) != 1):
        raise ValueError('conflicting or non-isolated arms')
    if not (1 <= args.rounds <= 24 and 0 <= args.budget <= 65536 and 0 <= args.move_budget <= 131072 and 1 <= args.setup_width <= 3 and 1 <= args.audit_every <= 1000000):
        raise ValueError('profile bounds invalid')
    settings = {'candidateSlots': '', 'chooser.experiments': ','.join(flags), 'chooser.rounds': str(args.rounds),
                'chooser.policyBudget': str(args.budget), 'chooser.moveBudget': str(args.move_budget),
                'chooser.setupWidth': str(args.setup_width), 'chooser.audit': str(args.audit).lower(), 'chooser.auditEvery': str(args.audit_every)}
    if {'student', 'assist'} & set(flags):
        if args.model is None: raise ValueError('student/assist requires a trained model')
        m = json.loads(args.model.read_text(encoding='utf-8')); validate_model(m)
        settings.update({'chooser.student.' + k: str(m[k]) for k in ('version', 'trainingSha256', 'margin')})
        settings['chooser.student.weights'] = ','.join(map(repr, m['weights'])); settings['chooser.student.features'] = ','.join(FEATURES)
    if any(f.startswith('legacy-') for f in flags):
        if args.legacy_model is None: raise ValueError('legacy control requires an explicit frozen v1 model')
        m = json.loads(args.legacy_model.read_text(encoding='utf-8'))
        if (m.get('version') != 1 or m.get('features') != LEGACY_FEATURES or not re.fullmatch('[0-9a-f]{64}', str(m.get('trainingSha256', '')))
                or len(m.get('weights', [])) != 12 or any(type(v) not in (float, int) or not math.isfinite(v) or abs(v) > 1e6 for v in m['weights'])
                or type(m.get('margin')) not in (int, float) or not math.isfinite(m['margin']) or not 0 <= m['margin'] <= 100):
            raise ValueError('invalid legacy v1 model')
        settings.update({'racecraft.model.' + k: str(m[k]) for k in ('version', 'trainingSha256', 'margin')})
        settings['racecraft.model.features'] = ','.join(LEGACY_FEATURES); settings['racecraft.model.weights'] = ','.join(map(repr, m['weights']))
    read_properties(args.base)
    with args.out.open('xb') as f: f.write(args.base.read_bytes())
    try: update_properties(args.out, settings)
    except BaseException: args.out.unlink(missing_ok=True); raise
    print('Created', args.out, '(candidateSlots intentionally empty)')


def audit_report(rows, moves):
    indexed = {m.index: m for m in moves}; observed_audits = {(r['turn'], r.get('mover')): r for r in rows}; paths = Counter(); overrides = Counter(); errors = Counter(); cases = []
    for row in rows:
        paths[row['path']] += 1
        if row['proposal'] and row['proposal'] != row['final']: overrides['proposal_replaced'] += 1
        previous = None
        for stage in row['stages']:
            if previous is not None and previous != stage['action']: overrides[stage['stage']] += 1
            previous = stage['action']
        plan = row.get('selectedPlan')
        forecast = plan if plan and plan['action'] == row['final'] else next((r for r in row['teacher'] if r['action'] == row['final']), None)
        if forecast is None:
            cases.append({'turn': row['turn'], 'reason': 'final_not_forecast'}); continue
        matched = 0; discrepancy = None
        for step in forecast['steps']:
            real = indexed.get(step['turn'] + 1)
            if real is None:
                discrepancy = {'reason': 'actual_race_ended', 'at': step['turn']}; break
            actual_status = 'LAP' if real.status.startswith('LAP ') else 'OK' if real.status == 'ok' else real.status
            if (real.player - 1 != step['mover'] or real.direction != step['action'] or actual_status != step['status']
                    or list((real.x, real.y, real.old_vx, real.old_vy)) != step['before'][:4]):
                discrepancy = {'reason': 'first_divergence', 'at': step['turn'], 'model': step['model'],
                               'predicted': step['action'], 'actual': real.direction, 'mover': step['mover']}
                observed = observed_audits.get((real.index - 1, real.player - 1))
                if observed is not None:
                    discrepancy['observedDecision'] = {key: observed.get(key) for key in ('path', 'scoreChoice', 'baseline', 'proposal', 'final', 'stages')}
                errors[step['model']] += 1; break
            matched += 1
        second = next((step for step in forecast['steps'][1:] if step['mover'] == row['mover']), None) if forecast['forcedSecond'] else None
        actual_second = indexed.get(second['turn'] + 1) if second else None
        followup = None if not second else dict(reached=actual_second is not None, predicted=forecast['forcedSecond'],
                      actual=actual_second.direction if actual_second else None,
                      samePrefix=matched >= forecast['steps'].index(second),
                      chosenAgain=actual_second is not None and actual_second.player - 1 == row['mover'] and actual_second.direction == forecast['forcedSecond'])
        cases.append({'turn': row['turn'], 'followup': followup, 'prefix_moves_matched': matched, 'first_difference': discrepancy,
                      'forced_second': forecast['forcedSecond']})
    return {'decisions': len(rows), 'paths': dict(paths), 'overrides': dict(overrides), 'first_errors_by_model': dict(errors),
            'cases': cases, 'scope': 'first-divergence audit; later predicted states are not independent errors; no causal place-gain claim'}


def audit(args):
    read_race(args.log)
    moves = [m for line in args.log.read_text(encoding='utf-8').splitlines() if (m := parse_move(line)) is not None]
    rows = [json.loads(line.split(' ', 1)[1]) for line in args.audit.read_text(encoding='utf-8').splitlines() if line.startswith('CHOOSER_AUDIT ')]
    if len({(r['turn'], r['mover']) for r in rows}) != len(rows): raise ValueError('duplicated audit decisions')
    indexed = {m.index: m for m in moves}
    for r in rows:
        real = indexed.get(r['turn'] + 1)
        if real is None or real.player - 1 != r['mover'] or real.direction != r['final'] or list((real.x, real.y, real.old_vx, real.old_vy)) != r['cars'][r['mover']][:4]:
            raise ValueError('audit and committed race do not match')
    result = audit_report(rows, moves); result.update(log_sha256=digest(args.log), audit_sha256=digest(args.audit))
    write_new(args.out, result); print(encoded({k: result[k] for k in ('decisions', 'paths', 'overrides', 'first_errors_by_model')}))


def continuation(oracle: Oracle, initial: State, focal: int, first_action: str, second_action: str | None, max_moves: int):
    state = initial.copy(); mover = focal; own = [0] * len(state.cars); steps = []
    while not race_finished(state.cars):
        if len(steps) >= max_moves: return {'complete': False, 'steps': steps}
        if state.cars[mover][4]: mover = (mover + 1) % len(state.cars); continue
        dx, dy, mask = oracle.request(state, mover)
        forced = first_action if mover == focal and own[focal] == 0 else second_action if mover == focal and own[focal] == 1 else None
        if forced is not None: dx, dy = DIRS[DIRNAMES.index(forced)]
        before = list(state.cars[mover]); fate = state.step(mover, dx, dy, mask); own[mover] += 1
        steps.append({'turn': state.cars.turns, 'mover': mover, 'action': DIRNAMES[DIRS.index((dx, dy))], 'before': before, 'fate': fate, 'forced': forced is not None})
        mover = (mover + 1) % len(state.cars)
    places = state.places()
    return {'complete': True, 'place': places[focal], 'ownMoves': own[focal], 'places': places, 'steps': steps}



def second_state(oracle: Oracle, initial: State, focal: int, first_action: str):
    """Recompute intervening real-policy replies before enumerating second moves."""
    state = initial.copy()
    _, _, mask = oracle.request(state, focal)
    dx, dy = DIRS[DIRNAMES.index(first_action)]
    state.step(focal, dx, dy, mask)
    mover = (focal + 1) % len(state.cars)
    while mover != focal and not race_finished(state.cars):
        if state.cars[mover][4] == 0:
            dx, dy, mask = oracle.request(state, mover); state.step(mover, dx, dy, mask)
        mover = (mover + 1) % len(state.cars)
    return state


def counterfactual(args):
    java = runtime(args)
    if args.max_moves < 1 or not 1 <= args.second_width <= 3: raise ValueError('positive continuation/width bounds required')
    jar, props, log = args.jar.resolve(), args.props.resolve(), args.log.resolve()
    race = read_race(log); roster = configured_players(props)
    if race.players != roster: raise ValueError('source roster differs')
    course = jar.parent / 'tracks' / (args.track + '.track')
    verify_geometry(race, course, read_properties(props))
    inputs = hashes([jar, props, log, course, java] + sorted((ROOT / 'tracks').glob('*.py')))
    args.out.mkdir(parents=True, exist_ok=False); write_new(args.out / 'pending.json', inputs)
    state, focal, _ = at(log, args.move, len(roster))
    with Oracle(java, args.heap, jar, props, args.track, args.seed, args.timeout, args.out / 'oracle.stderr') as oracle:
        verified = verify_source(oracle, log, len(roster)); record = oracle.request(state, focal, probe=True)
        actions = [r['action'] for r in record['teacher']]
        if not actions: raise ValueError('this decision bypasses the ordinary chooser')
        outcomes = []
        for forecast in record['teacher']:
            first = forecast['action']
            seconds = [None]
            if args.depth == 2:
                next_state = second_state(oracle, state, focal, first)
                if not race_finished(next_state.cars):
                    dx, dy, mask = oracle.request(next_state, focal)
                    baseline_second = DIRNAMES[DIRS.index((dx, dy))]
                    second_audit = oracle.request(next_state, focal, probe=True)
                    preferred = [r['action'] for r in second_audit['teacher']]
                    preferred += [name for name in DIRNAMES if name not in preferred]
                    legal = [name for name in preferred if name != baseline_second
                             and mask.transitions[DIRNAMES.index(name)].status not in ('CRASH', 'TIMEOUT')]
                    seconds += legal[:args.second_width - 1]
                    # None already includes the actual continuation; do not count
                    # it twice as independent evidence or force an illegal plan.
            for second in seconds:
                result = continuation(oracle, state, focal, first, second, args.max_moves)
                path = f'{first}-{second or "policy"}.json'; write_new(args.out / path, result)
                outcomes.append({'first': first, 'second': second, 'complete': result['complete'],
                                 'place': result.get('place'), 'ownMoves': result.get('ownMoves'), 'trace': path, 'sha256': digest(args.out / path)})
    unchanged(inputs)
    complete = all(r['complete'] for r in outcomes)
    result = {'schema': 1, 'move': args.move, 'depth': args.depth, 'verified_moves': verified, 'inputs': inputs,
              'comparable': complete, 'outcomes': outcomes, 'best': min(outcomes, key=lambda r: (r['place'], r['ownMoves'])) if complete else None,
              'scope': 'evaluated one/two-action deviations under the supplied frozen continuation policy; not a universal optimum'}
    singles = [r for r in outcomes if r['second'] is None]
    best_single = min(singles, key=lambda r: (r['place'], r['ownMoves'])) if complete and singles else None
    result['best_single'] = best_single
    result['setup_place_delta'] = result['best']['place'] - best_single['place'] if best_single else None
    result['setup_time_delta_at_equal_place'] = result['best']['ownMoves'] - best_single['ownMoves'] if best_single and result['setup_place_delta'] == 0 else None
    write_new(args.out / 'report.json', result); (args.out / 'pending.json').unlink(); print(encoded({'comparable': complete, 'alternatives': len(outcomes), 'best': result['best']}))



def lineup(n, focal, density, background, candidate):
    if not 1 <= density <= n or not 0 <= focal < n: raise ValueError('invalid density/focal')
    result = [background] * n
    for k in range(1, density): result[(focal + k) % n] = candidate
    return result


def league(args):
    java = runtime(args)
    spec = json.loads(args.spec.read_text(encoding='utf-8'))
    if spec.get('version') != 1 or args.max_moves < 1: raise ValueError('invalid league specification/bounds')
    policies = {}
    for item in spec['policies']:
        name = item['name']
        if name in policies or not re.fullmatch(r'[A-Za-z0-9_-]+', name): raise ValueError('unsafe/duplicate policy name')
        jar = (args.spec.parent / item['jar']).resolve(); props = (args.spec.parent / item['props']).resolve()
        course = jar.parent / 'tracks' / (args.track + '.track'); settings = read_properties(props)
        protocol = item.get('protocol', 'v3')
        if protocol not in ('v2', 'v3') or protocol == 'v2' and settings.get('chooser.experiments', '').strip():
            raise ValueError('experimental policies require V3')
        policies[name] = dict(jar=jar, props=props, course=course, settings=settings, roster=configured_players(props), protocol=protocol)
    baseline, candidate, referee = spec['baseline'], spec['candidate'], spec['referee']
    if baseline == candidate or any(v not in policies for v in (baseline, candidate, referee)): raise ValueError('invalid policy roles')
    reference = policies[referee]; n = len(reference['roster'])
    for policy in policies.values():
        if (policy['roster'] != reference['roster'] or digest(policy['course']) != digest(reference['course'])
                or int(policy['settings'].get('laps', '1')) != int(reference['settings'].get('laps', '1'))):
            raise ValueError('league geometry/roster/laps differ')
    backgrounds = spec['backgrounds']; densities = spec.get('densities', [1, 4, 7]); focals = list(range(n)) if not args.focals else list(map(int, args.focals.split(',')))
    if (not backgrounds or len(set(backgrounds)) != len(backgrounds) or any(v not in policies for v in backgrounds)
            or not densities or len(set(densities)) != len(densities) or any(type(d) is not int or not 1 <= d <= n for d in densities)
            or not focals or len(set(focals)) != len(focals) or any(not 0 <= f < n for f in focals)):
        raise ValueError('invalid league populations')
    inputs = hashes([args.spec, java] + args.logs + [v for policy in policies.values() for v in (policy['jar'], policy['props'], policy['course'])]
                    + sorted((ROOT / 'tracks').glob('*.py')))
    args.out.mkdir(parents=True, exist_ok=False); write_new(args.out / 'pending.json', inputs)
    for name, policy in policies.items(): shutil.copyfile(policy['props'], args.out / (name + '.properties'))
    pairs = []
    with contextlib.ExitStack() as stack:
        actors = {name: stack.enter_context(Oracle(java, args.heap, policy['jar'], policy['props'], args.track, args.seed,
                    args.timeout, args.out / (name + '.stderr'), policy['protocol'])) for name, policy in policies.items()}
        for li, log in enumerate(args.logs):
            race = read_race(log)
            if race.players != reference['roster'] or int(race.profile['laps']) != int(reference['settings'].get('laps', '1')):
                raise ValueError('league start roster/laps differ')
            verify_geometry(race, reference['course'], reference['settings'])
            initial, first, _ = at(log, 1, n)
            for background in backgrounds:
                for density in densities:
                    for focal in focals:
                        fixed = lineup(n, focal, density, background, candidate); results = []
                        for replacement in (baseline, candidate):
                            assignment = fixed.copy(); assignment[focal] = replacement
                            for i, name in enumerate(assignment):
                                settings = policies[name]['settings']
                                if settings.get('chooser.experiments', '').strip() and i + 1 not in candidate_slots(settings.get('candidateSlots', '')):
                                    raise ValueError('experimental actor disabled in assigned slot')
                            state = initial.copy(); mover = first; own = [0] * n; trace = []
                            while not race_finished(state.cars) and len(trace) < args.max_moves:
                                if state.cars[mover][4]: mover = (mover + 1) % n; continue
                                actor = actors[assignment[mover]]; dx, dy, mask = actor.request(state, mover)
                                _, _, authority = actors[referee].request(state, mover)
                                if mask.transitions != authority.transitions: raise ValueError('policy/referee transitions disagree')
                                fate = state.step(mover, dx, dy, authority); own[mover] += 1
                                trace.append(dict(turn=state.cars.turns, mover=mover, policy=assignment[mover], action=DIRNAMES[DIRS.index((dx, dy))], fate=fate))
                                mover = (mover + 1) % n
                            complete = race_finished(state.cars)
                            result = dict(complete=complete, lineup=assignment, place=state.places()[focal] if complete else None,
                                          ownMoves=own[focal], trace=trace, policy=replacement)
                            filename = f'{li}-{background}-{density}-{focal}-{replacement}.json'
                            write_new(args.out / filename, result)
                            results.append(dict(file=filename, sha256=digest(args.out / filename), complete=complete,
                                                place=result['place'], ownMoves=own[focal], lineup=assignment))
                        complete = all(r['complete'] for r in results)
                        pairs.append(dict(background=background, density=density, focal=focal, source=digest(log), arms=results,
                                          complete=complete, placeDelta=results[1]['place'] - results[0]['place'] if complete else None))
    unchanged(inputs)
    slices = []
    for background in backgrounds:
        for density in densities:
            group = [p for p in pairs if p['background'] == background and p['density'] == density]; valid = [p for p in group if p['complete']]
            times = [p['arms'][1]['ownMoves'] - p['arms'][0]['ownMoves'] for p in valid if p['placeDelta'] == 0]
            slices.append(dict(background=background, density=density, completePairs=len(valid), censoredPairs=len(group)-len(valid),
                               meanPlaceDelta=sum(p['placeDelta'] for p in valid)/len(valid) if valid else None,
                               meanTimeDeltaAtEqualPlace=sum(times)/len(times) if times else None))
    report = dict(schema=1, inputs=inputs, specification=spec, pairs=pairs, slices=slices,
                  scope='focal replacement with fixed opponents; process-oracle runtime is not production latency; no automatic promotion')
    write_new(args.out / 'report.json', report); (args.out / 'pending.json').unlink(); print(encoded(slices))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    def execution(name, function):
        c = sub.add_parser(name); c.set_defaults(func=function)
        for k in ('props', 'log', 'out'): c.add_argument('--' + k, type=Path, required=True)
        c.add_argument('--jar', type=Path, default=ROOT / 'theoreticRacing.jar'); c.add_argument('--track', required=True)
        c.add_argument('--java', default='java'); c.add_argument('--heap', default='-Xmx8g'); c.add_argument('--seed', type=int, default=1)
        c.add_argument('--timeout', type=float, default=3600); return c
    c = execution('collect', collect); c.add_argument('--family', required=True); c.add_argument('--stride', type=int, default=25)
    c.add_argument('--limit', type=int, default=20); c.add_argument('--moves')
    c = execution('counterfactual', counterfactual); c.add_argument('--move', type=int, required=True)
    c.add_argument('--second-width', type=int, default=2); c.add_argument('--depth', type=int, choices=(1, 2), default=2); c.add_argument('--max-moves', type=int, default=10000)
    t = sub.add_parser('train'); t.set_defaults(func=train); t.add_argument('--train', nargs='+', type=Path, required=True)
    t.add_argument('--validation', nargs='+', type=Path, required=True); t.add_argument('--out', type=Path, required=True)
    t.add_argument('--epochs', type=int, default=200); t.add_argument('--rate', type=float, default=.5); t.add_argument('--l2', type=float, default=.001)
    t.add_argument('--margin', type=float, default=.05)
    e = sub.add_parser('evaluate'); e.set_defaults(func=evaluate); e.add_argument('--model', type=Path, required=True)
    e.add_argument('--data', nargs='+', type=Path, required=True); e.add_argument('--out', type=Path, required=True)
    a = sub.add_parser('audit'); a.set_defaults(func=audit)
    for k in ('audit', 'log', 'out'): a.add_argument('--' + k, type=Path, required=True)
    f = sub.add_parser('profile'); f.set_defaults(func=profile); f.add_argument('--base', type=Path, default=ROOT / 'tracks/lap_bench.properties')
    f.add_argument('--experiments', default=''); f.add_argument('--out', type=Path, required=True)
    f.add_argument('--model', type=Path); f.add_argument('--legacy-model', type=Path); f.add_argument('--audit', action='store_true')
    f.add_argument('--rounds', type=int, default=12); f.add_argument('--budget', type=int, default=4096); f.add_argument('--move-budget', type=int, default=8192)
    f.add_argument('--setup-width', type=int, default=2); f.add_argument('--audit-every', type=int, default=1)
    l = sub.add_parser('league'); l.set_defaults(func=league)
    l.add_argument('--spec', type=Path, required=True); l.add_argument('--logs', type=Path, nargs='+', required=True)
    l.add_argument('--out', type=Path, required=True); l.add_argument('--track', required=True); l.add_argument('--focals')
    l.add_argument('--java', default='java'); l.add_argument('--heap', default='-Xmx8g'); l.add_argument('--seed', type=int, default=1)
    l.add_argument('--max-moves', type=int, default=10000); l.add_argument('--timeout', type=float, default=3600)
    args = p.parse_args(argv)
    try: args.func(args); return 0
    except (ValueError, OSError, RuntimeError, KeyError, TypeError, subprocess.SubprocessError) as e:
        print('chooser lab:', e, file=sys.stderr); return 2


if __name__ == '__main__':
    raise SystemExit(main())
