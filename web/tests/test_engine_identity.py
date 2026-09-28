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
            runtime.write_bytes(b"const ENGINE_BUILD = '__ENGINE_BUILD__';\n")
            identity = engine_identity.record(root / 'src', classes)
            self.assertRegex(identity, r'^[0-9a-f]{64}$')
            self.assertEqual(identity, engine_identity.stamp(classes, runtime))
            self.assertIn("'" + identity + "'", runtime.read_text(encoding='utf-8'))
            with self.assertRaises(ValueError):  # the placeholder is gone once stamped
                engine_identity.stamp(classes, runtime)
            (root / 'src/tr/A.java').write_bytes(b'class A { }\n')
            self.assertNotEqual(identity, engine_identity.digest(root / 'src'))

    def test_the_source_worker_carries_one_placeholder(self):
        text = (WEB / 'runtime.js').read_text(encoding='utf-8')
        self.assertEqual(1, text.count(engine_identity.PLACEHOLDER))


if __name__ == '__main__':
    unittest.main()
