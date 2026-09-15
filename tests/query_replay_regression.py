#!/usr/bin/env python3
"""Full live-policy replay plus policy-independent lap/finish boundary probes.

A complete race can end by crash/last-survivor classification without FINISH.
Replay what happened; test required transition shapes on deliberate boards.
"""
from pathlib import Path
import contextlib
import io
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracks.forensics_common import DIRNAMES, Oracle, ReplayBoard, reconstruct_board  # noqa: E402
from tracks.oracle_roll import apply_move, race_finished, verify  # noqa: E402


def single_lap_checkpoint_contract(jar, directory):
    """Real one-lap checkpoint races must never enter five-field diagnostics."""
    for track in ('circle', 'hairpin'):
        props = directory / (track + '-one-lap.properties')
        props.write_text('nPlayers=2\nplayer1Kind=AI2\nplayer2Kind=AI2\nlaps=1\n', encoding='utf-8')
        log = directory / (track + '-one-lap.log')
        result = subprocess.run(['java', '-jar', str(jar), '--auto', '--track', track,
                                 '--props', str(props), '--log', str(log), '--seed', '1'],
                                capture_output=True, text=True, timeout=300)
        if result.returncode:
            raise AssertionError('one-lap reference failed\n' + result.stdout + result.stderr)
        text = log.read_text(encoding='utf-8')
        assert '# checkpoints ' + ('enabled' if track == 'circle' else 'disabled') + '\n' in text
        if track == 'hairpin':
            legacy, _, _ = reconstruct_board(log, 1, 2)
            assert all(len(car) == 5 for car in legacy)
            continue
        try:
            reconstruct_board(log, 1, 2)
        except ValueError as error:
            assert 'complete=True' in str(error)
        else:
            raise AssertionError('one-lap checkpoint log was accepted as a legacy board')
        initial, mover, moves = reconstruct_board(log, 1, 2, complete=True)
        # Terminal shape is a policy outcome, not a precondition for replay.
        target = moves[-1].index
        board, _, _ = reconstruct_board(log, target, 2, complete=True)
        assert board.laps == 1
        with Oracle(track, jar, props) as oracle:
            watchdog = threading.Timer(300, oracle.proc.kill)
            watchdog.daemon = True
            watchdog.start()
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    assert verify(oracle, initial, mover, moves, len(moves)), 'one-lap full replay diverged'
                crossing_contract(oracle, 1)
            finally:
                watchdog.cancel()
        # Existing logs have no marker; V2 still reconstructs their earned gates.
        old_log = directory / 'historical-circle.log'
        old_log.write_text(text.replace('# checkpoints enabled\n', ''), encoding='utf-8')
        restored, _, _ = reconstruct_board(old_log, target, 2, complete=True)
        assert restored == board
        print('QueryReplay: one-lap Circle full replay, deliberate finish and legacy rejection; Hairpin legacy OK', flush=True)


def crossing_contract(oracle, laps):
    """Same legal Circle edge, different earned progress, irrespective of AI choice."""
    # E: (50,8), v(1,0) -> (52,8), beyond the forward S/F seam.
    # The far rival is on the road, and does not decide whether this is a finish.
    def board(lap, gate=0, turns=100):
        return ReplayBoard([(50, 8, 1, 0, 0, lap, gate), (87, 48, 0, 0, 0, 0, 1)],
                           laps=laps, turns=turns, complete=True)

    final = board(laps - 1)
    final_answer = oracle.ask(0, final)
    direction = DIRNAMES.index('E')
    assert final_answer[2].transitions[direction].status == 'FINISH'
    assert final_answer[2][direction] == 'F'
    owed = oracle.ask(0, board(laps - 1, gate=1))[2].transitions[direction]
    assert owed.status == 'OK' and owed.lap == laps - 1 and owed.gate == 1
    if laps > 1:
        initial_answer = oracle.ask(0, board(0))
        transition = initial_answer[2].transitions[direction]
        assert (transition.status, transition.lap, transition.gate) == ('LAP', 1, 1)
        assert initial_answer[2][direction] != 'F'
    repeated = oracle.ask(0, final)
    assert final_answer == repeated and final_answer[2].transitions == repeated[2].transitions
    timeout = oracle.ask(0, board(laps - 1, turns=laps * 750 * 2 + 1))[2]
    assert all(t.status == 'TIMEOUT' for t in timeout.transitions), 'timeout must precede finish'
    # Timeout alone removes one mover and immediately classifies the survivor.
    dx, dy, mask = oracle.ask(0, board(laps - 1, turns=laps * 750 * 2 + 1))
    ended, fate = apply_move(board(laps - 1, turns=laps * 750 * 2 + 1), 0, dx, dy, mask)
    assert fate == 'TIMEOUT' and race_finished(ended) and ended[1][4] == 0
    return final, final_answer


def crash_survivor_contract(jar, directory):
    """A real physical blockade ends without FINISH, regardless of chosen acceleration."""
    props = directory / 'blocked.properties'
    props.write_text('nPlayers=2\nplayer1Kind=AI2\nplayer2Kind=AI2\nlaps=1\n', encoding='utf-8')
    cars = ReplayBoard([(17, 25, 1, -2, 0, 0, 0), (17, 24, 2, 2, 0, 0, 0)],
                       laps=1, turns=2, complete=True)
    with Oracle('hairpin', jar, props) as oracle:
        watchdog = threading.Timer(300, oracle.proc.kill)
        watchdog.daemon = True
        watchdog.start()
        try:
            dx, dy, mask = oracle.ask(0, cars)
            assert all(t.status == 'CRASH' for t in mask.transitions), 'blockade fixture is not physical'
            ended, fate = apply_move(cars, 0, dx, dy, mask)
            assert fate == 'CRASH' and race_finished(ended)
            assert ended.turns == 3 and ended[1] == cars[1], 'invented a turn for the survivor'
        finally:
            watchdog.cancel()
    print('QueryReplay: deliberate crash/last-survivor termination without FINISH OK', flush=True)


def main():
    jar = ROOT / 'theoreticRacing.jar'
    with tempfile.TemporaryDirectory(prefix='racing-query-replay-') as directory:
        directory = Path(directory)
        single_lap_checkpoint_contract(jar, directory)
        crash_survivor_contract(jar, directory)
        props = directory / 'profile.properties'
        props.write_text('nPlayers=2\nplayer1Kind=AI2\nplayer2Kind=AI2\nlaps=2\n', encoding='utf-8')
        log = directory / 'race.log'
        run = subprocess.run(['java', '-jar', str(jar), '--auto', '--track', 'circle',
                              '--props', str(props), '--log', str(log), '--seed', '1'],
                             capture_output=True, text=True, timeout=300)
        if run.returncode != 0:
            raise AssertionError('reference race failed\n' + run.stdout + '\n' + run.stderr)
        cars, mover, moves = reconstruct_board(log, 1, 2, complete=True)
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
                final_board, final_answer = crossing_contract(oracle, 2)
                oracle.ask(mover, cars)
                repeated = oracle.ask(0, final_board)
                assert final_answer == repeated and final_answer[2].transitions == repeated[2].transitions
                legacy = [car[:5] for car in cars]
                after_final = oracle.ask(mover, legacy)
                oracle.ask(mover, cars)
                after_initial = oracle.ask(mover, legacy)
                assert after_final == after_initial, 'legacy query inherited prior lap/gate state'
                assert simulation() == first_simulation, 'simulation query inherited prior AI frame'
            finally:
                watchdog.cancel()
        print('QueryReplay: OK (%d recorded moves, full two-lap race, deliberate lap/finish/timeout, query-order isolation)' % len(moves))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
