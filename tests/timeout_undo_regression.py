#!/usr/bin/env python3
"""Exercise interactive Undo in the shared engine with its non-modal browser adapter."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True, timeout=180)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="racing-timeout-undo-") as tmp:
        work = Path(tmp)
        run(sys.executable, str(ROOT / "web/scripts/prepare_sources.py"), str(work / "src"))
        sources = sorted((work / "src").rglob("*.java"))
        sources.extend(ROOT / "tests/tr/logic" / name for name in
                       ("LifecycleTestSupport.java", "TimeoutUndoTests.java"))
        # Use an argument file so the command also works with Windows path limits.
        args = work / "sources.txt"
        args.write_text("".join('"' + str(p).replace('\\', '/') + '"\n' for p in sources), encoding="utf-8")
        run("javac", "--release", "17", "-encoding", "UTF-8", "-Xlint:all", "-Werror",
            "-d", str(work / "classes"), "@" + str(args))
        env = os.environ.copy()
        env["RACING_REACH_CACHE"] = str(work / "cache")
        subprocess.run(["java", "-ea", "-Djava.awt.headless=true", "-cp", str(work / "classes"),
                        "tr.logic.TimeoutUndoTests"], cwd=ROOT, env=env, check=True, timeout=180)


if __name__ == "__main__":
    main()
