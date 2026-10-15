#!/usr/bin/env python3
"""Functional learning arms and complete stateful continuations, not promotion."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import racecraft_next_cli as base

FLAGS='forecast-repair,corner-memory,time-investment,event-aware,proof-number'
ARMS=FLAGS.split(',')+['learning-control','combined']

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--baseline-jar',type=Path,required=True)
    args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    jar=(base.ROOT/'theoreticRacing.jar').resolve()
    inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (base.ROOT/'user.properties',base.ROOT/'tracks/lap_bench.properties')}
    count=0;records=[]
    for track,n,mode in [('hairpin',2,'legacy'),('circle',4,'informed')]:
        label=f'{track}-{n}-{mode}'
        control=base.race(out,label+'-control',jar,track,n,mode,2,{})
        champion=base.race(out,label+'-master',args.baseline_jar.resolve(),track,n,mode,2,{})
        count+=2
        if control!=champion: raise AssertionError(label+': defaults differ from current aware master')
        slots=','.join(str(i+1) for i in range(n))
        for name,extra in [('no-slots',dict(racecraftNext=FLAGS)),
                ('zero-nodes',dict(candidateSlots=slots,racecraftNext=FLAGS,racecraftLearningNodes='0')),
                ('zero-trials',dict(candidateSlots=slots,racecraftNext=FLAGS,racecraftLearningTrials='0'))]:
            value=base.race(out,label+'-'+name,jar,track,n,mode,2,extra);count+=1
            if value!=control: raise AssertionError(label+': inactive '+name+' changes policy')
        for arm in ARMS:
            name=label+'-'+arm
            flags=FLAGS if arm=='combined' else arm
            config=dict(candidateSlots=slots,racecraftNext=flags)
            value=base.race(out,name,jar,track,n,mode,2,config)
            audited=base.race(out,name+'-audit',jar,track,n,mode,2,
                    dict(config,racecraftCapture='true',racecraftCaptureLimit='10000'))
            count+=2
            if value!=audited: raise AssertionError(name+': audit altered policy')
            process=(out/(name+'-audit.process')).read_text(encoding='utf-8')
            if 'PERF-AWARE MEMO MISMATCH' in process: raise AssertionError(name+': memo disagreement')
            row=dict(track=track,players=n,mode=mode,arm=arm,changed=value!=control,
                captures=process.count('RACECRAFT_STATE '),learningSnapshots=process.count('RACECRAFT_STATE rc7,'),auditIdentity=True)
            records.append(row);print(json.dumps(row),flush=True)
    for track,n,mode in [('circle',4,'scatter'),('hairpin',8,'legacy')]:
        label=f'{track}-{n}-{mode}'
        control=base.race(out,label+'-control',jar,track,n,mode,2,{})
        champion=base.race(out,label+'-master',args.baseline_jar.resolve(),track,n,mode,2,{})
        if control!=champion: raise AssertionError(label+': current champion identity')
        config=dict(candidateSlots=','.join(str(i+1) for i in range(n)),racecraftNext=FLAGS)
        active=base.race(out,label+'-combined',jar,track,n,mode,2,config)
        audit=base.race(out,label+'-audit',jar,track,n,mode,2,dict(config,racecraftCapture='true'))
        if active!=audit: raise AssertionError(label+': active audit differs')
        count+=4
    old=base.FLAGS
    try:
        base.FLAGS=FLAGS
        corpus=[base.check_corpus(out,jar,'hairpin','legacy'),base.check_corpus(out,jar,'circle','informed')]
    finally: base.FLAGS=old
    # Actual CLI training round, including all-champion trace validation and
    # mutated own-place-first counterpolicies. Kept small, not a league campaign.
    props=out/'league-source.properties';base.profile(props,2,'legacy',{})
    capture=out/'league-capture'
    base.execute([sys.executable,str(base.ROOT/'tools/racecraft_corpus.py'),'capture','--jar',str(jar),
        '--props',str(props),'--track','hairpin','--seed','3','--limit','6','--every','11',
        '--out',str(capture),'--heap=-Xmx8g'],out/'league-capture.process')
    league=out/'league'
    base.execute([sys.executable,str(base.ROOT/'tools/racecraft_league.py'),'--capture',str(capture),'--out',str(league),
        '--pool','champion,scorer','--cases','1','--offset','1','--generations','1','--mutations','1',
        '--max-moves','20000','--timeout','300'],out/'league.process',timeout=1800)
    if not (league/'COMPLETE').is_file(): raise AssertionError('league runner did not finish valid trials')
    result=json.loads((league/'summary.json').read_text())
    if not result['evolution'] or result['promoted']: raise AssertionError('league did not evolve an unpromoted profile')
    for path,digest in inputs.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest: raise AssertionError('caller input changed')
    (out/'validation.json').write_text(json.dumps(dict(functionalRaces=count,arms=records,corpus=corpus,
        corpusCases=6,leagueTrials=result['trialCount'],leagueGenerations=len(result['evolution']),
        performanceScreen=False,promoted=False),indent=2)+'\n')
    print(f'Learning controls: {count} complete races, six full-suffix cases, and {result["trialCount"]} league tails OK',flush=True)

if __name__=='__main__': main()
