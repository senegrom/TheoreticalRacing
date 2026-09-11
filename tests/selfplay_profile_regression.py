#!/usr/bin/env python3
"""Real-JVM/CLI proof that custom self-play profiles run the labelled experiment.

Run after build_main.sh. All edited profiles, captured logs and helper classes
live under a temporary directory; repository tracks and user settings are untouched.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


PROBE = r'''
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;
import java.util.TreeSet;
public final class PropertiesProbe {
    private static String hex(final String text) {
        final StringBuilder out = new StringBuilder();
        for (int i = 0; i < text.length(); i++) out.append(String.format("%04x", (int) text.charAt(i)));
        return out.toString();
    }
    public static void main(final String[] args) throws Exception {
        final Properties p = new Properties();
        try (var in = Files.newInputStream(Path.of(args[0]))) { p.load(in); }
        for (final String key : new TreeSet<>(p.stringPropertyNames())) {
            System.out.println(hex(key) + "\t" + hex(p.getProperty(key)));
        }
    }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT)
    args = parser.parse_args()
    repo = args.repo.resolve()
    check((repo / 'theoreticRacing.jar').is_file(), 'run build_main.sh first')
    java, javac = shutil.which('java'), shutil.which('javac')
    check(java is not None and javac is not None, 'a JDK is required')
    spec = importlib.util.spec_from_file_location('profile_bench', repo / 'tracks/bench_ai.py')
    bench = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bench)
    from benchmark_io import read_race

    with tempfile.TemporaryDirectory(prefix='selfplay-profile-regression-') as directory:
        root = Path(directory)
        source = root / 'PropertiesProbe.java'
        source.write_text(PROBE, encoding='utf-8')
        subprocess.run([javac, '-Xlint:all', '-Werror', '-d', str(root), str(source)], check=True, timeout=60)

        def java_properties(path):
            result = subprocess.run([java, '-cp', str(root), 'PropertiesProbe', str(path)],
                                    capture_output=True, text=True, check=True, timeout=30)
            def decode(text):
                return bytes.fromhex(text).decode('utf-16-be', 'surrogatepass')
            return {decode(k): decode(v) for k, v in
                    (line.split('\t') for line in result.stdout.splitlines())}

        # Independent oracle: compare actual java.util.Properties maps, not two
        # uses of the Python parser/serializer under test.
        bench.configure_runtime(root / 'roundtrip')
        props = Path(bench.PROPS)
        props.write_bytes(b'nPlayers : 4\nplayer1Kind : AI2\nplayer2K\\u0069nd AI2\n'
                          b'player1Name=Andr\xe9\nplayer2Name=\\uD83D\\uDE80\n'
                          b'\\#key\\:\\==\\ leading\\tvalue  \n=empty key\nempty=\n'
                          b'path=C\\:\\\\tmp\\\\file\ncontrols=\\u0000\\n\\r\\f\n'
                          b'odd=\\uD800\ntail=continued\\\n  text\nlast=discarded\\')
        expected = java_properties(props)
        expected.update(nPlayers='2', player1Kind='AI1', player2Kind='AI1')
        bench.set_nplayers(2)
        bench.set_all_to('AI1')
        check(java_properties(props) == expected, 'setters changed unrelated Java values or left the wrong roster')
        print('Java-properties oracle: alternate keys, Latin-1, UTF-16, controls and unrelated values preserved')

        # The launcher only records inputs/logs and delegates to the real JVM.
        # The repository CLI, configuration helpers, game and log parser are real.
        launcher = root / 'bin/java'
        launcher.parent.mkdir()
        launcher.write_text('#!' + sys.executable + '\n' + '''
import json, os, pathlib, shutil, subprocess, sys
args = sys.argv[1:]
record = None
if '--auto' in args:
    home = pathlib.Path(os.environ['SELFPLAY_CAPTURE'])
    record = home / ('race-%d' % len(list(home.iterdir())))
    record.mkdir()
    shutil.copyfile(args[args.index('--props') + 1], record / 'input.properties')
    (record / 'args.json').write_text(json.dumps(args))
result = subprocess.run([os.environ['SELFPLAY_REAL_JAVA'], *args], check=False)
if record is not None:
    log = pathlib.Path(args[args.index('--log') + 1])
    for path in log.parent.glob(log.stem + '*.log'):
        shutil.copyfile(path, record / path.name)
sys.exit(result.returncode)
''', encoding='utf-8')
        launcher.chmod(0o755)
        base = (repo / 'tracks/bench.properties').read_bytes()
        custom = re.sub(rb'^nPlayers=.*$', b'nPlayers : 4', base, flags=re.MULTILINE)
        custom = re.sub(rb'^player([1-8])Kind=.*$', rb'  player\1Kind : AI2', custom, flags=re.MULTILINE)
        custom += b'player1Kind=AI1\nplayer1K\\u0069nd : AI2\nplayer2Ki\\\n nd AI2\n'
        # Names exercise the InputStream encoding through the real game log too.
        custom += b'player1Name=Andr\xe9\nplayer2Name=Pilot\\uD83D\\uDE80\n'
        original_path = root / 'custom.properties'
        cache = root / 'baseline.json'
        invocations = 0
        actual_races = 0

        def run_cli(mode, count, profile=custom, expected_kinds=('AI1', 'AI2'), cached=False, success=True):
            nonlocal invocations, actual_races
            home = root / ('cli-%d' % invocations)
            invocations += 1
            home.mkdir()
            captures = home / 'captured'
            captures.mkdir()
            original_path.write_bytes(profile)
            environment = {k: v for k, v in os.environ.items() if not k.startswith('BENCH_')}
            environment.update(RACING_PROPS=str(original_path), RACING_WORK_DIR=str(home),
                               SELFPLAY_CAPTURE=str(captures), SELFPLAY_REAL_JAVA=java,
                               PATH=str(launcher.parent) + os.pathsep + environment.get('PATH', ''))
            if cached:
                environment['BENCH_BASELINE'] = str(cache)
            result = subprocess.run([sys.executable, str(repo / 'tracks/bench_iso.py'), mode, '1', 'hairpin'],
                                    env=environment, cwd=repo, capture_output=True, text=True, timeout=240)
            check(original_path.read_bytes() == profile, 'source profile was changed')
            records = sorted(captures.iterdir())
            if not success:
                check(result.returncode != 0 and 'TOTAL' not in result.stdout,
                      'invalid profile produced a successful comparison: ' + result.stdout)
                check(not records, 'invalid preflight launched a race')
                print(mode + ': incompatible/malformed profile rejected before Java racing')
                return
            check(result.returncode == 0, result.stdout + result.stderr)
            check('TOTAL' in result.stdout, 'successful run has no aggregate')
            check(len(records) == len(expected_kinds), 'wrong number of self-play arms')
            for record, kind in zip(records, expected_kinds):
                properties = java_properties(record / 'input.properties')
                check(properties['nPlayers'] == str(count), 'CLI did not configure requested field size')
                expected_players = {n: (properties.get('player%dName' % n, 'Player %d' % n), kind)
                                    for n in range(1, count + 1)}
                check(all(properties.get('player%dKind' % n) == kind for n in expected_players),
                      'CLI arm has wrong controllers')
                logs = list(record.glob('*.log'))
                check(len(logs) == 5, 'expected one completed log per seed')
                for log in logs:
                    read_race(log, expected_players)
                    actual_races += 1
            print('%s: %d cars, %s, every real race log matches the requested roster' %
                  (mode, count, '/'.join(expected_kinds)))

        for mode, count in (('8car', 8), ('4car', 4), ('2car', 2)):
            run_cli(mode, count)
        run_cli('2car', 2, cached=True)
        saved_cache = cache.read_bytes()
        run_cli('2car', 2, cached=True, expected_kinds=('AI1',))
        check(cache.read_bytes() == saved_cache, 'cache hit rewrote baseline')
        run_cli('4car', 4, cached=True, success=False)
        check(cache.read_bytes() == saved_cache, 'incompatible field rewrote baseline')
        run_cli('8car', 8, profile=custom + b'maxPlayers : 2\n', success=False)
        run_cli('8car', 8, profile=custom + b'bad=\\uZZZZ\n', success=False)
        print('%d real races validated; custom profiles, field sizes and baseline reuse OK' % actual_races)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
