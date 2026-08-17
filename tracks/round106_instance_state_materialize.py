#!/usr/bin/env python3
"""Make recursive-confirm and query-trace state race-instance owned."""
from pathlib import Path

ai_path = Path('src/tr/logic/RaceAi.java')
ai = ai_path.read_text()
old_depth = '\tprivate static int\t\t\t\ttrueConfirmDepth;'
new_depth = '\tprivate int\t\t\t\t\ttrueConfirmDepth;'
assert ai.count(old_depth) == 1
ai = ai.replace(old_depth, new_depth, 1)
old_trace = '\tstatic volatile boolean\t\t\tsimTrace;'
new_trace = '\tvolatile boolean\t\t\t\tsimTrace;'
assert ai.count(old_trace) == 1
ai = ai.replace(old_trace, new_trace, 1)
ai_path.write_text(ai)

game_path = Path('src/tr/logic/RaceGame.java')
game = game_path.read_text()
assert game.count('RaceAi.simTrace') == 2
game = game.replace('RaceAi.simTrace', 'ai.simTrace')
game_path.write_text(game)
print('materialized per-AI trueConfirmDepth and simTrace state')
