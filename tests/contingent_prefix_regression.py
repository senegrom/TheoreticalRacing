#!/usr/bin/env python3
"""Real-JVM cached/uncached identity and two-response contracts; not a fleet."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracks import chooser_lab as lab
from tracks.benchmark_io import read_race
from tracks.forensics_common import normalized_sha256


def records(path: Path):
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('CHOOSER_AUDIT '):
            yield json.loads(line[len('CHOOSER_AUDIT '):])


def comparable(row):
    """Only physical saved-work counts/flag spelling may differ with caching."""
    return {key: row.get(key) for key in ('turn', 'mover', 'scoreChoice', 'baseline', 'proposal',
        'final', 'stages', 'teacher', 'experiments', 'contingent', 'exhausted', 'policies', 'moves')}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--heap', default='-Xmx2300m')
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(argv)
    lab.require_plain_java_environment()
    if not lab.re.fullmatch(r'-Xmx[1-9][0-9]*[kKmMgG]', args.heap):
        raise ValueError('one explicit heap required')
    args.out.mkdir(parents=True, exist_ok=False)
    out = args.out.resolve()
    inputs = lab.hashes([ROOT/'theoreticRacing.jar'] + sorted((ROOT/'src').rglob('*.java'))
        + sorted((ROOT/'tracks').glob('*.py')) + sorted((ROOT/'tracks').glob('*.track')))
    lab.write_new(out/'pending.json', inputs)
    env = os.environ.copy(); env['RACING_REACH_CACHE'] = str(out/'cache')
    def race(name, flags='', players=2, slots=None, budget=16000):
        pr=out/(name+'.properties')
        pr.write_text(f'nPlayers={players}\nlaps=1\n' + ''.join(f'player{i}Kind=AI2\n' for i in range(1,players+1))
            + f'candidateSlots={slots if slots is not None else ",".join(map(str,range(1,players+1)))}\n'
            + f'chooser.experiments={flags}\nchooser.rounds=4\nchooser.setupWidth=3\n'
            + f'chooser.policyBudget={budget}\nchooser.moveBudget=32000\nchooser.audit=true\nchooser.auditEvery=5\n', encoding='utf-8')
        log=out/(name+'.log')
        with (out/(name+'.stdout')).open('x') as stdout, (out/(name+'.stderr')).open('x') as stderr:
            run=subprocess.run(['java',args.heap,'-jar',str(ROOT/'theoreticRacing.jar'),'--auto','--track','hairpin',
                '--props',str(pr),'--seed','1','--log',str(log)],cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=600)
        if run.returncode: raise AssertionError(f'{name}: exit {run.returncode}')
        read_race(log)
        return normalized_sha256(log.read_text(encoding='utf-8')),list(records(out/(name+'.stderr')))
    baseline,_=race('default')
    disabled,_=race('unselected','contingent,prefix',slots='')
    zero,_=race('zero','contingent,prefix',budget=0)
    if not baseline==disabled==zero: raise AssertionError('inactive or zero-budget policy leak')
    saved=0; differences=0; comparisons=0; partial=0; pairs=[]
    for flag,players,budget in [('setup',2,16000),('contingent',4,16000),('contingent',4,1)]:
        name=f'{flag}-{players}-{budget}'
        a,ra=race(name,flag,players,budget=budget)
        b,rb=race(name+'-prefix',flag+',prefix',players,budget=budget)
        if a!=b: raise AssertionError('prefix changed complete race: '+name)
        if list(map(comparable,ra))!=list(map(comparable,rb)):
            raise AssertionError('prefix changed a plan, logical budget, or partial comparison: '+name)
        for r in rb:
            saved+=r.get('reusedPolicies',0)
            c=r.get('contingent',{})
            partial+=r.get('exhausted',False)
            for plan in c.get('plans',[]):
                comparisons+=1; differences+=plan['differentReply']
                # Each selected follow-up was enumerated separately on its world.
                for scenario in ('normal','chooser'):
                    plan_run=plan[scenario]
                    if plan_run['actualSecond']:
                        assert plan_run['actualSecond'] in plan_run['secondOptions']
        pairs.append({'case':name,'trace_sha256':a,'audited_decisions':len(rb)})
    if not saved or not comparisons: raise AssertionError('no exercised cache/plans')
    lab.unchanged(inputs)
    lab.write_new(out/'result.json',dict(native_races=9,pairs=pairs,reused_policy_calls=saved,
        compared_plans=comparisons,changed_rival_replies=differences,exhaustions=partial,
        scope='functional samples, not evidence of improved finishing places'))
    (out/'pending.json').unlink()
    print((out/'result.json').read_text())
    return 0


if __name__=='__main__':
    raise SystemExit(main())
