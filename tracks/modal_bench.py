#!/usr/bin/env python3
"""Fan the lap bench out over Modal: one container per track, all seeds in one JVM.

The unit is a batch race (`--seed A-B`), which builds the track's reachability
once and reuses it in-process, so a container costs one BFS plus N races. The
jar and tracks/ ride in the image (they are ~0.5 MB together); the properties
file travels as a string argument, so one image serves every bench shape.

    modal run tracks/modal_bench.py --seeds 1-5 --tracks rand2,rand19 --verify
    modal run tracks/modal_bench.py --seeds 1-10 --out E:/tmp/fleet.txt

Determinism is the whole basis of the instrument, so --verify races a few
(track, seed) pairs and prints the SHA-256 of each log for comparison with the
local ones; --logs-dir writes the raw logs back for a byte-for-byte diff.

Cost: a 73-track x 10-seed grid is roughly 2-3 core-hours, i.e. cents. The
containers are CPU-only and exit as soon as their batch is done.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess

import modal

ROOT = pathlib.Path(__file__).resolve().parent.parent
JAR = ROOT / "theoreticRacing.jar"
TRACKS = ROOT / "tracks"
REMOTE = "/opt/tr"

# Java 25 bytecode: the JRE must be 25 or newer. Pinned so a bench months
# apart is still comparable -- a different JVM is a different instrument.
image = (
    modal.Image.from_registry("eclipse-temurin:25-jre", add_python="3.12")
    .add_local_file(JAR, f"{REMOTE}/theoreticRacing.jar", copy=True)
    .add_local_dir(
        TRACKS,
        f"{REMOTE}/tracks",
        copy=True,
        # the jar resolves tracks/ next to itself; only the data belongs there
        ignore=lambda p: p.suffix != ".track",
    )
)

app = modal.App("tr-lap-bench", image=image)


# 8 GB / -Xmx6g is sized for the biggest board in the fleet: the Nordschleife's
# 89M states carry ~2.5 GB of arrays (three gate maps alone are 1.1 GB) and it
# died with OutOfMemoryError at -Xmx3g. Memory is the cheap axis here.
@app.function(cpu=1.0, memory=8192, timeout=3600, max_containers=80, retries=1)
def race_batch(track: str, seeds: str, props: str, want_logs: bool = False) -> dict:
    """Race one track over a seed range; return per-seed outcomes (+ optional logs)."""
    import os
    import re

    work = pathlib.Path("/tmp/work")
    work.mkdir(parents=True, exist_ok=True)
    props_path = work / "bench.properties"
    props_path.write_text(props, encoding="utf-8")
    env = dict(os.environ, RACING_REACH_CACHE="/tmp/reach")

    proc = subprocess.run(
        [
            "java", "-Xmx6g", "-Djava.awt.headless=true",
            "-jar", f"{REMOTE}/theoreticRacing.jar",
            "--auto", "--track", track,
            "--props", str(props_path),
            "--log", str(work / f"{track}.log"),
            "--seed", seeds,
        ],
        capture_output=True, text=True, env=env, check=False,
    )
    first, _, last = seeds.partition("-")
    lo = int(first)
    hi = int(last) if last else lo
    move = re.compile(r"^\d+ p\d ")
    out: dict = {"track": track, "returncode": proc.returncode, "races": {}}
    if "laps disabled" in proc.stdout:
        out["noloop"] = True
    for seed in range(lo, hi + 1):
        log = work / f"{track}_s{seed}.log"
        if not log.exists():
            out["races"][seed] = {"missing": True}
            continue
        text = log.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        row = {
            "fin": sum(1 for line in lines if "FINISH" in line),
            "crash": sum(1 for line in lines if "CRASH" in line),
            "timeout": sum(1 for line in lines if "TIMEOUT" in line),
            "moves": sum(1 for line in lines if move.match(line)),
            "sha": hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16],
        }
        if want_logs:
            row["log"] = text
        out["races"][seed] = row
    if proc.returncode != 0:
        out["stderr"] = proc.stderr[-2000:]
    return out


def _all_tracks() -> list[str]:
    """Every track in the fleet. Lap-readiness is not a file flag -- the game
    decides it per track when it places the gates, and a track whose boundary
    is too coarse reports NOLOOP from the container itself."""
    return sorted(path.stem for path in TRACKS.glob("*.track"))


@app.local_entrypoint()
def main(
    seeds: str = "1-5",
    tracks: str = "",
    props: str = "",
    out: str = "",
    logs_dir: str = "",
    want_logs: bool = False,
) -> None:
    names = [t.strip() for t in tracks.split(",") if t.strip()] or _all_tracks()
    props_text = (
        pathlib.Path(props).read_text(encoding="utf-8")
        if props else (TRACKS / "lap_bench.properties").read_text(encoding="utf-8")
    )
    want = want_logs or bool(logs_dir)
    print(f"{len(names)} tracks x seeds {seeds}")

    rows: list[str] = []
    totals = {"fin": 0, "crash": 0, "timeout": 0, "moves": 0, "races": 0}
    results = race_batch.starmap(
        [(t, seeds, props_text, want) for t in names], order_outputs=True
    )
    for name, res in zip(names, results):
        if res.get("noloop"):
            rows.append(f"{name} NOLOOP")
            continue
        for seed, row in sorted(res["races"].items(), key=lambda kv: int(kv[0])):
            if row.get("missing"):
                rows.append(f"{name} {seed} MISSING")
                continue
            rows.append(
                f"{name} {seed} fin={row['fin']} crash={row['crash']}"
                f" timeout={row['timeout']} moves={row['moves']} sha={row['sha']}"
            )
            for key in ("fin", "crash", "timeout", "moves"):
                totals[key] += row[key]
            totals["races"] += 1
            if logs_dir:
                target = pathlib.Path(logs_dir) / f"{name}_s{seed}.log"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(row["log"], encoding="utf-8", newline="")
        if res["returncode"] != 0:
            rows.append(f"{name} EXIT {res['returncode']} {res.get('stderr', '')[:200]}")

    body = "\n".join(rows)
    print(body)
    print(
        f"\nTOTAL races={totals['races']} fin={totals['fin']}"
        f" crash={totals['crash']} timeout={totals['timeout']} moves={totals['moves']}"
    )
    if out:
        pathlib.Path(out).write_text(body + "\n", encoding="utf-8")
        print(f"wrote {out}")
