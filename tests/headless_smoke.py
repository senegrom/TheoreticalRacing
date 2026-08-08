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

        invalid_props = work / "human.properties"
        invalid_props.write_text(
            (work / "bench.properties").read_text(encoding="utf-8").replace(
                "player1Kind=AI1", "player1Kind=HUMAN", 1
            ),
            encoding="utf-8",
        )
        invalid = subprocess.run(
            [
                "java",
                "-jar",
                str(JAR),
                "--auto",
                "--track",
                "sprint",
                "--props",
                invalid_props.name,
                "--log",
                "invalid.log",
                "--seed",
                "1",
            ],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if invalid.returncode == 0:
            raise SystemExit("invalid human auto-race configuration unexpectedly succeeded")
        if "--auto requires every configured player to be AI" not in invalid.stderr:
            raise SystemExit(
                f"invalid auto-race failed unclearly:\n{invalid.stdout}\n{invalid.stderr}"
            )

        narrow_text = (work / "bench.properties").read_text(encoding="utf-8")
        replacements = {
            "gameX=86": "gameX=20",
            "gameY=48": "gameY=25",
            "useLastTrack=false": "useLastTrack=true",
        }
        for old, new in replacements.items():
            narrow_text = narrow_text.replace(old, new, 1)
        narrow_text += "lastTrackLeft=5,20;5,3\nlastTrackRight=6,20;6,3\n"
        narrow_props = work / "narrow.properties"
        narrow_props.write_text(narrow_text, encoding="utf-8")
        narrow = subprocess.run(
            [
                "java",
                "-jar",
                str(JAR),
                "--auto",
                "--props",
                narrow_props.name,
                "--log",
                "narrow.log",
                "--seed",
                "1",
            ],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if narrow.returncode == 0:
            raise SystemExit("insufficient-start-grid auto race unexpectedly succeeded")
        if "couldn't find a start position" not in narrow.stderr:
            raise SystemExit(
                f"insufficient-start-grid auto race failed unclearly:\n{narrow.stdout}\n{narrow.stderr}"
            )
    print("HeadlessSmoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
