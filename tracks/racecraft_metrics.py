"""Own-place-first diagnostics shared by mirrored and entrant screens.

head_to_head.py (the mirrored screen) and run_1vfield.py (the lone-entrant
check) print these lines below their own reading. They are description only:
the reading above them stays the statistic, and no line here is a gate or a
veto (CLAUDE.md, racecraft evaluation rule).

Equal-place time is descriptive, conditional on BOTH runs really finishing.
A survivor's observed moves are not a finish time. Matched seats of a mirrored
pair race in different fields, and cars of one race are not independent
samples, so the counts carry no standard error.

The module also holds what both tools need for their reading's own standard
error, corrected for repeated races (round 344): a race's identity
(race_digest), the cluster-robust error over a reading's units
(clustered_standard_error) and the note a reading's line gains when units
repeat (repeat_note).
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
import hashlib
import math
import re
import statistics
from pathlib import Path

if __package__:
    from .benchmark_io import read_properties
    from .forensics_common import parse_move
else:
    from benchmark_io import read_properties
    from forensics_common import parse_move


def race_digest(path):
    """A race's identity in the screens' repeat check (round 344): the SHA-256
    of its move lines in log order, each without its kind label (the third
    token: AI1, AI2 or HUMAN) and ended by a newline.

    Only move lines count -- the lines benchmark_io.read_race counts as moves.
    Names, kinds, the header (candidate slots, start placement, grid,
    checkpoints, laps, the course), the player lines, the results and any
    comment or seed line do not, and neither do line endings. A car's first
    move line carries its start cell, so two races with one digest made the
    same moves from the same cells and took the same places.

    Read the log with read_race first: this reads the same file again and
    validates nothing. It lives here, not in benchmark_io.py, because the
    fleet manifest hashes benchmark_io.py: a new hash would refuse to resume,
    or to pool with a new one, every grid raced before the change.
    """
    digest = hashlib.sha256()
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if parse_move(line) is not None:
            turn, player, _kind, rest = line.split(' ', 3)
            digest.update(('%s %s %s\n' % (turn, player, rest)).encode('utf-8'))
    return digest.hexdigest()


def clustered_standard_error(values, identities):
    """The standard error of the mean of a reading's units, corrected for
    repeated races (round 344; the owner, 2026-11-06: "Report corrected").

    ``values`` are the units (a track-seed each) and ``identities`` theirs:
    the track and the digest (race_digest) of every race of the unit, so two
    units share an identity exactly when they raced the same races. On
    computed starts a race depends on its seed only through the start draw,
    and the draw repeated races across seeds (C+'s eight-car screen of seeds
    1-10: 733 distinct units of 840); duels repeat under any draw. The
    uncorrected error counts each repeat as a new observation.

    Units with one identity form one cluster, and the error is the
    cluster-robust one, scaled by C/(C-1) for C clusters (CR1):
        sqrt(C/(C-1) * sum over clusters of (sum of its units' x - mean)^2) / n
    with the mean over all n units -- the mean the reading prints. Without
    repeats every cluster is one unit and C = n, where this IS the
    uncorrected stdev/sqrt(n) (the n/(n-1) of the sample variance); it is
    then computed exactly as before, so a screen without repeats prints the
    old number to the last digit. With repeats the sums are exact (fractions
    of the float units), so the order of the units cannot move a digit. With
    every unit one repeated race there is no spread to measure: nan.

    Returns (distinct units C, corrected error, uncorrected error); both
    errors are nan for a single unit, as before.
    """
    n = len(values)
    uncorrected = statistics.stdev(values) / math.sqrt(n) if n > 1 else float('nan')
    clusters = {}
    for value, identity in zip(values, identities, strict=True):
        clusters.setdefault(identity, []).append(Fraction(value))
    distinct = len(clusters)
    if distinct == n:
        return distinct, uncorrected, uncorrected
    if distinct < 2:
        return distinct, float('nan'), uncorrected
    mean = sum((v for cluster in clusters.values() for v in cluster), Fraction(0)) / n
    spread = sum(((sum(cluster, Fraction(0)) - len(cluster) * mean) ** 2 for cluster in clusters.values()),
                 Fraction(0))
    return distinct, math.sqrt(spread * distinct / (distinct - 1)) / n, uncorrected


def repeat_note(distinct, units, uncorrected):
    """What a reading's line gains after its old text when some of its units
    repeat (round 344): the number of distinct units and the uncorrected
    error, in the line's own unit. Without repeats it is empty, so the line
    is exactly the old one -- the corrected error is then the old error."""
    if distinct == units:
        return ''
    return ('; corrected for repeated races: %d distinct of %d track-seed units, uncorrected %.3f'
            % (distinct, units, uncorrected))


def terminal(outcomes, seat):
    """The seat's terminal event; a car without one is the last survivor."""
    return outcomes.get(seat, 'SURVIVOR')


def family(track):
    """Conservative synthetic-family grouping; racing circuits stay separate."""
    match = re.fullmatch(r'(fractal|hybrid|rand|lobe|weave|dspiral|serpentine)\d*', track)
    return match[1] if match else track


def sensitivity(per_track, side='candidate'):
    """Leave-one-track-out and leave-one-family-out readings, in the caller's
    own unit: the mean of the same track-seed units as its reading, without
    one group's units. Negative favours ``side``, as in the reading.

    For tracks, then for families, two lines:
    - the group that carries the largest summed gain for ``side`` (the sum of
      its units: its contribution to the reading), and the reading without
      it. Chosen by the sum, not the mean, so a family of many courses that
      carries much of a gain is not passed over for one course with a larger
      mean: on 316pp1's duels the mean named the single track spiral (-0.060)
      and never showed the fractal family (-0.051 without it).
    - the least and the most favourable leave-one-out readings, so a loss
      that sits on one group shows as well as a gain (320 diverse, 8 cars:
      +0.039, all of it Nordschleife; -0.002 without it).
    Sums are exact (fractions of the float units). Where several groups tie,
    the first name is printed and the line counts the others, so a tied
    course is never presented as the only one (review, 2026-10-19).
    """
    if not per_track:
        return []
    families = {}
    for track in sorted(per_track):
        families.setdefault(family(track), []).extend(per_track[track])
    lines = []
    for kind, plural, groups in (('track', 'tracks', per_track), ('family', 'families', families)):
        lines += _leave_one_out(kind, plural, groups, side)
    return lines


def _leave_one_out(kind, plural, groups, side):
    groups = {name: list(values) for name, values in groups.items() if values}
    if len(groups) < 2:
        return ['leave-one-%s-out: at least two %s required' % (kind, plural)]
    names = sorted(groups)
    sums = {name: sum((Fraction(v) for v in groups[name]), Fraction(0)) for name in names}
    total, units = sum(sums.values(), Fraction(0)), sum(len(groups[name]) for name in names)
    without = {name: (total - sums[name]) / (units - len(groups[name])) for name in names}
    strongest = min(names, key=lambda name: sums[name])
    if sums[strongest] < 0:
        others = sum(sums[name] == sums[strongest] for name in names) - 1
        alike = ('' if not others else ', as does one other %s' % kind if others == 1
                 else ', as do %d other %s' % (others, plural))
        lines = ["excluding the %s's strongest %s %s (contributes %+.3f to the reading%s): %+.3f places "
                 '(%d track-seed units)'
                 % (side, kind, strongest, float(sums[strongest] / units), alike, float(without[strongest]),
                    units - len(groups[strongest]))]
    else:
        lines = ["excluding the %s's strongest %s: no %s contributes a gain for it" % (side, kind, kind)]
    least = max(names, key=lambda name: without[name])
    most = min(names, key=lambda name: without[name])
    if without[least] == without[most]:
        lines.append('leave-one-%s-out over %d %s: %+.3f whichever %s is left out'
                     % (kind, len(names), plural, float(without[least]), kind))
    else:
        def tied(name):
            others = sum(without[other] == without[name] for other in names) - 1
            return '' if not others else ' or one other' if others == 1 else ' or any of %d others' % others
        lines.append('leave-one-%s-out over %d %s: least favourable to the %s %+.3f without %s%s, '
                     'most favourable %+.3f without %s%s'
                     % (kind, len(names), plural, side, float(without[least]), least, tied(least),
                        float(without[most]), most, tied(most)))
    return lines


class MatchedMetrics:
    """One seat of one track-seed: the same car number raced by policy A in
    one run and by policy B in its paired run."""

    def __init__(self):
        self.places = Counter()
        self.fates = [Counter(), Counter()]
        self.time = []

    def add(self, a_places, b_places, a_moves, b_moves, a_outcomes, b_outcomes, seat):
        delta = a_places[seat] - b_places[seat]
        self.places['gain' if delta < 0 else 'loss' if delta > 0 else 'tie'] += 1
        for counts, outcomes in zip(self.fates, (a_outcomes, b_outcomes)):
            counts[terminal(outcomes, seat)] += 1
        if delta == 0 and terminal(a_outcomes, seat) == terminal(b_outcomes, seat) == 'FINISH':
            self.time.append(a_moves[seat] - b_moves[seat])

    def lines(self, a='candidate', b='champion'):
        lines = ['same-seat place comparisons, %s against %s: gains %d, losses %d, ties %d'
                 % (a, b, self.places['gain'], self.places['loss'], self.places['tie'])]
        for label, counts in zip((a, b), self.fates):
            lines.append('%s terminal fates: %s' % (label, ', '.join(
                '%s=%d' % (fate, counts[fate]) for fate in ('FINISH', 'CRASH', 'TIMEOUT', 'SURVIVOR'))))
        if self.time:
            lines.append('equal-place, both FINISH: %d paired own-time comparisons, %s minus %s %+.3f moves'
                         % (len(self.time), a, b, statistics.mean(self.time)))
        else:
            lines.append('equal-place, both FINISH: no comparable own-time pairs')
        lines.append('Equal-place time is conditional/descriptive; survivors, crashes and timeouts are excluded.')
        return lines


def profile_text(path: Path, changes: dict[str, str]) -> str:
    """A screen profile: the base profile at ``path`` with ``changes`` applied,
    written as canonical Java properties (sorted keys, escaped, ASCII). The
    JVM reads the same map as from the old verbatim copies; only the bytes
    differ, so a folder started under the old tools refuses to resume.

    Custom arm keys in the base profile are kept. A ``racecraftModel`` path is
    replaced by the model file's own keys (``racecraftModel.*``), so a fleet
    manifest binds the model's bytes, not its path. Write that path with
    forward slashes (a backslash is a properties escape); a relative one
    resolves against the current directory."""
    values = read_properties(path)
    model = values.pop('racecraftModel', '').strip()
    if model:
        for key, value in read_properties(Path(model).expanduser().resolve()).items():
            values['racecraftModel.' + key] = value
    values.update(changes)

    def escape(text):
        output = []
        for char in text:
            if char in '\\ =:#!':
                output.append('\\' + char)
            elif ' ' <= char <= '~':
                output.append(char)
            else:
                code = char.encode('utf-16-be', 'surrogatepass')
                output.extend('\\u%04x' % int.from_bytes(code[i:i + 2], 'big') for i in range(0, len(code), 2))
        return ''.join(output)

    return ''.join('%s=%s\n' % (escape(k), escape(v)) for k, v in sorted(values.items()))
