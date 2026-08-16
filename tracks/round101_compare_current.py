#!/usr/bin/env python3
"""Compare an AI1 candidate jar with the exact current-AI1 baseline jar."""
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('r101_exact', ROOT / 'tracks' / 'round101_compare_exact.py')
EXACT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(EXACT)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--track', required=True)
    parser.add_argument('--end', type=int, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix=f'r101-current-{args.track}-') as directory:
        tmp = Path(directory)
        started = time.perf_counter()
        EXACT.run_column(args.baseline.resolve(), args.track, args.end, 'AI1', tmp)
        baseline_seconds = time.perf_counter() - started
        for path in tmp.glob(f'AI1-{args.track}_s*.log'):
            path.rename(tmp / path.name.replace('AI1-', 'baseline-', 1))

        started = time.perf_counter()
        EXACT.run_column(args.candidate.resolve(), args.track, args.end, 'AI1', tmp)
        candidate_seconds = time.perf_counter() - started
        summary = {
            'track': args.track,
            'pairs': args.end,
            'identical': 0,
            'faster': 0,
            'slower': 0,
            'safety_gain': 0,
            'safety_regression': 0,
            'redistribution': 0,
            'net_moves': 0,
            'baseline_seconds': baseline_seconds,
            'candidate_seconds': candidate_seconds,
            'runtime_ratio': candidate_seconds / baseline_seconds,
            'events': [],
        }
        for seed in range(1, args.end + 1):
            baseline = EXACT.parse_log(tmp / f'baseline-{args.track}_s{seed}.log')
            candidate = EXACT.parse_log(tmp / f'AI1-{args.track}_s{seed}.log')
            if candidate == baseline:
                summary['identical'] += 1
                continue
            bf, cf = baseline['finishes'], candidate['finishes']
            bc, cc = baseline['crashes'], candidate['crashes']
            bsum, csum = sum(bf.values()), sum(cf.values())
            if len(cf) < len(bf) or len(cc) > len(bc):
                kind = 'safety_regression'
            elif len(cf) > len(bf) or len(cc) < len(bc):
                kind = 'safety_gain'
            elif csum < bsum:
                kind = 'faster'
            elif csum > bsum:
                kind = 'slower'
            else:
                kind = 'redistribution'
            summary[kind] += 1
            summary['net_moves'] += csum - bsum
            summary['events'].append({
                'seed': seed,
                'classification': kind,
                'delta': csum - bsum,
                'baseline_finishers': len(bf),
                'candidate_finishers': len(cf),
                'baseline_crashes': len(bc),
                'candidate_crashes': len(cc),
                'baseline_moves': bsum,
                'candidate_moves': csum,
                'baseline_by_player': bf,
                'candidate_by_player': cf,
            })

    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary['safety_regression'] or summary['slower'] or summary['redistribution']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
