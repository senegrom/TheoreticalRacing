"""Structural validator for rc7 per-race learning state; not a proof authenticator."""
from __future__ import annotations
import re

DIRECTIONS=dict(zip(('NW','N','NE','W','NONE','E','SW','S','SE'),
                    ((-1,-1),(0,-1),(1,-1),(-1,0),(0,0),(1,0),(-1,1),(0,1),(1,1))))

def number(text: str, low: int, high: int) -> int:
    value=int(text)
    if str(value)!=text or not low<=value<=high: raise ValueError('noncanonical learning integer')
    return value

def pose(text: str) -> tuple[int,...]:
    fields=text.split('_')
    if len(fields)!=7: raise ValueError('learning pose shape')
    limits=((0,2147483647),(0,2147483647),(-100000,100000),(-100000,100000),(0,2147483647),(0,2),(0,1))
    return tuple(number(v,*bounds) for v,bounds in zip(fields,limits))

def segment(text: str):
    fields=text.split('~')
    if len(fields)!=3: raise ValueError('learning segment shape')
    start,end=pose(fields[0]),pose(fields[2]);actions=fields[1].split('+')
    if not 1<=len(actions)<=4 or any(a not in DIRECTIONS for a in actions): raise ValueError('learning actions')
    if start[4]!=end[4] or start[6]!=end[6]: raise ValueError('segment crosses lap/grid boundary')
    x,y,vx,vy=start[:4]
    for action in actions:
        dx,dy=DIRECTIONS[action];vx+=dx;vy+=dy;x+=vx;y+=vy
    if (x,y,vx,vy)!=end[:4]: raise ValueError('learning segment kinematics')
    return start,actions,end

def proof(text: str,n: int):
    if text=='-': return 0
    rows=text.split('!');header=rows[0].split('_')
    if len(header)!=2 or not 2<=len(rows)<=513: raise ValueError('proof table shape')
    number(header[0],1,n);number(header[1],0,2147483647)
    keys=[]
    for row in rows[1:]:
        fields=row.split('_')
        if len(fields)!=3 or not re.fullmatch('[0-9a-f]{64}',fields[0]) or fields[1] not in DIRECTIONS:
            raise ValueError('proof answer shape')
        number(fields[2],1,12);keys.append(fields[0])
    if keys!=sorted(set(keys)): raise ValueError('proof keys duplicate/unsorted')
    return len(keys)

def validate(text: str,n: int) -> dict:
    if type(text) is not str or not 1<=n<=9 or len(text)>524288: raise ValueError('learning memory bound')
    if text=='-': return dict(segments=0,observations=0,proofStates=0)
    slots=text.split('.')
    if len(slots)!=n: raise ValueError('learning memory roster')
    segments=observations=proof_states=0
    for slot in slots:
        fields=slot.split('@')
        if len(fields)!=3: raise ValueError('learning slot shape')
        for index,cap in ((0,64),(1,4)):
            rows=[] if fields[index]=='-' else fields[index].split('/')
            if len(rows)>cap: raise ValueError('learning archive/trail bound')
            if index==0 and len(set(rows))!=len(rows): raise ValueError('duplicate learning segment')
            previous=None
            for row in rows:
                start,actions,end=segment(row)
                if index==0 and len(actions)<2: raise ValueError('short learned segment')
                if index==1 and (len(actions)!=1 or previous is not None and previous!=start):
                    raise ValueError('discontinuous committed history')
                previous=end
            if index==0: segments+=len(rows)
            else: observations+=len(rows)
        proof_states+=proof(fields[2],n)
    if not segments and not observations and not proof_states: raise ValueError('noncanonical empty learning memory')
    return dict(segments=segments,observations=observations,proofStates=proof_states)
