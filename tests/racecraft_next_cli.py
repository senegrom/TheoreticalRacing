#!/usr/bin/env python3
"""Bounded functional race checks, not a promotion screen."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tracks'))
from benchmark_io import update_properties
from forensics_common import normalized_sha256, potential_status, parse_move

FLAGS = 'crash-rank,rank-time,opening,start-ties'


def execute(command, output: Path, timeout=900):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=timeout)
    output.write_text(result.stdout + '\n' + result.stderr, encoding='utf-8')
    result.check_returncode()
    return result


def profile(path: Path, n: int, mode: str, extra: dict):
    path.write_bytes((ROOT / 'tracks' / 'lap_bench.properties').read_bytes())
    values = dict(nPlayers=str(n), useLastTrack='false', aiStartPlacement=mode,
                  candidateSlots='', racecraftNext='', racecraftCapture='false')
    values.update({f'player{i}Kind': 'AI1' for i in range(1, 10)})
    values.update({f'player{i}Name': f'P{i}' for i in range(1, 10)})
    values.update(extra)
    update_properties(path, values)


def race(directory: Path, label: str, jar: Path, track: str, n: int, mode: str, seed: int, extra: dict):
    props, log = directory / (label + '.properties'), directory / (label + '.log')
    profile(props, n, mode, extra)
    process = execute(['java', '-Xmx8g', '-Djava.awt.headless=true', '-jar', str(jar), '--auto', '--track', track,
                       '--props', str(props), '--seed', str(seed), '--log', str(log)], directory / (label + '.process'))
    status = potential_status(track, process.stdout + '\n' + process.stderr)
    text = log.read_text(encoding='utf-8')
    if '# results\n' not in text:
        raise AssertionError(label + ': incomplete race')
    return normalized_sha256(text), status


def check_corpus(directory: Path, jar: Path, track: str, mode: str):
    stem = directory / (track + '-corpus')
    props = stem.with_suffix('.properties')
    profile(props, 2, mode, {'candidateSlots': '1,2', 'racecraftNext': FLAGS})
    tool = ROOT / 'tools' / 'racecraft_corpus.py'
    execute([sys.executable, str(tool), 'capture', '--jar', str(jar), '--props', str(props), '--track', track,
             '--seed', '1', '--limit', '2', '--out', str(stem), '--heap=-Xmx8g'], stem.with_suffix('.capture.log'))
    out = directory / (track + '-counterfactuals')
    execute([sys.executable, str(tool), 'replay', '--capture', str(stem), '--cases', '1', '--max-moves', '20000',
             '--out', str(out)], stem.with_suffix('.replay.log'))
    if not (out / 'COMPLETE').is_file():
        raise AssertionError('counterfactual label incomplete')
    cases = [json.loads(line) for line in (stem / 'states.jsonl').read_text(encoding='utf-8').splitlines()]
    first = cases[0]
    if first['turn'] != 0:
        raise AssertionError('fixture must capture the first actual move')
    response = json.loads((out / 'case-0000.json').read_text(encoding='utf-8'))
    control = next(t for t in response['trials'] if t['action'] == first['actual'])
    text = (stem / 'race.log').read_text(encoding='utf-8')
    moves = [move for line in text.splitlines() if (move := parse_move(line)) is not None]
    actual = [(m.player - 1, m.direction, m.new_x, m.new_y, m.new_vx, m.new_vy,
               'OK' if m.status == 'ok' else 'LAP' if m.status.startswith('LAP') else m.status)
              for m in moves]
    replayed = []
    for line in control['trace']:
        f = line.split(':')
        replayed.append((int(f[0]), f[1], int(f[2]), int(f[3]), int(f[4]), int(f[5]), f[6]))
    if actual != replayed:
        for index, (a, b) in enumerate(zip(actual, replayed)):
            if a != b:
                raise AssertionError(f'{track}: control tail first differs from real race at {index}: {a} != {b}')
        raise AssertionError(f'{track}: control tail length differs {len(actual)} != {len(replayed)}')
    print(f'{track}: corpus capture, every legal first action and the actual full-race control trace OK', flush=True)
    return dict(track=track, trials=len(response['trials']), realControlMoves=len(actual))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-jar', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    jar = (ROOT / 'theoreticRacing.jar').resolve()
    if not jar.is_file():
        raise SystemExit('build the branch JAR first')
    temp = None
    if args.out:
        directory = args.out.resolve(); directory.mkdir(parents=True, exist_ok=False)
    else:
        temp = tempfile.TemporaryDirectory(prefix='racecraft-next-cli-'); directory = Path(temp.name)
    inputs = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in
              (ROOT / 'user.properties', ROOT / 'tracks' / 'lap_bench.properties') if p.exists()}
    records = []
    try:
        shapes = [('hairpin', 2, 'legacy', 1), ('circle', 4, 'informed', 1),
                  ('circle', 4, 'scatter', 2), ('hairpin', 8, 'legacy', 2)]
        for shape, (track, n, mode, seed) in enumerate(shapes):
            prefix = str(shape)
            base = race(directory, prefix + '-control', jar, track, n, mode, seed, {})
            count = 1
            if args.baseline_jar:
                old = race(directory, prefix + '-pinned-master', args.baseline_jar.resolve(), track, n, mode, seed, {})
                if old != base: raise AssertionError(f'{track}/{mode}: default differs from pinned master')
                count += 1
            slots = ','.join(map(str, range(1, n + 1)))
            controls = [dict(racecraftNext=FLAGS), dict(candidateSlots=slots), dict(racecraftCapture='true'),
                        dict(candidateSlots=slots, racecraftNext='opening', racecraftOpeningTrials='0')]
            for number, extra in enumerate(controls):
                got = race(directory, prefix + f'-disabled-{number}', jar, track, n, mode, seed, extra)
                if got != base: raise AssertionError(f'{track}/{mode}: disabled/audit control {number} changed a race')
                count += 1
            candidate = dict(candidateSlots=slots, racecraftNext=FLAGS)
            a = race(directory, prefix + '-candidate', jar, track, n, mode, seed, candidate)
            b = race(directory, prefix + '-candidate-audit', jar, track, n, mode, seed,
                     dict(candidate, racecraftCapture='true'))
            if a != b: raise AssertionError(f'{track}/{mode}: audit altered candidate decisions')
            count += 2
            records.append(dict(track=track, players=n, mode=mode, races=count, control=base, candidate=a))
            print(f'{track}/{mode}/{n}p: {count} complete control/candidate races OK', flush=True)
        corpus = [check_corpus(directory, jar, 'hairpin', 'legacy'), check_corpus(directory, jar, 'circle', 'informed')]
        for path, checksum in inputs.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
                raise AssertionError('caller-owned properties changed: ' + str(path))
        (directory / 'validation.json').write_text(json.dumps(dict(races=records, corpus=corpus,
                performanceScreen=False, promoted=False), indent=2) + '\n', encoding='utf-8')
        print('Racecraft next CLI: complete-race gating and counterfactual contracts passed; not a promotion', flush=True)
    finally:
        if temp is not None: temp.cleanup()


if __name__ == '__main__':
    main()
