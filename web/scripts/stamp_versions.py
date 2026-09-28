#!/usr/bin/env python3
"""Stamp every ?v= cache-buster in a built site with its target's content hash.

    python3 web/scripts/stamp_versions.py web/dist

The sources carry the placeholder ?v=0 (a hand-bumped number let a returning
browser pair a cached old module with a new one; review, 2026-09-27). Each
reference NAME?v=... in a published .html, .js, .css, .webmanifest or .json
file becomes NAME?v=<first 12 hex of sha256(NAME)>; tracks.json too, since
2026-09-28 (a cached catalogue could name courses the new jar lacks).
Files are stamped leaves first, so a module's hash covers the stamps of the
modules it imports, and a change anywhere below reaches index.html.
"""
import hashlib
import re
import sys
from pathlib import Path

REFERENCE = re.compile(r'([A-Za-z0-9_.-]+\.(?:js|css|html|webmanifest|json))\?v=[A-Za-z0-9]+')
TEXT = ('.html', '.js', '.css', '.webmanifest', '.json')


def references(text):
    return {m.group(1) for m in REFERENCE.finditer(text)}


def stamp(root):
    root = Path(root)
    pages = {p.name: p for p in root.iterdir() if p.is_file() and p.suffix in TEXT}
    order, state = [], {}

    def visit(name, chain):
        if state.get(name) == 'done':
            return
        if state.get(name) == 'open':
            raise ValueError('cache-buster cycle: ' + ' -> '.join(chain + [name]))
        state[name] = 'open'
        for ref in sorted(references(pages[name].read_text(encoding='utf-8'))):
            if ref not in pages:
                raise ValueError(f'{name} references {ref}, which is not published')
            visit(ref, chain + [name])
        state[name] = 'done'
        order.append(name)

    for name in sorted(pages):
        visit(name, [])
    for name in order:
        path = pages[name]
        text = path.read_bytes().decode('utf-8')  # bytes: line endings stay as built
        stamped = REFERENCE.sub(
            lambda m: m.group(1) + '?v=' + hashlib.sha256(pages[m.group(1)].read_bytes()).hexdigest()[:12],
            text)
        if stamped != text:
            path.write_bytes(stamped.encode('utf-8'))
    return order


if __name__ == '__main__':
    stamp(sys.argv[1])
