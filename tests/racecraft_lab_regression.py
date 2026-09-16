#!/usr/bin/env python3
"""Bounded real-JVM lab wiring, not promotion evidence. Retains every input/log.

Build first. --reference-jar optionally verifies default/control byte identity
against the exact base build on the SAME runtime and heap.
"""
from pathlib import Path
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracks.benchmark_io import read_race, update_properties  # noqa: E402
from tracks.forensics_common import normalized_lines  # noqa: E402


def run(out, name, command):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=900)
    (out / (name + '.stdout')).write_text(result.stdout, encoding='utf-8')
    (out / (name + '.stderr')).write_text(result.stderr, encoding='utf-8')
    if result.returncode:
        raise AssertionError('%s failed (%d)\n%s\n%s' % (name, result.returncode, result.stdout, result.stderr))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jar', type=Path, default=ROOT / 'theoreticRacing.jar')
    parser.add_argument('--reference-jar', type=Path)
    parser.add_argument('--heap', default='-Xmx8g')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    # Real profiles passed to collect, and the heap it records, must not be
    # silently overridden by ambient VM options.
    if any(os.environ.get(k, '').strip() for k in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')):
        raise ValueError('unset ambient JVM options; use --heap')
    if args.out is None:
        args.out = Path(tempfile.mkdtemp(prefix='racecraft-lab-regression-'))
    else:
        args.out.mkdir(parents=True, exist_ok=False)
    out, jar = args.out.resolve(), args.jar.resolve()
    base = out / 'base.properties'
    base.write_text('nPlayers=2\nplayer1Kind=AI1\nplayer2Kind=AI1\nplayer1Name=P1\nplayer2Name=P2\nlaps=1\n')
    lab = [sys.executable, str(ROOT / 'tracks/racecraft_lab.py')]

    def race(name, props, track='hairpin', engine=jar):
        result = run(out, name, ['java', args.heap, '-Djava.awt.headless=true', '-jar', str(engine), '--auto',
                                  '--track', track, '--props', str(props), '--log', str(out / (name + '.log')), '--seed', '1'])
        parsed = read_race(out / (name + '.log'))
        return result, parsed

    race('reference', base)
    race('circle', base, 'circle')
    for source, track, family, indices, target in (
            ('reference','hairpin','open-u','1,8','train'), ('circle','circle','closed-loop','1','validation')):
        run(out, 'collect-' + target, lab + ['collect', '--jar', str(jar), '--log', str(out / (source + '.log')),
                                             '--props', str(base), '--track', track, '--family', family, '--moves', indices,
                                             '--heap=' + args.heap, '--out', str(out / target)])
    model = out / 'pilot-model.json'
    run(out, 'train-model', lab + ['train', '--train', str(out / 'train'), '--validation', str(out / 'validation'),
                                  '--out', str(model)])
    if args.reference_jar:
        race('unchanged-base', base, engine=args.reference_jar.resolve())
        assert normalized_lines((out / 'reference.log').read_text()) == normalized_lines((out / 'unchanged-base.log').read_text())

    all_flags = 'interaction,refresh,opportunity,encounter,learned'
    races = 2
    graphs = predictions = 0
    for index, flags in enumerate(('interaction','refresh','opportunity','encounter','learned',all_flags)):
        for slots in ('1','2'):
            name = 'arm%d-slot%s' % (index, slots)
            props = out / (name + '.properties')
            run(out, 'profile-' + name, lab + ['profile', '--base', str(base), '--out', str(props),
                                              '--experiments', flags, '--model', str(model), '--rounds', '1',
                                              '--budget', '48', '--extension-budget', '16', '--alternatives', '2'])
            update_properties(props, {'candidateSlots': slots, 'racecraft.audit': 'true'})
            result, parsed = race(name, props)
            assert parsed.slots == {int(slots)}
            audit = [s for s in result.stderr.splitlines() if s.startswith('RACECRAFT ')]
            assert audit, 'selected experiment produced no root audit'
            for entry in audit:
                values = dict(re.findall(r'(\w+)=([^ ]+)', entry))
                assert values['p'] == slots, 'experimental context leaked into a control slot'
                assert int(values['policyCalls']) <= 48
                assert int(values['extensions']) <= 16
                graphs += int(values['graphs']); predictions += int(values['policyCalls'])
            races += 1
    # Exercise the target traffic population too, with complementary cohorts.
    for parity in (1, 2):
        name = 'pack-mirror%d' % parity
        props = out / (name + '.properties')
        run(out, 'profile-' + name, lab + ['profile', '--base', str(base), '--out', str(props),
                                          '--experiments', all_flags, '--model', str(model), '--rounds', '1',
                                          '--budget', '48', '--extension-budget', '16', '--alternatives', '1'])
        values = {'nPlayers': '8', 'candidateSlots': ','.join(map(str, range(parity, 9, 2))), 'racecraft.audit': 'true'}
        values.update({'player%dKind' % i: 'AI1' for i in range(1, 9)})
        values.update({'player%dName' % i: 'P%d' % i for i in range(1, 9)})
        update_properties(props, values)
        result, parsed = race(name, props)
        assert len(parsed.players) == 8 and parsed.slots == set(range(parity, 9, 2))
        for entry in result.stderr.splitlines():
            if not entry.startswith('RACECRAFT '):
                continue
            values = dict(re.findall(r'(\w+)=([^ ]+)', entry))
            assert int(values['p']) in parsed.slots
            assert int(values['policyCalls']) <= 48 and int(values['extensions']) <= 16
        races += 1
    # No candidate slots: even a model and all flags must reproduce champion.
    control = out / 'control.properties'
    run(out, 'control-profile', lab + ['profile', '--base', str(base), '--out', str(control),
                                      '--experiments', all_flags, '--model', str(model)])
    race('control', control)
    assert normalized_lines((out / 'reference.log').read_text()) == normalized_lines((out / 'control.log').read_text())
    # All opportunities unknown at zero budget; no speculative win/death override.
    budget = out / 'zero-budget.properties'
    run(out, 'budget-profile', lab + ['profile','--base',str(base),'--out',str(budget),
                                     '--experiments','opportunity','--budget','0'])
    update_properties(budget, {'candidateSlots':'1,2'})
    race('zero-budget',budget)
    assert normalized_lines((out / 'reference.log').read_text()) == normalized_lines((out / 'zero-budget.log').read_text())
    races += 2
    assert graphs > 0 and predictions > 0, 'smoke corpus did not exercise live experimental hooks'
    summary = {'complete_cli_races': races, 'graphs': graphs, 'forecast_policy_calls': predictions,
               'counterfactual_samples': sum(json.loads((out / d / 'manifest.json').read_text())['samples']
                                             for d in ('train','validation')),
               'scope':'configuration and correctness only; pilot model is not promotion evidence'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('RacecraftLabRegression:', json.dumps(summary), 'evidence:', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
