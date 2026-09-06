#!/usr/bin/env python3
"""Bind every published file to the tested build; reject missing or stale files."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = 'asset-manifest.json'
REQUIRED = {
    '.nojekyll', 'index.html', 'app.css', 'app.js', 'activity.js', 'board.js',
    'engine.js', 'runtime.js', 'runtime.html', 'racing.jar', 'tracks.json',
    'manifest.webmanifest', 'deployment.json', 'track-hashes.json',
    'engine-sources.json', 'icon-hashes.json', 'LICENSE.txt', 'favicon.ico',
    'icons/racing-apple-180-v3.png', 'icons/racing-app-192-v3.png',
    'icons/racing-app-512-v3.png', 'icons/racing-maskable-512-v3.png',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(directory):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('Artifact directory must be a real directory')
    result = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symlinks are not allowed in a Pages artifact: {path}')
        if path.is_file():
            name = path.relative_to(directory).as_posix()
            if name != MANIFEST:
                result[name] = digest(path)
        elif not path.is_dir():
            raise ValueError(f'Non-regular artifact entry: {path}')
    return result


def check_identity(source, repository):
    if not isinstance(source, str) or not re.fullmatch(r'[0-9a-f]{40}', source):
        raise ValueError('A complete expected commit SHA is required for publication')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid repository identity')


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def seal(directory, source, repository):
    # Local source archives without .git may build, but cannot claim a revision.
    if source is not None:
        check_identity(source, repository)
    write_json(directory / 'deployment.json', dict(source=source, repository=repository))
    write_json(directory / MANIFEST, dict(schema=1, source=source, repository=repository, files=files(directory)))


def verify(directory, source, repository):
    check_identity(source, repository)
    manifest = json.loads((directory / MANIFEST).read_text(encoding='utf-8'))
    if manifest.get('schema') != 1 or (manifest.get('source'), manifest.get('repository')) != (source, repository):
        raise ValueError('Artifact does not belong to the expected tested commit/repository')
    declared = manifest.get('files')
    if not isinstance(declared, dict) or not REQUIRED.issubset(declared):
        raise ValueError('Artifact manifest is incomplete')
    for name, sha in declared.items():
        if not isinstance(name, str) or '\\' in name or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:
            raise ValueError('Unsafe artifact path')
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{64}', sha):
            raise ValueError('Invalid artifact file digest')
    actual = files(directory)
    if actual != declared:
        missing = sorted(set(declared) - set(actual))
        extra = sorted(set(actual) - set(declared))
        changed = sorted(k for k in actual.keys() & declared.keys() if actual[k] != declared[k])
        raise ValueError(f'Artifact differs from tested files: missing={missing}, extra={extra}, changed={changed}')
    marker = json.loads((directory / 'deployment.json').read_text(encoding='utf-8'))
    if marker != dict(source=source, repository=repository):
        raise ValueError('Deployment marker does not identify the tested commit')
    # All bundled tracks and exported icons must be present, not just the entrypoint.
    tracks = json.loads((directory / 'track-hashes.json').read_text(encoding='utf-8'))
    icons = json.loads((directory / 'icon-hashes.json').read_text(encoding='utf-8'))['files']
    for name, sha in {**{'tracks/' + n: h for n, h in tracks.items()}, **icons}.items():
        if declared.get(name) != sha:
            raise ValueError(f'Missing or inconsistent track/icon: {name}')
    return manifest


def prepare(directory, source, repository):
    manifest = verify(directory, source, repository)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if head != source:
        raise ValueError('Source checkout does not match the tested artifact')
    archive = directory / 'source.tar.gz'
    if archive.exists():
        raise ValueError('Source archive must be created from the verified checkout, not reused')
    subprocess.run(['git', 'archive', '--format=tar.gz', f'--output={archive.resolve()}', source], cwd=ROOT, check=True)
    manifest['files']['source.tar.gz'] = digest(archive)
    write_json(directory / MANIFEST, manifest)
    verify(directory, source, repository)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['seal', 'verify', 'prepare'])
    parser.add_argument('directory', type=Path)
    parser.add_argument('--sha', default=os.environ.get('GITHUB_SHA'))
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY', 'senegrom/TheoreticalRacing'))
    args = parser.parse_args()
    if args.action == 'seal' and not args.sha:
        try:
            args.sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
        except subprocess.CalledProcessError:
            pass
    {'seal': seal, 'verify': verify, 'prepare': prepare}[args.action](args.directory, args.sha, args.repository)
    print(f'{args.action}: {args.directory} ({args.sha or "local, unversioned"})')


if __name__ == '__main__':
    main()
