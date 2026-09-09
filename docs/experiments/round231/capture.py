import hashlib, json, pathlib, runpy, subprocess, sys, time
root=pathlib.Path(__file__).resolve().parents[3]
test_args=sys.argv[3:]
test=pathlib.Path(sys.argv[1]); dest=pathlib.Path(sys.argv[2]); dest.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root/'tests')); sys.path.insert(0,str(root/'tracks'))
original=subprocess.run
counter=0
def record(*args,**kwargs):
    global counter
    started=time.monotonic()
    result=original(*args,**kwargs)
    command=args[0] if args else kwargs.get('args',[])
    if isinstance(command,(list,tuple)) and '-jar' in command:
        counter+=1
        prefix=dest/f'race-{counter:03d}'
        info={'input':kwargs.get('input'), 'command':[str(v) for v in command], 'seconds':time.monotonic()-started,'returncode':result.returncode}
        for key,suffix in [('--log','.log'),('--props','.properties')]:
            if key in command:
                path=pathlib.Path(command[command.index(key)+1])
                if path.is_file():prefix.with_suffix(suffix).write_bytes(path.read_bytes())
        for key in ['stdout','stderr']:
            text=getattr(result,key)
            if text is not None:prefix.with_suffix('.'+key).write_bytes(text.encode() if isinstance(text,str) else text)
        info['jar_sha256']=hashlib.sha256(pathlib.Path(command[command.index('-jar')+1]).read_bytes()).hexdigest()
        prefix.with_suffix('.json').write_text(json.dumps(info,indent=2)+'\n')
    return result
subprocess.run=record
sys.argv=[str(test),*test_args]
runpy.run_path(str(test),run_name='__main__')
