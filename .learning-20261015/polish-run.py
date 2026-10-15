from pathlib import Path
Path('docs/experiments/learning-racecraft').mkdir(parents=True,exist_ok=True)
p=Path('.learning-20261015/polish.py');s=p.read_text()
s=s.replace("edit('src/tr/logic/RacecraftReplay.java','270000','1060000',1)","edit('src/tr/logic/RacecraftReplay.java','280000','1060000',1)")
exec(compile(s,str(p),'exec'))
