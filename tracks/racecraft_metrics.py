"""Own-place-first diagnostics shared by mirrored and entrant screens.

Equal-place time is descriptive, conditional on BOTH runs really finishing.
A survivor's observed moves are not a finish time. Do not treat same-race cars
as independent samples when reporting uncertainty.
"""
from __future__ import annotations

from collections import Counter
import re
import statistics
from pathlib import Path

if __package__:
    from .benchmark_io import read_properties
else:
    from benchmark_io import read_properties


def terminal(outcomes, seat):
    return outcomes.get(seat, 'SURVIVOR')


def family(track):
    """Conservative synthetic-family grouping; racing circuits stay separate."""
    match = re.fullmatch(r'(fractal|hybrid|rand|lobe|weave|dspiral|serpentine)\d*', track)
    return match[1] if match else track


def sensitivity(per_track):
    """Leave-one-track/family-out effect, in the caller's original units."""
    if not per_track:
        return []
    groups = {}
    for track, values in per_track.items():
        groups.setdefault(family(track), []).extend(values)
    lines = []
    for kind, data in (('track', per_track), ('family', groups)):
        if len(data) < 2:
            lines.append(f'{kind} sensitivity: at least two groups required')
            continue
        best = min(data, key=lambda key: statistics.mean(data[key]))
        remaining = [v for key, values in data.items() if key != best for v in values]
        lines.append('excluding strongest %s %s: %+.3f places (%d track-seed units)'
                     % (kind, best, statistics.mean(remaining), len(remaining)))
    return lines


class MatchedMetrics:
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
        lines = ['same-seat place comparisons: gains %d, losses %d, ties %d'
                 % (self.places['gain'], self.places['loss'], self.places['tie'])]
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
    """Canonical Java properties, preserving custom arms and embedding model
    bytes so a fleet manifest binds the actual executable model, not its path."""
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
