#!/usr/bin/env python3
"""Twelve complete races verify experiment gating and audit noninterference.
This is a bounded functional check, not a candidate promotion or place screen.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
from benchmark_io import update_properties
from golden_races import normalized_log, summarize

SPEC = importlib.util.spec_from_file_location("review_audit", ROOT / "docs/experiments/racecraft-review/audit.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def main() -> None:
    for key in ("JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS"):
        if os.environ.get(key, "").strip():
            raise RuntimeError("unset " + key + "; this test specifies the reference heap explicitly")
    jar = ROOT / "theoreticRacing.jar"
    if not jar.is_file():
        raise RuntimeError("build theoreticRacing.jar first")
    source = (ROOT / "tracks/lap_bench.properties").read_bytes()
    modes = {
        "control": ("", "", False),
        "flags-no-slots": ("all", "", False),
        "slots-no-flags": ("", "1,2", False),
        "control-audit": ("", "", True),
        "candidate": ("all", "1,2", False),
        "candidate-audit": ("all", "1,2", True),
    }
    with tempfile.TemporaryDirectory(prefix="racecraft-review-controls-") as directory:
        work = Path(directory)
        for track in ("hairpin", "circle"):
            logs = {}
            for name, (features, slots, trace) in modes.items():
                props = work / f"{track}-{name}.properties"
                props.write_bytes(source)
                update_properties(props, {"nPlayers": "2", "player1Kind": "AI1", "player2Kind": "AI1",
                                         "aiStartPlacement": "legacy", "candidateSlots": slots,
                                         "racecraftReview": features, "racecraftReviewAudit": str(trace).lower()})
                log = work / f"{track}-{name}.log"
                result = subprocess.run(["java", "-Xmx8g", "-Djava.awt.headless=true", "-jar", str(jar),
                                         "--auto", "--track", track, "--props", str(props),
                                         "--log", str(log), "--seed", "2"],
                                        cwd=ROOT, capture_output=True, text=True, timeout=600)
                if result.returncode != 0 or not log.is_file():
                    raise RuntimeError(f"{track}/{name} failed: {result.stderr[-4000:]}")
                text = log.read_text(encoding="utf-8")
                summary = summarize(text)
                if len(summary["results"]) != 2 or summary["turns"] <= 0:
                    raise RuntimeError(f"{track}/{name} incomplete race: {summary}")
                logs[name] = normalized_log(text)
                if trace:
                    stderr = work / f"{track}-{name}.stderr"
                    stderr.write_text(result.stderr, encoding="utf-8")
                    report = audit.summarize([stderr])
                    if report["counts"]["decisions"] <= 0:
                        raise RuntimeError("audit check was vacuous")
            for control in ("flags-no-slots", "slots-no-flags", "control-audit"):
                if logs[control] != logs["control"]:
                    raise AssertionError(f"{track}: {control} changed control decisions")
            if logs["candidate"] != logs["candidate-audit"]:
                raise AssertionError(f"{track}: audit changed candidate decisions")
            print(f"{track}: complete-race gating and audit identity OK", flush=True)
    print("Racecraft review controls: 12 complete races OK; no promotion claim")


if __name__ == "__main__":
    main()
