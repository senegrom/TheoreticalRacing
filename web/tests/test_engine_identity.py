"""The browser build's engine identity: recorded in the jar, stamped in the worker."""
import sys
import tempfile
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB / 'scripts'))
import engine_identity  # noqa: E402


class EngineIdentityTests(unittest.TestCase):
    def test_record_then_stamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'src/tr').mkdir(parents=True)
            (root / 'src/tr/A.java').write_bytes(b'class A {}\n')
            classes, runtime = root / 'classes', root / 'runtime.js'
            runtime.write_bytes(b"const ENGINE_BUILD = '__ENGINE_BUILD__';\n"
                                b"const ENGINE_JAR = '__ENGINE_JAR__';\n")
            identity = engine_identity.record(root / 'src', classes)
            self.assertRegex(identity, r'^[0-9a-f]{64}$')
            self.assertEqual(identity, engine_identity.stamp(classes, runtime))
            self.assertIn("'" + identity + "'", runtime.read_text(encoding='utf-8'))
            self.assertIn("'racing-" + identity[:12] + ".jar'", runtime.read_text(encoding='utf-8'))
            with self.assertRaises(ValueError):  # the placeholder is gone once stamped
                engine_identity.stamp(classes, runtime)
            (root / 'src/tr/A.java').write_bytes(b'class A { }\n')
            self.assertNotEqual(identity, engine_identity.digest(root / 'src'))

    def test_the_source_worker_carries_one_placeholder(self):
        text = (WEB / 'runtime.js').read_text(encoding='utf-8')
        self.assertEqual(1, text.count(engine_identity.PLACEHOLDER))
        self.assertEqual(1, text.count(engine_identity.JAR_PLACEHOLDER))

    @unittest.skipUnless((WEB / 'dist/runtime.js').is_file(), 'no browser build')
    def test_the_built_worker_names_its_own_jar(self):
        # Review, 2026-09-29: the published jar is named after the build, so a
        # page of one deploy never loads another's jar from a cache.
        text = (WEB / 'dist/runtime.js').read_text(encoding='utf-8')
        import re
        identity = re.search(r"const ENGINE_BUILD = '([0-9a-f]{64})';", text).group(1)
        name = engine_identity.jar_name(identity)
        self.assertIn("const ENGINE_JAR = '" + name + "';", text)
        self.assertEqual((WEB / 'dist' / name).read_bytes(), (WEB / 'dist/racing.jar').read_bytes())


if __name__ == '__main__':
    unittest.main()
