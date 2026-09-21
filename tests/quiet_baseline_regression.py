#!/usr/bin/env python3
"""Attribute changed pins to the quiet rule, not opt-in research machinery.

Build --reference-jar from master 3466471 with ONLY the adjacent
fixtures/quiet-rule-reference.patch. Compare complete recorded races against
this branch with experiments disabled. No expected result is changed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FROZEN_TRACKS = ('hungaroring', 'interlagos', 'lemans', 'monaco', 'zandvoort', 'spa', 'monza')
SLACK_CASES = (('hungaroring', 12), ('lemans', 2), ('spa', 1), ('hungaroring', 40),
               ('interlagos', 47), ('monza', 30), ('monaco', 35), ('zandvoort', 34),
               ('monza', 145), ('serpentine', 38))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cases() -> list[dict]:
    specs = json.loads((ROOT / 'tests/golden_races.json').read_text(encoding='utf-8'))['cases']
    result = [dict({k: s[k] for k in ('name', 'track', 'seed', 'players')},
                   kind='AI2', frozen=False) for s in specs]
    for kind in ('AI1', 'AI2'):
        result.append(dict(name=f'rand3-s1-{kind}', track='rand3', seed=1,
                           players=8, kind=kind, frozen=False))
        result.extend(dict(name=f'{track}-s{seed}-slack-{kind}', track=track, seed=seed,
                           players=8, kind=kind, frozen=True) for track, seed in SLACK_CASES)
    return result


def normalized_log(text: str) -> str:
    lines = []
    results = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if re.match(r'^\d+ p\d+ ', line):
            lines.append(line)
        elif line == '# results':
            results = True
            lines.append(line)
        elif results and re.match(r'^\d+\. ', line):
            lines.append(line)
    return '\n'.join(lines) + '\n'


def require_same(left: str, right: str, label: str) -> None:
    if normalized_log(left) != normalized_log(right):
        a, b = normalized_log(left).splitlines(), normalized_log(right).splitlines()
        first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        raise AssertionError(f'{label}: research differs from quiet-only reference at line {first + 1}')


def main(argv=None) -> int:
    # Load the command-line helpers only here: importing this comparison in a
    # unit test must not reorder sys.path or pre-import a second bench_ai module.
    sys.path.insert(0, str(ROOT))
    from tracks.benchmark_io import read_race, update_properties
    from tracks.promotion_pair import require_plain_java_environment
    from tracks.forensics_common import normalized_sha256, race_events
    from golden_races import summarize
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference-jar', type=Path, required=True)
    p.add_argument('--jar', type=Path, default=ROOT / 'theoreticRacing.jar')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--java', default='java')
    p.add_argument('--heap', default='-Xmx8g')
    p.add_argument('--case', action='append', default=[])
    args = p.parse_args(argv)
    require_plain_java_environment()
    if not re.fullmatch(r'-Xmx[1-9][0-9]*[kKmMgG]', args.heap):
        raise ValueError('one explicit --heap is required')
    executable = shutil.which(args.java)
    if executable is None:
        raise ValueError('Java executable not found')
    java = Path(executable).resolve()
    jars = {'reference': args.reference_jar.resolve(), 'research': args.jar.resolve()}
    if not all(j.is_file() for j in jars.values()) or jars['reference'] == jars['research']:
        raise ValueError('supply separate quiet-only reference and research builds')
    selected = cases()
    unknown = set(args.case) - {c['name'] for c in selected}
    if unknown:
        raise ValueError('unknown cases: ' + ', '.join(sorted(unknown)))
    selected = [c for c in selected if not args.case or c['name'] in args.case]
    inputs = list(jars.values()) + [java, Path(__file__), ROOT / 'tracks/bench.properties']
    inputs += sorted((ROOT / 'tracks').glob('*.track')) + sorted((ROOT / 'tracks').glob('*.py'))
    inputs += [ROOT / 'tests/fixtures' / (track + '.track') for track in FROZEN_TRACKS]
    inputs += [ROOT / 'tests/fixtures/quiet-rule-reference.patch', ROOT / 'tests/golden_races.json']
    before = {str(path): digest(path) for path in inputs}
    args.out.mkdir(parents=True, exist_ok=False)
    out = args.out.resolve()
    pending = out / 'pending.json'
    pending.write_text(json.dumps(before, indent=2) + '\n')
    version = subprocess.run([str(java), '-version'], capture_output=True, text=True, check=True, timeout=30).stderr
    builds = {}
    for label, jar in jars.items():
        for frozen in (False, True):
            install = out / f'{label}-{"frozen" if frozen else "current"}'
            install.mkdir()
            shutil.copyfile(jar, install / 'theoreticRacing.jar')
            shutil.copytree(ROOT / 'tracks', install / 'tracks', ignore=shutil.ignore_patterns('*.bin', '__pycache__'))
            if frozen:
                for track in FROZEN_TRACKS:
                    shutil.copyfile(ROOT / 'tests/fixtures' / (track + '.track'),
                                    install / 'tracks' / (track + '.track'))
            builds[label, frozen] = install / 'theoreticRacing.jar'
            for copied in [install / 'theoreticRacing.jar', *sorted((install / 'tracks').glob('*.track'))]:
                before[str(copied)] = digest(copied)
    records = []
    for spec in selected:
        texts = {}
        profile = out / (spec['name'] + '.properties')
        shutil.copyfile(ROOT / 'tracks/bench.properties', profile)
        values = {'nPlayers': str(spec['players']), 'candidateSlots': '',
                  'chooser.experiments': '', 'chooser.audit': 'false'}
        values.update({f'player{i}Kind': spec['kind'] for i in range(1, spec['players'] + 1)})
        update_properties(profile, values)
        before[str(profile)] = digest(profile)
        for label in jars:
            log = out / (spec['name'] + '-' + label + '.log')
            env = dict(os.environ, RACING_REACH_CACHE=str(out / ('cache-' + label)))
            with log.with_suffix('.stdout').open('x') as stdout, log.with_suffix('.stderr').open('x') as stderr:
                subprocess.run([str(java), args.heap, '-Djava.awt.headless=true', '-jar',
                                str(builds[label, spec['frozen']]), '--auto', '--track', spec['track'],
                                '--props', str(profile), '--log', str(log), '--seed', str(spec['seed'])],
                               cwd=ROOT, env=env, stdout=stdout, stderr=stderr, check=True, timeout=1200)
            race = read_race(log)
            if len(race.players) != spec['players'] or race.slots:
                raise AssertionError('wrong control roster/cohort: ' + str(log))
            texts[label] = log.read_text(encoding='utf-8')
        require_same(texts['reference'], texts['research'], spec['name'])
        text = texts['research']
        records.append(dict(spec, golden_sha256=hashlib.sha256(normalized_log(text).encode()).hexdigest(),
                            normalized_sha256=normalized_sha256(text), summary=summarize(text),
                            per_car_events=race_events(text)))
        print(spec['name'] + ': exact quiet-only/reference equality', flush=True)
    for path, sha in before.items():
        if digest(Path(path)) != sha:
            raise ValueError('input changed: ' + path)
    manifest = {'schema': 1, 'java': version.strip(), 'heap': args.heap, 'inputs': before,
                'cases': records, 'races': 2 * len(records),
                'scope': 'exact disabled-research identity against an independently built quiet-rule correction'}
    (out / 'result.json').write_text(json.dumps(manifest, indent=2) + '\n')
    pending.unlink()
    # No installs or caches are evidence; retained logs, profiles and hashes are.
    for install in {path.parent for path in builds.values()}:
        shutil.rmtree(install)
    print(f'QuietBaselineRegression: {len(records)} comparisons, {2 * len(records)} complete races')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
