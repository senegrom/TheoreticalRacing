#!/usr/bin/env python3
"""Offline own-place-first cross-play and bounded counterpolicy evolution.

Consumes a verified racecraft capture. Every trial runs reacting controllers to
complete referee classification; no incomplete result enters fitness. This is a
discovery tool, not a champion-promotion runner or an automatically installed AI.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path
import random
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import racecraft_corpus as corpus
import racecraft_validation as validation

GENES=((0,2,4,6,8,12),(4,8,12,20),(2,4,6,8,12))

def profile(name: str) -> str:
    if name in ('champion','scorer','pace'): return name
    match=re.fullmatch(r'g_(\d+)_(\d+)_(\d+)',name)
    if not match: raise ValueError('unknown league profile')
    s,r,h=map(int,match.groups())
    if not 0<=s<=12 or not 1<=r<=20 or not 2<=h<=12 or name!=f'g_{s}_{r}_{h}':
        raise ValueError('invalid league genome')
    return name

def mutate(name: str,rng: random.Random) -> str:
    parent=[int(x) for x in name.split('_')[1:]] if name.startswith('g_') else [0,20,4]
    index=rng.randrange(3);parent[index]=rng.choice(GENES[index])
    return 'g_'+'_'.join(map(str,parent))

def fitness(rows: list[tuple[int,int]]) -> tuple[Fraction,Fraction]:
    if not rows: raise ValueError('empty league fitness')
    if any(type(p) is not int or p<1 or type(t) is not int or t<0 for p,t in rows): raise ValueError('invalid own result')
    return Fraction(sum(p for p,_ in rows),len(rows)),Fraction(sum(t for _,t in rows),len(rows))

def validate_answer(case: dict,request: str,response: dict,bound: int,names: list[str]) -> dict:
    if response.get('schema')!=1 or response.get('requestSha256')!=validation.sha(request) or response.get('maxMoves')!=bound:
        raise ValueError('league response is not bound to the complete request')
    if response.get('profiles')!='/'.join(names): raise ValueError('wrong league controllers')
    trial=response.get('trial')
    if not isinstance(trial,dict) or not validation.validate_trial(case,trial,bound):
        raise ValueError('league trial incomplete; no fitness label')
    _,end=validation.snapshot(trial['finalState'])
    moves=[0]*len(end)
    for transition in trial['trace']: moves[int(transition.split(':')[0])]+=1
    if response.get('places')!=[r[6] for r in end] or response.get('moves')!=moves:
        raise ValueError('league all-player results disagree with trace')
    return trial

class Oracle:
    def __init__(self,directory: Path,out: Path,args):
        self.directory=directory.resolve();self.out=out;out.mkdir(parents=True,exist_ok=False)
        self.args=args;self.manifest=json.loads((self.directory/'manifest.json').read_text())
        if self.manifest.get('schema')!=2: raise ValueError('recapture with current corpus protocol')
        m=self.manifest;self.jar=Path(m['jar']);self.source=self.directory/'race.properties'
        self.track=Path(m['trackFile']);self.states=self.directory/'states.jsonl'
        self.java,version=corpus.java_runtime(args.java,m['heap'])
        if version!=m['javaVersion']: raise ValueError('capture and league Java runtimes differ')
        self.cases=[json.loads(row) for row in self.states.read_text().splitlines()][args.offset:args.offset+args.cases]
        if not self.cases: raise ValueError('no training positions selected')
        configured,update,_=corpus.helpers();self.roster=configured(self.source)
        self.race=(self.directory/'race.log').read_text(encoding='utf-8')
        self.props=out/'league.properties';self.props.write_bytes(self.source.read_bytes());update(self.props,{'racecraftCapture':'false'})
        self.props_hash=corpus.digest(self.props);self.cache={};self.readings=[]
        self.check_inputs()
        # Authenticate the supplied generating history via a complete control
        # continuation before using any counterpolicy result from each root.
        for case in self.cases:
            _,cars=validation.snapshot(case['snapshot']);names=['champion']*len(cars)
            control=self.run(case,names)
            if control['trial']['action']!=case['actual']: raise ValueError('league control first action differs')
            validation.validate_control(case,control['trial'],self.race,self.roster)
    def check_inputs(self):
        m=self.manifest
        if (m['inputs']!=dict(jar=corpus.digest(self.jar),track=corpus.digest(self.track),profile=corpus.digest(self.source))
                or m['statesSha256']!=corpus.digest(self.states) or m['raceSha256']!=corpus.digest(self.directory/'race.log')
                or m['tooling']!=corpus.tooling_identity() or self.props_hash!=corpus.digest(self.props)):
            raise ValueError('league inputs changed or capture belongs to different tools')
    def run(self,case,names):
        self.check_inputs();names=[profile(name) for name in names]
        request=f"league1,{self.args.max_moves},{'/'.join(names)}|{case['snapshot']}"
        key=validation.sha(request)
        if key in self.cache: return self.cache[key]
        prefix=self.out/key;query=prefix.with_suffix('.in');answer=prefix.with_suffix('.json')
        query.write_text(request+'\n',encoding='utf-8')
        command=[self.java,self.manifest['heap'],'-Djava.awt.headless=true','-jar',str(self.jar),
                 '--auto','--track',self.manifest['track'],'--props',str(self.props),'--seed',str(self.manifest['seed']),
                 '--query-moves',str(query),str(answer)]
        result,seconds=corpus.run_java(command,corpus.ROOT,prefix.with_suffix('.process.log'),self.args.timeout)
        _,_,potential_status=corpus.helpers()
        if potential_status(self.manifest['track'],result.stdout+'\n'+result.stderr)!=self.manifest['potential']:
            raise ValueError('league map preparation differs from capture')
        value=json.loads(answer.read_text());validate_answer(case,request,value,self.args.max_moves,names)
        self.check_inputs();self.cache[key]=value
        self.readings.append(dict(request=key,seconds=seconds,profiles=names,case=case['id']))
        return value
    def evaluate(self,actor,opponents):
        rows=[]
        for case in self.cases:
            _,cars=validation.snapshot(case['snapshot'])
            for rival in opponents:
                for slot,car in enumerate(cars):
                    if car[6]: continue
                    names=[rival]*len(cars);names[slot]=actor
                    result=self.run(case,names)
                    rows.append((result['places'][slot],result['moves'][slot]))
        return fitness(rows),len(rows)

def number_pair(score): return [float(score[0]),float(score[1])]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--heldout-capture',type=Path)
    parser.add_argument('--pool',default='champion,scorer,pace');parser.add_argument('--seed',type=int,default=1)
    parser.add_argument('--generations',type=int,default=1);parser.add_argument('--mutations',type=int,default=4)
    parser.add_argument('--cases',type=int,default=2);parser.add_argument('--offset',type=int,default=0)
    parser.add_argument('--max-moves',type=int,default=10000);parser.add_argument('--java',default='java')
    parser.add_argument('--timeout',type=int,default=180)
    args=parser.parse_args()
    if not 0<=args.generations<=20 or not 1<=args.mutations<=64 or not 1<=args.cases<=100 or args.offset<0 or not 1<=args.max_moves<=100000:
        raise ValueError('league work limits out of range')
    pool=list(dict.fromkeys(profile(name.strip()) for name in args.pool.split(',')))
    if not 2<=len(pool)<=12: raise ValueError('league needs two to twelve distinct profiles')
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    oracle=Oracle(args.capture,out/'training',args);rng=random.Random(args.seed)
    matrix=[];pair_scores={}
    for actor,rival in itertools.product(pool,repeat=2):
        score,count=oracle.evaluate(actor,[rival]);pair_scores[actor,rival]=score
        matrix.append(dict(actor=actor,opponent=rival,ownMean=number_pair(score),observations=count))
    candidate='g_0_20_4';history=[]
    for generation in range(args.generations):
        # Counterpolicies are selected for their own result against the current
        # candidate, not for damage to a target or for field-wide crash counts.
        proposals={candidate}
        for _ in range(args.mutations*8):
            proposals.add(mutate(candidate,rng))
            if len(proposals)>=args.mutations+1: break
        measured=[]
        for proposal in sorted(proposals):
            score,count=oracle.evaluate(proposal,[candidate]);measured.append((score,proposal,count))
        measured.sort();counter=measured[0][1]
        if counter not in pool: pool.append(counter)
        best,count=oracle.evaluate(candidate,pool);selected=candidate
        for proposal in sorted(proposals):
            score,n=oracle.evaluate(proposal,pool)
            if score<best: best=score;selected=proposal;count=n
        history.append(dict(generation=generation,counterpolicy=counter,candidate=selected,ownMean=number_pair(best),observations=count))
        candidate=selected
    # Nontransitivity is reported only for genuine two-live-car roots.
    cycles=[]
    if all(sum(r[6]==0 for r in validation.snapshot(c['snapshot'])[1])==2 for c in oracle.cases):
        initial=list(dict.fromkeys(r['actor'] for r in matrix))
        for a,b,c in itertools.combinations(initial,3):
            for x,y,z in ((a,b,c),(a,c,b)):
                if pair_scores[x,y]<pair_scores[y,x] and pair_scores[y,z]<pair_scores[z,y] and pair_scores[z,x]<pair_scores[x,z]:
                    cycles.append([x,y,z])
    heldout=None
    if args.heldout_capture:
        if args.heldout_capture.resolve()==args.capture.resolve(): raise ValueError('held-out capture must be separate')
        test=Oracle(args.heldout_capture,out/'heldout',args);score,count=test.evaluate(candidate,pool)
        heldout=dict(ownMean=number_pair(score),observations=count,manifest=corpus.digest(args.heldout_capture/'manifest.json'))
    oracle.check_inputs()
    summary=dict(schema=1,seed=args.seed,pool=pool,candidate=candidate,crossPlay=matrix,cycles=cycles,evolution=history,
                 heldout=heldout,trialCount=len(oracle.cache),trials=oracle.readings,
                 captureManifestSha256=corpus.digest(args.capture/'manifest.json'),
                 toolSha256=corpus.digest(Path(__file__)),promoted=False,
                 interpretation='Completed conditional continuations on legally captured boards; not fleet promotion evidence.')
    corpus.atomic_json(out/'summary.json',summary)
    (out/'COMPLETE').write_text(corpus.digest(out/'summary.json')+'\n')
    print(json.dumps(dict(trials=len(oracle.cache),candidate=candidate,promoted=False)))

if __name__=='__main__': main()
