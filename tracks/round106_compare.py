#!/usr/bin/env python3
"""Compare one seed window between baseline and candidate jars."""
from __future__ import annotations
import argparse, json, re, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROW = re.compile(r'^(\d+) p(\d+) ')


def props(out: Path) -> None:
    text = (ROOT / 'tracks' / 'bench.properties').read_text()
    text = re.sub(r'^(player[1-8]Kind)=.*$', r'\1=AI1', text, flags=re.M)
    text = re.sub(r'^nPlayers=\d+$', 'nPlayers=8', text, flags=re.M)
    out.write_text(text)


def parse(path: Path) -> dict:
    moves: dict[int, int] = {}
    finishes: dict[int, int] = {}
    crashes: set[int] = set()
    saw = False
    for line in path.read_text().splitlines():
        saw |= line.startswith('# results')
        match = ROW.match(line)
        if not match:
            continue
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if 'CRASH' in line:
            crashes.add(player)
        elif 'FINISH' in line:
            finishes[player] = moves[player]
    if not saw:
        raise RuntimeError(f'invalid log {path}')
    return {'finishes': finishes, 'crashes': sorted(crashes)}


def run(jar: Path, track: str, start: int, end: int, tmp: Path, tag: str) -> dict[int, dict]:
    config = tmp / f'{tag}.properties'
    props(config)
    log = tmp / f'{tag}-{track}.log'
    result = subprocess.run([
        'java', '-Djava.awt.headless=true', '-jar', str(jar.resolve()), '--auto',
        '--track', track, '--props', str(config), '--log', str(log),
        '--seed', f'{start}-{end}'
    ], cwd=ROOT, text=True, capture_output=True, timeout=300 + 45 * (end - start + 1))
    (tmp / f'{tag}.stdout').write_text(result.stdout)
    (tmp / f'{tag}.stderr').write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(f'{tag} failed: {result.stderr[-2000:]}')
    stem = log.with_suffix('')
    return {seed: parse(Path(f'{stem}_s{seed}.log')) for seed in range(start, end + 1)}


def classify(candidate: dict, baseline: dict) -> tuple[str, int]:
    if candidate == baseline:
        return 'identical', 0
    cf, bf = candidate['finishes'], baseline['finishes']
    cc, bc = candidate['crashes'], baseline['crashes']
    delta = sum(cf.values()) - sum(bf.values())
    if len(cf) < len(bf) or len(cc) > len(bc):
        return 'safety_regression', delta
    if len(cf) > len(bf) or len(cc) < len(bc):
        return 'safety_gain', delta
    if delta < 0:
        return 'faster', delta
    if delta > 0:
        return 'slower', delta
    return 'redistribution', 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--track', required=True)
    parser.add_argument('--start', type=int, required=True)
    parser.add_argument('--end', type=int, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    summary = {'track': args.track, 'start': args.start, 'end': args.end,
               'pairs': args.end - args.start + 1, 'counts': {},
               'net_moves': 0, 'events': []}
    with tempfile.TemporaryDirectory(prefix=f'r106-{args.track}-') as directory:
        tmp = Path(directory)
        baseline = run(args.baseline, args.track, args.start, args.end, tmp, 'baseline')
        candidate = run(args.candidate, args.track, args.start, args.end, tmp, 'candidate')
        for seed in range(args.start, args.end + 1):
            kind, delta = classify(candidate[seed], baseline[seed])
            summary['counts'][kind] = summary['counts'].get(kind, 0) + 1
            summary['net_moves'] += delta
            if kind != 'identical':
                summary['events'].append({'seed': seed, 'classification': kind,
                    'delta': delta, 'candidate': candidate[seed], 'baseline': baseline[seed]})
    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summary, indent=2, sort_keys=True))
    bad = sum(summary['counts'].get(k, 0) for k in
              ('safety_regression', 'slower', 'redistribution'))
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
