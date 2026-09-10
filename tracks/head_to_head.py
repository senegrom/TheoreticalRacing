#!/usr/bin/env python3
"""Score complete mirrored fleet pairs by each policy's finishing places.

Usage: head_to_head.py ODD_GRID EVEN_GRID [ODD_GRID EVEN_GRID ...]

Every grid must have a schema-2 fleet manifest and validated completion markers.
Assignments must be complementary, configurations/builds identical apart from
candidateSlots, and every expected log present. Old unmanifested logs cannot
serve as promotion evidence; rerun them in fresh fleet output directories.
"""
from __future__ import annotations

import argparse
import collections
from contextlib import ExitStack
import hashlib
import json
import math
import pathlib
import re
import statistics
import sys

if __package__:
    from .benchmark_io import read_race
    from .fleet_grid import completed, directory_lock, json_text, seed_range
else:
    from benchmark_io import read_race
    from fleet_grid import completed, directory_lock, json_text, seed_range


def read(path):
    """Read a single complete result; never silently discard a malformed log."""
    race = read_race(path)
    return race.places, race.slots, race.crashed


def load_grid(directory):
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    required = {'schema', 'runner', 'log_parser', 'benchmark_parser', 'jar', 'properties',
                'comparison', 'java', 'java_sha256', 'heap', 'java_environment', 'seeds', 'tracks'}
    if not isinstance(manifest, dict) or not required <= manifest.keys() or manifest['schema'] != 2:
        raise ValueError('grid requires a schema-2 fleet manifest; rerun into a fresh directory')
    comparison = manifest['comparison']
    if (not isinstance(comparison, dict) or set(comparison) != {'properties', 'candidate_slots'}
            or not isinstance(comparison['candidate_slots'], list) or not comparison['candidate_slots']
            or any(type(n) is not int for n in comparison['candidate_slots'])
            or len(set(comparison['candidate_slots'])) != len(comparison['candidate_slots'])):
        raise ValueError('manifest has no valid candidate assignment')
    if (not isinstance(manifest['tracks'], dict) or not manifest['tracks']
            or any(not re.fullmatch(r'[A-Za-z0-9_-]+', t) for t in manifest['tracks'])):
        raise ValueError('manifest has invalid tracks')
    seeds = manifest['seeds']
    if not isinstance(seeds, list) or len(seeds) != 2 or any(type(n) is not int for n in seeds):
        raise ValueError('manifest has invalid seeds')
    lo, hi = seed_range('%d-%d' % tuple(seeds))
    seeds = range(lo, hi + 1)
    run_id = hashlib.sha256(json_text(manifest).encode()).hexdigest()
    races, expected_logs = {}, set()
    for track in sorted(manifest['tracks']):
        record = completed(directory, track, run_id, seeds)
        if record is None:
            raise ValueError('%s: missing, incomplete or corrupt completed track %s' % (directory, track))
        for seed in seeds:
            name = '%s_s%d.log' % (track, seed)
            expected_logs.add(name)
            race = read_race(directory / name)
            if race.slots != set(comparison['candidate_slots']):
                raise ValueError('candidate assignment differs between log and manifest: ' + name)
            if not {'grid', 'trackLeft', 'trackRight'} <= race.profile.keys():
                raise ValueError('missing race geometry: ' + name)
            races[track, seed] = race
    if {p.name for p in directory.glob('*_s*.log')} != expected_logs:
        raise ValueError('unexpected or missing race logs in ' + str(directory))
    return manifest, races


def comparison_key(manifest):
    # Seed windows and selected track subsets may vary across independent pairs.
    key = {k: v for k, v in manifest.items() if k not in ('properties', 'comparison', 'seeds', 'tracks')}
    key['properties'] = manifest['comparison']['properties']
    return key


def paired_races(directories):
    paths = [pathlib.Path(d).resolve() for d in directories]
    if len(paths) < 2 or len(paths) % 2:
        raise ValueError('supply complete pairs of mirrored grid directories')
    if len(set(paths)) != len(paths):
        raise ValueError('duplicate input grid directory')
    races, track_hashes = {}, {}
    common_key = common_roster = None
    with ExitStack() as locks:
        for path in sorted(paths):
            if not path.is_dir():
                raise ValueError('grid directory not found: ' + str(path))
            locks.enter_context(directory_lock(path))
        for offset in range(0, len(paths), 2):
            left, lr = load_grid(paths[offset])
            right, rr = load_grid(paths[offset + 1])
            key = comparison_key(left)
            if (key != comparison_key(right) or left['seeds'] != right['seeds']
                    or left['tracks'] != right['tracks'] or set(lr) != set(rr)
                    or common_key is not None and key != common_key):
                raise ValueError('incompatible mirrored build, runtime, configuration, tracks or seeds')
            common_key = key
            for track, digest in left['tracks'].items():
                if track in track_hashes and track_hashes[track] != digest:
                    raise ValueError('track changed between seed slices: ' + track)
                track_hashes[track] = digest
            for identity, a in lr.items():
                b = rr[identity]
                if identity in races:
                    raise ValueError('duplicate track/seed pair: %s %s' % identity)
                roster = set(a.players)
                if (a.players != b.players or a.profile != b.profile
                        or common_roster is not None and a.players != common_roster):
                    raise ValueError('incompatible mirrored roster or race geometry/profile')
                common_roster = a.players
                if (a.slots & b.slots or a.slots | b.slots != roster
                        or len(a.slots) != len(b.slots)):
                    raise ValueError('candidate assignments must be complementary balanced cohorts')
                races[identity] = [(r.places, r.slots, r.crashed) for r in (a, b)]
    if not races:
        raise ValueError('no complete mixed-field pairs')
    return races


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('grids', nargs='+')
    args = parser.parse_args(argv)
    try:
        races = paired_races(args.grids)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('head-to-head: ' + str(error), file=sys.stderr)
        return 2
    cand, champ = [], []
    cand_wins = champ_wins = cand_crash = champ_crash = 0
    per_track = collections.defaultdict(lambda: [[], []])
    paired = []
    for (track, seed), runs in sorted(races.items()):
        diff = []
        for places, slots, crashed in runs:
            c = [p for n, p in places.items() if n in slots]
            h = [p for n, p in places.items() if n not in slots]
            cand += c
            champ += h
            cand_wins += sum(1 for p in c if p == 1)
            champ_wins += sum(1 for p in h if p == 1)
            cand_crash += sum(1 for n in crashed if n in slots)
            champ_crash += sum(1 for n in crashed if n not in slots)
            per_track[track][0] += c
            per_track[track][1] += h
            diff.append(statistics.mean(c) - statistics.mean(h))
        if len(runs) >= 2:
            paired.append(statistics.mean(diff))
    n = len(cand)
    tie = (len(next(iter(races.values()))[0][0]) + 1) / 2
    print("%d candidate car-races, %d champion car-races over %d races" % (n, len(champ), sum(len(r) for r in races.values())))
    mc, mh = statistics.mean(cand), statistics.mean(champ)
    print("mean place   candidate %.3f   champion %.3f   (lower is better; %.3f is a tie)" % (mc, mh, tie))
    print("race wins    candidate %d   champion %d" % (cand_wins, champ_wins))
    print("crashes      candidate %d   champion %d" % (cand_crash, champ_crash))
    if paired:
        m = statistics.mean(paired)
        se = statistics.stdev(paired) / math.sqrt(len(paired)) if len(paired) > 1 else float("nan")
        print("mirrored races %d: candidate minus champion mean place %+.3f  (standard error %.3f; negative favours the candidate)"
              % (len(paired), m, se))
    rows = sorted(((statistics.mean(c) - statistics.mean(h), t, len(c)) for t, (c, h) in per_track.items() if c and h))
    print("\ntracks where the candidate gains most (mean place difference, candidate car-races):")
    for d, t, k in rows[:8]:
        print("    %-14s %+.3f  (%d)" % (t, d, k))
    print("tracks where it loses most:")
    for d, t, k in rows[-8:]:
        print("    %-14s %+.3f  (%d)" % (t, d, k))
    better = sum(1 for d, _, _ in rows if d < 0)
    print("\n%d tracks favour the candidate, %d the champion, %d tied" % (better, sum(1 for d, _, _ in rows if d > 0), sum(1 for d, _, _ in rows if d == 0)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
