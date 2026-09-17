#!/usr/bin/env python3
"""Real JVM wiring for opt-in second-batch research modes. Tiny pilot only.
Preserves profiles, complete races, source replays, counterfactuals and leagues.
"""
from pathlib import Path
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracks.benchmark_io import read_race,update_properties
from tracks.forensics_common import normalized_lines


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--heap',default='-Xmx8g');parser.add_argument('--out',type=Path)
    parser.add_argument('--jar',type=Path,default=ROOT/'theoreticRacing.jar')
    args=parser.parse_args()
    if any(os.environ.get(k,'').strip() for k in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')):
        raise ValueError('use an explicit heap, not ambient VM flags')
    out=args.out or Path(tempfile.mkdtemp(prefix='racecraft-next-'))
    if args.out:out.mkdir(parents=True,exist_ok=False)
    out=out.resolve();jar=args.jar.resolve();cmd=[sys.executable,str(ROOT/'tracks/racecraft_next.py')]
    def run(name,command,success=True):
        p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=900)
        (out/(name+'.stdout')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
        if success and p.returncode:raise AssertionError(name+' failed\n'+p.stdout+p.stderr)
        if not success and not p.returncode:raise AssertionError(name+' unexpectedly succeeded')
        return p
    base=out/'base.properties';base.write_text('nPlayers=2\nplayer1Kind=AI1\nplayer2Kind=AI1\nplayer1Name=P1\nplayer2Name=P2\nlaps=1\n')
    def race(name,profile,track='hairpin'):
        run(name,['java',args.heap,'-Djava.awt.headless=true','-jar',str(jar),'--auto','--track',track,
                  '--props',str(profile),'--log',str(out/(name+'.log')),'--seed','1'])
        return read_race(out/(name+'.log'))
    race('champion',base)
    arm=out/'arm.properties'
    run('profile',cmd+['profile','--base',str(base),'--out',str(arm),'--experiments','diverse,progressive',
                       '--rounds','2','--budget','12','--alternatives','2'])
    # No selected slot => exact default move and result trace.
    race('disabled',arm)
    assert normalized_lines((out/'champion.log').read_text())==normalized_lines((out/'disabled.log').read_text())
    update_properties(arm,{'candidateSlots':'1,2','racecraft.audit':'true'})
    race('experimental',arm)
    for entry in (out/'experimental.stderr').read_text().splitlines():
        if entry.startswith('RACECRAFT '):
            values=dict(re.findall(r'(\w+)=([^ ]+)',entry));assert int(values['policyCalls'])<=12
    zero=out/'zero.properties';zero.write_bytes(arm.read_bytes());update_properties(zero,{'racecraft.policyBudget':'0'})
    race('zero',zero)
    assert normalized_lines((out/'champion.log').read_text())==normalized_lines((out/'zero.log').read_text())
    race('circle',base,'circle')
    for name,log,profile,track,family,mode,continuing in (
            ('train','experimental',arm,'hairpin','open-u','experimental','source'),
            ('validation','circle',base,'circle','closed-loop','champion','champion')):
        run('collect-'+name,cmd+['collect','--jar',str(jar),'--props',str(profile),'--log',str(out/(log+'.log')),
             '--track',track,'--family',family,'--state-policy',mode,'--continuation',continuing,
             '--moves','1,8' if name=='train' else '1','--heap='+args.heap,'--out',str(out/name)])
    m=out/'model.json'
    run('train',cmd+['train','--train',str(out/'train'),'--validation',str(out/'validation'),'--out',str(m),'--epochs','40'])
    run('leakage-rejection',cmd+['evaluate','--data',str(out/'validation'),'--model',str(m),'--out',str(out/'invalid-eval')],False)
    run('regret',cmd+['regret','--data',str(out/'train'),'--out',str(out/'regret.json')])
    trained=out/'learned.properties'
    run('trained-profile',cmd+['profile','--base',str(base),'--model',str(m),'--out',str(trained),
                             '--experiments','diverse,progressive,lexicographic','--budget','24','--rounds','1'])
    update_properties(trained,{'candidateSlots':'1,2'});race('learned',trained)
    # Source states, but a different declared continuation policy.
    run('collect-champion-follow',cmd+['collect','--jar',str(jar),'--props',str(arm),'--log',str(out/'experimental.log'),
         '--track','hairpin','--family','open-u','--state-policy','experimental','--continuation','champion',
         '--moves','8','--heap='+args.heap,'--out',str(out/'alternate-follow')])
    source=json.loads((out/'train/manifest.json').read_text());alternate=json.loads((out/'alternate-follow/manifest.json').read_text())
    assert source['generating_policy']==alternate['generating_policy']
    assert source['continuation_policy']['props_sha256']!=alternate['continuation_policy']['props_sha256']
    # An actual eight-car field, all three deployment densities, rotated focal slots.
    pack=out/'pack.properties';pack.write_bytes(base.read_bytes())
    changes={'nPlayers':'8'}
    changes.update({'player%dKind'%i:'AI1' for i in range(1,9)});changes.update({'player%dName'%i:'P%d'%i for i in range(1,9)})
    update_properties(pack,changes);race('pack',pack)
    packarm=out/'pack-arm.properties';packarm.write_bytes(arm.read_bytes());update_properties(packarm,dict(changes,candidateSlots='1,2,3,4,5,6,7,8'))
    # Historical compatibility is tested with an explicitly v2-configured frozen
    # control here; a genuine historical-policy campaign must supply its own jar.
    spec={'version':1,'referee':'champion','baseline':'champion','candidate':'research','backgrounds':['frozen-v2'],
          'densities':[1,4,7], 'policies':[
              {'name':'champion','jar':str(jar),'props':str(pack),'protocol':'v3'},
              {'name':'frozen-v2','jar':str(jar),'props':str(pack),'protocol':'v2'},
              {'name':'research','jar':str(jar),'props':str(packarm),'protocol':'v3'}]}
    specpath=out/'league-spec.json';specpath.write_text(json.dumps(spec))
    run('league',cmd+['league','--spec',str(specpath),'--logs',str(out/'pack.log'),'--track','hairpin',
                      '--focals','0,1','--heap='+args.heap,'--out',str(out/'league')])
    league=json.loads((out/'league/report.json').read_text())
    assert league['complete_races']==12
    assert [s['density'] for s in league['slices']]==[1,4,7]
    for line in (out/'league/pairs.jsonl').read_text().splitlines():
        pair=json.loads(line);a,b=pair['arms'];assert pair['complete']
        assert [i for i,(x,y) in enumerate(zip(a['lineup'],b['lineup'])) if x!=y]==[pair['focal']]
    summary={'native_complete_races':7,'league_complete_races':12,
             'counterfactual_samples':source['samples']+alternate['samples']+json.loads((out/'validation/manifest.json').read_text())['samples'],
             'scope':'functional controls only, no performance promotion or generalization claim'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('RacecraftNextRegression:',json.dumps(summary))
    return 0


if __name__=='__main__':raise SystemExit(main())
