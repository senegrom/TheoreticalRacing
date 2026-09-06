"""Exercise the production build's version probe without requiring a JDK."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BuildVersionTests(unittest.TestCase):
    def probe(self, output, status=0, name='javac'):
        text = (ROOT / 'build_main.sh').read_text(encoding='utf-8')
        function = text.split('require_jdk25_or_newer() {', 1)[1].split('\n}', 1)[0]
        script = 'set -eu\nrequire_jdk25_or_newer() {' + function + '\n}\n'
        script += 'require_jdk25_or_newer "$1" "$2"\n'
        with tempfile.TemporaryDirectory() as temporary:
            tool = Path(temporary, name)
            tool.write_text('#!/bin/sh\ncat <<\'VERSION\'\n' + output
                            + '\nVERSION\nexit ' + str(status) + '\n', encoding='utf-8')
            tool.chmod(0o755)
            return subprocess.run(['sh', '-c', script, 'probe', str(tool), name],
                                  text=True, capture_output=True, timeout=10,
                                  env=os.environ.copy())

    def test_heap_banners_are_not_versions(self):
        for name in ('javac', 'jar'):
            for banner in ('Picked up JAVA_TOOL_OPTIONS: -Xmx3g',
                           'Picked up _JAVA_OPTIONS: -Xmx2g',
                           'NOTE: Picked up JDK_JAVA_OPTIONS: -Xmx1g'):
                with self.subTest(name=name, banner=banner):
                    self.assertEqual(self.probe(banner + '\n' + name + ' 25.0.4', name=name).returncode, 0)

    def test_release_and_early_access(self):
        for version in ('25', '25.0.4.1', '26-ea', '26.0.1+7'):
            self.assertEqual(self.probe('javac ' + version).returncode, 0)

    def test_old_release_cannot_hide_behind_banner(self):
        self.assertEqual(self.probe('Picked up JAVA_TOOL_OPTIONS: -Xmx99g\njavac 21.0.11').returncode, 2)

    def test_invalid_version_is_rejected(self):
        for text in ('', 'javac unknown', '25.0.4', 'version 25', 'jar 25.0.4'):
            self.assertEqual(self.probe(text).returncode, 2)

    def test_failed_probe_is_rejected(self):
        self.assertEqual(self.probe('javac 25.0.4', status=17).returncode, 2)


if __name__ == '__main__':
    unittest.main()
