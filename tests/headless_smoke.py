#!/usr/bin/env python3
"""End-to-end smoke test for genuine headless auto-play and relative log paths."""

from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / "theoreticRacing.jar"


def main() -> int:
    if not JAR.is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    with tempfile.TemporaryDirectory(prefix="theoretical-racing-headless-") as directory:
        work = Path(directory)
        shutil.copyfile(ROOT / "tracks" / "bench.properties", work / "bench.properties")
        result = subprocess.run(
            [
                "java",
                "-jar",
                str(JAR),
                "--auto",
                "--track",
                "sprint",
                "--props",
                "bench.properties",
                "--log",
                "race.log",
                "--seed",
                "1",
            ],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise SystemExit(f"headless race failed ({result.returncode})\n{result.stdout}\n{result.stderr}")
        log = (work / "race.log").read_text(encoding="utf-8")
        if "# results" not in log or log.count(" FINISH ") != 7 or " CRASH " in log:
            raise SystemExit("headless race did not produce the expected complete sprint result")
    print("HeadlessSmoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
