#!/usr/bin/env python3
"""Round 112 exact comparison with unchanged finish order required."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import round109_compare_pace as base  # noqa: E402

_original_classify = base.classify


def strict_classify(candidate: dict, baseline: dict):
    classification, delta, by_player = _original_classify(candidate, baseline)
    if classification == "pareto_faster" and candidate["order"] != baseline["order"]:
        return "redistribution", delta, by_player
    return classification, delta, by_player


base.classify = strict_classify

if __name__ == "__main__":
    raise SystemExit(base.main())
