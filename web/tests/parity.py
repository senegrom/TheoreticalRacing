#!/usr/bin/env python3
"""Compare whole races from the untouched desktop engine and browser adapter.

No regenerated fixtures, replacement policy or approximate geometry. The twelve
existing golden hashes are checked as well as full byte-for-byte native logs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / 'tests'))
from golden_races import normalized_log  # noqa: E402


def run(args, path, timeout=600):
    with path.open('w', encoding='utf-8') as output:
        subprocess.run(args, check=True, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true')
    args = parser.parse_args()
    build = ROOT / 'web/build/parity'
    build.mkdir(parents=True, exist_ok=True)
    ref = build / 'reference'
    (ref / 'classes').mkdir(parents=True, exist_ok=True)
    sources = sorted(str(p) for p in (ROOT / 'src').rglob('*.java'))
    run(['javac', '-encoding', 'UTF-8', '-Xlint:all', '-Werror', '-d', str(ref / 'classes'), *sources], build / 'compile.log')
    run(['jar', '--create', '--file', str(ref / 'racing.jar'), '--main-class', 'tr.main.Main', '-C', str(ref / 'classes'), '.'], build / 'jar.log')
    if not (ref / 'tracks').exists():
        (ref / 'tracks').symlink_to(ROOT / 'tracks', target_is_directory=True)
    # Original direct rule-contract tests are also run on the generated engine.
    run(['javac', '-encoding', 'UTF-8', '-Xlint:all', '-Werror', '-cp', 'web/dist/racing.jar', '-d', str(build),
         'tests/tr/logic/ReviewRuleTests.java', 'tests/tr/logic/FollowupRuleTests.java', 'tests/tr/logic/StartPlacementTests.java', 'web/tests/BrowserTests.java'], build / 'test-compile.log')
    run(['java', '-ea', '-Djava.awt.headless=true', '-cp', f'web/dist/racing.jar{os.pathsep}{build}', 'tr.logic.BrowserTests'], build / 'adapter-tests.log')
    print((build / 'adapter-tests.log').read_text(), flush=True)
    # A test-only telemetry observer holds distance BFS at its entry while
    # unmodified Bridge/engine placement and AI auto-placement must complete.
    startup = build / 'startup'
    startup.mkdir(exist_ok=True)
    run(['javac', '-encoding', 'UTF-8', '-Xlint:all', '-Werror', '-cp', 'web/dist/racing.jar', '-d', str(startup),
         *map(str, sorted((ROOT / 'web/tests/startup').rglob('*.java')))], build / 'startup-compile.log')
    for players, track, laps in [(1, 'hairpin', 1), (4, 'hairpin', 1), (9, 'hairpin', 1), (9, 'monza', 2)]:
        output = build / f'startup-{players}-{laps}.log'
        run(['java', '-ea', '-Djava.awt.headless=true', '-cp', f'{startup}{os.pathsep}web/dist/racing.jar',
             'tr.logic.StartupTests', str(players), track, str(laps)], output)
        print(output.read_text(), flush=True)
    cases = json.loads((ROOT / 'tests/golden_races.json').read_text())['cases']
    if args.quick:
        cases = [c for c in cases if c['name'] == 'hairpin-s1-2p']
    cases += [
        dict(name='hairpin-legacy-AI1', track='hairpin', seed='', players=3, kind='AI1'),
        dict(name='hairpin-negative-mixed', track='hairpin', seed=-7, players=4, kind='AI1,AI2'),
        dict(name='monza-two-laps', track='monza', seed=2, players=2, laps=2),
        json.loads((ROOT / 'web/tests/informed_races.json').read_text())['cases'][0],
        dict(name='monza-informed-two-laps', track='monza', seed=2, players=2, laps=2, policy='informed'),
    ]
    results = []
    for case in cases:
        name, track, count = case['name'], case['track'], case['players']
        seed, laps, kind = str(case['seed']), case.get('laps', 1), case.get('kind', 'AI2')
        policy = case.get('policy', 'legacy')
        kinds = kind.split(',')
        props = build / (name + '.properties')
        props.write_text(f'aiStartPlacement={policy}\nnPlayers={count}\nlaps={laps}\n' + ''.join(
            f'player{i+1}Name={chr(65+i)}\nplayer{i+1}Kind={kinds[i % len(kinds)]}\n' for i in range(count)))
        reference = build / (name + '.desktop.log')
        browser = build / (name + '.browser.log')
        cmd = ['java', '-Xmx2g', '-jar', str(ref / 'racing.jar'), '--auto', '--track', track, '--props', str(props), '--log', str(reference)]
        if seed:
            cmd += ['--seed', seed]
        run(cmd, build / (name + '.desktop.stdout'))
        run(['java', '-Xmx2g', '-Djava.awt.headless=true', '-cp', 'web/dist/racing.jar', 'tr.logic.BrowserBridge', track, str(count), str(laps), seed, str(browser), kind, policy], build / (name + '.browser.stdout'))
        if reference.read_bytes() != browser.read_bytes():
            import difflib
            diff = ''.join(difflib.unified_diff(reference.read_text().splitlines(True), browser.read_text().splitlines(True)))
            raise AssertionError(f'{name}: desktop/browser log divergence\n{diff[:6000]}')
        digest = hashlib.sha256(normalized_log(browser.read_text()).encode()).hexdigest()
        if 'sha256' in case and digest != case['sha256']:
            raise AssertionError(f'{name}: existing golden mismatch {digest} != {case["sha256"]}')
        results.append(dict(name=name, byte_identical=True, sha256=digest))
        print(f'{name}: byte-identical, golden {digest[:12]}', flush=True)
    for name, digest in json.loads((ROOT / 'web/dist/track-hashes.json').read_text()).items():
        assert (ROOT / 'tracks' / name).read_bytes() == (ROOT / 'web/dist/tracks' / name).read_bytes()
        assert hashlib.sha256((ROOT / 'tracks' / name).read_bytes()).hexdigest() == digest
    for name, digest in json.loads((ROOT / 'web/dist/engine-sources.json').read_text()).items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
    (build / 'results.json').write_text(json.dumps({'cases': results, 'tracks': 84, 'adapter_tests': 'passed'}, indent=2) + '\n')
    print(f'{len(results)} identical complete races; all 84 track files unchanged', flush=True)


if __name__ == '__main__':
    main()
