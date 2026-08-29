#!/usr/bin/env python3
"""Verify a small deterministic AI2 race corpus against normalized log hashes.

The suite is intentionally much smaller than the promotion battery. It catches
changes to physics, turn ordering, reachability, collision handling and the
frozen AI2 policy in a few minutes on CI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

FIXTURE = ROOT / "tests" / "golden_races.json"
SPECS = [
    {"name": "hairpin-s10-8p", "track": "hairpin", "seed": 10, "players": 8},
    {"name": "zigzag-s4-8p", "track": "zigzag", "seed": 4, "players": 8},
    {"name": "hungaroring-s13-8p", "track": "hungaroring", "seed": 13, "players": 8},
    {"name": "lemans-s4-8p", "track": "lemans", "seed": 4, "players": 8},
    {"name": "hairpin-s1-2p", "track": "hairpin", "seed": 1, "players": 2},
    {"name": "monaco-s9-4p", "track": "monaco", "seed": 9, "players": 4},
    {"name": "monaco-s16-8p", "track": "monaco", "seed": 16, "players": 8},
    {"name": "nurburgring-s19-8p", "track": "nurburgring", "seed": 19, "players": 8},
    {"name": "interlagos-s10-8p", "track": "interlagos", "seed": 10, "players": 8},
    {"name": "zigzag-s22-8p", "track": "zigzag", "seed": 22, "players": 8},
    {"name": "zandvoort-s45-8p", "track": "zandvoort", "seed": 45, "players": 8},
    {"name": "lemans-s1-4p", "track": "lemans", "seed": 1, "players": 4},
]


def normalized_log(text: str) -> str:
    """Keep behavior-bearing turn/result lines and normalize line endings."""
    lines = []
    in_results = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if re.match(r"^\d+ p\d+ ", line):
            lines.append(line)
        elif line == "# results":
            in_results = True
            lines.append(line)
        elif in_results and re.match(r"^\d+\. ", line):
            lines.append(line)
    return "\n".join(lines) + "\n"


def summarize(text: str) -> dict[str, object]:
    turns = finishes = crashes = 0
    results: list[str] = []
    in_results = False
    for line in text.splitlines():
        if re.match(r"^\d+ p\d+ ", line):
            turns += 1
            finishes += " FINISH " in line
            crashes += " CRASH " in line
        elif line == "# results":
            in_results = True
        elif in_results:
            match = re.match(r"^\d+\. (.*)$", line)
            if match:
                results.append(match.group(1))
    return {"turns": turns, "finishes": finishes, "crashes": crashes, "results": results}


def run_case(spec: dict[str, object]) -> dict[str, object]:
    bench_ai.set_nplayers(int(spec["players"]))
    bench_ai.set_all_to("AI2")
    result = bench_ai.run_track(str(spec["track"]), timeout=600, seed=int(spec["seed"]))
    if result is None:
        raise RuntimeError(f"{spec['name']}: race failed or produced no complete log")
    text = Path(bench_ai.LOG).read_text(encoding="utf-8")
    normalized = normalized_log(text)
    return {
        "sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        "summary": summarize(text),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", action="store_true", help="replace the committed fixture with current AI2 results")
    parser.add_argument("--case", action="append", default=[], help="run only the named case (repeatable)")
    args = parser.parse_args()

    selected = [spec for spec in SPECS if not args.case or spec["name"] in args.case]
    unknown = sorted(set(args.case) - {str(spec["name"]) for spec in SPECS})
    if unknown:
        parser.error("unknown case(s): " + ", ".join(unknown))
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    expected = {}
    if FIXTURE.is_file():
        expected = {case["name"]: case for case in json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]}
    elif not args.update:
        raise SystemExit(f"missing fixture: {FIXTURE}")

    actual_cases = []
    failures = 0
    with tempfile.TemporaryDirectory(prefix="theoretical-racing-golden-") as directory:
        bench_ai.configure_runtime(directory)
        for spec in selected:
            actual = run_case(spec)
            record = {**spec, **actual}
            actual_cases.append(record)
            prior = expected.get(str(spec["name"]))
            if args.update:
                print(f"{spec['name']}: {actual['sha256']} {actual['summary']}")
            elif prior is None:
                failures += 1
                print(f"{spec['name']}: missing expected fixture", file=sys.stderr)
            elif prior["sha256"] != actual["sha256"] or prior["summary"] != actual["summary"]:
                failures += 1
                print(f"{spec['name']}: GOLDEN MISMATCH", file=sys.stderr)
                print(f"  expected {prior['sha256']} {prior['summary']}", file=sys.stderr)
                print(f"  actual   {actual['sha256']} {actual['summary']}", file=sys.stderr)
            else:
                print(f"{spec['name']}: OK ({actual['sha256'][:12]})")

    if args.update:
        if args.case:
            merged = dict(expected)
            for case in actual_cases:
                merged[str(case["name"])] = case
            ordered = [merged[str(spec["name"])] for spec in SPECS]
        else:
            ordered = actual_cases
        FIXTURE.write_text(json.dumps({"format": 1, "cases": ordered}, indent=2) + "\n", encoding="utf-8")
        print(f"updated {FIXTURE}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
