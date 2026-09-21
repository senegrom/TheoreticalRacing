import gzip
import hashlib
from pathlib import Path
import os
import subprocess

base = '446affe53f8ff689bb53f52ca2e0c054c1c82080'
if subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() != base:
    raise SystemExit('Unexpected source base')
compressed = b''.join(subprocess.check_output(['git', 'show', os.environ['GITHUB_SHA'] + f':.github/contingent-payload/part{i}']) for i in range(4))
patch = gzip.decompress(compressed)
if hashlib.sha256(patch).hexdigest() != 'ba6b7a1c26280b440234cdde79f7512c8d38a6ca74eade34a891fddd3dd93501':
    raise SystemExit('Patch identity mismatch')
subprocess.run(['git', 'apply', '--index', '-'], input=patch, check=True)
if subprocess.check_output(['git', 'write-tree'], text=True).strip() != '90572ac892dda3a56d7663af7973610a563b254f':
    raise SystemExit('Original patch tree mismatch')
p = Path('.github/workflows/contingent-prefix.yml')
p.write_text(p.read_text().replace('RACING_REACH_CACHE: $' + '{{ runner.temp }}', 'RACING_REACH_CACHE: /tmp'))
subprocess.run(['git', 'add', str(p)], check=True)
expected = '3c237f54a610e33efe9a67c1dbac4f7133ba70bc'
if subprocess.check_output(['git', 'write-tree'], text=True).strip() != expected:
    raise SystemExit('Corrected workflow/source tree mismatch')
print('Verified tested tree', expected)
