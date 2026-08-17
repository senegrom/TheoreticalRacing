#!/usr/bin/env python3
"""Run the Round-109 branch audit and normalize matrix artifact names."""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys

branch = os.environ["AUDIT_BRANCH"]
slug = os.environ["AUDIT_SLUG"]
derived = re.sub(r"[^A-Za-z0-9_.-]+", "-", branch).strip("-")

result = subprocess.run([sys.executable, "tracks/round109_audit.py"])
for suffix in ("json", "patch"):
    source = Path(f"round109-audit-{derived}.{suffix}")
    destination = Path(f"round109-audit-{slug}.{suffix}")
    if source.exists():
        source.replace(destination)
raise SystemExit(result.returncode)
