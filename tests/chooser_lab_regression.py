#!/usr/bin/env python3
"""Real-JVM contracts for each research arm and the teacher/student pipeline.
Tiny models and small race sets test plumbing, never establish policy strength.
"""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tracks import chooser_lab as lab
from tracks.benchmark_io import read_race, update_properties
from tracks.forensics_common import normalized_sha256


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--heap',default='-Xmx8g')
    p.add_argument('--reference-jar',type=Path);args=p.parse_args();lab.require_plain_java_environment()
    args.out.mkdir(parents=True,exist_ok=False);out=args.out.resolve()
    env=os.environ.copy();env['RACING_REACH_CACHE']=str(out/'cache')
    before=lab.hashes([ROOT/'theoreticRacing.jar']+sorted((ROOT/'src').rglob('*.java'))+sorted((ROOT/'tracks').glob('*.py'))+sorted((ROOT/'tracks').glob('*.track')))
    lab.write_new(out/'pending.json',before)
    def command(name,argv,expected=0):
        with (out/(name+'.stdout')).open('x',encoding='utf-8') as stdout,(out/(name+'.stderr')).open('x',encoding='utf-8') as stderr:
            r=subprocess.run(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=900)
        if r.returncode!=expected:raise AssertionError(f'{name}: exit {r.returncode}, expected {expected}; see {out}')
    def cli(name,*parts,expected=0):command(name,[sys.executable,'tracks/chooser_lab.py',*map(str,parts)],expected)
    def native(name,track='hairpin',flags='',extra=None,jar=None,players=2):
        props=out/(name+'.properties')
        props.write_text('nPlayers='+str(players)+'\nlaps=1\n'+''.join(f'player{i}Kind=AI2\n' for i in range(1,players+1)),encoding='utf-8')
        values={'candidateSlots':','.join(map(str,range(1,players+1))) if flags else '', 'chooser.experiments':flags}
        if extra:values.update(extra)
        update_properties(props,values);log=out/(name+'.log')
        command(name,['java',args.heap,'-jar',str(jar or ROOT/'theoreticRacing.jar'),'--auto','--track',track,'--props',str(props),'--seed','1','--log',str(log)])
        read_race(log);return props,log
    props,log=native('default')
    native('disabled',flags='aware,setup,terminal',extra={'candidateSlots':''})
    native('zero',flags='aware,setup,terminal',extra={'chooser.policyBudget':'0'})
    native('audit',extra={'chooser.audit':'true'})
    reference=normalized_sha256(log.read_text(encoding='utf-8'))
    for name in ('disabled','zero','audit'):
        if normalized_sha256((out/(name+'.log')).read_text(encoding='utf-8'))!=reference:raise AssertionError('default leak: '+name)
    if args.reference_jar:
        _,ref=native('reference',jar=args.reference_jar.resolve())
        if normalized_sha256(ref.read_text(encoding='utf-8'))!=reference:raise AssertionError('pristine baseline differs')
    cli('audit-report','audit','--log',out/'audit.log','--audit',out/'audit.stderr','--out',out/'audit-report.json')
    for flag in ('aware','setup','terminal'):
        native(flag,flags=flag,extra={'chooser.audit':'true','chooser.auditEvery':'5'})
    native('combined',flags='aware,setup,terminal',extra={'chooser.rounds':'3','chooser.audit':'true','chooser.auditEvery':'3'},players=4)
    datasets=[]
    for name,track in [('training','hairpin'),('validation','chicane'),('heldout','bigoval')]:
        pr,lg=(props,log) if name=='training' else native(name,track=track)
        target=out/(name+'-data');datasets.append(target)
        cli(name+'-collect','collect','--props',pr,'--log',lg,'--track',track,'--family',name,'--moves','1,3,5','--heap='+args.heap,'--out',target)
    cli('train','train','--train',datasets[0],'--validation',datasets[1],'--epochs','50','--out',out/'student.json')
    cli('heldout-evaluate','evaluate','--model',out/'student.json','--data',datasets[2],'--out',out/'student-report.json')
    cli('reject-overlap','evaluate','--model',out/'student.json','--data',datasets[0],'--out',out/'bad-report.json',expected=2)
    for flag in ('student','assist'):
        profile=out/(flag+'.properties')
        cli(flag+'-profile','profile','--base',props,'--experiments',flag,'--model',out/'student.json','--out',profile)
        update_properties(profile,{'candidateSlots':'1,2'})
        command(flag,['java',args.heap,'-jar',str(ROOT/'theoreticRacing.jar'),'--auto','--track','hairpin','--props',str(profile),'--seed','1','--log',str(out/(flag+'.log'))])
        read_race(out/(flag+'.log'))
    # Train a tiny frozen v1-format diagnostic model on the teacher's first 12
    # features. This is format/insertion-point coverage, not the old fleet model.
    rows,_=lab.load([datasets[0]])
    for r in rows:
        for vector in r['audit']['features'].values():vector[12:]=[0.0]*7
    weights=lab.fit(rows,30,.5,.001)[:12]
    legacy=dict(version=1,features=lab.LEGACY_FEATURES,weights=weights,margin=.05,trainingSha256=lab.digest(datasets[0]/'manifest.json'))
    lab.write_new(out/'legacy.json',legacy)
    for flag in ('legacy-guarded','legacy-unchecked'):
        profile=out/(flag+'.properties')
        cli(flag+'-profile','profile','--base',props,'--experiments',flag,'--legacy-model',out/'legacy.json','--out',profile)
        update_properties(profile,{'candidateSlots':'1,2','chooser.audit':'true'})
        command(flag,['java',args.heap,'-jar',str(ROOT/'theoreticRacing.jar'),'--auto','--track','hairpin','--props',str(profile),'--seed','1','--log',str(out/(flag+'.log'))])
        read_race(out/(flag+'.log'))
    cli('two-actions','counterfactual','--props',props,'--log',log,'--track','hairpin','--move','1','--depth','2','--heap='+args.heap,'--out',out/'deviations')
    # Focal replacement includes compatibility with the non-experimental V2
    # interface. Same binary is a protocol control, not a historical-strength test.
    spec={'version':1,'referee':'base','baseline':'base','candidate':'student','backgrounds':['base','v2'], 'densities':[1,2],
          'policies':[{'name':name,'jar':str(ROOT/'theoreticRacing.jar'),'props':str(pr),'protocol':proto}
                      for name,pr,proto in [('base',props,'v3'),('student',out/'student.properties','v3'),('v2',props,'v2')]]}
    lab.write_new(out/'league-spec.json',spec)
    cli('league','league','--spec',out/'league-spec.json','--logs',log,'--track','hairpin','--focals','0','--heap='+args.heap,'--out',out/'league')
    lab.unchanged(before)
    report={'native_races':len(list(out.glob('*.log'))),'datasets':len(datasets),'default_sha256':reference,'heap':args.heap,
            'scope':'functional contracts only; no campaign or historical-opponent gain is claimed',
            'files':{str(path.relative_to(out)):lab.digest(path) for path in out.rglob('*') if path.is_file() and 'cache' not in path.parts and path.name!='pending.json'}}
    lab.write_new(out/'report.json',report);(out/'pending.json').unlink();print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
