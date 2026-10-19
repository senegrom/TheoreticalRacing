#!/usr/bin/env python3
"""Small functional/identity checks, not a fleet promotion battery.

Use --baseline-jar for a separately compiled pre-change executable. The default
control is this executable with all research disabled; that alone is not a
cross-build identity check. All files go into a new isolated output directory.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tracks'))
from benchmark_io import read_race
from forensics_common import normalized_sha256, potential_status
from racecraft_metrics import profile_text


def run(args, out, label, changes, jar=None, mode='legacy'):
    props = out / (label + '.properties'); log = out / (label + '.log'); stdout = out / (label + '.out')
    values = {'nPlayers': '2', 'laps': '1', 'aiStartPlacement': mode, 'candidateSlots': '', 'racecraftFeatures': ''}
    values.update(changes)
    props.write_text(profile_text(ROOT / 'tracks/lap_bench.properties', values), encoding='ascii')
    jar = (jar or args.jar).resolve()
    with stdout.open('w', encoding='utf-8') as stream:
        subprocess.run(['java', '-Xmx2g', '-Djava.awt.headless=true', '-jar', str(jar), '--auto',
                        '--props', str(props), '--track', 'hairpin', '--seed', '41', '--log', str(log)],
                       check=True, timeout=600, stdout=stream, stderr=subprocess.STDOUT)
    race = read_race(log); potential_status('hairpin', stdout.read_text())
    return normalized_sha256(log.read_text()), race


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jar',type=Path,default=ROOT/'theoreticRacing.jar')
    parser.add_argument('--baseline-jar',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(argv); out=args.out.resolve(); out.mkdir(parents=True,exist_ok=False)
    results={'schema':1,'promoted':False,'jar':hashlib.sha256(args.jar.read_bytes()).hexdigest(),
             'cross_build_identity':args.baseline_jar is not None,'checks':[]}
    flags='response-cycle,duel-ties,contingent,paired-shadow'
    for mode in ('legacy','informed','scatter'):
        baseline,_=run(args,out,mode+'-baseline',{},args.baseline_jar,mode)
        for name,changes in [('off',{}), ('no-slots',{'racecraftFeatures':flags}),
                              ('zero',{'candidateSlots':'1','racecraftFeatures':flags,'racecraftTrials':'0'})]:
            actual,_=run(args,out,mode+'-'+name,changes,mode=mode)
            if actual != baseline: raise AssertionError(f'{mode} {name} changed champion behaviour')
            results['checks'].append(mode+'-'+name)
    for flag in ('response-cycle','duel-ties','contingent','paired-shadow','paired-value',
                 'response-cycle,duel-ties,contingent'):
        # No trained model is supplied here: paired modes explicitly test fallback.
        name=flag.replace(',','-')
        digest,_=run(args,out,name,{'candidateSlots':'1','racecraftFeatures':flag,'racecraftTrials':'8'})
        audited,_=run(args,out,name+'-audit',{'candidateSlots':'1','racecraftFeatures':flag,
                                           'racecraftTrials':'8','racecraftAudit':'true'})
        if digest != audited: raise AssertionError(f'{flag} audit changed behaviour')
        results['checks'].append(name+'-audit-identity')
    tools=ROOT/'tools/racecraft_pairs.py'; study=out/'study.properties'
    study.write_text(profile_text(ROOT/'tracks/lap_bench.properties',{'nPlayers':'2','laps':'1',
        'candidateSlots':'1','racecraftFeatures':'response-cycle,duel-ties','racecraftTrials':'8'}),encoding='ascii')
    capture=out/'capture'; labels=out/'labels'; model=out/'model'
    commands=[['capture','--jar',str(args.jar.resolve()),'--props',str(study),'--tracks','hairpin','chicane',
               '--seeds','41','--limit','2','--out',str(capture)],
              ['label','--capture',str(capture),'--limit','1','--out',str(labels)],
              ['train','--labels',str(labels),'--holdout-families','chicane','--out',str(model)]]
    for command in commands:
        subprocess.run([sys.executable,str(tools),*command],check=True,timeout=1800)
    labelled=json.loads((labels/'manifest.json').read_text())['stats']
    if labelled.get('exact_controls',0)<2 or labelled.get('pairs',0)<2:
        raise AssertionError('pipeline did not exercise complete controls and disputed-action labels')
    results['pipeline']=labelled
    results['model_validation']=json.loads((model/'validation.json').read_text())['stats']
    results['checks'].append('complete-referee-control-label-train')
    # Apply the model produced by the SAME executable/profile, rather than merely
    # checking that a missing model falls back. Out-of-domain falls back by design.
    for flag in ('paired-shadow','paired-value'):
        changes={'candidateSlots':'1','racecraftFeatures':'response-cycle,duel-ties,'+flag,'racecraftTrials':'8',
                 'racecraftAudit':'true'}
        # run() takes an inline profile so the coefficients, not a mutable path,
        # are bound into this exact race's input file.
        from benchmark_io import read_properties
        loaded=read_properties(model/'model.properties')
        changes.update({'racecraftModel.'+k:v for k,v in loaded.items()})
        run(args,out,'trained-'+flag,changes)
        results['checks'].append('trained-'+flag)
    (out/'validation.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())
