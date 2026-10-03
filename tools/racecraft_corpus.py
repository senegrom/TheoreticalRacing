#!/usr/bin/env python3
"""Capture decision states and replay counterfactual first actions.

No training, policy promotion, or fleet-performance claim. Every label is a
completed referee tail under a pinned continuation policy. All output directories
must be new; caller-owned profiles and bundled tracks are never modified.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import racecraft_validation as validation
DIRECTIONS = dict(zip(('NW', 'N', 'NE', 'W', 'NONE', 'E', 'SW', 'S', 'SE'),
                      ((-1,-1), (0,-1), (1,-1), (-1,0), (0,0), (1,0), (-1,1), (0,1), (1,1))))


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        h = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
        return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def board(snapshot: str) -> tuple[list[str], list[list[int]]]:
    groups = snapshot.split(';')
    h = groups[0].split(',')
    cars = [list(map(int, group.split(','))) for group in groups[1:]]
    if not ((len(h) == 7 and h[0] == 'rc3') or (len(h) == 8 and h[0] == 'rc4')) or not 1 <= len(cars) <= 9 or any(len(c) != 14 for c in cars):
        raise ValueError('not a complete rc3 decision state')
    validation.snapshot(snapshot)
    slot = int(h[3])
    if not 0 <= slot < len(cars) or cars[slot][6] != 0:
        raise ValueError('invalid rc3 mover')
    return h, cars


def parse_capture(text: str) -> list[dict]:
    rows, seen = [], set()
    for line in text.splitlines():
        if not line.startswith('RACECRAFT_STATE '):
            continue
        fields = line[len('RACECRAFT_STATE '):].split('|')
        if len(fields) != 7 or fields[1] not in DIRECTIONS:
            raise ValueError('malformed decision capture')
        h, _ = board(fields[0])
        key = hashlib.sha256((fields[0] + '|' + fields[1]).encode()).hexdigest()
        if key in seen:
            raise ValueError('duplicate captured decision')
        seen.add(key)
        rows.append(dict(id=key, snapshot=fields[0], actual=fields[1],
                         scorer=None if fields[2] == 'null' else fields[2],
                         chooser=None if fields[3] == 'null' else fields[3],
                         opening=None if fields[4] == 'null' else fields[4],
                         shortlist=fields[5].split(',') if fields[5] else [], turn=int(h[1]),
                         legalActions=validation.action_list(fields[6].split(',') if fields[6] else [])))
    return rows


def influence_diagnostic(snapshot: str, horizon: int = 3) -> dict:
    """Shadow ONLY. Unclipped acceleration envelopes deliberately overinclude.

    Check both pre/post-action occupations; do not assume simultaneous moves.
    Overlap is not a threat probability or a proof that dropping a rival is safe.
    Two-hop closure records possible indirect blockers, not an opponent coalition.
    """
    if horizon < 1 or horizon > 6:
        raise ValueError('diagnostic horizon out of range')
    h, cars = board(snapshot)
    self = int(h[3])
    live = [i for i, c in enumerate(cars) if c[6] == 0]
    adjacency = {i: set() for i in live}

    def overlaps(a: list[int], ka: int, b: list[int], kb: int) -> bool:
        radius = ka * (ka + 1) // 2 + kb * (kb + 1) // 2
        return all(abs(a[2 + axis] + ka * a[4 + axis]
                       - b[2 + axis] - kb * b[4 + axis]) <= radius for axis in (0, 1))

    for offset, i in enumerate(live):
        for j in live[offset + 1:]:
            possible = any(overlaps(cars[i], k, cars[j], m)
                           for k in range(horizon + 1)
                           for m in {max(0, k - 1), k, min(horizon, k + 1)})
            if possible:
                adjacency[i].add(j)
                adjacency[j].add(i)
    direct = adjacency[self]
    indirect = set(direct)
    for j in direct:
        indirect.update(adjacency[j])
    indirect.discard(self)
    return dict(shadowOnly=True, horizon=horizon, geometryClipped=False,
                direct=[cars[i][0] for i in sorted(direct)],
                twoHop=[cars[i][0] for i in sorted(indirect)],
                edges=[[cars[i][0], cars[j][0]] for i in live for j in sorted(adjacency[i]) if i < j])


def analyze(case: dict, answer: dict, *, max_moves: int, original_race: str, roster: dict) -> dict:
    base, complete = validation.validate_response(case, answer, max_moves)
    if base['complete']:
        validation.validate_control(case, base, original_race, roster)
    summary = dict(id=case['id'], actual=case['actual'],
                   influence=influence_diagnostic(case['snapshot']))
    if not complete:
        return dict(summary, labelled=False, excluded='incomplete-counterfactuals',
                    incomplete=[t['action'] for t in answer['trials'] if not t['complete']])
    best = base
    for trial in answer['trials']:
        if (trial['place'], trial['ownMoves']) < (best['place'], best['ownMoves']): best = trial
    if best is base: reason = 'no-observed-regret'
    elif not base['legal']: reason = 'selected-illegal-action'
    elif not case.get('shortlist'): reason = 'pre-chooser-or-unobserved'
    elif best['action'] not in case['shortlist']: reason = 'shortlist-exclusion'
    elif best['action'] == case.get('chooser') and case['actual'] != case.get('chooser'):
        reason = 'downstream-replacement'
    else: reason = 'forecast-horizon-or-ranking'
    return dict(summary, labelled=True, best=best['action'], placeGain=base['place']-best['place'],
                ownMoveGain=base['ownMoves']-best['ownMoves'], baselinePlace=base['place'],
                bestPlace=best['place'], diagnosis=reason)


def tooling_identity() -> dict:
    paths = ('tools/racecraft_corpus.py', 'tools/racecraft_validation.py',
             'tracks/benchmark_io.py', 'tracks/forensics_common.py')
    return {path: digest(ROOT / path) for path in paths}


def java_runtime(java: str, heap: str) -> tuple[str, str]:
    if any(os.environ.get(k, '').strip() for k in ('JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS')):
        raise ValueError('unset implicit JVM option variables; use --heap explicitly')
    if not re.fullmatch(r'-Xmx[1-9][0-9]*[kKmMgG]', heap):
        raise ValueError('one explicit -Xmx heap is required')
    executable = shutil.which(java)
    if executable is None:
        raise ValueError('Java executable not found')
    info = subprocess.run([executable, heap, '-version'], capture_output=True, text=True, check=True, timeout=15)
    return str(Path(executable).resolve()), info.stderr.strip()


def helpers():
    sys.path.insert(0, str(ROOT / 'tracks'))
    from benchmark_io import configured_players, update_properties
    from forensics_common import potential_status
    return configured_players, update_properties, potential_status


def run_java(command: list[str], cwd: Path, log: Path, timeout: int):
    began = time.monotonic()
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding='utf-8', timeout=timeout)
    log.write_text(result.stdout + '\n' + result.stderr, encoding='utf-8')
    result.check_returncode()
    return result, time.monotonic() - began


def capture(args) -> None:
    configured_players, update_properties, potential_status = helpers()
    java, version = java_runtime(args.java, args.heap)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.track):
        raise ValueError('invalid track name')
    jar, source = args.jar.resolve(), args.props.resolve()
    track = jar.parent / 'tracks' / (args.track + '.track')
    source_hash = digest(source)
    roster = configured_players(source)
    if not roster or any(kind not in ('AI1', 'AI2') for _, kind in roster.values()):
        raise ValueError('capture/replay requires an AI-only roster')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    profile = out / 'race.properties'
    profile.write_bytes(source.read_bytes())
    update_properties(profile, {'racecraftCapture': 'true', 'racecraftCaptureEvery': str(args.every),
                                'racecraftCaptureLimit': str(args.limit), 'useLastTrack': 'false'})
    command = [java, args.heap, '-Djava.awt.headless=true', '-jar', str(jar), '--auto', '--track', args.track,
               '--props', str(profile), '--seed', str(args.seed), '--log', str(out / 'race.log')]
    inputs = dict(jar=digest(jar), track=digest(track), profile=digest(profile))
    result, elapsed = run_java(command, ROOT, out / 'capture-process.log', args.timeout)
    status = potential_status(args.track, result.stdout + '\n' + result.stderr)
    race = (out / 'race.log').read_text(encoding='utf-8')
    if '# results\n' not in race:
        raise ValueError('capture race is incomplete')
    results = re.findall(r'^([1-9][0-9]*)\. ', race.split('# results\n', 1)[1], re.MULTILINE)
    if sorted(map(int, results)) != list(range(1, len(roster) + 1)):
        raise ValueError('capture race has an incomplete classification')
    cases = parse_capture(result.stderr)
    if not cases:
        raise ValueError('no rc3 decisions captured; check capture limits and JAR')
    states = out / 'states.jsonl'
    states.write_text(''.join(json.dumps(c, sort_keys=True) + '\n' for c in cases), encoding='utf-8')
    if inputs != dict(jar=digest(jar), track=digest(track), profile=digest(profile)) or digest(source) != source_hash:
        raise ValueError('capture inputs changed during execution')
    manifest = dict(schema=2, jar=str(jar), track=args.track, trackFile=str(track), seed=args.seed,
                    inputs=inputs, sourceProfileSha256=source_hash, java=java, javaVersion=version,
                    heap=args.heap, potential=status, statesSha256=digest(states), raceSha256=digest(out / 'race.log'),
                    tooling=tooling_identity(), cases=len(cases), seconds=elapsed)
    atomic_json(out / 'manifest.json', manifest)
    print(f'Captured {len(cases)} complete decision states; no counterfactual gain has been measured.')


def replay(args) -> None:
    configured_players, update_properties, potential_status = helpers()
    directory = args.capture.resolve()
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema') != 2: raise ValueError('old corpus manifest: capture again with cf4')
    java, version = java_runtime(args.java, manifest['heap'])
    if version != manifest['javaVersion']:
        raise ValueError('replay Java runtime differs from capture')
    jar, track = Path(manifest['jar']), Path(manifest['trackFile'])
    source = directory / 'race.properties'
    states = directory / 'states.jsonl'
    def unchanged():
        if (manifest['inputs'] != dict(jar=digest(jar), track=digest(track), profile=digest(source))
                or digest(states) != manifest['statesSha256'] or digest(directory / 'race.log') != manifest['raceSha256']
                or tooling_identity() != manifest['tooling']):
            raise ValueError('capture/replay input identity changed')
    unchanged()
    cases = [json.loads(line) for line in states.read_text(encoding='utf-8').splitlines()]
    cases = cases[args.offset:args.offset + args.cases]
    if not cases:
        raise ValueError('selected no captured decisions')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    profile = out / 'replay.properties'
    profile.write_bytes(source.read_bytes())
    update_properties(profile, {'racecraftCapture': 'false'})
    summaries = []
    original_race = (directory / 'race.log').read_text(encoding='utf-8')
    roster = configured_players(source)
    for index, case in enumerate(cases):
        unchanged()
        prefix = out / f'case-{index:04d}'
        query, answer = prefix.with_suffix('.in'), prefix.with_suffix('.json')
        query.write_text(validation.query(case, args.max_moves) + '\n', encoding='utf-8')
        command = [java, manifest['heap'], '-Djava.awt.headless=true', '-jar', str(jar), '--auto', '--track', manifest['track'],
                   '--props', str(profile), '--seed', str(manifest['seed']), '--query-moves', str(query), str(answer)]
        result, elapsed = run_java(command, ROOT, prefix.with_suffix('.process.log'), args.timeout)
        potential = potential_status(manifest['track'], result.stdout + '\n' + result.stderr)
        if potential != manifest['potential']:
            raise ValueError('replay map preparation differs from capture')
        response = json.loads(answer.read_text(encoding='utf-8'))
        summary = analyze(case, response, max_moves=args.max_moves, original_race=original_race, roster=roster)
        summary['seconds'] = elapsed
        summaries.append(summary)
    unchanged()
    summary = dict(schema=1, captureManifestSha256=digest(directory / 'manifest.json'),
                   maxMoves=args.max_moves, cases=summaries,
                   counts=dict(Counter(s.get('diagnosis', s.get('excluded')) for s in summaries)),
                   allLabelled=all(s['labelled'] for s in summaries),
                   interpretation='Conditional counterfactual tails, not fleet evidence or universal proofs.')
    atomic_json(out / 'summary.json', summary)
    if not summary['allLabelled']:
        raise ValueError('some tails hit the work limit; stored as unlabelled, no completed corpus marker')
    (out / 'COMPLETE').write_text(digest(out / 'summary.json') + '\n', encoding='utf-8')
    print(f'Validated {len(summaries)} counterfactual cases; see summary.json and the full per-action traces.')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    c = subs.add_parser('capture')
    c.add_argument('--jar', type=Path, default=ROOT / 'theoreticRacing.jar')
    c.add_argument('--props', type=Path, required=True)
    c.add_argument('--track', required=True)
    c.add_argument('--seed', type=int, default=1)
    c.add_argument('--heap', default='-Xmx8g')
    c.add_argument('--limit', type=int, default=100)
    c.add_argument('--every', type=int, default=1)
    c.set_defaults(function=capture)
    r = subs.add_parser('replay')
    r.add_argument('--capture', type=Path, required=True)
    r.add_argument('--cases', type=int, default=10)
    r.add_argument('--offset', type=int, default=0)
    r.add_argument('--max-moves', type=int, default=10000)
    r.set_defaults(function=replay)
    for sub in (c, r):
        sub.add_argument('--out', type=Path, required=True)
        sub.add_argument('--java', default='java')
        sub.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args(argv)
    try:
        if args.timeout < 1:
            raise ValueError('timeout must be positive')
        if args.command == 'capture' and (not 1 <= args.limit <= 100000 or not 1 <= args.every <= 1000000):
            raise ValueError('capture limits out of range')
        if args.command == 'replay' and (args.cases < 1 or args.offset < 0 or not 1 <= args.max_moves <= 100000):
            raise ValueError('replay bounds out of range')
        args.function(args)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'racecraft corpus failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
