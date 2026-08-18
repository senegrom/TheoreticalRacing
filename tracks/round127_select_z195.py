#!/usr/bin/env python3
"""Select the critical Zandvoort-195 decisions for Round 127 forensics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
from forensics_common import parse_move  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()

    moves = []
    for line in args.log.read_text(encoding="utf-8", errors="replace").splitlines():
        move = parse_move(line)
        if move is not None:
            moves.append(move)
    crashes = [move for move in moves if move.status == "CRASH"]
    if not crashes:
        raise SystemExit("Zandvoort seed 195 unexpectedly has no crash")
    crash = crashes[-1]
    player_moves = [move for move in moves if move.player == crash.player]
    if player_moves[-1].index != crash.index:
        raise SystemExit("crash is not the player's final move")
    if len(player_moves) < 13:
        raise SystemExit("insufficient decision history for the branching-window audit")
    tail = player_moves[-16:]
    # Pass one proved the final four decisions have 36/36 crashing
    # continuations. Move the deep oracle to the last genuine branching
    # window: the five decisions 13..9 mover turns before the crash.
    probe = player_moves[-13:-8]
    late_probe = player_moves[-4:]
    data = {
        "crash_player": crash.player,
        "crash_index": crash.index,
        "crash_direction": crash.direction,
        "crash_state": {
            "x": crash.x, "y": crash.y,
            "old_vx": crash.old_vx, "old_vy": crash.old_vy,
            "new_vx": crash.new_vx, "new_vy": crash.new_vy,
            "new_x": crash.new_x, "new_y": crash.new_y,
        },
        "player_move_count": len(player_moves),
        "tail_indices": [move.index for move in tail],
        "probe_indices": [move.index for move in probe],
        "late_probe_indices": [move.index for move in late_probe],
        "tail": [move._asdict() for move in tail],
    }
    args.out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
