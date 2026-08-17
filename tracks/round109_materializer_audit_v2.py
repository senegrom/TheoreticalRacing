#!/usr/bin/env python3
"""Run the materializer audit with binary git-archive handling corrected."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

source = Path("tracks/round109_materializer_audit.py").read_text()
old = '''            raw = run([\n                "git", "archive", "--format=tar", f"origin/{BRANCH}", "tracks"\n            ]).stdout\n            # git archive is binary; rerun without text capture into a file.\n'''
new = '''            # git archive is binary; capture it directly into a file.\n'''
if source.count(old) != 1:
    raise SystemExit("materializer-audit archive anchor changed")
source = source.replace(old, new, 1)
with tempfile.TemporaryDirectory(prefix="round109-materializer-v2-") as directory:
    script = Path(directory) / "audit.py"
    script.write_text(source)
    result = subprocess.run([sys.executable, str(script)])
raise SystemExit(result.returncode)
