#!/usr/bin/env python3
"""Independent strategy arms, current-master identity and complete referee tails.
This is a functional regression suite, not a policy-promotion screen.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import racecraft_next_cli as base

FLAGS='suffix-manoeuvres,response-strategy,place-certificates,forced-sequence,continuation-policies,ordered-blockade'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--baseline-jar',type=Path,required=True)
    args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    jar=(base.ROOT/'theoreticRacing.jar').resolve()
    records=[];count=0
    for track,n,mode in [('hairpin',2,'legacy'),('circle',4,'informed')]:
        root=track+'-'+mode
        control=base.race(out,root+'-control',jar,track,n,mode,3,{})
        baseline=base.race(out,root+'-master',args.baseline_jar.resolve(),track,n,mode,3,{})
        if control!=baseline:raise AssertionError(root+': default changed current master')
        count+=2
        for label,properties in [
            ('no-slots',dict(racecraftNext=FLAGS)),
            ('zero',dict(candidateSlots='1',racecraftNext=FLAGS,racecraftStrategyNodes='0'))]:
            value=base.race(out,root+'-'+label,jar,track,n,mode,3,properties);count+=1
            if value!=control:raise AssertionError(root+': inactive '+label+' changed race')
        for arm in FLAGS.split(',')+['combined']:
            properties=dict(candidateSlots='1',racecraftNext=FLAGS if arm=='combined' else arm)
            label=root+'-'+arm
            before=base.race(out,label,jar,track,n,mode,3,properties)
            audit=base.race(out,label+'-audit',jar,track,n,mode,3,dict(properties,racecraftCapture='true',racecraftCaptureLimit='10000'))
            count+=2
            if before!=audit:raise AssertionError(label+': observation changed policy')
            process=(out/(label+'-audit.process')).read_text(encoding='utf-8')
            record=dict(track=track,mode=mode,arm=arm,changed=before!=control,auditIdentity=True,
                        responseSnapshots=process.count('RACECRAFT_STATE rc6,'))
            records.append(record);print(json.dumps(record),flush=True)
    old=base.FLAGS
    try:
        base.FLAGS=FLAGS
        corpus=[base.check_corpus(out,jar,'hairpin','legacy'),base.check_corpus(out,jar,'circle','informed')]
    finally:base.FLAGS=old
    (out/'validation.json').write_text(json.dumps(dict(functionalRaces=count,arms=records,corpus=corpus,
        corpusCases=6,performanceScreen=False,promoted=False),indent=2)+'\n',encoding='utf-8')
    print(f'Strategy controls: {count} complete races and six full-suffix counterfactual cases OK',flush=True)

if __name__=='__main__':main()
