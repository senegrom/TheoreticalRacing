#!/usr/bin/env python3
"""Dual-order runtime screen for primitive boundary intersections."""
from __future__ import annotations
import argparse, hashlib, json, os, re, statistics, subprocess, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CASES = [("monaco",1,10),("nurburgring",17,19),("zandvoort",31,33),("interlagos",45,47),("sprint",1,100)]
def write_props(path):
    lines=[]
    for line in (ROOT/"tracks"/"bench.properties").read_text().splitlines():
        if re.match(r"^player[1-8]Kind=",line): line=line.split("=",1)[0]+"=AI2"
        lines.append(line)
    path.write_text("\n".join(lines)+"\n")
def run(jar,track,start,end,label,work,cache):
    pattern=work/f"{label}-{track}.log"; env=os.environ.copy(); env["RACING_REACH_CACHE"]=str(cache)
    began=time.perf_counter(); result=subprocess.run(["java","-Djava.awt.headless=true","-jar",str(jar.resolve()),"--auto","--track",track,"--props",str(work/"bench.properties"),"--log",str(pattern),"--seed",f"{start}-{end}"],cwd=ROOT,env=env,text=True,capture_output=True,timeout=7200)
    elapsed=time.perf_counter()-began
    if result.returncode: raise RuntimeError(f"{label} {track} failed: {result.stderr[-5000:]}")
    stem=pattern.with_suffix(""); hashes={}
    for seed in range(start,end+1):
        log=Path(f"{stem}_s{seed}{pattern.suffix}")
        if not log.is_file(): raise FileNotFoundError(log)
        hashes[seed]=hashlib.sha256(log.read_bytes()).hexdigest()
    return elapsed,hashes
def main():
    p=argparse.ArgumentParser(); p.add_argument("--baseline",type=Path,required=True); p.add_argument("--candidate",type=Path,required=True); p.add_argument("--pairs",type=int,default=4); p.add_argument("--out",type=Path,required=True); a=p.parse_args(); rows=[]
    for track,start,end in CASES:
        with tempfile.TemporaryDirectory(prefix=f"round142-{track}-") as d:
            work=Path(d); cache=work/"reach-cache"; write_props(work/"bench.properties"); run(a.baseline,track,start,end,"warm-baseline",work,cache); run(a.candidate,track,start,end,"warm-candidate",work,cache); bt=[]; ct=[]; pr=[]
            for i in range(a.pairs):
                order=[("baseline",a.baseline),("candidate",a.candidate)]
                if i&1: order.reverse()
                m={label:run(jar,track,start,end,f"pair-{i}-{label}",work,cache) for label,jar in order}; b,bh=m["baseline"]; c,ch=m["candidate"]
                if bh!=ch: raise RuntimeError(f"{track} byte mismatch: {[s for s in bh if bh[s]!=ch.get(s)]}")
                bt.append(b); ct.append(c); pr.append(c/b)
        mb=statistics.median(bt); mc=statistics.median(ct); row={"track":track,"start":start,"end":end,"races_per_run":end-start+1,"baseline_times":bt,"candidate_times":ct,"pair_ratios":pr,"median_baseline":mb,"median_candidate":mc,"ratio":mc/mb,"byte_identical":True}; rows.append(row); print(json.dumps(row,indent=2),flush=True)
    tb=sum(r["median_baseline"] for r in rows); tc=sum(r["median_candidate"] for r in rows); out={"pairs_per_case":a.pairs,"cases":rows,"total_median_baseline":tb,"total_median_candidate":tc,"aggregate_ratio":tc/tb,"screen_threshold":0.97}; out["promising"]=out["aggregate_ratio"]<=out["screen_threshold"]; a.out.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(json.dumps(out,indent=2,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
