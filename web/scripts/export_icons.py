#!/usr/bin/env python3
"""Export one authored racing illustration to tabs and installed-app icons.

Build dependencies: web/requirements-icons.txt. The build emits every PNG/ICO
from this editable SVG, so source and deployed icons cannot silently diverge.
"""
import argparse
import hashlib
import io
import json
import shutil
from pathlib import Path
from PIL import Image
import cairosvg

WEB = Path(__file__).resolve().parents[1]
SOURCE = WEB / 'branding/racing-icon.svg'
SIZES = {'favicon-16x16.png': 16, 'favicon-32x32.png': 32,
         'apple-touch-icon.png': 180, 'apple-touch-icon-152.png': 152,
         'apple-touch-icon-167.png': 167, 'icons/racing-192.png': 192,
         'icons/racing-512.png': 512}


def export(output):
    svg = SOURCE.read_bytes()
    master = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg, output_width=1024, output_height=1024))).convert('RGB')
    output.mkdir(parents=True, exist_ok=True)
    for name, size in SIZES.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        master.resize((size, size), Image.Resampling.LANCZOS).save(path, optimize=True)
    master.save(output / 'favicon.ico', format='ICO', sizes=[(16, 16), (32, 32), (48, 48)])
    # Full master, not just the car, stays within the central safe circle.
    # 280 * sqrt(2) / 2 < 512 * .4. The system supplies the outer mask.
    mask = Image.new('RGB', (512, 512), '#163e32')
    mask.paste(master.resize((280, 280), Image.Resampling.LANCZOS), (116, 116))
    mask.save(output / 'icons/racing-512-maskable.png', optimize=True)
    files = [*SIZES, 'icons/racing-512-maskable.png', 'favicon.ico']
    # Distinct physical URLs (not only query strings) avoid reusing old
    # Home Screen/tab icon requests on the shared github.io origin.
    aliases = {
        'favicon.ico': 'icons/racing-favicon-v3.ico',
        'favicon-16x16.png': 'icons/racing-tab-16-v3.png',
        'favicon-32x32.png': 'icons/racing-tab-32-v3.png',
        'apple-touch-icon.png': 'icons/racing-apple-180-v3.png',
        'apple-touch-icon-152.png': 'icons/racing-apple-152-v3.png',
        'apple-touch-icon-167.png': 'icons/racing-apple-167-v3.png',
        'icons/racing-192.png': 'icons/racing-app-192-v3.png',
        'icons/racing-512.png': 'icons/racing-app-512-v3.png',
        'icons/racing-512-maskable.png': 'icons/racing-maskable-512-v3.png',
    }
    for source, target in aliases.items():
        shutil.copyfile(output / source, output / target)
        files.append(target)
    report = {'source': hashlib.sha256(svg).hexdigest(),
              'files': {n: hashlib.sha256((output / n).read_bytes()).hexdigest() for n in files}}
    (output / 'icon-hashes.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Exported opaque racing icons:', ', '.join(files))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=WEB / 'build/icons')
    export(parser.parse_args().output)
