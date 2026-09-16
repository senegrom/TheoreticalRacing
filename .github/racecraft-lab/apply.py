import base64, gzip, hashlib, os, subprocess
from pathlib import Path
expected = ['de43fd817f5c16276d63f91d664e3bf49bb619b7','031d7d404c9ef2765bf6bc1383a8d087aeb94942','1b26fe41bae4da03309119f3ef76c48fa10337db','e9288736970dfa0134fbc78350a3ec8340b26b5a','9a6e83a0ca119762f43e8f4cd5940453cdda418e','823a94839b914505fccc706d956653e9d8f3d08a','8e9a091b37b08af7a776ca3c08c651da70e9dfad','7a0c7a1c1bd02795f648c5bc824303f40a66f88c']
parts=[]
for i,sha in enumerate(expected):
    b=subprocess.check_output(['git','show',os.environ['GITHUB_SHA']+':.github/racecraft-lab/patch.gz.'+str(i)])
    if i == 4:
        # Correct a known one-character transport transcription; verify the
        # complete reconstructed object below, not just this substitution.
        s=base64.b64encode(b).decode().replace('M1i35r9V9Vfg6LWq','M1i35r9V/vg6LWq').rstrip('=')
        b=base64.b64decode(s+'='*(-len(s)%4),validate=True)
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==sha, i
    parts.append(b)
patch=gzip.decompress(b''.join(parts))
assert hashlib.sha256(patch).hexdigest()=='ebaa379e99640760bc9ffa4e568798bbdd1196fc58a3cc929867e8b0dcd2abeb'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='614fef76564b3e6d4fcdd78a7d378483c5fa61f0'
p=Path(os.environ['RUNNER_TEMP'])/'racecraft-lab.patch';p.write_bytes(patch)
subprocess.run(['git','apply','--index',str(p)],check=True)
assert subprocess.check_output(['git','write-tree'],text=True).strip()=='3dc11f541b54d45d7819eeea465fc9bb94582ebe'
print('Verified exact experiment tree 3dc11f541b54d45d7819eeea465fc9bb94582ebe')
