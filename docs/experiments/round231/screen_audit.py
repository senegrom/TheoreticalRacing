"""Validate every Round 231 screening record before comparing candidate places."""
import collections
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]
if len(sys.argv) != 4 or sys.argv[3] not in ('initial', 'gates'):
    raise SystemExit('usage: screen_audit.py ARTIFACTS OUTPUT initial|gates')
ROOT = Path(sys.argv[1])
phase = sys.argv[3]
sys.path.insert(0, str(REPO / 'tracks'))
import fleet_grid
import head_to_head
from forensics_common import normalized_sha256, race_events

state = json.loads((Path(__file__).resolve().parent / (phase + '-state.json')).read_text())
tracks = sorted(state['screen_tracks'])
seeds = state['screen_seeds']
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
all_rows, sources, metrics = [], [], {}

for arm, label in state['arms'].items():
    pairs = collections.defaultdict(list)
    per_track = collections.defaultdict(list)
    policies = {p: {'places': [], 'wins': 0, 'crashes': 0} for p in ('candidate', 'champion')}
    directories = []
    for slot in ('odd', 'even'):
        artifact = ROOT / (state['artifact_prefix'] + f'{label}-{slot}')
        grid = artifact / 'fleet'
        directories.append(grid)
        manifest = json.loads((grid / 'manifest.json').read_text())
        run_id = hashlib.sha256(fleet_grid.json_text(manifest).encode()).hexdigest()
        assert manifest['seeds'] == [seeds[0], seeds[-1]]
        assert manifest['heap'] == ['-Xmx4g', '-XX:ActiveProcessorCount=2', '-D' + state['experiment_property'] + '=' + arm]
        assert manifest['tracks'] == {t: fleet_grid.digest(REPO / 'tracks' / (t+'.track')) for t in tracks}
        assert manifest['runner'] == fleet_grid.digest(REPO / 'tracks/fleet_grid.py')
        assert manifest['log_parser'] == fleet_grid.digest(REPO / 'tracks/forensics_common.py')
        slots = {1,3,5,7} if slot == 'odd' else {2,4,6,8}
        props = (REPO / 'tracks/lap_bench.properties').read_text() + '\naiStartPlacement=legacy\ncandidateSlots=' + ','.join(map(str, sorted(slots)))+'\n'
        assert (artifact / 'profile.properties').read_text() == props
        assert manifest['properties'] == hashlib.sha256(props.encode()).hexdigest()
        build = (artifact / 'build-sha256.txt').read_text().splitlines()
        assert build[0].split()[0] == manifest['jar'] == state['candidate_jar_sha256']
        assert build[1].split()[0] == state['patch_sha256']
        assert {p.name.removesuffix('.complete.json') for p in grid.glob('*.complete.json')} == set(tracks)
        assert len(list(grid.glob('*_s*.log'))) == len(tracks) * len(seeds)
        for track in tracks:
            record = fleet_grid.completed(grid, track, run_id, range(seeds[0], seeds[-1]+1))
            assert record is not None, (label, slot, track)
            for seed, saved in zip(seeds, record['logs']):
                log = grid / f'{track}_s{seed}.log'
                places, actual_slots, crashed = head_to_head.read(log)
                assert actual_slots == slots
                assert set(places) == set(range(1,9)) and set(places.values()) == set(range(1,9))
                text = log.read_text()
                finishers, crashes, moves = race_events(text)
                statuses = {n: 'unfinished' for n in places}
                for n,_ in finishers: statuses[n] = 'FINISH'
                for n,_ in crashes: statuses[n] = 'CRASH'
                assert saved['counts']['timeout'] == 0
                values = {'candidate': [], 'champion': []}
                for n,p in places.items():
                    policy = 'candidate' if n in slots else 'champion'
                    values[policy].append(p)
                    policies[policy]['places'].append(p)
                    policies[policy]['wins'] += p == 1
                    policies[policy]['crashes'] += n in crashed
                diff = statistics.mean(values['candidate']) - statistics.mean(values['champion'])
                pairs[(track,seed)].append((slot,diff))
                per_track[track].append(diff)
                all_rows.append({'arm':arm,'label':label,'assignment':slot,'track':track,'seed':seed,'laps':not record['no_loop'],
                                 'places':'|'.join(str(places[n]) for n in range(1,9)),
                                 'moves':'|'.join(str(moves[n]) for n in range(1,9)),
                                 'statuses':'|'.join(statuses[n] for n in range(1,9)),
                                 'sha256':saved['sha256'],'normalized_sha256':normalized_sha256(text)})
        sources.append({'artifact':artifact.name,'zip_sha256':fleet_grid.digest(artifact.with_suffix('.zip')),
                        'run_id':run_id,'manifest':manifest,'profile':props,
                        'java':(artifact/'java-version.txt').read_text()})
    assert set(pairs) == {(t,s) for t in tracks for s in seeds}
    assert all(len(v)==2 and {a for a,d in v}=={'odd','even'} for v in pairs.values())
    differences = [statistics.mean(d for a,d in v) for v in pairs.values()]
    for p in policies.values():
        p['car_races'] = len(p['places'])
        p['mean_place'] = statistics.mean(p.pop('places'))
    metrics[label] = {'mirrored_pairs':len(pairs),'races':2*len(pairs),'policies':policies,
                      'difference':statistics.mean(differences),'paired_standard_error':statistics.pstdev(differences)/math.sqrt(len(differences)),
                      'per_track':{t:statistics.mean(d) for t,d in sorted(per_track.items())}}
    score = subprocess.run([sys.executable,str(REPO/'tracks/head_to_head.py'),*map(str,directories)],capture_output=True,text=True,check=True)
    (out/(label+'.txt')).write_text(score.stdout)
    print(label+'\n'+score.stdout,flush=True)

(out/'metrics.json').write_text(json.dumps(metrics,indent=2,sort_keys=True)+'\n')
(out/'sources.json').write_text(json.dumps(sources,indent=2,sort_keys=True)+'\n')
buffer = io.StringIO(newline='')
writer = csv.DictWriter(buffer,list(all_rows[0]))
writer.writeheader();writer.writerows(all_rows)
(out/'outcomes.csv.gz').write_bytes(gzip.compress(buffer.getvalue().encode(),mtime=0))
print('Verified',len(all_rows),'complete screening races',flush=True)
