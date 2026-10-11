#!/usr/bin/env python3
"""Creative-arm functional tests and legal-prefix breeding; not a promotion grid."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import racecraft_next_cli as base

FLAGS = 'pace-feints,ambush,traffic-judo,selfish-search,two-judge'
STRATEGIES = 'suffix-manoeuvres,response-strategy,place-certificates,forced-sequence,continuation-policies,ordered-blockade'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-jar', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    jar = (base.ROOT / 'theoreticRacing.jar').resolve()
    records, count = [], 0
    shapes = [('hairpin', 2, 'legacy'), ('circle', 3, 'informed'), ('circle', 4, 'scatter')]
    for track, players, mode in shapes:
        name = f'{track}-{players}-{mode}'
        stock = base.race(out, name + '-stock', jar, track, players, mode, 3, {})
        champion = base.race(out, name + '-master', args.baseline_jar.resolve(), track, players, mode, 3, {})
        count += 2
        if stock != champion: raise AssertionError(name + ': no-flag policy changed master')
        for label, extra in [
            ('no-slots', dict(racecraftNext=FLAGS)),
            ('zero-nodes', dict(candidateSlots='1', racecraftNext=FLAGS, racecraftCreativeNodes='0')),
            ('zero-trials', dict(candidateSlots='1', racecraftNext=FLAGS, racecraftCreativeTrials='0'))]:
            result = base.race(out, name + '-' + label, jar, track, players, mode, 3, extra); count += 1
            if result != stock: raise AssertionError(name + ': inactive ' + label + ' changed decisions')
        for arm in FLAGS.split(',') + ['combined']:
            properties = dict(candidateSlots='1', racecraftNext=FLAGS if arm == 'combined' else arm)
            label = name + '-' + arm
            result = base.race(out, label, jar, track, players, mode, 3, properties)
            observed = base.race(out, label + '-audit', jar, track, players, mode, 3,
                                 dict(properties, racecraftCapture='true', racecraftCaptureLimit='10000'))
            count += 2
            if result != observed: raise AssertionError(label + ': observation changed the race')
            record = dict(track=track, players=players, start=mode, arm=arm, changed=result != stock, auditIdentity=True)
            records.append(record); print(json.dumps(record), flush=True)
    # One integrated pack: all previous driving arms plus all creative arms.
    all_flags = ','.join([base.FLAGS, STRATEGIES, FLAGS])
    all_flags = ','.join(dict.fromkeys(all_flags.split(',')))
    properties = dict(candidateSlots='1,3,5,7', racecraftNext=all_flags)
    integrated = base.race(out, 'integrated-8p', jar, 'hairpin', 8, 'legacy', 2, properties)
    observed = base.race(out, 'integrated-8p-audit', jar, 'hairpin', 8, 'legacy', 2,
                         dict(properties, racecraftCapture='true'))
    count += 2
    if integrated != observed: raise AssertionError('combined old/new flags are not audit-transparent')
    old_flags = base.FLAGS
    try:
        base.FLAGS = FLAGS
        corpus = [base.check_corpus(out, jar, 'hairpin', 'legacy'), base.check_corpus(out, jar, 'circle', 'informed')]
    finally:
        base.FLAGS = old_flags
    # Mutate legal prefixes from real, mid-race captures. A positive discovery is
    # not required by a functional test, and is not evidence of general strength.
    breeder = base.ROOT / 'tools' / 'racecraft_breeder.py'
    breeding = []
    for track in ['hairpin', 'circle']:
        destination = out / (track + '-breeding')
        base.execute([sys.executable, str(breeder), '--capture', str(out / (track + '-corpus')),
                      '--out', str(destination), '--cases', '1', '--offset', '1', '--trials', '8',
                      '--depth', '4', '--max-moves', '20000', '--seed', '3'], out / (track + '-breeding.process'))
        if not (destination / 'RUN_COMPLETE').is_file(): raise AssertionError('breeder did not complete its bounded search')
        payload = json.loads((destination / 'archive.json').read_text(encoding='utf-8'))
        mutations = [r for r in payload['records'] if not r['control']]
        if not mutations or not any(len(r['prefix']) >= 2 and r['validated'] for r in mutations):
            raise AssertionError('breeder did not validate a multi-action mutation')
        breeding.append(dict(track=track, attempts=len(mutations), validated=sum(r['validated'] for r in mutations),
                             positiveCells=len(payload['archive'])))
        print(json.dumps(breeding[-1]), flush=True)
    record = dict(functionalRaces=count, independentArms=records, corpus=corpus, corpusCases=6, breeding=breeding,
                  performanceScreen=False, promoted=False)
    (out / 'validation.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(f'Creative controls: {count} complete races, six counterfactual cases, two bounded breeder runs OK', flush=True)


if __name__ == '__main__': main()
