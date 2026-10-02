from pathlib import Path
import subprocess
master='b54e9bb05f91c0011e8d5e82178d1d13f3c1b494'
expected=subprocess.check_output(['git','show',master+':src/tr/logic/StartPlacement.java'])
assert Path('src/tr/logic/StartPlacement.java').read_bytes()==expected
assert 'START_TIES' not in Path('src/tr/logic/RacecraftNext.java').read_text()
# Workflow changes are installed through the authorized connector, not generated
# by the source assembly job. Its token needs contents permission only.
subprocess.run(['git','diff','--exit-code','HEAD','--','.github/workflows/racecraft-next.yml'],check=True)
print('Owner computed-start implementation preserved; validation workflow already installed.')
