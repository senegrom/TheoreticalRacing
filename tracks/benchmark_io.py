"""Strict input contracts shared by benchmark and head-to-head scoring.

Names are presentation data. Resolve a complete, unambiguous classification
once, then use player numbers for all scoring. This is format validation, not
a substitute for replaying moves through the game's referee.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

if __package__:
    from .forensics_common import parse_move
else:
    from forensics_common import parse_move

PLAYER = re.compile(r'player(\d+) name=(.*?) kind=(HUMAN|AI1|AI2) start=-?\d+,-?\d+'
                    r'(?: vel=-?\d+,-?\d+ gate=[0-2])?')
RESULT = re.compile(r'(\d+)\. (.*)')


@dataclass
class CompletedRace:
    players: dict[int, tuple[str, str]]  # number -> (name, kind)
    places: dict[int, int]               # number -> place
    slots: set[int]
    outcomes: dict[int, str]
    moves: dict[int, int]
    profile: dict[str, str]

    @property
    def crashed(self):
        return {n for n, outcome in self.outcomes.items() if outcome == 'CRASH'}

    def self_play(self):
        finishers = [self.moves[n] for n, event in self.outcomes.items() if event == 'FINISH']
        return len(finishers), len(self.crashed), finishers


def candidate_slots(value):
    try:
        slots = {int(s.strip()) for s in value.split(',') if s.strip()}
    except ValueError as error:
        raise ValueError('invalid candidate slots') from error
    if any(n < 1 or n > 9 for n in slots):
        raise ValueError('candidate slot out of range')
    return slots


def read_race(path, expected_players=None):
    """Read a complete current-format game log, or raise ValueError/OSError."""
    players, by_name, places, outcomes, moves, terminal_places = {}, {}, {}, {}, {}, {}
    profile = {'laps': '1', 'start-placement': 'legacy'}
    slots, seen_profile = set(), set()
    in_results = False
    turns = finished = retired = 0
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line:
            continue
        if in_results:
            result = RESULT.fullmatch(line)
            if result is None or result[2] not in by_name:
                raise ValueError('malformed or unknown result')
            place, number = int(result[1]), by_name[result[2]]
            if number in places or place in places.values():
                raise ValueError('duplicate player or place in results')
            places[number] = place
            continue
        player = PLAYER.fullmatch(line)
        if player:
            number, name, kind = int(player[1]), player[2], player[3]
            if turns or number in players or name in by_name or not 1 <= number <= 9:
                raise ValueError('late/duplicate player declaration or ambiguous name')
            players[number] = (name, kind)
            by_name[name] = number
            moves[number] = 0
            continue
        if line == '# results':
            in_results = True
            continue
        move = parse_move(line)
        if move:
            limit = len(players) if len(players) == 1 else len(players) - 1
            if (move.player not in players or move.player in outcomes or retired >= limit
                    or move.index != turns + 1 or line.split()[2] != players[move.player][1]):
                raise ValueError('invalid move order, player, kind or terminal state')
            turns += 1
            moves[move.player] += 1
            if move.status in ('FINISH', 'CRASH', 'TIMEOUT'):
                rank = re.fullmatch(r' place=(\d+)', move.detail)
                expected = finished + 1 if move.status == 'FINISH' else len(players) - (retired - finished)
                if rank is None or int(rank[1]) != expected:
                    raise ValueError('terminal place disagrees with finish/crash order')
                terminal_places[move.player] = expected
                outcomes[move.player] = move.status
                retired += 1
                finished += move.status == 'FINISH'
            continue
        if line.startswith('# candidate-slots '):
            key, value = 'candidate-slots', line[len('# candidate-slots '):]
            slots = candidate_slots(value)
        elif line.startswith('# Grid '):
            key, value = 'grid', line[len('# Grid '):]
        elif line.startswith('# laps '):
            key, value = 'laps', line[len('# laps '):]
        elif line.startswith('# start-placement '):
            key, value = 'start-placement', line[len('# start-placement '):]
        elif line.startswith(('trackLeft=', 'trackRight=')):
            key, value = line.split('=', 1)
        elif line.startswith('player') or line.startswith('# results') or re.match(r'^\d', line):
            raise ValueError('malformed player, move or results section')
        elif line.startswith('#'):
            continue
        else:
            raise ValueError('unknown log record')
        if turns or key in seen_profile:
            raise ValueError('duplicate or late log metadata')
        seen_profile.add(key)
        if key != 'candidate-slots':
            profile[key] = value
    expected = set(range(1, len(players) + 1))
    if (not players or set(players) != expected or not in_results
            or set(places) != expected or set(places.values()) != expected):
        raise ValueError('incomplete roster or classification')
    if retired != (len(players) if len(players) == 1 else len(players) - 1):
        raise ValueError('race has not reached a terminal result')
    for number in players:
        if places[number] != terminal_places.get(number, finished + 1):
            raise ValueError('classification disagrees with terminal events or last survivor')
    if not slots <= expected:
        raise ValueError('candidate slot is outside the active roster')
    if expected_players is not None and players != expected_players:
        raise ValueError('log roster does not match the requested configuration')
    return CompletedRace(players, places, slots, outcomes, moves, profile)


def _unescape(value):
    """java.util.Properties escapes (load(InputStream) uses ISO-8859-1)."""
    result, i = [], 0
    while i < len(value):
        char = value[i]
        i += 1
        if char == '\\' and i < len(value):
            char = value[i]
            i += 1
            if char == 'u':
                digits = value[i:i + 4]
                if not re.fullmatch(r'[0-9a-fA-F]{4}', digits):
                    raise ValueError('invalid Unicode escape in properties')
                char = chr(int(digits, 16))
                i += 4
            else:
                char = {'t': '\t', 'n': '\n', 'r': '\r', 'f': '\f'}.get(char, char)
        result.append(char)
    return ''.join(result).encode('utf-16-le', 'surrogatepass').decode('utf-16-le', 'surrogatepass')


def read_properties(path):
    """Parse Java properties, including continuations, escaped keys and last-wins."""
    properties, pending, continuing = {}, '', False
    for physical in Path(path).read_bytes().decode('latin-1').replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        line = physical.lstrip(' \t\f')
        if not continuing and (not line or line.startswith(('#', '!'))):
            continue
        line = pending + line
        slashes = len(line) - len(line.rstrip('\\'))
        if slashes % 2:
            pending, continuing = line[:-1], True
            continue
        pending, continuing = '', False
        _property_line(properties, line)
    if pending:
        _property_line(properties, pending)
    return properties


def _property_line(properties, line):
    escaped = False
    end = len(line)
    for i, char in enumerate(line):
        if not escaped and char in '=:\t\f ':
            end = i
            break
        escaped = not escaped if char == '\\' else False
    tail = line[end:].lstrip(' \t\f')
    if tail.startswith(('=', ':')):
        tail = tail[1:].lstrip(' \t\f')
    properties[_unescape(line[:end])] = _unescape(tail)


def update_properties(path, changes):
    """Update decoded Java keys in an isolated profile, preserving other values.

    Canonical ASCII output avoids encoding changes under Properties.load(InputStream).
    Reading first resolves alternate separators, continuations, duplicate keys and
    escaped aliases. Malformed input is rejected before the file is touched.
    """
    properties = read_properties(path)
    properties.update(changes)

    def escape(text):
        parts = []
        for char in text:
            if char in '\\ =:#!':
                parts.append('\\' + char)
            elif ' ' <= char <= '~':
                parts.append(char)
            else:
                # Java Unicode escapes encode UTF-16 code units, not code points.
                units = char.encode('utf-16-be', 'surrogatepass')
                parts.extend('\\u%04x' % int.from_bytes(units[i:i + 2], 'big')
                             for i in range(0, len(units), 2))
        return ''.join(parts)

    text = ''.join('%s=%s\n' % (escape(key), escape(value))
                   for key, value in sorted(properties.items()))
    Path(path).write_bytes(text.encode('ascii'))


def configured_players(path):
    props = read_properties(path)
    def bounded(key, default, high):
        try:
            value = int(props.get(key, ''))
        except ValueError:
            value = default
        return max(1, min(value, high))
    count = bounded('nPlayers', 2, bounded('maxPlayers', 9, 9))
    players = {}
    for n in range(1, count + 1):
        kind = props.get('player%dKind' % n, 'HUMAN').strip().upper()
        players[n] = (props.get('player%dName' % n, 'Player %d' % n),
                      kind if kind in ('AI1', 'AI2') else 'HUMAN')
    return players


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def comparison_profile(path):
    """Only the explicit candidate assignment may differ between mirrored grids."""
    props = read_properties(path)
    slots = candidate_slots(props.pop('candidateSlots', ''))
    return {'properties': fingerprint(props), 'candidate_slots': sorted(slots)}
