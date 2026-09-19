import base64
import gzip
import hashlib
import os
from pathlib import Path
import subprocess

BASE = '720f421fc5c93795f9f0d4f14249b0c6898af7b8'
TREE = '1c37022fb3615e8c7c72f23bd96c91881b3cd57d'
PATCH = 'b1e9fc48934c03ec57776e8603ec1bd4035e1f0883f7714c3ee8be924c608655'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == BASE

def get(name):
    return subprocess.check_output(['git', 'show', os.environ['GITHUB_SHA'] + ':.github/chooser-policy/' + name])

first = get('part0')
first = first[:422] + get('part0-missing') + first[422:]
assert len(first) == 10000
assert hashlib.sha1(b'blob ' + str(len(first)).encode() + b'\0' + first).hexdigest() == '4012760bb6cc0886676a4748dc62a7e42bb56a5b'
encoded = first + b''.join(get('part' + str(i)) for i in range(1, 6))
assert len(encoded) == 57560
patch = gzip.decompress(base64.b64decode(encoded, validate=True))
assert len(patch) == 153368 and hashlib.sha256(patch).hexdigest() == PATCH
path = Path(os.environ['RUNNER_TEMP']) / 'chooser-policy.patch'
path.write_bytes(patch)
subprocess.run(['git', 'apply', '--index', str(path)], check=True)
actual = subprocess.check_output(['git', 'write-tree'], text=True).strip()
assert actual == TREE, (actual, TREE)
print('Applied exact source tree', actual, 'patch', PATCH)
