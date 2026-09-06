"""Offline GitHub transport tests: no tokens or network needed."""
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

SPEC = importlib.util.spec_from_file_location('publish_pages', Path(__file__).resolve().parents[1] / 'scripts/publish_pages.py')
PUBLISH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PUBLISH)
SOURCE, COMMIT = 'a' * 40, 'b' * 40


class Response(io.BytesIO):
    def __init__(self, value):
        super().__init__(json.dumps(value).encode())


class PublisherTests(unittest.TestCase):
    def exercise(self, existing=False, branch='browser', stale=False, changed_site=False):
        calls, polls = [], []
        base = 'https://api.github.com/repos/example/racing'

        def send(request, timeout=60):
            if isinstance(request, str):
                self.assertTrue(request.startswith('https://example.github.io/racing/deployment.json'))
                return Response({'source': SOURCE})
            method, url = request.get_method(), request.full_url
            body = json.loads(request.data) if request.data else None
            endpoint = url.removeprefix(base)
            calls.append((method, endpoint, body))
            if endpoint == '/git/ref/heads/browser':
                return Response({'object': {'sha': 'c' * 40 if stale else SOURCE}})
            if endpoint == '/git/ref/heads/gh-pages':
                if existing:
                    return Response({'object': {'sha': 'd' * 40}})
                raise HTTPError(url, 404, 'Not Found', {}, io.BytesIO())
            if endpoint.startswith('/git/trees/'):
                return Response({'tree': []})
            if endpoint == '/git/blobs':
                data = base64.b64decode(body['content'])
                return Response({'sha': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()})
            if endpoint == '/git/trees':
                return Response({'sha': 'e' * 40})
            if endpoint == '/git/commits':
                return Response({'sha': COMMIT})
            if endpoint == '/git/refs/heads/gh-pages':
                self.assertEqual(body, {'sha': COMMIT, 'force': False})
                return Response({})
            if endpoint == '/pages/builds':
                # The documented response has no id. Poll latest, checking SHA.
                return Response({'status': 'queued', 'url': base + '/pages/builds/latest'})
            if endpoint == '/pages/builds/latest':
                polls.append(True)
                return Response({'status': 'built', 'commit': 'd' * 40 if len(polls) == 1 else COMMIT})
            if endpoint == '/pages':
                return Response({'source': {'branch': 'master' if changed_site else 'gh-pages', 'path': '/'},
                                 'html_url': 'https://example.github.io/racing/'})
            self.fail(f'Unexpected request: {method} {endpoint}')

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['index.html', 'racing.jar', 'runtime.js', 'tracks.json', '.nojekyll']:
                (root / name).write_bytes(b'test')
            report = root / 'report.json'
            env = {'GITHUB_REF': f'refs/heads/{branch}', 'GITHUB_REPOSITORY': 'example/racing', 'GITHUB_SHA': SOURCE,
                   'GH_TOKEN': 'test-only', 'GITHUB_OUTPUT': str(root / 'out'), 'GITHUB_STEP_SUMMARY': str(root / 'summary')}
            def archive(command, check):
                self.assertEqual(command[-1], SOURCE)
                (root / 'source.tar.gz').write_bytes(b'corresponding source')
            with patch.dict(os.environ, env), patch.object(PUBLISH, 'urlopen', send), patch.object(PUBLISH.subprocess, 'run', archive), \
                 patch.object(PUBLISH.time, 'sleep'), patch('sys.argv', ['publish', str(root), '--report', str(report)]), \
                 contextlib.redirect_stdout(io.StringIO()):
                PUBLISH.main()
            data = json.loads(report.read_text())
            self.assertEqual(data['published'], existing)
            self.assertEqual(data['commit'], COMMIT)
            self.assertEqual(len(polls), 2 if existing else 0)
            self.assertEqual(any(c[0] == 'PATCH' for c in calls), existing)
            return calls

    def test_first_publication_only_stages_objects(self):
        self.exercise()

    def test_existing_site_build_and_exact_commit_poll(self):
        self.exercise(existing=True)

    def test_other_branch_cannot_publish(self):
        with self.assertRaises(SystemExit):
            self.exercise(branch='master')

    def test_stale_source_is_rejected(self):
        with self.assertRaises(SystemExit):
            self.exercise(stale=True)

    def test_changed_pages_source_is_not_overwritten(self):
        with self.assertRaisesRegex(RuntimeError, 'publishing source changed'):
            self.exercise(existing=True, changed_site=True)


if __name__ == '__main__':
    unittest.main()
