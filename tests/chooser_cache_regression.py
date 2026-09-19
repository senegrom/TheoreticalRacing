#!/usr/bin/env python3
"""Cache-history invariance with isolated cold, warm and post-suite directories.
This is an identity check, not a racing-policy performance screen.
"""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracks.forensics_common import normalized_sha256
from tracks.chooser_lab import digest, hashes, unchanged, write_new
from tracks.promotion_pair import require_plain_java_environment


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--heap',default='-Xmx8g');p.add_argument('--skip-suite',action='store_true',help='diagnostic only: does not establish post-suite identity')
    args=p.parse_args();require_plain_java_environment()
    if not __import__('re').fullmatch(r'-Xmx[1-9][0-9]*[kKmMgG]',args.heap):raise ValueError('one explicit heap required')
    args.out.mkdir(parents=True,exist_ok=False)
    tracked=[ROOT/'theoreticRacing.jar',ROOT/'src/tr/logic/Reachability.java',ROOT/'src/tr/logic/RaceGame.java']+sorted((ROOT/'tracks').glob('*.track'))
    before=hashes(tracked);write_new(args.out/'pending.json',before)
    test_cache=args.out/'after-tests';test_cache.mkdir()
    if not args.skip_suite:
        env=os.environ.copy();env['RACING_REACH_CACHE']=str(test_cache.resolve());env['JAVA_TOOL_OPTIONS']=args.heap
        with (args.out/'java-suites.log').open('x') as log:
            subprocess.run(['sh','run_tests.sh'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
    cases=[]
    for track,laps in [('hairpin',1),('circle',2)]:
        props=args.out/(track+'.properties');props.write_text(f'nPlayers=2\nplayer1Kind=AI2\nplayer2Kind=AI2\nlaps={laps}\n',encoding='utf-8')
        cache=args.out/(track+'-isolated');cache.mkdir();results={}
        for mode,directory in [('cold',cache),('warm',cache),('after-tests',test_cache)]:
            env=os.environ.copy();env['RACING_REACH_CACHE']=str(directory.resolve());log=args.out/f'{track}-{mode}.log'
            with (args.out/f'{track}-{mode}.stdout').open('x') as stdout, (args.out/f'{track}-{mode}.stderr').open('x') as stderr:
                subprocess.run(['java',args.heap,'-jar',str(ROOT/'theoreticRacing.jar'),'--auto','--track',track,'--props',str(props.resolve()),'--seed','1','--log',str(log.resolve())],cwd=ROOT,env=env,stdout=stdout,stderr=stderr,check=True,timeout=300)
            results[mode]=normalized_sha256(log.read_text(encoding='utf-8'))
        if len(set(results.values()))!=1:raise AssertionError('cache history changed '+track+': '+str(results))
        cases.append(dict(track=track,laps=laps,digests=results))
    unchanged(before)
    report=dict(cases=cases,post_suite=not args.skip_suite,heap=args.heap,inputs=before,
                outputs={x.name:digest(x) for x in args.out.iterdir() if x.is_file() and x.name!='pending.json'})
    write_new(args.out/'report.json',report);(args.out/'pending.json').unlink();print(json.dumps(report['cases'],indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
