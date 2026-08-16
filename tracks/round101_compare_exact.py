#!/usr/bin/env python3
"""Run an exact AI1-vs-AI2 per-seed differential for one track."""
from __future__ import annotations
import argparse, json, re, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT_RE = re.compile(r'^(\d+) p(\d+) ')


def configure(source: Path, destination: Path, kind: str) -> None:
    lines = []
    for line in source.read_text().splitlines():
        if re.match(r'^player[1-8]Kind=', line):
            line = line.split('=', 1)[0] + '=' + kind
        lines.append(line)
    destination.write_text('\n'.join(lines) + '\n')


def parse_log(path: Path) -> dict:
    moves: dict[int, int] = {}
    finishes: dict[int, int] = {}
    crashes: set[int] = set()
    saw_results = False
    for line in path.read_text().splitlines():
        if line.startswith('# results'):
            saw_results = True
        match = RESULT_RE.match(line)
        if not match:
            continue
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if 'CRASH' in line:
            crashes.add(player)
        elif 'FINISH' in line:
            finishes[player] = moves[player]
    if not saw_results:
        raise RuntimeError(f'invalid log: {path}')
    return {'finishes': finishes, 'crashes': sorted(crashes)}


def run_column(jar: Path, track: str, seed_end: int, kind: str, tmp: Path) -> None:
    props = tmp / f'{kind}.properties'
    configure(ROOT / 'tracks' / 'bench.properties', props, kind)
    log = tmp / f'{kind}-{track}.log'
    result = subprocess.run([
        'java', '-Djava.awt.headless=true', '-jar', str(jar), '--auto', '--track', track,
        '--props', str(props), '--log', str(log), '--seed', f'1-{seed_end}'
    ], cwd=ROOT, text=True, capture_output=True, timeout=3300)
    (tmp / f'{kind}-{track}.stdout').write_text(result.stdout)
    (tmp / f'{kind}-{track}.stderr').write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(f'{kind} {track} failed with {result.returncode}: {result.stderr[-2000:]}')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--jar', type=Path, required=True)
    parser.add_argument('--track', required=True)
    parser.add_argument('--seeds', type=int, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix=f'r101-{args.track}-') as directory:
        tmp = Path(directory)
        run_column(args.jar.resolve(), args.track, args.seeds, 'AI1', tmp)
        run_column(args.jar.resolve(), args.track, args.seeds, 'AI2', tmp)
        summary = {
            'track': args.track, 'pairs': args.seeds, 'identical': 0, 'faster': 0,
            'slower': 0, 'safety_gain': 0, 'safety_regression': 0,
            'redistribution': 0, 'net_moves': 0, 'events': []
        }
        for seed in range(1, args.seeds + 1):
            candidate = parse_log(tmp / f'AI1-{args.track}_s{seed}.log')
            champion = parse_log(tmp / f'AI2-{args.track}_s{seed}.log')
            if candidate == champion:
                summary['identical'] += 1
                continue
            cf, bf = candidate['finishes'], champion['finishes']
            cc, bc = candidate['crashes'], champion['crashes']
            csum, bsum = sum(cf.values()), sum(bf.values())
            event = {
                'seed': seed, 'candidate_finishers': len(cf), 'champion_finishers': len(bf),
                'candidate_crashes': len(cc), 'champion_crashes': len(bc),
                'candidate_moves': csum, 'champion_moves': bsum, 'delta': csum - bsum,
                'candidate_by_player': cf, 'champion_by_player': bf,
            }
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
            event['classification'] = kind
            summary[kind] += 1
            summary['net_moves'] += csum - bsum
            summary['events'].append(event)

    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
