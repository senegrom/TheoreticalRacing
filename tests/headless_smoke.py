#!/usr/bin/env python3
"""Headless auto-play, batch memory recovery, and result-write failures."""

from pathlib import Path
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / "theoreticRacing.jar"


def run_solo(work: Path, seed: str, log: str, *, heap: str = "256m",
             cache: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["java", f"-Xms{heap}", f"-Xmx{heap}", "-XX:+UseSerialGC",
         "-XX:ActiveProcessorCount=1", "-Dtr.reachMemoBytes=0",
         "-jar", str(JAR), "--auto", "--track", "chicane",
         "--props", "solo.properties", "--seed", seed, "--log", log],
        cwd=work, capture_output=True, text=True, timeout=180,
        env=dict(os.environ, RACING_REACH_CACHE=str(cache or work / "reach-cache")),
    )


def check_batch_memory(work: Path) -> None:
    # With a disabled memo, each seed must allocate maps again. Before the fix,
    # discarded earlier races made the 64 MiB guard reject later seeds without a GC.
    batch = run_solo(work, "1-12", "batch.log", heap="64m")
    if batch.returncode != 0:
        raise SystemExit(f"low-memory batch failed\n{batch.stdout}\n{batch.stderr}")
    if "cache-hit" not in batch.stdout:
        raise SystemExit("batch did not exercise cached map loading")
    for seed in range(1, 13):
        single = run_solo(work, str(seed), "single.log", heap="64m")
        if single.returncode != 0:
            raise SystemExit(f"fresh seed {seed} failed\n{single.stdout}\n{single.stderr}")
        expected = (work / "single.log").read_bytes()
        actual = (work / f"batch_s{seed}.log").read_bytes()
        if b"# results" not in actual or b" FINISH " not in actual or actual != expected:
            raise SystemExit(f"batch seed {seed} differs from the complete fresh-JVM race")

    # An unavailable optional cache exercises the same guard on the compute
    # path, rather than only validating the disk-load preflight.
    unavailable_cache = work / "cache-is-a-file"
    unavailable_cache.write_text("not a directory", encoding="utf-8")
    uncached = run_solo(work, "1-12", "uncached.log", heap="64m", cache=unavailable_cache)
    if uncached.returncode != 0:
        raise SystemExit(f"uncached low-memory batch failed\n{uncached.stdout}\n{uncached.stderr}")
    for seed in range(1, 13):
        if (work / f"uncached_s{seed}.log").read_bytes() != (work / f"batch_s{seed}.log").read_bytes():
            raise SystemExit(f"uncached batch seed {seed} changed the race")

    insufficient = run_solo(work, "1", "insufficient.log", heap="16m")
    if insufficient.returncode == 0 or "Reachability needs roughly" not in insufficient.stderr:
        raise SystemExit(f"insufficient heap was not rejected clearly\n{insufficient.stdout}\n{insufficient.stderr}")
    if (work / "insufficient.log").exists():
        raise SystemExit("insufficient-memory run wrote a successful result")


def check_cache_generation(work: Path) -> None:
    cache = work / "migration-cache"
    first = run_solo(work, "1", "generation-first.log", cache=cache)
    namespace = cache / "maps-v2"
    if first.returncode != 0 or not namespace.is_dir():
        raise SystemExit(f"new cache generation failed\n{first.stdout}\n{first.stderr}")
    # Simulate checksum-valid files left by the former unversioned writer.
    old_files = {}
    for path in namespace.iterdir():
        old_files[path.name] = path.read_bytes()
        path.rename(cache / path.name)
    if not old_files:
        raise SystemExit("cache-generation test did not create any cached maps")
    namespace.rmdir()
    cold = run_solo(work, "1", "generation-cold.log", cache=cache)
    if cold.returncode != 0 or "cache-hit" in cold.stdout:
        raise SystemExit(f"unsafe generation was reused\n{cold.stdout}\n{cold.stderr}")
    warm = run_solo(work, "1", "generation-warm.log", cache=cache)
    if warm.returncode != 0 or "cache-hit" not in warm.stdout:
        raise SystemExit(f"new-generation warm cache failed\n{warm.stdout}\n{warm.stderr}")
    expected = (work / "generation-first.log").read_bytes()
    for name in ("generation-cold.log", "generation-warm.log"):
        if (work / name).read_bytes() != expected:
            raise SystemExit("cache generation changed the race")
    if any((cache / name).read_bytes() != data for name, data in old_files.items()):
        raise SystemExit("migration modified old cache evidence")
    print("HeadlessSmoke: old map generation ignored; fresh cold/warm logs identical")



def check_log_failures(work: Path) -> None:
    # A regular file as the parent fails consistently, even when CI runs as root.
    (work / "blocked").write_text("not a directory", encoding="utf-8")
    for seed in ("1", "1-2"):
        failed = run_solo(work, seed, "blocked/race.log")
        if failed.returncode != 3 or failed.stdout.count("Could not write log") != 1:
            raise SystemExit(f"log failure was not propagated once for {seed}\n{failed.stdout}\n{failed.stderr}")
    if (work / "blocked/race.log").exists():
        raise SystemExit("failed log-write fixture unexpectedly created a result")


def main() -> int:
    if not JAR.is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    with tempfile.TemporaryDirectory(prefix="theoretical-racing-headless-") as directory:
        work = Path(directory)
        (work / "solo.properties").write_text(
            "nPlayers=1\nplayer1Kind=AI2\nlaps=1\naiStartPlacement=legacy\n",
            encoding="utf-8",
        )
        shutil.copyfile(ROOT / "tracks" / "bench.properties", work / "bench.properties")
        result = subprocess.run(
            [
                "java",
                "-jar",
                str(JAR),
                "--auto",
                "--track",
                "chicane",
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
            raise SystemExit("headless race did not produce the expected complete chicane result")

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
                "chicane",
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
        check_cache_generation(work)
        check_log_failures(work)
        check_batch_memory(work)
    print("HeadlessSmoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
