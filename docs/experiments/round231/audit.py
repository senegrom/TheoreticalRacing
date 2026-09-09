#!/usr/bin/env python3
"""Validate the preserved Round 231 shards and export their complete results.

Extract all 18 GitHub fleet ZIPs into sibling directories named after their
artifacts, then run: python docs/experiments/round231/audit.py ARTIFACT_ROOT OUT
Run once with --phase mixed and once with --phase all. Requires the unchanged
Round 231 track files, profiles and fleet parser from the recorded base commit.
"""
import argparse
import collections
import csv
import gzip
import hashlib
import io
import json
import math
import pathlib
import statistics
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
ROOT = None
OUT = None
sys.path.insert(0, str(REPO / 'tracks'))
import fleet_grid as fleet
import head_to_head as h2h
from forensics_common import parse_move, normalized_lines

TRACKS = {p.stem: fleet.digest(p) for p in (REPO / 'tracks').glob('*.track')}
SEEDS = list(range(21, 31))
PATCH_SHA = {'mixed': 'ba7c55e390ab4122b027011600ee4234babb0e1f653fff8871ea732d8e0edab1',
             'all': 'd8ebdb5944134e7cf1c3db3b7ac2f88ab92ee3b53a2f8f15deebbb8125693326'}
JARS = {'mixed': '2bca73117dbe8efeaf6995c76fbc0805f0c0fd3b39c81cab64f9f373a4d1a2b1', 'all': 'fbe7073d71f786e67a57859c010a47d2e1d85dd95951139a6260ff9c437182db'}
SLOTS = {'odd': {1, 3, 5, 7}, 'even': {2, 4, 6, 8}, 'all': set(range(1, 9))}


def audit(mode, assignment):
    rows = []
    seen = set()
    sources = []
    for shard in ('regular', 'nordschleife'):
        artifact = ROOT / ('round231-full-' + mode + '-' + assignment + '-' + shard)
        grid = artifact / 'fleet'
        manifest = json.loads((grid / 'manifest.json').read_text())
        run_id = hashlib.sha256(fleet.json_text(manifest).encode()).hexdigest()
        assert manifest['seeds'] == [21, 30]
        expected_tracks = set(TRACKS) - {'nordschleife'} if shard == 'regular' else {'nordschleife'}
        assert manifest['tracks'] == {t: TRACKS[t] for t in expected_tracks}
        assert manifest['properties'] == fleet.digest(artifact / 'profile.properties')
        assert manifest['runner'] == fleet.digest(REPO / 'tracks/fleet_grid.py')
        assert manifest['log_parser'] == fleet.digest(REPO / 'tracks/forensics_common.py')
        assert manifest['heap'] == [('-Xmx4g' if shard == 'regular' else '-Xmx8g'), '-XX:ActiveProcessorCount=2']
        props = (artifact / 'profile.properties').read_text()
        assert props == (REPO / 'tracks/lap_bench.properties').read_text() + '\naiStartPlacement=' + mode + '\ncandidateSlots=' + ','.join(map(str, sorted(SLOTS[assignment]))) + '\n'
        build = (artifact / 'build-sha256.txt').read_text().splitlines()
        assert build[0].split()[0] == manifest['jar'] == JARS['all' if assignment == 'all' else 'mixed']
        assert build[1].split()[0] == PATCH_SHA['all' if assignment == 'all' else 'mixed']
        selected = expected_tracks
        assert {p.name.removesuffix('.complete.json') for p in grid.glob('*.complete.json')} == selected
        errors = [line for line in (grid / 'fleet.txt').read_text().splitlines() if line.endswith(' ERROR')]
        assert not errors, errors
        assert len(list(grid.glob('*_s*.log'))) == len(selected) * len(SEEDS)
        for track in sorted(selected):
            record = fleet.completed(grid, track, run_id, range(21, 31))
            assert record is not None, (artifact.name, track)
            for seed, saved in zip(SEEDS, record['logs']):
                assert (track, seed) not in seen
                seen.add((track, seed))
                log = grid / f'{track}_s{seed}.log'
                places, slots, crashed = h2h.read(log)
                assert slots == SLOTS[assignment]
                assert set(places) == set(range(1, 9)) and set(places.values()) == set(range(1, 9))
                text = log.read_text()
                moves = collections.Counter()
                statuses = {n: 'unfinished' for n in places}
                for line in text.splitlines():
                    move = parse_move(line)
                    if move:
                        moves[move.player] += 1
                        if move.status in ('FINISH', 'CRASH', 'TIMEOUT'):
                            statuses[move.player] = move.status
                assert sum(moves.values()) == saved['counts']['moves']
                assert {n for n, s in statuses.items() if s == 'CRASH'} == crashed
                rows.append(dict(mode=mode, assignment=assignment, track=track, seed=seed,
                                 laps=not record['no_loop'], places=places, slots=slots, crashed=crashed,
                                 moves=dict(moves), statuses=statuses, counts=saved['counts'],
                                 sha256=saved['sha256'], normalized_sha256=hashlib.sha256('\n'.join(normalized_lines(text)).encode()).hexdigest(),
                                 artifact=artifact.name, run_id=run_id))
        sources.append(dict(name=artifact.name, zip_sha256=fleet.digest(artifact.with_suffix('.zip')),
                            run_id=run_id, manifest=manifest, profile=props,
                            java=(artifact / 'java-version.txt').read_text(), selected_tracks=sorted(selected)))
    assert seen == {(track, seed) for track in TRACKS for seed in SEEDS}
    assert sum(r['laps'] for r in rows) == 730
    print(f'Validated {mode}/{assignment}: 840 races, all hashes, counters, profiles and manifests', flush=True)
    return rows, sources


def score(rows):
    pairs = collections.defaultdict(list)
    per_track = collections.defaultdict(list)
    policy = {key: dict(places=[], wins=0, crashes=0, moves=0, finishers=0, finisher_moves=0) for key in ('candidate', 'champion')}
    for row in rows:
        cm, hm = [], []
        for player, place in row['places'].items():
            key = 'candidate' if player in row['slots'] else 'champion'
            p = policy[key]
            p['places'].append(place)
            p['wins'] += place == 1
            p['crashes'] += player in row['crashed']
            p['moves'] += row['moves'][player]
            if row['statuses'][player] == 'FINISH':
                p['finishers'] += 1
                p['finisher_moves'] += row['moves'][player]
            (cm if key == 'candidate' else hm).append(place)
        diff = statistics.mean(cm) - statistics.mean(hm)
        pairs[(row['track'], row['seed'])].append((row['assignment'], diff))
        per_track[row['track']].append(diff)
    assert len(pairs) == 840 and all({r[0] for r in p} == {'odd', 'even'} and len(p) == 2 for p in pairs.values())
    paired = [statistics.mean(r[1] for r in p) for p in pairs.values()]
    for p in policy.values():
        p['car_races'] = len(p['places'])
        p['mean_place'] = statistics.mean(p.pop('places'))
    return dict(races=len(rows), mirrored_pairs=len(pairs), policies=policy,
                mean_place_difference=statistics.mean(paired),
                paired_standard_error=statistics.pstdev(paired) / math.sqrt(len(paired)),
                per_track={t: statistics.mean(values) for t, values in sorted(per_track.items())})


def main():
    global ROOT, OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    parser.add_argument('--phase', choices=('mixed', 'all'), default='mixed')
    parser.add_argument('--mode', choices=('legacy', 'informed', 'scatter'), help='audit one complete start mode')
    args = parser.parse_args()
    ROOT, OUT, phase = args.artifacts, args.output, args.phase
    OUT.mkdir(parents=True, exist_ok=True)
    all_rows, sources, metrics = [], [], {}
    for mode in ((args.mode,) if args.mode else ('legacy', 'informed', 'scatter')):
        mode_rows = []
        for assignment in (('odd', 'even') if phase == 'mixed' else ('all',)):
            rows, src = audit(mode, assignment)
            mode_rows.extend(rows)
            sources.extend(src)
        all_rows.extend(mode_rows)
        if phase == 'mixed':
            metrics[mode] = score(mode_rows)
        else:
            metrics[mode] = dict(races=len(mode_rows), lap_races=sum(r['laps'] for r in mode_rows),
                                all_tracks={key: sum(r['counts'][key] for r in mode_rows) for key in ('fin', 'crash', 'timeout', 'moves')},
                                lap_tracks={key: sum(r['counts'][key] for r in mode_rows if r['laps']) for key in ('fin', 'crash', 'timeout', 'moves')})
        print(json.dumps({mode: {k: v for k, v in metrics[mode].items() if k != 'per_track'}}, indent=2), flush=True)
    prefix = phase + ('-' + args.mode if args.mode else '')
    (OUT / (prefix + '-metrics.json')).write_text(json.dumps(metrics, sort_keys=True, indent=2) + '\n')
    (OUT / (prefix + '-sources.json')).write_text(json.dumps(sources, sort_keys=True, indent=2) + '\n')
    buffer = io.StringIO(newline='')
    fields = ['mode', 'assignment', 'track', 'seed', 'laps', 'places', 'moves', 'statuses', 'sha256', 'normalized_sha256']
    writer = csv.DictWriter(buffer, fields)
    writer.writeheader()
    for r in all_rows:
        writer.writerow({**{k: r[k] for k in ('mode', 'assignment', 'track', 'seed', 'laps', 'sha256', 'normalized_sha256')},
                         **{k: '|'.join(str(r[k][n]) for n in range(1, 9)) for k in ('places', 'moves', 'statuses')}})
    (OUT / (prefix + '-outcomes.csv.gz')).write_bytes(gzip.compress(buffer.getvalue().encode(), mtime=0))


if __name__ == '__main__':
    main()
