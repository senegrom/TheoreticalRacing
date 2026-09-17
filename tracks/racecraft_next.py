#!/usr/bin/env python3
"""Second research batch: policy-state collection, place-first learning, regret
attribution and focal-replacement opponent leagues. Nothing is promoted.

All successful artifacts bind input identities and complete traces. Censored
comparisons are excluded as whole groups, never counted as wins. Policies remain
frozen during collection; each car chooses for itself, never for a coalition.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

if __package__:
    from . import racecraft_lab as lab
    from .forensics_common import DIRS, DIRNAMES, ReplayBoard, parse_v2_answer, reconstruct_board
    from .oracle_roll import apply_move, race_finished
else:
    import racecraft_lab as lab
    from forensics_common import DIRS, DIRNAMES, ReplayBoard, parse_v2_answer, reconstruct_board
    from oracle_roll import apply_move, race_finished

FEATURES = lab.FEATURES + ('closing_motion', 'relative_route', 'route_known', 'rival_moves_first',
                          'response_delta', 'rival_exits', 'field_size')
FLAGS = lab.EXPERIMENTS | {'diverse', 'progressive', 'lexicographic'}
ROOT = Path(__file__).resolve().parents[1]


def json_read(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


class Inputs:
    """Bind original AND effective inputs. Failure leaves diagnostics, no success marker."""
    def __init__(self, paths):
        self.hashes = {str(Path(p).resolve()): lab.digest(Path(p)) for p in paths}

    def add(self, path):
        self.hashes[str(Path(path).resolve())] = lab.digest(Path(path))

    def verify(self):
        lab.require_plain_java_environment()
        if any(lab.digest(Path(p)) != value for p, value in self.hashes.items()):
            raise ValueError('input identity changed; incomplete evidence is not publishable')


def runtime(args):
    lab.require_plain_java_environment()
    if not lab.re.fullmatch(r'-Xmx[1-9][0-9]*[kKmMgG]', args.heap):
        raise ValueError('one explicit heap is required')
    found = shutil.which(args.java)
    if not found:
        raise ValueError('Java executable not found')
    if not math.isfinite(args.timeout) or args.timeout <= 0 or args.max_moves < 1:
        raise ValueError('positive finite collection limits required')
    java = Path(found).resolve()
    version = subprocess.run([str(java), '-version'], capture_output=True, text=True, check=True, timeout=30).stderr
    return java, version.strip()


def policy(name, jar, props, track, *, protocol='v3'):
    if protocol not in ('v2', 'v3') or not name or not lab.re.fullmatch(r'[A-Za-z0-9_-]+', track):
        raise ValueError('invalid policy or protocol')
    jar, props = Path(jar).resolve(), Path(props).resolve()
    course = jar.parent / 'tracks' / (track + '.track')
    settings = lab.read_properties(props)
    roster = lab.configured_players(props)
    if any(kind == 'HUMAN' for _, kind in roster.values()):
        raise ValueError('laboratory policies must be all-AI')
    experimental = bool(settings.get('racecraft.experiments', '').strip())
    if experimental and protocol != 'v3':
        raise ValueError('experimental policies require classification-aware v3')
    return {'name': name, 'jar': jar, 'props': props, 'course': course, 'protocol': protocol,
            'slots': {int(v.strip()) for v in settings.get('candidateSlots','').split(',') if v.strip()},
            'roster': roster, 'laps': int(settings.get('laps', '1')), 'experimental': experimental,
            'jar_sha256': lab.digest(jar), 'props_sha256': lab.digest(props),
            'course_sha256': lab.digest(course)}


def policy_identity(p):
    return {k: p[k] for k in ('name', 'protocol', 'experimental', 'jar_sha256', 'props_sha256', 'course_sha256', 'laps')}


def compatible(a, b):
    if a['roster'] != b['roster'] or a['laps'] != b['laps'] or a['course_sha256'] != b['course_sha256']:
        raise ValueError('policy roster, lap rules or exact course geometry differ')


class PolicyOracle(lab.LabOracle):
    """A v3 policy gets actual classification order, not old query sentinels.
    v2 is explicitly supported only for frozen non-experimental historical cars.
    The designated referee, not the opponent implementation, owns transitions.
    """
    def __init__(self, p, track, java, heap, seed, timeout, stderr):
        super().__init__(track, p['jar'], p['props'], java, heap, seed, timeout, stderr)
        self.policy = p

    def exchange(self, header, board, prefix):
        assert self.proc.stdin is not None and self.proc.stdout is not None
        self.proc.stdin.write(header + ';' + ';'.join(','.join(map(str, car)) for car in board) + '\n')
        self.proc.stdin.flush()
        self.asks += 1
        while True:
            text = self.proc.stdout.readline()
            if not text:
                raise RuntimeError('policy oracle terminated or exceeded its deadline')
            if text.startswith(prefix):
                return text.strip()

    def classified(self, board, placed, first, last):
        if len(placed) != first + last:
            raise ValueError('classification count mismatch')
        cars = board.copy()
        for i, car in enumerate(cars):
            if car[4]:
                if i not in placed:
                    raise ValueError('missing classification for retired car')
                cars[i] = tuple(list(car[:4]) + [placed[i]] + list(car[5:]))
            elif i in placed:
                raise ValueError('live car already classified')
        return cars

    def ask_at(self, mover, board, placed, first, last):
        if self.policy['protocol'] == 'v2':
            return super().ask(mover, board)
        cars = self.classified(board, placed, first, last)
        return parse_v2_answer(self.exchange('v3,%d,%d,%d,%d,%d' %
                                            (mover, board.turns, board.laps, first, last), cars, 'v2;'), board.laps)

    def feature_rows(self, mover, board, placed, first, last):
        cars = self.classified(board, placed, first, last)
        answer = self.exchange('lab3,%d,%d,%d,%d,%d' %
                               (mover, board.turns, board.laps, first, last), cars, 'lab3;').split(';')
        if len(answer) != 3 or answer[1] != '2':
            raise ValueError('incompatible schema-2 features')
        rows = [None if s == '-' else list(map(float, s.split(','))) for s in answer[2].split('|')]
        if len(rows) != 9:
            raise ValueError('incomplete action features')
        for f in rows:
            if f is not None:
                lab.check_features(f, FEATURES)
        return rows

    def audit(self, mover, board, placed, first, last):
        cars = self.classified(board, placed, first, last)
        answer = self.exchange('audit3,%d,%d,%d,%d,%d' %
                               (mover, board.turns, board.laps, first, last), cars, 'audit3;').split(';', 2)
        direction = DIRNAMES[DIRS.index(tuple(map(int, answer[1].split(','))))]
        trace = json.loads(answer[2])
        trace.setdefault('selected', direction)
        if trace['selected'] != direction:
            raise ValueError('search diagnostic disagrees with executed action')
        return trace


def classify(placed, first, last, mover, fate, n):
    if fate == 'FINISH':
        first += 1; placed[mover] = first
    elif fate in ('CRASH', 'TIMEOUT'):
        placed[mover] = n - last; last += 1
    return first, last


def replay(oracle, log, n, trace):
    board, mover, moves = reconstruct_board(log, 1, n, complete=True)
    placed, first, last = {}, 0, 0
    for observed in moves:
        while board[mover][4] != 0:
            mover = (mover + 1) % n
        if race_finished(board):
            raise ValueError('source trace continues after classification')
        dx, dy, mask = oracle.ask_at(mover, board, placed, first, last)
        x, y, vx, vy = board[mover][:4]
        after, fate = apply_move(board, mover, dx, dy, mask)
        if (observed.index != board.turns + 1 or observed.player != mover + 1
                or observed.direction != DIRNAMES[DIRS.index((dx, dy))] or observed.status != fate
                or (x, y, vx, vy, x + vx + dx, y + vy + dy, vx + dx, vy + dy) !=
                (observed.x, observed.y, observed.old_vx, observed.old_vy,
                 observed.new_x, observed.new_y, observed.new_vx, observed.new_vy)):
            raise ValueError('generating policy does not replay source exactly at move %d' % observed.index)
        expected_cp = (1 if 'cp1' in observed.detail.split() else 0) | (2 if 'cp2' in observed.detail.split() else 0)
        if fate == 'ok' and mask.transitions[DIRS.index((dx,dy))].checkpoints != expected_cp:
            raise ValueError('source checkpoint replay differs')
        trace.write(lab.encoded({'move': observed.index, 'action': observed.direction, 'fate': fate}) + '\n')
        first, last = classify(placed, first, last, mover, fate, n)
        board, mover = after, (mover + 1) % n
    if not race_finished(board):
        raise ValueError('source race is incomplete')
    return moves


def continuation(actors, referee, initial, focal, action, placed, first, last, max_moves, trace):
    board, placed = initial.copy(), dict(placed)
    n = len(board); own = [0] * n; mover = focal; committed = 0
    trace.write(lab.encoded({'initial': list(board), 'turns': board.turns, 'laps': board.laps,
                            'focal': focal, 'action': None if action is None else DIRNAMES[action],
                            'placed': placed, 'first': first, 'last': last,
                            'lineup': [p.policy['name'] for p in actors]}) + '\n')
    while not race_finished(board):
        if committed >= max_moves:
            return {'complete': False, 'place': None, 'own_moves': None, 'committed': committed}
        if board[mover][4] != 0:
            mover = (mover + 1) % n; continue
        dx, dy, answer = actors[mover].ask_at(mover, board, placed, first, last)
        _, _, authority = referee.ask_at(mover, board, placed, first, last)
        if answer.transitions != authority.transitions:
            raise ValueError('opponent and authoritative referee rules disagree')
        if committed == 0 and action is not None:
            dx, dy = DIRS[action]
        before_turn = board.turns
        board, fate = apply_move(board, mover, dx, dy, authority)
        own[mover] += 1; committed += 1
        first, last = classify(placed, first, last, mover, fate, n)
        trace.write(lab.encoded({'turn': before_turn + 1, 'mover': mover,
                                'action': DIRNAMES[DIRS.index((dx, dy))], 'fate': fate,
                                'transition': list(authority.transitions[DIRS.index((dx,dy))]),
                                'placed': placed}) + '\n')
        mover = (mover + 1) % n
    for i, car in enumerate(board):
        if car[4] == 0: placed[i] = first + 1
    if set(placed) != set(range(n)) or set(placed.values()) != set(range(1, n + 1)):
        raise ValueError('invalid final classification')
    return {'complete': True, 'place': placed[focal], 'own_moves': own[focal], 'committed': committed,
            'classification': [placed[i] for i in range(n)], 'all_own_moves': own}


def collect(args):
    java, version = runtime(args)
    if min(args.limit, args.stride) < 1 or not args.family.strip():
        raise ValueError('positive selection limits and explicit family required')
    source = policy('generating', args.jar, args.props, args.track)
    if source['experimental'] and args.state_policy != 'experimental':
        raise ValueError('experimental source requires --state-policy experimental')
    if not source['experimental'] and args.state_policy == 'experimental':
        raise ValueError('experimental source profile has no experiment')
    race = lab.read_race(args.log)
    if race.players != source['roster'] or int(race.profile['laps']) != source['laps']:
        raise ValueError('source log/profile roster or laps differ')
    if race.slots != source['slots']:
        raise ValueError('source log/profile candidate slots differ')
    if args.state_policy == 'champion' and source['slots']:
        raise ValueError('champion-state collection requires no candidate slots')
    if args.state_policy == 'experimental' and not race.slots:
        raise ValueError('experimental source log has no selected slots')
    logged_flags = [s[len('# racecraft-experiments '):].strip()
                    for s in args.log.read_text(encoding='utf-8').splitlines()
                    if s.startswith('# racecraft-experiments ')]
    configured_flags = lab.read_properties(source['props']).get('racecraft.experiments', '').strip()
    if logged_flags != ([configured_flags] if configured_flags else []):
        raise ValueError('source log/profile experiment flags differ')
    paths = [java, args.log, source['jar'], source['props'], source['course']] + sorted((ROOT/'tracks').glob('*.py'))
    args.out.mkdir(parents=True, exist_ok=False)
    out = args.out.resolve()
    inputs = Inputs(paths)
    for origin, name in ((args.log, 'source.log'), (source['props'], 'generating.properties'),
                         (source['course'], 'course.track')):
        shutil.copyfile(origin, out/name); inputs.add(out/name)
    if args.continuation == 'source':
        following = source
    elif args.continuation == 'champion':
        clean = out/'continuation.properties'; shutil.copyfile(source['props'], clean)
        lab.update_properties(clean, {'racecraft.experiments': '', 'candidateSlots': ''})
        following = policy('continuation-champion', source['jar'], clean, args.track)
    else:
        if args.continuation_jar is None or args.continuation_props is None:
            raise ValueError('specified continuation requires jar AND props')
        following = policy('continuation-specified', args.continuation_jar, args.continuation_props,
                           args.track, protocol=args.continuation_protocol)
    compatible(source, following)
    for p in (following['jar'], following['props'], following['course']): inputs.add(p)
    shutil.copyfile(following['props'], out/'following.properties'); inputs.add(out/'following.properties')
    identity = {'schema': 2, 'features': list(FEATURES), 'family': args.family.strip().casefold(),
                'track': args.track, 'race_sha256': lab.digest(args.log), 'course_sha256': source['course_sha256'],
                'state_policy': args.state_policy, 'generating_policy': policy_identity(source),
                'continuation_policy': policy_identity(following), 'java': version, 'heap': args.heap,
                'seed': args.seed, 'selection': {'moves': args.moves, 'stride': args.stride, 'limit': args.limit},
                'max_moves': args.max_moves, 'timeout': args.timeout, 'inputs': inputs.hashes}
    lab.write_new(out/'manifest.pending.json', lab.encoded(identity)+'\n')
    with contextlib.ExitStack() as stack:
        generator = stack.enter_context(PolicyOracle(source, args.track, java, args.heap, args.seed,
                                                      args.timeout, out/'generating.stderr'))
        follower = stack.enter_context(PolicyOracle(following, args.track, java, args.heap, args.seed,
                                                     args.timeout, out/'following.stderr'))
        with (out/'source-replay.jsonl').open('x', encoding='utf-8') as trace:
            moves = replay(generator, args.log, len(race.players), trace)
        targets = [int(s) for s in args.moves.split(',')] if args.moves else [m.index for m in moves[::args.stride]][:args.limit]
        if not targets or len(set(targets)) != len(targets) or not set(targets) <= {m.index for m in moves}:
            raise ValueError('select unique existing source moves')
        rows = []
        for target in targets:
            board, focal, _ = reconstruct_board(args.log, target, len(race.players), complete=True)
            placed, first, last = lab.prefix_classification(args.log, target, len(board))
            dx, dy, mask = generator.ask_at(focal, board, placed, first, last)
            features = generator.feature_rows(focal, board, placed, first, last)
            audit = generator.audit(focal, board, placed, first, last)
            if audit['selected'] != DIRNAMES[DIRS.index((dx, dy))]:
                raise ValueError('audit altered source action')
            actions = []
            for i, f in enumerate(features):
                if f is None: continue
                if mask.transitions[i].status not in ('OK','LAP','FINISH'):
                    raise ValueError('feature/referee action mismatch')
                name = '%06d-%s.jsonl' % (target, DIRNAMES[i])
                with (out/name).open('x', encoding='utf-8') as trace:
                    result = continuation([follower]*len(board), generator, board, focal, i, placed,
                                          first, last, args.max_moves, trace)
                actions.append({'direction': DIRNAMES[i], 'features': f, 'outcome': result,
                                'trace': name, 'trace_sha256': lab.digest(out/name)})
            row = {'id': identity['race_sha256']+':'+str(target), 'race_sha256': identity['race_sha256'],
                   'family': identity['family'], 'track': args.track, 'course_sha256': identity['course_sha256'],
                   'move': target, 'focal': focal, 'players': len(board), 'baseline': DIRNAMES[DIRS.index((dx,dy))],
                   'actions': actions, 'audit': audit}
            rows.append(row)
            with (out/'rows.pending.jsonl').open('a', encoding='utf-8') as f: f.write(lab.encoded(row)+'\n')
    inputs.verify()
    identity.update(rows_sha256=lab.digest(out/'rows.pending.jsonl'), samples=len(rows),
                    censored_samples=sum(any(not a['outcome']['complete'] for a in r['actions']) for r in rows),
                    outputs={p.name: lab.digest(p) for p in out.iterdir() if p.is_file() and not p.name.startswith('manifest')})
    (out/'rows.pending.jsonl').rename(out/'rows.jsonl')
    identity['outputs']['rows.jsonl'] = identity['outputs'].pop('rows.pending.jsonl')
    lab.write_new(out/'manifest.json', lab.encoded(identity)+'\n'); (out/'manifest.pending.json').unlink()
    print('Policy-state dataset:', out, 'samples:', len(rows))


def load(paths):
    rows, digests = lab.load_datasets(paths, features=FEATURES, schema=2)
    for path in paths:
        m = json_read(path/'manifest.json')
        for name, expected in m.get('outputs', {}).items():
            if Path(name).name != name or lab.digest(path/name) != expected:
                raise ValueError('dataset output hash mismatch')
        if m.get('state_policy') not in ('champion','experimental'):
            raise ValueError('missing generating policy identity')
        for name in ('generating_policy','continuation_policy'):
            ident=m.get(name,{})
            if any(not isinstance(ident.get(k),str) or not lab.HEX.fullmatch(ident[k])
                   for k in ('jar_sha256','props_sha256','course_sha256')):
                raise ValueError('missing policy identity hashes')
    return rows, digests


def linear(w, f):
    return sum(a*b for a,b in zip(w[:-1],f)) + w[-1]


def fit_heads(rows, epochs, rate, l2):
    if epochs < 1 or not math.isfinite(rate) or not 0 < rate <= .1 or not math.isfinite(l2) or l2 < 0:
        raise ValueError('invalid two-stage training controls (rate <= 0.1)')
    usable=lab.usable(rows)
    examples=[(a['features']+[1.], (a['outcome']['place']-1)/max(1,r['players']-1)) for r in usable for a in r['actions']]
    if not examples: raise ValueError('no complete training examples')
    time_pairs=[]
    for r in usable:
        for i,a in enumerate(r['actions']):
            for b in r['actions'][i+1:]:
                if lab.key(a)[0] != lab.key(b)[0] or lab.key(a)[1] == lab.key(b)[1]: continue
                time_pairs.append(([y-x for x,y in zip(a['features'],b['features'])]+[0.], float(lab.key(a)[1]<lab.key(b)[1])))
    place=[0.]*(len(FEATURES)+1); time=place.copy()
    for epoch in range(epochs):
        gp=[l2*w for w in place]; gt=[l2*w for w in time]
        for f,y in examples:
            error=sum(w*x for w,x in zip(place,f))-y
            for i,x in enumerate(f): gp[i]+=error*x/len(examples)
        for delta,y in time_pairs:
            z=max(-40., min(40.,sum(w*x for w,x in zip(time,delta))))
            error=1/(1+math.exp(-z))-y
            for i,x in enumerate(delta): gt[i]+=error*x/len(time_pairs)
        step=rate/math.sqrt(1+epoch/10)
        place=[w-step*g for w,g in zip(place,gp)]; time=[w-step*g for w,g in zip(time,gt)]
    return place,time,len(time_pairs)


def predicted_place(model, f, n):
    score=linear(model['weights'],f)
    if not 0 <= score <= 1: return None
    rank=lambda v: math.floor(max(0.,min(1.,v))*(n-1)+1.5)
    low,high=rank(score-model['placeRadius']),rank(score+model['placeRadius'])
    return low if low==high else None


def better(model, a, b, n):
    pa,pb=predicted_place(model,a,n),predicted_place(model,b,n)
    return pa is not None and pb is not None and (pa<pb or pa==pb and linear(model['timeWeights'],b)-linear(model['timeWeights'],a)>model['margin'])


def validate_model(m):
    if not isinstance(m,dict) or type(m.get('version')) is not int or m['version'] != 2 or m.get('features') != list(FEATURES):
        raise ValueError('invalid place-first model schema')
    for name in ('weights','timeWeights'):
        w=m.get(name)
        if not isinstance(w,list) or len(w)!=len(FEATURES)+1 or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1e6 for x in w):
            raise ValueError('invalid model head')
    for name,bound in (('placeRadius',1),('margin',100)):
        v=m.get(name)
        if type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=bound: raise ValueError('invalid '+name)
    if not isinstance(m.get('trainingSha256'),str) or not lab.HEX.fullmatch(m['trainingSha256']): raise ValueError('missing model provenance')
    for field in ('Families','Races','Courses'):
        for prefix in ('training','validation'):
            values=m.get(prefix+field)
            if not isinstance(values,list) or not values or any(not isinstance(x,str) or not x for x in values):
                raise ValueError('missing split identities')
        if set(m['training'+field]) & set(m['validation'+field]): raise ValueError('model split leakage')


def model_report(rows,m):
    ready=lab.usable(rows); deltas=[]; own=[]; switches=unknown=0
    for r in ready:
        baseline=next(a for a in r['actions'] if a['direction']==r['baseline']); best=baseline
        unknown+=predicted_place(m,baseline['features'],r['players']) is None
        for a in sorted(r['actions'],key=lambda x:DIRNAMES.index(x['direction'])):
            if better(m,a['features'],best['features'],r['players']): best=a
        if best!=baseline and not better(m,best['features'],baseline['features'],r['players']): best=baseline
        switches+=best!=baseline; deltas.append(lab.key(best)[0]-lab.key(baseline)[0])
        if lab.key(best)[0]==lab.key(baseline)[0]: own.append(lab.key(best)[1]-lab.key(baseline)[1])
    if not ready: raise ValueError('no usable comparisons')
    return {'decisions':len(ready),'excluded':len(rows)-len(ready),'switches':switches,'unknown_place':unknown,
            'mean_counterfactual_place_delta':sum(deltas)/len(deltas),
            'mean_time_delta_at_equal_place':sum(own)/len(own) if own else None,
            'scope':'frozen one-action counterfactuals; not deployment results'}


def train(args):
    rows,ids=load(args.train); validation,vids=load(args.validation); lab.separation(rows,validation)
    place,time,count=fit_heads(rows,args.epochs,args.rate,args.l2)
    ready=lab.usable(validation)
    if not ready: raise ValueError('no complete validation decisions')
    # Empirical max residual is diagnostic calibration, NOT a confidence bound.
    radius=min(1., max(abs(linear(place,a['features'])-(a['outcome']['place']-1)/max(1,r['players']-1)) for r in ready for a in r['actions']))
    m={'version':2,'features':list(FEATURES),'weights':place,'timeWeights':time,'placeRadius':radius,'margin':args.margin,
       'trainingSha256':hashlib.sha256(lab.encoded(sorted(ids)).encode()).hexdigest(),
       'trainingDatasets':ids,'validationDatasets':vids,'equalPlaceTimePairs':count,
       'hyperparameters':{'epochs':args.epochs,'rate':args.rate,'l2':args.l2},
       'calibration':'maximum held-out validation residual, empirical only; not a guarantee'}
    for field,key in (('Families','family'),('Races','race_sha256'),('Courses','course_sha256')):
        m['training'+field]=sorted({r[key] for r in rows}); m['validation'+field]=sorted({r[key] for r in validation})
    validate_model(m); m['validation']=model_report(validation,m)
    lab.write_new(args.out,lab.encoded(m)+'\n'); print(json.dumps(m['validation'],indent=2))


def evaluate(args):
    m=json_read(args.model); validate_model(m); rows,ids=load(args.data)
    for field,key in (('Families','family'),('Races','race_sha256'),('Courses','course_sha256')):
        if {r[key] for r in rows} & (set(m['training'+field])|set(m['validation'+field])): raise ValueError('evaluation overlaps development '+key)
    result=model_report(rows,m); result.update(model_sha256=lab.digest(args.model),datasets=ids)
    lab.write_new(args.out,lab.encoded(result)+'\n'); print(json.dumps(result,indent=2))


def profile(args):
    flags=args.experiments.split(',')
    if not flags or len(set(flags))!=len(flags) or any(f not in FLAGS for f in flags): raise ValueError('invalid experiment flags')
    if not 1<=args.rounds<=4 or not 0<=args.extra_rounds<=3 or not 0<=args.budget<=512 or not 0<=args.extension_budget<=512 or not 1<=args.alternatives<=8:
        raise ValueError('invalid experiment limits')
    values={'candidateSlots':'','racecraft.experiments':','.join(flags),'racecraft.rounds':str(args.rounds),
            'racecraft.extraRounds':str(args.extra_rounds),'racecraft.policyBudget':str(args.budget),
            'racecraft.extensionBudget':str(args.extension_budget),'racecraft.alternatives':str(args.alternatives)}
    if 'lexicographic' in flags:
        if not args.model: raise ValueError('lexicographic requires a trained model')
        m=json_read(args.model);validate_model(m)
        values.update({'racecraft.model.'+k:str(m[k]) for k in ('version','margin','placeRadius','trainingSha256')})
        values['racecraft.model.features']=','.join(FEATURES)
        for k in ('weights','timeWeights'): values['racecraft.model.'+k]=','.join(repr(w) for w in m[k])
    elif 'learned' in flags:
        if not args.model: raise ValueError('learned requires a trained model')
        m=json_read(args.model);lab.validate_model(m)
        values.update({'racecraft.model.'+k:str(m[k]) for k in ('version','margin','trainingSha256')})
        values['racecraft.model.features']=','.join(lab.FEATURES); values['racecraft.model.weights']=','.join(map(repr,m['weights']))
    lab.read_properties(args.base)
    with args.out.open('xb') as f:f.write(args.base.read_bytes())
    try:lab.update_properties(args.out,values)
    except BaseException:args.out.unlink(missing_ok=True);raise
    print('Created',args.out,'with no selected slots; enable explicitly for a research arm')


def regret_report(rows):
    ready=lab.usable(rows); details=[]
    for r in ready:
        audit=r.get('audit',{}); by={a['direction']:a for a in r['actions']}
        selected=by[r['baseline']]; optimal=min(r['actions'],key=lab.key)
        shortlist=audit.get('shortlist',[])
        valid=[by[n] for n in shortlist if n in by]
        gap=lab.key(selected)[0]-lab.key(optimal)[0]
        excluded=bool(valid) and not any(lab.key(a)==lab.key(optimal) for a in valid)
        in_list=min(valid,key=lab.key) if valid else None
        details.append({'id':r['id'],'focal':r['focal'],'family':r['family'],
                        'selected':r['baseline'],'best_evaluated':optimal['direction'],
                        'place_regret':gap,'equal_place_time_regret':lab.key(selected)[1]-lab.key(optimal)[1] if not gap else None,
                        'best_missing_from_shortlist':excluded,'hook_observed':bool(valid),
                        'selection_regret_within_shortlist': lab.key(selected)[0]-lab.key(in_list)[0] if in_list else None,
                        'exhausted':audit.get('exhausted',False),'completed_rounds':audit.get('completedRounds'),
                        'forecast_values':audit.get('values',[]),'reason':audit.get('reason','unobserved')})
    return {'usable':len(ready),'excluded':len(rows)-len(ready), 'details':details,
            'mean_place_regret':sum(d['place_regret'] for d in details)/len(details) if details else None,
            'best_missing_count':sum(d['best_missing_from_shortlist'] for d in details),
            'exhausted_count':sum(d['exhausted'] for d in details),
            'scope':'best among evaluated first actions under declared frozen continuations; not a game-theoretic optimum',
            'deployment_and_matchup_effects':'not inferable from one-decision data; use focal-replacement league evidence'}


def regret(args):
    rows,ids=load(args.data);report=regret_report(rows);report['datasets']=ids
    lab.write_new(args.out,lab.encoded(report)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='details'},indent=2))


def lineup(n,focal,density,background,candidate):
    if not 1<=density<=n or not 0<=focal<n:raise ValueError('invalid density/focal')
    rivals=[background]*n
    for k in range(1,density):rivals[(focal+k)%n]=candidate
    return rivals


def league(args):
    java,version=runtime(args); spec=json_read(args.spec)
    if spec.get('version')!=1:raise ValueError('unsupported league specification')
    entries=spec['policies']; policies={}
    for e in entries:
        if e['name'] in policies:raise ValueError('duplicate league policy')
        # Relative paths resolve against the spec, not the caller's working directory.
        policies[e['name']]=policy(e['name'],args.spec.parent/e['jar'],args.spec.parent/e['props'],args.track,protocol=e.get('protocol','v3'))
    referee=policies[spec['referee']];base=spec['baseline'];candidate=spec['candidate']
    if base==candidate or base not in policies or candidate not in policies:raise ValueError('distinct known candidate and baseline required')
    for p in policies.values():compatible(referee,p)
    n=len(referee['roster']);focals=list(range(n)) if not args.focals else [int(v) for v in args.focals.split(',')]
    densities=spec.get('densities',[1,4,7]);backgrounds=spec['backgrounds']
    if len(set(focals))!=len(focals) or any(not 0<=v<n for v in focals) or not focals:raise ValueError('invalid focal slots')
    if not densities or len(set(densities))!=len(densities) or any(type(d) is not int or not 1<=d<=n for d in densities):raise ValueError('invalid densities')
    if not backgrounds or len(set(backgrounds))!=len(backgrounds) or any(b not in policies for b in backgrounds):raise ValueError('invalid background population')
    paths=[java,args.spec]+args.logs+sorted((ROOT/'tracks').glob('*.py'))
    for p in policies.values():paths += [p['jar'],p['props'],p['course']]
    inputs=Inputs(paths); args.out.mkdir(parents=True,exist_ok=False);out=args.out.resolve()
    for name,p in policies.items():
        if not lab.re.fullmatch(r'[A-Za-z0-9_-]+',name):raise ValueError('safe policy names required')
        shutil.copyfile(p['props'],out/(name+'.properties'));inputs.add(out/(name+'.properties'))
    manifest={'version':1,'policies':[policy_identity(p) for p in policies.values()], 'spec':spec,
              'java':version,'heap':args.heap,'inputs':inputs.hashes,'focals':focals,'max_moves':args.max_moves,
              'scope':'complete oracle-driven mixed-policy races on a fixed referee; each focal replacement holds all opponents fixed'}
    lab.write_new(out/'manifest.pending.json',lab.encoded(manifest)+'\n');pairs=[]
    with contextlib.ExitStack() as stack:
        actors={name:stack.enter_context(PolicyOracle(p,args.track,java,args.heap,args.seed,args.timeout,out/(name+'.stderr'))) for name,p in policies.items()}
        for li,log in enumerate(args.logs):
            race=lab.read_race(log)
            if race.players!=referee['roster'] or int(race.profile['laps'])!=referee['laps']:raise ValueError('league start roster/rules differ')
            board,start,_=reconstruct_board(log,1,n,complete=True)
            # Start state is shared, not a moving-policy comparison generated afresh per arm.
            for background in backgrounds:
                for density in densities:
                    for focal in focals:
                        fixed=lineup(n,focal,density,background,candidate);outcomes=[]
                        for replacement in (base,candidate):
                            line=fixed.copy();line[focal]=replacement
                            for slot,pname in enumerate(line):
                                if policies[pname]['experimental'] and slot+1 not in policies[pname]['slots']:
                                    raise ValueError('experimental league policy is not enabled in mapped slot %d' % (slot+1))
                            name='%d-%s-d%d-f%d-%s.jsonl'%(li,background,density,focal,replacement)
                            # Start at the actual first mover, count focal's own outcome.
                            with (out/name).open('x',encoding='utf-8') as trace:
                                result=continuation([actors[v] for v in line],actors[spec['referee']],board,start,None,{},0,0,args.max_moves,trace)
                            if result['complete']:
                                result['place']=result['classification'][focal];result['own_moves']=result['all_own_moves'][focal]
                            outcomes.append({'policy':replacement,'lineup':line,'outcome':result,'trace':name,'trace_sha256':lab.digest(out/name)})
                        complete=all(v['outcome']['complete'] for v in outcomes)
                        pair={'source_sha256':lab.digest(log),'background':background,'density':density,'focal':focal,
                              'complete':complete,'arms':outcomes,'place_delta':outcomes[1]['outcome']['place']-outcomes[0]['outcome']['place'] if complete else None}
                        pairs.append(pair)
                        with (out/'pairs.pending.jsonl').open('a',encoding='utf-8') as f:f.write(lab.encoded(pair)+'\n')
    inputs.verify();slices=[]
    for bg in backgrounds:
        for d in densities:
            group=[p for p in pairs if p['background']==bg and p['density']==d];valid=[p for p in group if p['complete']]
            times=[p['arms'][1]['outcome']['own_moves']-p['arms'][0]['outcome']['own_moves'] for p in valid if p['place_delta']==0]
            slices.append({'background':bg,'density':d,'pairs':len(valid),'censored_pairs':len(group)-len(valid),
                           'mean_focal_place_delta':sum(p['place_delta'] for p in valid)/len(valid) if valid else None,
                           'mean_time_delta_at_equal_place':sum(times)/len(times) if times else None})
    (out/'pairs.pending.jsonl').rename(out/'pairs.jsonl')
    report={'slices':slices,'complete_races':sum(a['outcome']['complete'] for p in pairs for a in p['arms']),
            'scope':manifest['scope'],'acceptance':'no automatic promotion and no crash-count veto'}
    lab.write_new(out/'report.json',lab.encoded(report)+'\n')
    manifest['outputs']={p.name:lab.digest(p) for p in out.iterdir() if p.is_file() and not p.name.startswith('manifest')}
    lab.write_new(out/'manifest.json',lab.encoded(manifest)+'\n');(out/'manifest.pending.json').unlink()
    print(json.dumps(report,indent=2))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    c=commands.add_parser('collect')
    for n in ('log','props','out'):c.add_argument('--'+n,type=Path,required=True)
    c.add_argument('--jar',type=Path,default=ROOT/'theoreticRacing.jar');c.add_argument('--track',required=True);c.add_argument('--family',required=True)
    c.add_argument('--state-policy',choices=('champion','experimental'),required=True)
    c.add_argument('--continuation',choices=('champion','source','specified'),required=True)
    c.add_argument('--continuation-jar',type=Path);c.add_argument('--continuation-props',type=Path)
    c.add_argument('--continuation-protocol',choices=('v2','v3'),default='v3')
    c.add_argument('--moves');c.add_argument('--stride',type=int,default=25);c.add_argument('--limit',type=int,default=20)
    c.set_defaults(func=collect)
    t=commands.add_parser('train');t.add_argument('--train',nargs='+',type=Path,required=True);t.add_argument('--validation',nargs='+',type=Path,required=True)
    t.add_argument('--out',type=Path,required=True);t.add_argument('--epochs',type=int,default=400);t.add_argument('--rate',type=float,default=.05)
    t.add_argument('--l2',type=float,default=.001);t.add_argument('--margin',type=float,default=.05);t.set_defaults(func=train)
    e=commands.add_parser('evaluate');e.add_argument('--model',type=Path,required=True);e.add_argument('--data',nargs='+',type=Path,required=True);e.add_argument('--out',type=Path,required=True);e.set_defaults(func=evaluate)
    p=commands.add_parser('profile');p.add_argument('--base',type=Path,default=ROOT/'tracks/lap_bench.properties');p.add_argument('--out',type=Path,required=True)
    p.add_argument('--experiments',required=True);p.add_argument('--model',type=Path);p.add_argument('--rounds',type=int,default=2);p.add_argument('--extra-rounds',type=int,default=1)
    p.add_argument('--budget',type=int,default=96);p.add_argument('--extension-budget',type=int,default=64);p.add_argument('--alternatives',type=int,default=2);p.set_defaults(func=profile)
    a=commands.add_parser('regret');a.add_argument('--data',nargs='+',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.set_defaults(func=regret)
    l=commands.add_parser('league');l.add_argument('--spec',type=Path,required=True);l.add_argument('--logs',nargs='+',type=Path,required=True)
    l.add_argument('--track',required=True);l.add_argument('--focals',help='zero-based focal slots; default every slot');l.add_argument('--out',type=Path,required=True);l.set_defaults(func=league)
    for cmd in (c,l):
        cmd.add_argument('--java',default='java');cmd.add_argument('--heap',default='-Xmx8g');cmd.add_argument('--seed',type=int,default=1)
        cmd.add_argument('--timeout',type=float,default=3600);cmd.add_argument('--max-moves',type=int,default=10000)
    args=parser.parse_args(argv)
    try:args.func(args);return 0
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,subprocess.SubprocessError) as error:
        print('racecraft next:',error,file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
