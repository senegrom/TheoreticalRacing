#!/usr/bin/env python3
"""Deep faithful-oracle audit of the final Zandvoort-195 decisions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
from forensics_common import (  # noqa: E402
    DIRNAMES, DIRS, Oracle, Reach, log_player_count, reconstruct_board,
)


def apply_candidate(cars, mover, direction_index, mask):
    x, y, vx, vy, _ = cars[mover]
    outcome = mask[direction_index]
    next_cars = list(cars)
    if outcome == "F":
        next_cars[mover] = (x, y, vx, vy, 90)
        return next_cars, "FINISH"
    if outcome in "XB":
        next_cars[mover] = (x, y, vx, vy, 99)
        return next_cars, "CRASH"
    dx, dy = DIRS[direction_index]
    nvx, nvy = vx + dx, vy + dy
    next_cars[mover] = (x + nvx, y + nvy, nvx, nvy, 0)
    return next_cars, "ok"


def run_candidate(oracle, reach, cars, mover, direction_index, mask, max_rounds):
    current, fate = apply_candidate(cars, mover, direction_index, mask)
    result = {
        "direction": DIRNAMES[direction_index],
        "mask": mask[direction_index],
        "initial_fate": fate,
        "checkpoints": [],
    }
    if fate != "ok":
        return result

    player_count = len(current)
    index = (mover + 1) % player_count
    for round_no in range(1, max_rounds + 1):
        for _ in range(player_count):
            if current[index][4] == 0:
                dx, dy, live_mask = oracle.ask(index, current)
                live_direction = DIRS.index((dx, dy))
                current, _ = apply_candidate(
                    current, index, live_direction, live_mask)
            index = (index + 1) % player_count
        x, y, vx, vy, mover_fate = current[mover]
        checkpoint = {
            "round": round_no,
            "state": [x, y, vx, vy, mover_fate],
            "turns": reach.turns(x, y, vx, vy) if mover_fate == 0 else None,
        }
        result["checkpoints"].append(checkpoint)
        if mover_fate != 0:
            result["terminal_fate"] = "FINISH" if mover_fate == 90 else "CRASH"
            result["terminal_round"] = round_no
            break
    else:
        result["terminal_fate"] = "alive"
        result["terminal_round"] = max_rounds
    return result


def compact(decision):
    lines = [
        "move %d p%d logged=%s oracle=%s exact=%s mask=%s"
        % (
            decision["move_index"], decision["player"],
            decision["logged_direction"], decision["oracle_direction"],
            decision["oracle_matches_log"], decision["mask"],
        )
    ]
    for candidate in decision["candidates"]:
        terminal = candidate.get("terminal_fate", candidate["initial_fate"])
        terminal_round = candidate.get("terminal_round", 0)
        checkpoints = candidate["checkpoints"]
        samples = []
        for target in (4, 8, 12, 16, 18):
            if target <= len(checkpoints):
                row = checkpoints[target - 1]
                samples.append("r%d:t=%s:f=%s" % (
                    target, row["turns"], row["state"][4]))
        lines.append(
            "  %-4s mask=%s -> %s@r%d %s"
            % (
                candidate["direction"], candidate["mask"], terminal,
                terminal_round, " ".join(samples),
            )
        )
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("track")
    parser.add_argument("reach", type=Path)
    parser.add_argument("metadata", type=Path)
    parser.add_argument("out_json", type=Path)
    parser.add_argument("out_text", type=Path)
    parser.add_argument("--rounds", type=int, default=18)
    parser.add_argument("--seed", type=int, default=195)
    parser.add_argument("--props", type=Path, default=ROOT / "tracks" / "bench.properties")
    args = parser.parse_args()

    metadata = json.loads(args.metadata.read_text())
    reach = Reach(args.reach)
    decisions = []
    player_count = log_player_count(args.log)
    with Oracle(args.track, ROOT / "theoreticRacing.jar", args.props, seed=args.seed) as oracle:
        for move_index in metadata["probe_indices"]:
            cars, mover, real = reconstruct_board(args.log, move_index, player_count)
            if not real:
                raise RuntimeError("missing logged move %d" % move_index)
            logged = real[0]
            dx, dy, mask = oracle.ask(mover, cars)
            oracle_direction = DIRNAMES[DIRS.index((dx, dy))]
            decision = {
                "move_index": move_index,
                "player": mover + 1,
                "logged_direction": logged.direction,
                "oracle_direction": oracle_direction,
                "oracle_matches_log": oracle_direction == logged.direction,
                "mask": mask,
                "board": [list(car) for car in cars],
                "candidates": [],
            }
            for direction_index in range(len(DIRS)):
                decision["candidates"].append(run_candidate(
                    oracle, reach, cars, mover, direction_index, mask, args.rounds))
            decisions.append(decision)

    output = {
        "track": args.track,
        "seed": args.seed,
        "rounds": args.rounds,
        "decisions": decisions,
    }
    args.out_json.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    text = []
    for decision in decisions:
        text.extend(compact(decision))
        text.append("")
    args.out_text.write_text("\n".join(text))
    print("\n".join(text))
    if not all(decision["oracle_matches_log"] for decision in decisions):
        raise SystemExit("oracle failed to reproduce one or more logged choices")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
