#!/usr/bin/env python3
"""Exercise the production promotion command with real JVMs, not mocked races.

Run after build_main.sh. Temporary profiles/cache/logs never touch saved settings.
--out retains evidence; otherwise a temporary directory is removed after the test.
"""
import argparse
import contextlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracks.benchmark_io import configured_players, read_properties, read_race


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def exercise(root):
    java = shutil.which('java')
    check(java is not None and (ROOT / 'theoreticRacing.jar').is_file(), 'build the JAR with a JDK first')
    env = dict(os.environ, JAVA_TOOL_OPTIONS='', JDK_JAVA_OPTIONS='', _JAVA_OPTIONS='',
               RACING_REACH_CACHE=str(root / 'cache'))
    source = ROOT / 'tracks/lap_bench.properties'
    original = source.read_bytes()
    races = car_races = 0
    for players in (2, 4, 8):
        for mode in ('legacy', 'informed', 'scatter'):
            out = root / ('%dp-%s' % (players, mode))
            result = subprocess.run(
                [sys.executable, str(ROOT / 'tracks/promotion_pair.py'), '--players', str(players),
                 '--start-mode', mode, '--seeds', '1', '--heap=-Xmx8g', '--tracks', 'hairpin', 'circle',
                 '--out', str(out)], cwd=ROOT, env=env, text=True, capture_output=True, timeout=300)
            (root / ('%dp-%s.stdout' % (players, mode))).write_text(result.stdout, encoding='utf-8')
            (root / ('%dp-%s.stderr' % (players, mode))).write_text(result.stderr, encoding='utf-8')
            check(result.returncode == 0, result.stdout + result.stderr)
            check('candidate car-races' in (out / 'head-to-head.txt').read_text(), 'no validated place report')
            for parity, label in ((1, 'odd'), (2, 'even')):
                profile = out / (label + '.properties')
                roster = configured_players(profile)
                slots = set(range(parity, players + 1, 2))
                check(len(roster) == players and {kind for _, kind in roster.values()} == {'AI1'}, 'wrong cohort controllers')
                check(read_properties(profile)['aiStartPlacement'] == mode, 'wrong requested start mode')
                logs = sorted((out / label).glob('*_s*.log'))
                check(len(logs) == 2, 'missing completed course')
                for log in logs:
                    race = read_race(log, roster)
                    check(race.slots == slots, 'real JVM did not enable the requested candidate slots')
                    check(len(race.slots) == players // 2 and set(race.players) - race.slots,
                          'a policy cohort is absent')
                    races += 1
                    car_races += len(roster)
            print('%d cars / %s: both actual slot assignments and complete place reports verified' % (players, mode), flush=True)

    # An old/broken engine that omits candidate metadata can still emit otherwise
    # complete races. Strip it only after the real JVM exits: fleet checksums now
    # cover those logs, so the cohort contract (not a checksum mismatch) must fail.
    launcher = root / 'java-without-candidate-metadata'
    launcher.write_text('#!' + sys.executable + '\n' + '''
import pathlib, subprocess, sys
args = sys.argv[1:]
status = subprocess.run([''' + repr(java) + ''', *args], check=False).returncode
if '--log' in args:
    path = pathlib.Path(args[args.index('--log') + 1])
    for log in path.parent.glob(path.stem + '*.log'):
        text = log.read_text(encoding='utf-8')
        log.write_text(''.join(line for line in text.splitlines(keepends=True)
                               if not line.startswith('# candidate-slots ')), encoding='utf-8')
sys.exit(status)
''', encoding='utf-8')
    launcher.chmod(0o755)
    out = root / 'missing-cohort'
    result = subprocess.run([sys.executable, str(ROOT / 'tracks/promotion_pair.py'), '--players', '2',
                             '--start-mode', 'legacy', '--seeds', '1', '--tracks', 'hairpin',
                             '--java', str(launcher), '--out', str(out)],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    (root / 'missing-cohort.stdout').write_text(result.stdout, encoding='utf-8')
    (root / 'missing-cohort.stderr').write_text(result.stderr, encoding='utf-8')
    check(result.returncode != 0 and not (out / 'head-to-head.txt').exists(),
          'complete races without candidate metadata became promotion evidence')
    check('candidate car-races' not in result.stdout, 'invalid comparison printed a successful aggregate')
    check(source.read_bytes() == original, 'caller-owned profile changed')
    print('%d real races / %d car-races: candidate and champion cohorts present; missing metadata rejected' %
          (races, car_races), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    with contextlib.ExitStack() as stack:
        if args.out is None:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='promotion-pair-regression-')))
        else:
            root = args.out.resolve()
            root.mkdir(parents=True, exist_ok=False)
        exercise(root)


if __name__ == '__main__':
    main()
