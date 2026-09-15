"""Validation-only isolation of corrected and original decision bodies."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import statistics
import math
import subprocess
import sys

BASE = '094f242214b7bc5176a2a236df8bb1cac4d04b86'
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from tracks.forensics_common import normalized_sha256
from tracks.benchmark_io import update_properties
from tracks import head_to_head


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prepare():
    # Leave each policy's internal hypothetical model intact. Only real race
    # turns select a policy. They are not told what class opponents are using.
    for name in ('RaceAi', 'RaceAiPrivateLane'):
        old = subprocess.check_output(['git', 'show', BASE + ':src/tr/logic/' + name + '.java'], text=True)
        import re
        old = re.sub(r'\bRaceAiPrivateLane\b', 'ControlPrivateLane', old)
        old = re.sub(r'\bRaceAi\b', 'ControlAi', old)
        target = 'ControlAi' if name == 'RaceAi' else 'ControlPrivateLane'
        (ROOT / 'src/tr/logic' / (target + '.java')).write_text(old)
    p = ROOT / 'src/tr/logic/RaceGame.java'
    s = p.read_text()
    needle = 'executeMove(ai.computeAiMove());'
    assert s.count(needle) == 1
    s = s.replace(needle, 'executeMove(candidatePolicy(players[subgamestate].getNumber())\n'
                         '\t\t\t\t? ai.computeAiMove() : controlAi.computeAiMove());')
    needle = 'final RaceAi ai = new RaceAi(this);'
    assert s.count(needle) == 1
    p.write_text(s.replace(needle, needle + '\n\tfinal ControlAi controlAi = new ControlAi(this);'))


def identity(jars, output):
    jars, output = Path(jars).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    original = (ROOT / 'tracks/lap_bench.properties').read_bytes()
    records = []
    for players, mode, track in ((2, 'legacy', 'hairpin'), (2, 'informed', 'circle'),
                                  (8, 'legacy', 'hairpin'), (8, 'scatter', 'circle')):
        for corrected in (False, True):
            key = f'{players}-{mode}-{track}-{corrected}'
            props = output / (key + '.properties')
            props.write_bytes(original)
            updates = {'nPlayers': str(players), 'aiStartPlacement': mode,
                       'candidateSlots': ','.join(map(str, range(1, players + 1))) if corrected else ''}
            updates.update({f'player{i}Kind': 'AI1' for i in range(1, players + 1)})
            update_properties(props, updates)
            hashes = []
            for variant in ('corrected' if corrected else 'baseline', 'comparison'):
                log = output / (key + '-' + variant + '.log')
                with (output / (key + '-' + variant + '.out')).open('w') as stream:
                    subprocess.run(['java', '-Xmx8g', '-Djava.awt.headless=true', '-jar',
                                    str(jars / (variant + '.jar')), '--auto', '--track', track,
                                    '--props', str(props), '--seed', '1', '--log', str(log)],
                                    check=True, stdout=stream, stderr=subprocess.STDOUT, timeout=600)
                hashes.append(normalized_sha256(log.read_text()))
            assert hashes[0] == hashes[1], (key, hashes)
            records.append({'case': key, 'normalized_sha256': hashes[0], 'identical': True})
    (output / 'identity.json').write_text(json.dumps({'base': BASE, 'cases': records,
        'jars': {p.name: sha(p) for p in jars.glob('*.jar')}}, indent=2) + '\n')
    print('Cohort isolation: eight cases / sixteen races match their standalone policy exactly')


def aggregate(directory, output):
    directory, output = Path(directory).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    summary = []
    tracks = {p.stem for p in (ROOT / 'tracks').glob('*.track')}
    for players in (2, 8):
        for mode in ('legacy', 'informed', 'scatter'):
            grids = []
            for shard in range(7):
                pair = directory / f'{players}-{mode}-{shard}'
                assert (pair / 'head-to-head.txt').is_file(), str(pair)
                grids.extend([str(pair / 'odd'), str(pair / 'even')])
            races = head_to_head.paired_races(grids)
            assert set(races) == {(t, s) for t in tracks for s in range(1, 11)}
            diff = [statistics.mean(statistics.mean(p for n,p in places.items() if n in slots)
                        - statistics.mean(p for n,p in places.items() if n not in slots)
                        for places, slots, _ in mirrors) for mirrors in races.values()]
            record = {'players': players, 'mode': mode, 'tracks': len(tracks), 'pairs': len(races),
                      'races': 2*len(races), 'mean_place_delta': statistics.mean(diff),
                      'standard_error': statistics.stdev(diff)/math.sqrt(len(diff))}
            summary.append(record)
            result = subprocess.run([sys.executable, str(ROOT/'tracks/head_to_head.py'), *grids],
                                    capture_output=True, text=True, check=True)
            (output/f'{players}-{mode}.txt').write_text(result.stdout)
            print(record, flush=True)
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')


if __name__ == '__main__':
    if sys.argv[1] == 'prepare': prepare()
    elif sys.argv[1] == 'identity': identity(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'aggregate': aggregate(sys.argv[2], sys.argv[3])
    else: raise ValueError('unknown mode')
