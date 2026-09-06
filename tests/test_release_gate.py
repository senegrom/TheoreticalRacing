"""Fail closed if Pages stops requiring the same engine suite as ordinary CI.

These are source-contract tests for the intentionally simple workflow layout;
GitHub validates YAML execution semantics. No extra runtime dependency is needed.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]


def block(text, heading):
    """Read an exact mapping block, refusing missing/ambiguous headings."""
    lines = text.splitlines()
    matches = [i for i, line in enumerate(lines) if line == heading]
    if len(matches) != 1:
        raise AssertionError('Expected exactly one workflow heading: ' + heading)
    first = matches[0]
    indent = len(heading) - len(heading.lstrip())
    end = first + 1
    while end < len(lines):
        line = lines[end]
        if line.strip() and not line.lstrip().startswith('#'):
            if len(line) - len(line.lstrip()) <= indent:
                break
        end += 1
    return '\n'.join(lines[first:end])


class ReleaseGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workflows = ROOT / '.github/workflows'
        cls.ci = (workflows / 'ci.yml').read_text()
        cls.browser = (workflows / 'browser.yml').read_text()

    def test_browser_requires_full_ci_at_the_callers_commit(self):
        self.assertIn('  workflow_call:', block(self.ci, 'on:'))
        job = block(self.browser, '  engine-validation:')
        self.assertIn('    uses: ./.github/workflows/ci.yml', job)
        self.assertNotRegex(job, r'(?m)^\s+(if|continue-on-error|with):')
        # Checkout defaults to the triggering commit; never a moving branch.
        for ref in re.findall(r'(?m)^\s+ref:\s*(.+)$', self.ci):
            self.assertEqual(ref, '${{ github.sha }}')
        self.assertNotIn('continue-on-error:', self.ci)
        self.assertNotRegex(self.ci, r'(?m)^\s+if:')

    def test_failed_skipped_or_cancelled_gate_cannot_publish(self):
        publish = block(self.browser, '  publish:')
        needs = re.findall(r'(?m)^    needs: \[([^\]]+)\]$', publish)
        self.assertEqual(len(needs), 1)
        self.assertEqual({item.strip() for item in needs[0].split(',')},
                         {'engine-validation', 'parity', 'browsers'})
        condition = re.findall(r'(?m)^    if: (.+)$', publish)
        self.assertEqual(len(condition), 1)
        # Without status overrides GitHub applies success() to all needs.
        self.assertNotRegex(condition[0], r'\b(always|cancelled|failure)\s*\(')
        self.assertNotIn('continue-on-error:', publish)
        self.assertIn("github.ref == 'refs/heads/master'", condition[0])

    def test_every_shared_engine_check_is_preserved(self):
        self.assertIn("java: ['25', '26']", block(self.ci, '  java:'))
        for command in ['sh ./run_tests.sh', 'sh ./build_main.sh',
                        'python tests/headless_smoke.py',
                        'python tests/query_replay_regression.py',
                        'python tests/lap_progress_regression.py',
                        'python tests/golden_races.py',
                        'for test in tests/ai1_*_regression.py; do',
                        'python "$test"',
                        'python tracks/bench_ai.py --seeds 1 definitely-not-a-track',
                        "python -m unittest discover -s tests -p 'test_*.py'"]:
            self.assertIn(command, self.ci)
        self.assertGreaterEqual(len(list((ROOT / 'tests').glob('ai1_*_regression.py'))), 22)

    def test_regression_failure_stops_the_actual_ci_loop(self):
        frozen = block(self.ci, '  frozen-ai2:')
        match = re.search(r'      - name: Run every champion AI regression pin\n'
                          r'        shell: bash\n        run: \|\n'
                          r'((?:          .*\n)+)', frozen + '\n')
        self.assertIsNotNone(match)
        loop = textwrap.dedent(match[1])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'tests').mkdir()
            for name in ['ai1_00broken_regression.py', 'ai1_zzlater_regression.py']:
                (root / 'tests' / name).touch()
            executable = root / 'python'
            executable.write_text('#!/bin/sh\nprintf "%s\\n" "$1" >> "$CALLS"\n'
                                  'case "$1" in *00broken*) exit 17;; esac\n')
            executable.chmod(0o755)
            calls = root / 'calls'
            env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ['PATH'], CALLS=str(calls))
            # Same fail-fast flags as GitHub's explicit bash shell.
            result = subprocess.run(['bash', '--noprofile', '--norc', '-e', '-o', 'pipefail', '-c', loop],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 17, result.stdout + result.stderr)
            self.assertEqual(calls.read_text().splitlines(), ['tests/ai1_00broken_regression.py'])

    def test_gate_and_tooling_edits_trigger_browser_validation(self):
        triggers = block(self.browser, 'on:')
        for event in ('push', 'pull_request'):
            event_block = block(triggers, '  ' + event + ':')
            for path in ['web/**', 'src/**', 'tests/**', 'tracks/**', '*.sh',
                         '.github/workflows/browser.yml', '.github/workflows/ci.yml']:
                self.assertIn("      - '" + path + "'", event_block)

    def test_reusable_ci_cannot_cancel_its_browser_caller(self):
        ci_group = block(self.ci, 'concurrency:')
        browser_group = block(self.browser, 'concurrency:')
        self.assertIn('group: ci-${{ github.workflow }}-', ci_group)
        self.assertIn('group: browser-', browser_group)
        self.assertNotIn('group: browser-', ci_group)


if __name__ == '__main__':
    unittest.main()
