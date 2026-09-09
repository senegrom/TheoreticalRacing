#!/usr/bin/env python3
"""Validate Round 232 candidate fleets against the saved Round 231 baseline.

Usage: audit.py ROUND232_ARTIFACTS ROUND231_ARTIFACTS OUTPUT [--mode MODE]
Extract ZIPs into directories with the artifact names, beside their ZIPs.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

import lexicographic as lex

REPO = Path(__file__).resolve().parents[3]
JAR = 'a5e6e411d8daad998b3b9919029dc1b0f667a7271483ff4ed9633e6a71655928'
BASE_JAR = 'fbe7073d71f786e67a57859c010a47d2e1d85dd95951139a6260ff9c437182db'
PATCH = '41f8913e5f24228c7fc131c1b34092c141c93937928fb1cbb0ffeb577345c5f5'
BASE_PATCH = 'd8ebdb5944134e7cf1c3db3b7ac2f88ab92ee3b53a2f8f15deebbb8125693326'


def read_mode(root, mode, arm):
    rows, sources = {}, []
    for shard in ('regular', 'nordschleife'):
        name = f'round232-full-{mode}-{arm}-{shard}' if arm else f'round231-full-{mode}-all-{shard}'
        artifact = root / name
        data, source = lex.read_grid(artifact / 'fleet')
        manifest = source['manifest']
        assert manifest['seeds'] == [21, 30]
        assert set(manifest['tracks']) == ({'nordschleife'} if shard == 'nordschleife' else {
            p.stem for p in (REPO / 'tracks').glob('*.track')} - {'nordschleife'})
        heap = ['-Xmx8g' if shard == 'nordschleife' else '-Xmx4g', '-XX:ActiveProcessorCount=2']
        if arm:
            heap.append(f'-Dai.experiment.checkpointTie={arm}')
        assert manifest['heap'] == heap
        assert all(v == hashlib.sha256(b'').hexdigest() for v in manifest['java_environment'].values())
        props = (artifact / 'profile.properties').read_text()
        assert props == (REPO / 'tracks/lap_bench.properties').read_text() + (
            f'\naiStartPlacement={mode}\ncandidateSlots=1,2,3,4,5,6,7,8\n')
        assert lex.fleet.digest(artifact / 'profile.properties') == manifest['properties']
        build = (artifact / 'build-sha256.txt').read_text().splitlines()
        assert build[0].split()[0] == manifest['jar'] == (JAR if arm else BASE_JAR)
        assert build[1].split()[0] == (PATCH if arm else BASE_PATCH)
        assert not (data.keys() & rows.keys())
        rows.update(data)
        source.update(name=name, zip_sha256=lex.fleet.digest(artifact.with_suffix('.zip')),
                      profile=props, java=(artifact / 'java-version.txt').read_text())
        sources.append(source)
    assert len(rows) == 840 and sum(r['laps'] for r in rows.values()) == 730
    return rows, sources


def export_rows(path, by_arm):
    buffer = io.StringIO(newline='')
    fields = ['arm', 'track', 'seed', 'laps', 'finish_order', 'moves', 'statuses', 'sha256', 'normalized_sha256']
    writer = csv.DictWriter(buffer, fields)
    writer.writeheader()
    for arm, rows in by_arm.items():
        for _, row in sorted(rows.items()):
            record = {k:row[k] for k in fields if k not in ('arm','finish_order','moves','statuses')}
            for key in ('finish_order','moves','statuses'):
                record[key] = '|'.join(map(str,row[key]))
            writer.writerow(dict(arm=arm, **record))
    path.write_bytes(gzip.compress(buffer.getvalue().encode(), mtime=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=Path)
    parser.add_argument('baseline_artifacts', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--mode', choices=('legacy','informed','scatter'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for mode in ([args.mode] if args.mode else ('legacy','informed','scatter')):
        baseline, base_sources = read_mode(args.baseline_artifacts, mode, 0)
        all_rows = {0:baseline}
        results = dict(baseline_sources=base_sources, candidates=[])
        for arm in (1, 2):
            candidate, sources = read_mode(args.artifacts, mode, arm)
            all_rows[arm] = candidate
            metrics = lex.score(candidate, baseline)
            results['candidates'].append(dict(arm=arm, sources=sources, metrics=metrics))
            print(json.dumps(dict(mode=mode, arm=arm, **{k:v for k,v in metrics.items()
                if k not in ('comparisons','equal_prefix')})), flush=True)
        (args.output / f'{mode}-metrics.json').write_text(json.dumps(results, indent=2, sort_keys=True)+'\n')
        export_rows(args.output / f'{mode}-outcomes.csv.gz', all_rows)


if __name__ == '__main__':
    main()
