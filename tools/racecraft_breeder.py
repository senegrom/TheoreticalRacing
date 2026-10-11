#!/usr/bin/env python3
"""Offline quality-diversity search over legally generated racing prefixes.

Requires a hash-pinned complete race capture. Every mutation starts at a real
captured state, applies up to four actual own accelerations, and recomputes all
rival actions. Only complete, validated tails enter the discovery archive.
This tool does not train, install or promote a driving policy.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import racecraft_corpus as corpus
import racecraft_validation as validation

DIRECTIONS = corpus.DIRECTIONS


def sequence(value, maximum=4):
    if not isinstance(value, list) or len(value) > maximum or any(type(a) is not str or a not in DIRECTIONS for a in value):
        raise ValueError('invalid breeder acceleration prefix')
    return value


def request(case, prefix, max_moves):
    validation.integer(max_moves, 1, 100000)
    sequence(prefix)
    validation.snapshot(case['snapshot'])
    return f"breed1,{max_moves},{'+'.join(prefix) if prefix else '-'}|{case['snapshot']}"


def validate(case, prefix, answer, max_moves):
    """Bind the whole request and replay the transcript, including its endpoint.

    Geometric legality/endpoint legal-action enumeration belongs to the pinned
    Java referee; Python independently checks the transcript and classification.
    Invalid or truncated continuations never become labelled discoveries.
    """
    expected = request(case, prefix, max_moves)
    header, _ = validation.snapshot(case['snapshot'])
    if (answer.get('schema') != 1 or answer.get('requestSha256') != validation.sha(expected)
            or answer.get('prefix') != prefix or answer.get('maxMoves') != max_moves
            or answer.get('baseline') != case['actual'] or answer.get('rootIdentity') != header[5]):
        raise ValueError('breeder response does not match the captured decision and request')
    if type(answer.get('validPrefix')) is not bool:
        raise ValueError('missing breeder prefix validity')
    forced = validation.integer(answer.get('forcedExecuted'), 0, len(prefix))
    trial = answer.get('trial')
    if not isinstance(trial, dict) or trial.get('action') != (prefix[0] if prefix else case['actual']):
        raise ValueError('breeder trial has the wrong first action')
    if not answer['validPrefix']:
        if trial.get('complete') is not False:
            raise ValueError('invalid prefix labelled complete')
        return None
    validation.validate_trial(case, trial, max_moves)
    self = header[2]
    own = [row.split(':')[1] for row in trial['trace']
           if int(row.split(':')[0]) == self and row.split(':')[6] != 'TIMEOUT']
    if own[:len(prefix)] != prefix[:len(own)] or forced != min(len(prefix), len(own)):
        raise ValueError('trace did not execute the declared multi-action prefix')
    if sequence(answer.get('ownActions')) != own[:4]:
        raise ValueError('advertised continuation differs from the referee trace')
    legal_next = validation.action_list(answer.get('legalNext'))
    seeds = answer.get('seeds')
    if not isinstance(seeds, list) or len(seeds) > 10:
        raise ValueError('invalid breeder seeds')
    for seed in seeds: sequence(seed)
    endpoint = answer.get('endpoint')
    cut = None
    seen = 0
    for index, row in enumerate(trial['trace']):
        fields = row.split(':')
        if int(fields[0]) == self and fields[6] != 'TIMEOUT':
            if seen == len(prefix): cut = index; break
            seen += 1
    if endpoint is None:
        if legal_next or cut is not None:
            raise ValueError('missing live prefix endpoint')
    else:
        if cut is None: raise ValueError('prefix endpoint is not reached in the transcript')
        end_header, _ = validation.snapshot(endpoint)
        if end_header[2] != self: raise ValueError('prefix endpoint is not an own decision')
        partial = dict(trial, complete=False, place=0, ownMoves=len(prefix), status='RUNNING',
                       trace=trial['trace'][:cut], finalState=endpoint)
        partial['traceSha256'] = validation.sha('\n'.join(partial['trace']))
        validation.validate_trial(case, partial, max_moves)
    return trial if trial['complete'] else None


def quality(control, trial):
    return control['place'] - trial['place'], control['ownMoves'] - trial['ownMoves']


def descriptor(case, prefix, control, trial):
    header, cars = validation.snapshot(case['snapshot'])
    self = header[2]
    car = cars[self]
    steering = sum(DIRECTIONS[a][0] for a in prefix), sum(DIRECTIONS[a][1] for a in prefix)
    # The first response of each rival is compared by identity, not by a frozen
    # schedule: both full transcripts arose from freshly recomputed policies.
    def replies(t):
        result = {}
        for line in t['trace']:
            fields = line.split(':'); actor = int(fields[0])
            if actor != self and actor not in result: result[actor] = tuple(fields[1:6])
        return result
    a, b = replies(control), replies(trial)
    changed = sum(a.get(i) != b.get(i) for i in set(a) | set(b))
    return (sum(c[6] == 0 for c in cars), car[8], min(3, max(abs(car[4]), abs(car[5])) // 3),
            self, len(prefix), (steering[0] > 0) - (steering[0] < 0),
            (steering[1] > 0) - (steering[1] < 0), min(3, changed))


def breed(args):
    directory = args.capture.resolve()
    manifest_path = directory / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('schema') != 2: raise ValueError('capture again with the current corpus protocol')
    if not 1 <= args.trials <= 256 or not 1 <= args.cases <= 8 or not 1 <= args.depth <= 4 or args.offset < 0:
        raise ValueError('breeding budget out of range')
    validation.integer(args.max_moves, 1, 100000)
    java, version = corpus.java_runtime(args.java, manifest['heap'])
    if version != manifest['javaVersion']: raise ValueError('Java runtime differs from capture')
    source, states, race_path = directory / 'race.properties', directory / 'states.jsonl', directory / 'race.log'
    jar, track = Path(manifest['jar']), Path(manifest['trackFile'])
    def unchanged():
        if (manifest['inputs'] != dict(jar=corpus.digest(jar), track=corpus.digest(track), profile=corpus.digest(source))
                or corpus.digest(states) != manifest['statesSha256'] or corpus.digest(race_path) != manifest['raceSha256']
                or corpus.tooling_identity() != manifest['tooling']):
            raise ValueError('breeder inputs differ from the pinned capture')
    unchanged()
    cases = [json.loads(line) for line in states.read_text(encoding='utf-8').splitlines()][args.offset:args.offset + args.cases]
    if not cases: raise ValueError('no captured decisions selected')
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    profile = out / 'breeding.properties'; profile.write_bytes(source.read_bytes())
    configured_players, update_properties, potential_status = corpus.helpers()
    update_properties(profile, {'racecraftCapture': 'false'})
    roster, original_race = configured_players(source), race_path.read_text(encoding='utf-8')
    archive, records = {}, []
    randomizer = random.Random(args.seed)
    profile_hash = corpus.digest(profile)
    for case_index, case in enumerate(cases):
        def evaluate(prefix, number):
            unchanged()
            if corpus.digest(profile) != profile_hash: raise ValueError('breeding profile changed')
            stem = out / f'case-{case_index:03d}-trial-{number:04d}'
            query_path, answer_path = stem.with_suffix('.in'), stem.with_suffix('.json')
            text = request(case, prefix, args.max_moves)
            query_path.write_text(text + '\n', encoding='utf-8')
            command = [java, manifest['heap'], '-Djava.awt.headless=true', '-jar', str(jar), '--auto',
                       '--track', manifest['track'], '--props', str(profile), '--seed', str(manifest['seed']),
                       '--query-moves', str(query_path), str(answer_path)]
            process, seconds = corpus.run_java(command, corpus.ROOT, stem.with_suffix('.process.log'), args.timeout)
            if potential_status(manifest['track'], process.stdout + '\n' + process.stderr) != manifest['potential']:
                raise ValueError('map preparation differs from capture')
            answer = json.loads(answer_path.read_text(encoding='utf-8'))
            trial = validate(case, prefix, answer, args.max_moves)
            return answer, trial, dict(case=case['id'], prefix=prefix, response=answer_path.name,
                                       requestSha256=validation.sha(text), seconds=seconds)
        control_answer, control, control_record = evaluate([], 0)
        if control is None: raise ValueError('control tail incomplete; no discoveries accepted')
        validation.validate_control(case, control, original_race, roster)
        control_record.update(control=True, validated=True); records.append(control_record)
        queued = [list(p) for p in control_answer['seeds'] if len(p) <= args.depth]
        single = [[a] for a in case['legalActions']]; randomizer.shuffle(single); queued.extend(single)
        seen = {()}
        species = Counter()
        count = 0
        while queued and count < args.trials:
            # Alternate deeper mutations and broad exploration, with seeded tie
            # choices. Each accepted parent supplies legal actions at its actual
            # reactive endpoint; no arbitrary coordinate/velocity mutations.
            if count % 2 == 0:
                longest = max(len(p) for p in queued)
                eligible = [i for i, p in enumerate(queued) if len(p) == longest]
                index = randomizer.choice(eligible)
            else:
                index = randomizer.randrange(len(queued))
            prefix = queued.pop(index)
            if tuple(prefix) in seen: continue
            seen.add(tuple(prefix)); count += 1
            answer, trial, record = evaluate(prefix, count)
            record.update(control=False, validated=trial is not None)
            if trial is not None:
                cell = descriptor(case, prefix, control, trial)
                q = quality(control, trial)
                species[cell] += 1
                record.update(placeGain=q[0], ownMoveGain=q[1], descriptor=cell)
                old = archive.get(cell)
                if q > (0, 0) and (old is None or q > tuple(old['quality'])):
                    archive[cell] = dict(record, quality=q, rootSnapshot=case['snapshot'],
                                         actual=case['actual'], baselineResponse=control_record['response'],
                                         endpoint=answer['endpoint'])
                if len(prefix) < args.depth and answer['endpoint'] is not None:
                    children = [prefix + [a] for a in answer['legalNext']]
                    randomizer.shuffle(children); queued.extend(children)
            records.append(record)
        print(f"Breeder case {case_index}: {count} legal-prefix attempts; {len(species)} behaviour cells; {len(archive)} positive archive cells", flush=True)
    unchanged()
    if corpus.digest(profile) != profile_hash: raise ValueError('breeding profile changed')
    payload = dict(schema=1, captureManifestSha256=corpus.digest(manifest_path), seed=args.seed,
                   maxMoves=args.max_moves, maxDepth=args.depth, trialsPerCase=args.trials,
                   tooling={str(Path(__file__).name): corpus.digest(Path(__file__))},
                   discoveryOnly=True, exhaustive=False, promoted=False,
                   records=records, archive=list(archive.values()),
                   skippedIncomplete=sum(not r['validated'] for r in records))
    corpus.atomic_json(out / 'archive.json', payload)
    (out / 'RUN_COMPLETE').write_text(corpus.digest(out / 'archive.json') + '\n', encoding='utf-8')
    print(f"Offline discovery complete: {len(archive)} positive behaviour cells. No policy was trained or promoted.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--cases', type=int, default=1)
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--trials', type=int, default=32)
    parser.add_argument('--depth', type=int, default=4)
    parser.add_argument('--max-moves', type=int, default=20000)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--java', default='java')
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    try: breed(args)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        raise SystemExit(f'Breeding refused: {error}') from error


if __name__ == '__main__': main()
