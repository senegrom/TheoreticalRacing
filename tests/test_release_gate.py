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
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'web/scripts'))
from ci_scope import browser_path, changed_paths, needs_browser

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
        self.assertEqual(block(self.browser, 'on:').strip(), 'on:\n  workflow_call:')
        job = block(self.ci, '  browser:')
        self.assertIn('    uses: ./.github/workflows/browser.yml', job)
        self.assertIn("    if: needs.tooling.outputs.browser == 'true'", job)
        self.assertNotRegex(job, r'(?m)^\s+(continue-on-error|with):')
        # Checkout defaults to the triggering commit; never a moving branch.
        for ref in re.findall(r'(?m)^\s+ref:\s*(.+)$', self.ci + self.browser):
            self.assertEqual(ref, '${{ github.sha }}')
        for name in ('java', 'frozen-ai2', 'tooling'):
            engine = block(self.ci, '  ' + name + ':')
            self.assertNotRegex(engine, r'(?m)^\s+(if|continue-on-error):')
        self.assertNotIn('engine-validation:', self.browser)
        self.assertNotIn('sh run_tests.sh', self.browser)

    def test_failed_skipped_or_cancelled_gate_cannot_publish(self):
        publish = block(self.ci, '  publish:')
        needs = re.findall(r'(?m)^    needs: \[([^\]]+)\]$', publish)
        self.assertEqual(len(needs), 1)
        self.assertEqual({item.strip() for item in needs[0].split(',')},
                         {'java', 'frozen-ai2', 'tooling', 'browser'})
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
        for path in ['web/app.js', 'src/tr/Main.java', 'tests/test_release_gate.py',
                     'tracks/bench_ai.py', 'build_main.sh', '.gitattributes', '.gitignore',
                     '.github/dependabot.yml', 'LICENSE',
                     '.github/workflows/browser.yml', '.github/workflows/ci.yml']:
            with self.subTest(path=path):
                self.assertTrue(browser_path(path))
        tooling = block(self.ci, '  tooling:')
        self.assertIn('fetch-depth: 0', tooling)
        self.assertIn('run: python3 web/scripts/ci_scope.py', tooling)
        self.assertIn('browser: ${{ steps.scope.outputs.browser }}', tooling)
        self.assertNotIn('paths:', block(self.ci, 'on:'))

    def test_browser_cannot_cancel_its_ci_caller_but_superseded_commits_can_cancel(self):
        ci_group = block(self.ci, 'concurrency:')
        browser_group = block(self.browser, 'concurrency:')
        self.assertIn('group: ci-${{ github.workflow }}-', ci_group)
        self.assertIn('group: browser-', browser_group)
        self.assertNotIn('group: browser-', ci_group)
        self.assertNotIn('github.sha', ci_group + browser_group)


class BrowserScopeTests(unittest.TestCase):
    SHA = 'a' * 40

    def test_documentation_only_skips_browsers_and_mixed_changes_run(self):
        for event, data in [('push', {'before': self.SHA}),
                            ('pull_request', {'pull_request': {'base': {'sha': self.SHA}}})]:
            with self.subTest(event=event):
                def docs(base, is_pr):
                    self.assertEqual(base, self.SHA)
                    self.assertEqual(is_pr, event == 'pull_request')
                    return ['README.md', 'racing-memory.md']
                self.assertFalse(needs_browser(event, data, docs))
                self.assertTrue(needs_browser(event, data, lambda *_: ['README.md', 'web/app.js']))

    def test_manual_new_branch_missing_data_and_failed_diff_run_browsers(self):
        for event, data in [('workflow_dispatch', {}), ('unknown', {}), ('push', {}),
                            ('push', {'before': '0' * 40}), ('push', {'before': '--help'}),
                            ('pull_request', {'pull_request': {}})]:
            self.assertTrue(needs_browser(event, data))
        def unavailable(*args):
            raise subprocess.CalledProcessError(128, 'git')
        self.assertTrue(needs_browser('push', {'before': self.SHA}, unavailable))

    def test_diff_keeps_deleted_or_renamed_browser_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def git(*args):
                return subprocess.check_output(['git', '-C', temp, *args], stderr=subprocess.DEVNULL).decode().strip()
            git('init')
            git('config', 'user.name', 'Test')
            git('config', 'user.email', 'test@example.invalid')
            (root / 'web').mkdir()
            (root / 'web/old file.js').write_text('old')
            git('add', '.')
            git('commit', '-m', 'base')
            base = git('rev-parse', 'HEAD')
            git('mv', 'web/old file.js', 'README.md')
            git('commit', '-m', 'move')
            previous = Path.cwd()
            try:
                os.chdir(root)
                for is_pr in (False, True):
                    self.assertIn('web/old file.js', changed_paths(base, is_pr))
            finally:
                os.chdir(previous)


if __name__ == '__main__':
    unittest.main()
