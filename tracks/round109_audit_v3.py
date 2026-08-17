#!/usr/bin/env python3
"""Run the Round-109 branch audit with seed-log discovery corrected."""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

branch = os.environ["AUDIT_BRANCH"]
slug = os.environ["AUDIT_SLUG"]
derived = re.sub(r"[^A-Za-z0-9_.-]+", "-", branch).strip("-")
source = Path("tracks/round109_audit.py").read_text()
old = '''        return parse_log(log)\n'''
new = '''        candidates = []
        for candidate in tmp.glob("*.log"):
            try:
                if "# results" in candidate.read_text(errors="replace"):
                    candidates.append(candidate)
            except OSError:
                pass
        if not candidates:
            raise RuntimeError(f"no valid race log for {label} {track} seed {seed} in {tmp}")
        actual_log = max(candidates, key=lambda candidate: candidate.stat().st_mtime_ns)
        return parse_log(actual_log)
'''
if source.count(old) != 1:
    raise SystemExit("branch-audit log anchor changed")
source = source.replace(old, new, 1)
with tempfile.TemporaryDirectory(prefix="round109-audit-v3-") as directory:
    script = Path(directory) / "audit.py"
    script.write_text(source)
    result = subprocess.run([sys.executable, str(script)])
for suffix in ("json", "patch"):
    original = Path(f"round109-audit-{derived}.{suffix}")
    normalized = Path(f"round109-audit-{slug}.{suffix}")
    if original.exists():
        original.replace(normalized)
raise SystemExit(result.returncode)
