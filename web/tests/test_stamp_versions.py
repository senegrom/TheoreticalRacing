import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import stamp_versions  # noqa: E402


def short(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


class StampVersionsTests(unittest.TestCase):
    def build(self, root, leaf='export const x = 1;\n'):
        (root / 'runtime.js').write_text(leaf, encoding='utf-8')
        (root / 'engine.js').write_text("new URL('./runtime.js?v=6', import.meta.url);\n", encoding='utf-8')
        (root / 'app.js').write_text("import {E} from './engine.js?v=6';\n", encoding='utf-8')
        (root / 'app.css').write_text('body {}\n', encoding='utf-8')
        (root / 'index.html').write_text('<link href="./app.css?v=8"><script src="./app.js?v=7"></script>\n',
                                         encoding='utf-8')
        stamp_versions.stamp(root)

    def test_every_reference_carries_its_targets_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.build(root)
            self.assertIn('runtime.js?v=' + short(root / 'runtime.js'), (root / 'engine.js').read_text())
            self.assertIn('engine.js?v=' + short(root / 'engine.js'), (root / 'app.js').read_text())
            index = (root / 'index.html').read_text()
            self.assertIn('app.js?v=' + short(root / 'app.js'), index)
            self.assertIn('app.css?v=' + short(root / 'app.css'), index)

    def test_a_changed_leaf_reaches_the_page(self):
        pages = []
        for leaf in ('export const x = 1;\n', 'export const x = 2;\n'):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.build(root, leaf)
                pages.append((root / 'index.html').read_text())
        self.assertNotEqual(pages[0], pages[1])

    def test_an_unpublished_reference_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'app.js').write_text("import './missing.js?v=1';\n", encoding='utf-8')
            with self.assertRaises(ValueError):
                stamp_versions.stamp(root)


if __name__ == '__main__':
    unittest.main()
