#!/usr/bin/env python3
"""Generate a browser build of the *same* engine. Never edit generated Java.

Swing host imports, Java 21 list conveniences and the distance-map thread
schedule are adapted. Distance BFS runs first in the existing preparation job. RaceAi and MoveQueries are byte-for-byte copies. Reachability has only
erasable, output-only progress hooks added to the browser copy. Every replacement is counted, so upstream drift fails the build.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
from instrument_progress import instrument, instrument_game
from startup_schedule import adapt

ROOT = Path(__file__).resolve().parents[2]


def prepare(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    rules = {
        'RaceGame.java': [
            ('import javax.swing.JOptionPane;', 'import tr.browser.JOptionPane;', 1),
            ('import javax.swing.SwingUtilities;', 'import tr.browser.SwingUtilities;', 1),
            ('import javax.swing.Timer;', 'import tr.browser.Timer;', 1),
            ('player.getHistory().removeLast();',
             'player.getHistory().remove(player.getHistory().size() - 1);', 1),
        ],
        'TrackIO.java': [
            ('left.getFirst()', 'left.get(0)', 1),
            ('right.getFirst()', 'right.get(0)', 1),
            ('left.getLast()', 'left.get(left.size() - 1)', 1),
            ('right.getLast()', 'right.get(right.size() - 1)', 1),
        ],
        'TrackGeometry.java': [
            ('p1.getFirst()', 'p1.get(0)', 1),
            ('p1.getLast()', 'p1.get(p1.size() - 1)', 1),
            ('p2.getFirst()', 'p2.get(0)', 1),
            ('p2.getLast()', 'p2.get(p2.size() - 1)', 1),
            ('active.getLast()', 'active.get(active.size() - 1)', 1),
            ('right.reversed()', 'tr.browser.Lists.reversed(right)', 1),
        ],
    }
    hashes = {}
    for source in sorted((ROOT / 'src/tr/logic').glob('*.java')):
        content = source.read_text(encoding='utf-8')
        hashes[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()
        for old, new, count in rules.get(source.name, []):
            actual = content.count(old)
            if actual != count:
                raise RuntimeError(f'{source.name}: expected {count} occurrences of {old!r}, found {actual}; audit the upstream change')
            content = content.replace(old, new)
        content = adapt(source.name, content)
        if source.name == 'RaceGame.java':
            content = instrument_game(content)
        if source.name == 'Reachability.java':
            content = instrument(content)
        target = out / 'tr/logic' / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    for source in sorted((ROOT / 'web/java').rglob('*.java')):
        target = out / source.relative_to(ROOT / 'web/java')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (out.parent / 'engine-sources.json').write_text(json.dumps(hashes, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('out', type=Path)
    prepare(parser.parse_args().out)
