#!/usr/bin/env python3
"""Independent traffic experiment controls; not performance promotion data."""
import argparse
import json
from pathlib import Path
import sys
import racecraft_next_cli as base

FLAGS='denial,manoeuvre,checkpoint-traffic,decision-endpoint,staged-order,short-transitions'

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    jar=(base.ROOT/'theoreticRacing.jar').resolve();results=[]
    for track,n,mode in [('hairpin',2,'legacy'),('circle',4,'informed')]:
        control=base.race(out,track+'-control',jar,track,n,mode,3,{})
        inactive=base.race(out,track+'-no-slots',jar,track,n,mode,3,dict(racecraftNext=FLAGS))
        if inactive!=control:raise AssertionError('empty slots changed race')
        zero=base.race(out,track+'-zero',jar,track,n,mode,3,dict(candidateSlots='1',racecraftNext='manoeuvre',racecraftManoeuvreNodes='0'))
        if zero!=control:raise AssertionError('zero budget changed race')
        for flag in FLAGS.split(','):
            props=dict(candidateSlots='1',racecraftNext=flag)
            label=track+'-'+flag
            a=base.race(out,label,jar,track,n,mode,3,props)
            b=base.race(out,label+'-audit',jar,track,n,mode,3,dict(props,racecraftCapture='true',racecraftCaptureLimit='10000'))
            if a!=b:raise AssertionError(label+': audit changed decisions')
            record=dict(track=track,flag=flag,changed=a!=control,auditIdentity=True)
            results.append(record);print(json.dumps(record),flush=True)
    (out/'validation.json').write_text(json.dumps(dict(functionalRaces=30,arms=results,promotion=False),indent=2)+'\n')
    print('Traffic controls: 30 complete independent-arm/default/zero-budget races OK',flush=True)

if __name__=='__main__':main()
