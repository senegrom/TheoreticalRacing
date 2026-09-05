#!/usr/bin/env python3
"""End-to-end V2 oracle replay: a complete two-car, two-lap race."""
from pathlib import Path
import contextlib
import io
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracks.forensics_common import DIRNAMES, Oracle, reconstruct_board  # noqa: E402
from tracks.oracle_roll import verify  # noqa: E402


def main():
    jar = ROOT / 'theoreticRacing.jar'
    with tempfile.TemporaryDirectory(prefix='racing-query-replay-') as directory:
        directory = Path(directory)
        props = directory / 'profile.properties'
        props.write_text('nPlayers=2\nplayer1Kind=AI2\nplayer2Kind=AI2\nlaps=2\n', encoding='utf-8')
        log = directory / 'race.log'
        run = subprocess.run(['java', '-jar', str(jar), '--auto', '--track', 'circle',
                              '--props', str(props), '--log', str(log), '--seed', '1'],
                             capture_output=True, text=True, timeout=300)
        if run.returncode != 0:
            raise AssertionError('reference race failed\n' + run.stdout + '\n' + run.stderr)
        cars, mover, moves = reconstruct_board(log, 1, 2, complete=True)
        lap_move = next(move for move in moves if move.status.startswith('LAP '))
        finish_move = next(move for move in moves if move.status == 'FINISH')
        lap_board, lap_mover, _ = reconstruct_board(log, lap_move.index, 2, complete=True)
        final_board, final_mover, _ = reconstruct_board(log, finish_move.index, 2, complete=True)
        with Oracle('circle', jar, props) as oracle:
            # Bound an accidental protocol/read deadlock too, not just JVM startup.
            watchdog = threading.Timer(300, oracle.proc.kill)
            watchdog.daemon = True
            watchdog.start()
            try:
                def simulation():
                    request = 'sim2,0,2,smom,1,0,2;' + ';'.join(
                        ','.join(str(v) for v in car) for car in cars)
                    oracle.proc.stdin.write(request + '\n')
                    oracle.proc.stdin.flush()
                    while True:
                        reply = oracle.proc.stdout.readline()
                        if not reply:
                            raise AssertionError('standalone simulation query failed')
                        if reply.startswith('V='):
                            return reply.strip()
                first_simulation = simulation()  # no preceding move query to initialize AI scratch state
                captured = io.StringIO()
                with contextlib.redirect_stdout(captured):
                    exact = verify(oracle, cars, mover, moves, len(moves))
                if not exact:
                    raise AssertionError('complete race replay diverged\n' + captured.getvalue())
                lap_answer = oracle.ask(lap_mover, lap_board)
                assert lap_answer[2].transitions[DIRNAMES.index(lap_move.direction)].status == 'LAP'
                assert lap_answer[2][DIRNAMES.index(lap_move.direction)] != 'F'
                final_answer = oracle.ask(final_mover, final_board)
                assert final_answer[2].transitions[DIRNAMES.index(finish_move.direction)].status == 'FINISH'
                oracle.ask(mover, cars)
                repeated = oracle.ask(final_mover, final_board)
                assert final_answer == repeated and final_answer[2].transitions == repeated[2].transitions
                legacy = [car[:5] for car in cars]
                after_final = oracle.ask(mover, legacy)
                oracle.ask(mover, cars)
                after_initial = oracle.ask(mover, legacy)
                assert after_final == after_initial, 'legacy query inherited prior lap/gate state'
                assert simulation() == first_simulation, 'simulation query inherited prior AI frame'
            finally:
                watchdog.cancel()
        print('QueryReplay: OK (%d recorded moves, full two-lap race, query-order isolation)' % len(moves))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
