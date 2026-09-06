"""Publication must contain exactly the verified build, never checkout leftovers."""
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

WEB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB / 'scripts'))
import site_artifact as artifact
from deployment_guard import is_current

SHA = 'a' * 40
REPO = 'senegrom/TheoreticalRacing'


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.site = Path(self.temp.name) / 'staged'
        shutil.copytree(WEB / 'dist', self.site)
        artifact.seal(self.site, SHA, REPO)

    def test_complete_artifact_and_identity(self):
        self.assertEqual(artifact.verify(self.site, SHA, REPO)['source'], SHA)
        for sha, repo in [('b' * 40, REPO), (SHA, 'other/repository')]:
            with self.assertRaises(ValueError):
                artifact.verify(self.site, sha, repo)

    def test_missing_or_old_entrypoint_is_rejected(self):
        index = self.site / 'index.html'
        index.unlink()
        with self.assertRaisesRegex(ValueError, 'missing='):
            artifact.verify(self.site, SHA, REPO)
        index.write_text('old checkout entrypoint')
        with self.assertRaisesRegex(ValueError, 'changed='):
            artifact.verify(self.site, SHA, REPO)

    def test_obsolete_extra_file_is_rejected(self):
        (self.site / 'old-script.js').write_text('obsolete')
        with self.assertRaisesRegex(ValueError, 'extra='):
            artifact.verify(self.site, SHA, REPO)

    def test_missing_icon_even_if_manifest_was_resealed(self):
        (self.site / 'icons/racing-tab-16-v3.png').unlink()
        artifact.seal(self.site, SHA, REPO)
        with self.assertRaisesRegex(ValueError, 'track/icon'):
            artifact.verify(self.site, SHA, REPO)

    def test_manifest_cannot_omit_mandatory_asset(self):
        (self.site / 'racing.jar').unlink()
        artifact.seal(self.site, SHA, REPO)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            artifact.verify(self.site, SHA, REPO)

    def test_symlinks_are_rejected(self):
        (self.site / 'alias').symlink_to('index.html')
        with self.assertRaisesRegex(ValueError, 'Symlinks'):
            artifact.verify(self.site, SHA, REPO)

    def test_wrong_checkout_cannot_supply_source(self):
        with patch.object(artifact.subprocess, 'check_output', return_value='b' * 40):
            with self.assertRaisesRegex(ValueError, 'checkout'):
                artifact.prepare(self.site, SHA, REPO)
        self.assertFalse((self.site / 'source.tar.gz').exists())

    def test_exact_source_attached_and_hashed(self):
        def archive(command, **kwargs):
            output = next(x.split('=', 1)[1] for x in command if x.startswith('--output='))
            self.assertEqual(command[-1], SHA)
            Path(output).write_bytes(b'corresponding source')
        with patch.object(artifact.subprocess, 'check_output', return_value=SHA), patch.object(artifact.subprocess, 'run', side_effect=archive):
            artifact.prepare(self.site, SHA, REPO)
        manifest = artifact.verify(self.site, SHA, REPO)
        self.assertEqual(manifest['files']['source.tar.gz'], artifact.digest(self.site / 'source.tar.gz'))


    def test_every_required_asset_is_checked_without_checkout_fallback(self):
        # A previous checkout may contain all missing files; it must never be read.
        checkout = Path(self.temp.name) / 'old-checkout' / 'site'
        for name in sorted(artifact.REQUIRED):
            with self.subTest(asset=name):
                staged = self.site / name
                data = staged.read_bytes()
                old = checkout / name
                old.parent.mkdir(parents=True, exist_ok=True)
                old.write_bytes(data)
                staged.unlink()
                try:
                    with self.assertRaisesRegex(ValueError, 'missing='):
                        artifact.verify(self.site, SHA, REPO)
                finally:
                    staged.write_bytes(data)
        artifact.verify(self.site, SHA, REPO)

    def test_source_link_identifies_the_exact_tested_revision(self):
        page = (self.site / 'index.html').read_text()
        self.assertIn(f'https://github.com/{REPO}/tree/{SHA}', page)
        self.assertIn('href="./source.tar.gz"', page)
        self.assertIn(f'https://github.com/{REPO}/tree/master', page)
        other = 'b' * 40
        artifact.seal(self.site, other, REPO)
        page = (self.site / 'index.html').read_text()
        self.assertIn(f'https://github.com/{REPO}/tree/{other}', page)
        self.assertNotIn(f'https://github.com/{REPO}/tree/{SHA}', page)
        artifact.verify(self.site, other, REPO)

    def test_hash_consistent_wrong_source_link_is_rejected(self):
        page = self.site / 'index.html'
        page.write_text(page.read_text().replace('/tree/' + SHA, '/tree/' + 'b' * 40))
        manifest_path = self.site / artifact.MANIFEST
        manifest = json.loads(manifest_path.read_text())
        manifest['files']['index.html'] = artifact.digest(page)
        artifact.write_json(manifest_path, manifest)
        with self.assertRaisesRegex(ValueError, 'source link'):
            artifact.verify(self.site, SHA, REPO)

    def test_source_template_drift_fails_closed(self):
        page = self.site / 'index.html'
        html = page.read_text()
        for changed in [artifact.REVISION_LINK.sub('', html),
                        html + artifact.revision_link(SHA, REPO)]:
            with self.subTest(template=changed[-100:]):
                page.write_text(changed)
                with self.assertRaisesRegex(ValueError, 'exactly one'):
                    artifact.seal(self.site, SHA, REPO)

    def test_unversioned_local_build_does_not_invent_a_revision(self):
        artifact.seal(self.site, None, REPO)
        page = (self.site / 'index.html').read_text()
        self.assertEqual(artifact.REVISION_LINK.findall(page),
                         ['<a id="build-revision" hidden target="_blank" rel="noopener"></a>'])


class DeploymentGuardTests(unittest.TestCase):
    def test_current_only(self):
        fetch = lambda url: dict(ref='refs/heads/master', object=dict(type='commit', sha=SHA))
        self.assertTrue(is_current(SHA, REPO, fetch))
        self.assertFalse(is_current('b' * 40, REPO, fetch))

    def test_bad_or_unavailable_ref_fails_closed(self):
        for response in [{}, dict(ref='refs/heads/master', object=dict(type='tag', sha=SHA)),
                         dict(ref='refs/heads/master', object=dict(type='commit', sha=None))]:
            with self.assertRaises(ValueError):
                is_current(SHA, REPO, lambda url: response)
        def unavailable(url):
            raise OSError('offline')
        with self.assertRaises(OSError):
            is_current(SHA, REPO, unavailable)

    def test_publish_staging_and_validation_inputs(self):
        workflow = (WEB.parent / '.github/workflows/browser.yml').read_text()
        self.assertLess(workflow.index('rm -rf -- "$RUNNER_TEMP/racing-pages"'), workflow.index('uses: actions/download-artifact'))
        self.assertIn('path: ${{ runner.temp }}/racing-pages', workflow)
        self.assertNotIn('path: site', workflow)
        self.assertLess(workflow.index('deployment_guard.py'), workflow.index('uses: actions/deploy-pages'))
        self.assertIn('queue: max', workflow)
        self.assertIn('--expected-sha "$GITHUB_SHA"', workflow)
        self.assertIn('group: browser-${{ github.ref }}-${{ github.sha }}', workflow)
        for path in ['tests/**', '*.sh', '.gitattributes', '.gitignore']:
            self.assertEqual(workflow.count("- '" + path + "'"), 2)
        self.assertIn('/site/', (WEB.parent / '.gitignore').read_text().splitlines())
        self.assertFalse((WEB.parent / 'site').exists())

    def test_dependency_ecosystems_and_source_links(self):
        config = (WEB.parent / '.github/dependabot.yml').read_text()
        self.assertIn('package-ecosystem: github-actions', config)
        self.assertIn('package-ecosystem: pip', config)
        self.assertIn('directory: /web', config)
        self.assertNotIn('package-ecosystem: ""', config)
        page = (WEB / 'index.html').read_text()
        self.assertIn('TheoreticalRacing/tree/master', page)
        self.assertNotIn('TheoreticalRacing/tree/browser', page)
        self.assertIn('href="./source.tar.gz"', page)


if __name__ == '__main__':
    unittest.main()
