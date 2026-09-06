"""PNG/ICO integrity, opaque Apple exports and project-scoped declarations."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import struct
import unittest
from urllib.parse import urljoin, urlsplit
import zlib

WEB = Path(__file__).resolve().parents[1]
SITE = WEB / 'dist'


class Head(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.links = []; self.meta = {}; self.feed(text)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link': self.links.append(attrs)
        if tag == 'meta': self.meta[attrs.get('name')] = attrs.get('content')


def png(data):
    assert data.startswith(b'\x89PNG\r\n\x1a\n')
    offset = 8; compressed = bytearray(); width = height = None
    while offset < len(data):
        length = struct.unpack_from('>I', data, offset)[0]
        kind = data[offset+4:offset+8]; chunk = data[offset+8:offset+8+length]
        assert len(chunk) == length
        assert zlib.crc32(kind + chunk) == struct.unpack_from('>I', data, offset+8+length)[0]
        if kind == b'IHDR':
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', chunk)
            assert (depth, color, compression, filtering, interlace) == (8, 2, 0, 0, 0), 'PNG must be opaque RGB'
        if kind == b'IDAT': compressed.extend(chunk)
        offset += length + 12
        if kind == b'IEND': break
    assert offset == len(data)
    raw = zlib.decompress(compressed)
    assert len(raw) == (width * 3 + 1) * height
    assert all(raw[i * (width * 3 + 1)] <= 4 for i in range(height))
    return width, height


class IconTests(unittest.TestCase):
    def test_generated_assets_are_current_and_decodable(self):
        report = json.loads((SITE / 'icon-hashes.json').read_text())
        self.assertEqual(report['source'], hashlib.sha256((WEB / 'branding/racing-icon.svg').read_bytes()).hexdigest())
        expected = {'favicon-16x16.png': 16, 'favicon-32x32.png': 32, 'apple-touch-icon.png': 180,
                    'apple-touch-icon-152.png': 152, 'apple-touch-icon-167.png': 167,
                    'icons/racing-192.png': 192, 'icons/racing-512.png': 512, 'icons/racing-512-maskable.png': 512}
        aliases = {'icons/racing-tab-16-v3.png': 16, 'icons/racing-tab-32-v3.png': 32,
                   'icons/racing-apple-180-v3.png': 180, 'icons/racing-apple-152-v3.png': 152,
                   'icons/racing-apple-167-v3.png': 167, 'icons/racing-app-192-v3.png': 192,
                   'icons/racing-app-512-v3.png': 512, 'icons/racing-maskable-512-v3.png': 512}
        expected.update(aliases)
        self.assertEqual(set(report['files']), set(expected) | {'favicon.ico', 'icons/racing-favicon-v3.ico'})
        self.assertEqual((SITE / 'favicon.ico').read_bytes(), (SITE / 'icons/racing-favicon-v3.ico').read_bytes())
        for name, digest in report['files'].items():
            data = (SITE / name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest, name)
            if name in expected:
                self.assertEqual(png(data), (expected[name], expected[name]), name)
        ico = (SITE / 'favicon.ico').read_bytes()
        self.assertEqual(struct.unpack_from('<HHH', ico), (0, 1, 3))
        sizes = set()
        for i in range(3):
            width, height, _, _, _, _, length, offset = struct.unpack_from('<BBBBHHII', ico, 6 + 16 * i)
            self.assertEqual(png(ico[offset:offset+length]), (width, height))
            sizes.add((width, height))
        self.assertEqual(sizes, {(16, 16), (32, 32), (48, 48)})

    def test_apple_links_manifest_and_app_identity(self):
        head = Head((SITE / 'index.html').read_text())
        self.assertEqual(head.meta['apple-mobile-web-app-capable'], 'yes')
        self.assertEqual(head.meta['mobile-web-app-capable'], 'yes')
        self.assertEqual(head.meta['apple-mobile-web-app-title'], 'Racing')
        apple = [link for link in head.links if link.get('rel') == 'apple-touch-icon']
        self.assertEqual({link['sizes'] for link in apple}, {'152x152', '167x167', '180x180'})
        self.assertTrue(all('/racing-apple-' in link['href'] for link in apple))
        self.assertTrue(any(link.get('rel') == 'manifest' for link in head.links))
        manifest = json.loads((SITE / 'manifest.webmanifest').read_text())
        self.assertEqual(manifest['id'], '/TheoreticalRacing/')
        self.assertEqual(manifest['display'], 'standalone')
        self.assertEqual(manifest['start_url'], './')
        self.assertEqual(manifest['scope'], './')
        self.assertEqual({(i['sizes'], i['purpose']) for i in manifest['icons']},
                         {('192x192', 'any'), ('512x512', 'any'), ('512x512', 'maskable')})
        refs = [link['href'] for link in head.links if link.get('rel') in ('icon', 'apple-touch-icon', 'manifest')]
        refs += [icon['src'] for icon in manifest['icons']]
        for ref in refs:
            for base in ['https://senegrom.github.io/TheoreticalRacing/', 'https://test.invalid/preview/']:
                url = urljoin(base, ref)
                self.assertTrue(url.startswith(base), url)
                self.assertTrue((SITE / urlsplit(ref).path.removeprefix('./')).is_file(), ref)

    def test_maskable_corners_are_opaque_background(self):
        # RGB color type is checked above; verify exact corner pixel values too.
        # Pillow is already a pinned build dependency, not a runtime browser one.
        from PIL import Image
        with Image.open(SITE / 'icons/racing-512-maskable.png') as icon:
            for xy in [(0, 0), (511, 0), (0, 511), (511, 511)]:
                self.assertEqual(icon.getpixel(xy), (22, 62, 50))
            self.assertEqual(icon.mode, 'RGB')


if __name__ == '__main__':
    unittest.main()
