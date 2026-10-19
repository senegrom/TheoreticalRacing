"""Own-place-first diagnostics shared by mirrored and entrant screens.

head_to_head.py (the mirrored screen) and run_1vfield.py (the lone-entrant
check) print these lines below their own reading. They are description only:
the reading above them stays the statistic, and no line here is a gate or a
veto (CLAUDE.md, racecraft evaluation rule).

Equal-place time is descriptive, conditional on BOTH runs really finishing.
A survivor's observed moves are not a finish time. Matched seats of a mirrored
pair race in different fields, and cars of one race are not independent
samples, so the counts carry no standard error.
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
import re
import statistics
from pathlib import Path

if __package__:
    from .benchmark_io import read_properties
else:
    from benchmark_io import read_properties


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
