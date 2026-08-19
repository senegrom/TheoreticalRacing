#!/usr/bin/env python3
"""Materialize Round 129's measured frontier-to-champion promotion.

The harvest-23 mixed census measured the AI1 frontier ahead of frozen AI2 on
21 of 22 tracks. Promote the already-certified Round 115 moderate-energy,
Round 117 six-ahead, and Round 124 early-round trap acceleration arms to both
smart driver kinds. Also promote Round 126's homogeneous equal-speed false-
target veto. Round 128's mixed fast-funnel confirm remains AI1-only: a broad
mirror made mixed confirmations recursively expensive and is not part of the
pace promotion.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceAi.java")
source = race.read_text()

old_equal = """\t\t\t\t\t\t\t\t\t\tif (moverKind(playerNum) == Player.Kind.AI1
\t\t\t\t\t\t\t\t\t\t\t\t&& poTByDir[chosen.ordinal()] == poTByDir[smomAlt.ordinal()]"""
new_equal = """\t\t\t\t\t\t\t\t\t\t// Round 129 promotion: the Round-126 false-target veto is now
\t\t\t\t\t\t\t\t\t\t// champion policy for both smart driver kinds.
\t\t\t\t\t\t\t\t\t\tif (poTByDir[chosen.ordinal()] == poTByDir[smomAlt.ordinal()]"""
assert source.count(old_equal) == 1, source.count(old_equal)
source = source.replace(old_equal, new_equal, 1)

old_frontier = "\t\tfinal boolean frontierMover = moverKind(playerNum) == Player.Kind.AI1;"
new_frontier = """\t\t// Round 129 promotion: Rounds 115, 117 and 124 cleared the
\t\t// frontier census; both smart driver kinds use the certified pace arms.
\t\tfinal boolean frontierMover = true;"""
assert source.count(old_frontier) == 1, source.count(old_frontier)
source = source.replace(old_frontier, new_frontier, 1)

old_doc = """\t/**
\t * AI2 (CHAMPION MIRROR): promoted at Round 109 to the Round-108 champion --
\t * the full frontier stack through the true-rival confirm family (rounds
\t * 98-107: thread-fragility audit, bounded certification-cap confirms with
\t * three fragility legs and cost ladders, slower-first ladder targets, the
\t * ESC-route direct true-rival confirm) plus the profiled smoke proximity
\t * gate (round 108). Mirrored by DELEGATION: the champion is one body of
\t * code and the strict probe (tracks/ai_probe.py, 27 races move-identical
\t * all-AI1 vs all-AI2) is the mirror proof; every kind-sensitive gate in the
\t * shared machinery is mover-symmetric, so a homogeneous AI2 field behaves
\t * exactly as a homogeneous AI1 field. During the next experiment AI2 is
\t * again the frozen yardstick: frontier work happens in optimalMoveAI1 and
\t * must leave this delegation untouched until the next promotion.
\t */"""
new_doc = """\t/**
\t * AI2 (CHAMPION MIRROR): Round 129 promotes the measured Round 115/117/124
\t * field-acceleration frontier and Round 126's homogeneous false-target veto
\t * to both smart driver kinds. The scorer remains one body by delegation.
\t * Round 128's mixed fast-funnel confirm is deliberately still AI1-only: it
\t * is a safety experiment, not part of this pace promotion, and mirroring it
\t * broadly made mixed confirmation recursively expensive. Future frontier
\t * work must keep this delegation and the promoted gates fixed until the next
\t * independently measured promotion.
\t */"""
assert source.count(old_doc) == 1, source.count(old_doc)
source = source.replace(old_doc, new_doc, 1)

assert source.count("moverKind(playerNum) == Player.Kind.AI1") == 1
assert source.count("final boolean frontierMover = true;") == 1
assert source.count("private Direction optimalMoveAI2") == 1
race.write_text(source)

Path("tests/ai1_early_round_trap_regression.py").write_text('#!/usr/bin/env python3\n"""Pin Round 124\'s phase-consistent trap-L2 pace gain after promotion."""\nfrom pathlib import Path\nimport sys\nimport tempfile\n\nROOT = Path(__file__).resolve().parents[1]\nsys.path.insert(0, str(ROOT / "tracks"))\nimport bench_ai  # noqa: E402\n\nCASES = [("silverstone", 93)]\nPROMOTED = (7, 0, [81, 82, 83, 84, 85, 85, 87])\nLEGACY_CHAMPION = (7, 0, [81, 82, 83, 84, 85, 86, 87])\nEXPECTED = {kind: {"silverstone:93": PROMOTED} for kind in ("AI1", "AI2")}\n\n\ndef main() -> int:\n    if not Path(bench_ai.JAR).is_file():\n        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")\n    actual = {"AI1": {}, "AI2": {}}\n    with tempfile.TemporaryDirectory(prefix="round124-regression-") as directory:\n        bench_ai.configure_runtime(directory)\n        bench_ai.set_nplayers(8)\n        for kind in ("AI1", "AI2"):\n            bench_ai.set_all_to(kind)\n            for track, seed in CASES:\n                actual[kind][f"{track}:{seed}"] = bench_ai.run_track(\n                    track, timeout=1200, seed=seed)\n    if actual != EXPECTED:\n        raise SystemExit(f"Round-124 promoted regression: {actual}, expected {EXPECTED}")\n    result = actual["AI1"]["silverstone:93"]\n    if actual["AI1"] != actual["AI2"]:\n        raise SystemExit(f"Round-124 promotion is not mirrored: {actual}")\n    if result[:2] != LEGACY_CHAMPION[:2] or any(\n            a > b for a, b in zip(result[2], LEGACY_CHAMPION[2])):\n        raise SystemExit(f"Round-124 Pareto contract lost: {result}, legacy {LEGACY_CHAMPION}")\n    if sum(result[2]) >= sum(LEGACY_CHAMPION[2]):\n        raise SystemExit(f"Round-124 pace gain lost: {result}, legacy {LEGACY_CHAMPION}")\n    print("AI1EarlyRoundTrapRegression: OK (Silverstone s93 promoted to both driver kinds)")\n    return 0\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n')
Path("tests/ai1_equal_speed_veto_regression.py").write_text('#!/usr/bin/env python3\n"""Pin Round 126\'s equal-speed false-target rescue after promotion."""\nfrom pathlib import Path\nimport sys\nimport tempfile\n\nROOT = Path(__file__).resolve().parents[1]\nsys.path.insert(0, str(ROOT / "tracks"))\nimport bench_ai  # noqa: E402\n\nCASES = [("zandvoort", 115)]\nPROMOTED = (7, 0, [139, 140, 141, 142, 143, 144, 145])\nLEGACY_CHAMPION = (6, 1, [139, 140, 141, 143, 144, 146])\nEXPECTED = {kind: {"zandvoort:115": PROMOTED} for kind in ("AI1", "AI2")}\n\n\ndef main() -> int:\n    if not Path(bench_ai.JAR).is_file():\n        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")\n    actual = {"AI1": {}, "AI2": {}}\n    with tempfile.TemporaryDirectory(prefix="round126-regression-") as directory:\n        bench_ai.configure_runtime(directory)\n        bench_ai.set_nplayers(8)\n        for kind in ("AI1", "AI2"):\n            bench_ai.set_all_to(kind)\n            for track, seed in CASES:\n                actual[kind][f"{track}:{seed}"] = bench_ai.run_track(\n                    track, timeout=1200, seed=seed)\n    if actual != EXPECTED:\n        raise SystemExit(f"Round-126 promoted regression: {actual}, expected {EXPECTED}")\n    if actual["AI1"] != actual["AI2"]:\n        raise SystemExit(f"Round-126 promotion is not mirrored: {actual}")\n    result = actual["AI1"]["zandvoort:115"]\n    if not (result[0] > LEGACY_CHAMPION[0] and result[1] < LEGACY_CHAMPION[1]):\n        raise SystemExit(f"Round-126 safety contract lost: {result}, legacy {LEGACY_CHAMPION}")\n    print("AI1EqualSpeedVetoRegression: OK (Zandvoort s115 rescue promoted to both kinds)")\n    return 0\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n')
Path("tests/ai1_graduated_field_accel_regression.py").write_text('#!/usr/bin/env python3\n"""Pin Round 115\'s low-energy field acceleration after promotion."""\nfrom pathlib import Path\nimport sys\nimport tempfile\n\nROOT = Path(__file__).resolve().parents[1]\nsys.path.insert(0, str(ROOT / "tracks"))\nimport bench_ai  # noqa: E402\n\nPROMOTED = {\n    1: (7, 0, [58, 59, 60, 61, 62, 62, 63]),\n    38: (7, 0, [58, 59, 61, 61, 62, 62, 62]),\n    106: (7, 0, [58, 59, 60, 62, 62, 63, 63]),\n}\nLEGACY_CHAMPION = {\n    1: (7, 0, [58, 59, 60, 62, 62, 63, 63]),\n    38: (7, 0, [58, 59, 61, 61, 62, 62, 63]),\n    106: PROMOTED[106],\n}\nEXPECTED = {kind: PROMOTED for kind in ("AI1", "AI2")}\n\n\ndef main() -> int:\n    if not Path(bench_ai.JAR).is_file():\n        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")\n    actual = {"AI1": {}, "AI2": {}}\n    with tempfile.TemporaryDirectory(prefix="round115-regression-") as directory:\n        bench_ai.configure_runtime(directory)\n        bench_ai.set_nplayers(8)\n        for kind in ("AI1", "AI2"):\n            bench_ai.set_all_to(kind)\n            for seed in (1, 38, 106):\n                actual[kind][seed] = bench_ai.run_track("coil", timeout=1200, seed=seed)\n    if actual != EXPECTED:\n        raise SystemExit(f"Round-115 promoted regression: {actual}, expected {EXPECTED}")\n    if actual["AI1"] != actual["AI2"]:\n        raise SystemExit(f"Round-115 promotion is not mirrored: {actual}")\n    for seed in (1, 38):\n        result, legacy = actual["AI1"][seed], LEGACY_CHAMPION[seed]\n        if result[:2] != legacy[:2] or any(a > b for a, b in zip(result[2], legacy[2])):\n            raise SystemExit(f"Round-115 Pareto contract lost on seed {seed}: {result}, {legacy}")\n        if sum(result[2]) >= sum(legacy[2]):\n            raise SystemExit(f"Round-115 pace gain lost on seed {seed}: {result}, {legacy}")\n    if actual["AI1"][106] != LEGACY_CHAMPION[106]:\n        raise SystemExit(f"Round-115 coast control changed: {actual}")\n    print("AI1GraduatedFieldAccelRegression: OK (Coil s1/s38 promoted; s106 frozen)")\n    return 0\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n')
Path("tests/ai1_six_ahead_accel_regression.py").write_text('#!/usr/bin/env python3\n"""Pin Round 117\'s synchronized six-ahead acceleration after promotion."""\nfrom pathlib import Path\nimport sys\nimport tempfile\n\nROOT = Path(__file__).resolve().parents[1]\nsys.path.insert(0, str(ROOT / "tracks"))\nimport bench_ai  # noqa: E402\n\nPROMOTED = {\n    5: (7, 0, [58, 59, 60, 61, 62, 62, 62]),\n    22: (7, 0, [58, 59, 60, 61, 61, 62, 63]),\n    86: (7, 0, [58, 59, 61, 61, 62, 62, 62]),\n}\nLEGACY_CHAMPION_86 = (7, 0, [58, 59, 61, 61, 62, 62, 63])\nEXPECTED = {kind: PROMOTED for kind in ("AI1", "AI2")}\n\n\ndef main() -> int:\n    if not Path(bench_ai.JAR).is_file():\n        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")\n    actual = {"AI1": {}, "AI2": {}}\n    with tempfile.TemporaryDirectory(prefix="round117-regression-") as directory:\n        bench_ai.configure_runtime(directory)\n        bench_ai.set_nplayers(8)\n        for kind in ("AI1", "AI2"):\n            bench_ai.set_all_to(kind)\n            for seed in (5, 22, 86):\n                actual[kind][seed] = bench_ai.run_track("coil", timeout=1200, seed=seed)\n    if actual != EXPECTED:\n        raise SystemExit(f"Round-117 promoted regression: {actual}, expected {EXPECTED}")\n    if actual["AI1"] != actual["AI2"]:\n        raise SystemExit(f"Round-117 promotion is not mirrored: {actual}")\n    result = actual["AI1"][86]\n    if result[:2] != LEGACY_CHAMPION_86[:2] or any(\n            a > b for a, b in zip(result[2], LEGACY_CHAMPION_86[2])):\n        raise SystemExit(f"Round-117 Pareto contract lost: {result}, {LEGACY_CHAMPION_86}")\n    if sum(result[2]) >= sum(LEGACY_CHAMPION_86[2]):\n        raise SystemExit(f"Round-117 pace gain lost: {result}, {LEGACY_CHAMPION_86}")\n    print("AI1SixAheadAccelRegression: OK (Coil s86 promoted; s5/s22 controls pinned)")\n    return 0\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n')

print("materialized Round 129 frontier promotion and permanent pins")
