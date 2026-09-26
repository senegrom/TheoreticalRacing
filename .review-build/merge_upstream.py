"""Merge the observed concurrent master update without discarding either journal.
Unexpected code conflicts stop for explicit review; never choose a whole code file.
"""
from pathlib import Path
import subprocess

UPSTREAM = '1dc7b65f76c72bf78c7ce67732a4cdc29b5f3e4f'
ROOT = Path(__file__).resolve().parents[1]

def git(*args, check=True):
    return subprocess.run(['git', *args], cwd=ROOT, check=check, capture_output=True, text=True)

if git('merge-base', '--is-ancestor', UPSTREAM, 'HEAD', check=False).returncode == 0:
    raise SystemExit(0)

journal = (ROOT / 'racing-memory.md').read_text(encoding='utf-8')
start = journal.index('## Review branch, 2026-09-26:')
end = journal.index('\n## Round 278:', start)
entry = journal[start:end].strip()
entry = entry.replace('Baseline: `31bf6b986b669831a4ebc0b9d87cac5adb711a96` (round 278). NOT a promotion.',
    'Reviewed at `31bf6b986b669831a4ebc0b9d87cac5adb711a96` (round 278); integrated with\n'
    'the concurrent round-279 promotion `1dc7b65f76c72bf78c7ce67732a4cdc29b5f3e4f`.\n'
    'NOT a promotion. The round-279 owner rules and measured corpus are retained.')
result = git('merge', '--no-commit', '--no-ff', UPSTREAM, check=False)
print(result.stdout, result.stderr, flush=True)
conflicts = git('diff', '--name-only', '--diff-filter=U').stdout.splitlines()
for path in conflicts:
    if path != 'racing-memory.md':
        text = (ROOT / path).read_text(encoding='utf-8')
        print('UNEXPECTED CONFLICT:', path, flush=True)
        active = False
        for line in text.splitlines():
            if line.startswith('<<<<<<<'): active = True
            if active: print(line, flush=True)
            if line.startswith('>>>>>>>'): active = False
        raise RuntimeError('code conflict requires explicit review: ' + path)
if result.returncode != 0 and not conflicts:
    raise RuntimeError('merge failed without a resolvable journal conflict')
upstream_journal = git('show', UPSTREAM + ':racing-memory.md').stdout
heading, body = upstream_journal.split('\n', 1)
(ROOT / 'racing-memory.md').write_text(heading + '\n\n' + entry + '\n' + body, encoding='utf-8')
git('add', 'racing-memory.md')
p = ROOT / 'docs/experiments/racecraft-review/README.md'
text = p.read_text(encoding='utf-8')
text = text.replace('Baseline: `31bf6b986b669831a4ebc0b9d87cac5adb711a96` (round 278).',
    'Originally reviewed at `31bf6b986b669831a4ebc0b9d87cac5adb711a96` (round 278).\n'
    'Integration baseline: `1dc7b65f76c72bf78c7ce67732a4cdc29b5f3e4f` (round 279),\n'
    'which reached master during the review implementation. Its promoted fixes,\n'
    'owner rules and measured golden/pin updates are preserved, not reimplemented.')
p.write_text(text, encoding='utf-8')
git('diff', '--check')
