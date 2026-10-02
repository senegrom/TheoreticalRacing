#!/usr/bin/env python3
"""Give one browser build one engine identity: in the jar and in its worker.

    python3 web/scripts/engine_identity.py record SRC_DIR CLASSES_DIR
    python3 web/scripts/engine_identity.py stamp CLASSES_DIR RUNTIME_JS

record hashes every .java file under SRC_DIR (sorted by path; path and bytes)
and writes the digest to CLASSES_DIR/tr/browser/engine-build.txt, before the
jar is made. stamp writes that digest into runtime.js's ENGINE_BUILD
placeholder, and the jar's published name, racing-<first 12 hex>.jar, into
its ENGINE_JAR one; build.sh publishes the jar under that name too. The
worker compares the two identities before its first race: for a few minutes
after a deploy a browser cache could pair a page with the jar of another
deploy under the old fixed name (review, 2026-09-28), and a page never names
another build's jar now (review, 2026-09-29).
"""
import hashlib
import sys
from pathlib import Path

RESOURCE = Path('tr/browser/engine-build.txt')
PLACEHOLDER = "'__ENGINE_BUILD__'"
JAR_PLACEHOLDER = "'__ENGINE_JAR__'"


def jar_name(identity):
    return 'racing-' + identity[:12] + '.jar'


def digest(src):
    src = Path(src)
    h = hashlib.sha256()
    for path in sorted(src.rglob('*.java'), key=lambda p: p.relative_to(src).as_posix()):
        name = path.relative_to(src).as_posix().encode('utf-8')
        body = path.read_bytes()
        h.update(len(name).to_bytes(4, 'big') + name + len(body).to_bytes(8, 'big') + body)
    return h.hexdigest()


def record(src, classes):
    identity = digest(src)
    target = Path(classes) / RESOURCE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(identity.encode('ascii') + b'\n')
    return identity


def stamp(classes, runtime):
    identity = (Path(classes) / RESOURCE).read_bytes().decode('ascii').strip()
    runtime = Path(runtime)
    text = runtime.read_bytes().decode('utf-8')
    if text.count(PLACEHOLDER) != 1 or text.count(JAR_PLACEHOLDER) != 1:
        raise ValueError(f'{runtime} must hold each engine placeholder exactly once')
    text = text.replace(PLACEHOLDER, "'" + identity + "'")
    runtime.write_bytes(text.replace(JAR_PLACEHOLDER, "'" + jar_name(identity) + "'").encode('utf-8'))
    return identity


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] not in ('record', 'stamp'):
        raise SystemExit(__doc__)
    print((record if sys.argv[1] == 'record' else stamp)(sys.argv[2], sys.argv[3]))
