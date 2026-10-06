from pathlib import Path
source=Path('.traffic-20261006/apply.py').read_text()
a=source.index("p=Path('tools/racecraft_corpus.py'); t=p.read_text();")
b=source.index('\n\n# Checkpoint',a)
source=source[:a]+'''p=Path('tools/racecraft_corpus.py'); t=p.read_text()
t=one(t, "h[0] == 'rc4'", "h[0] in ('rc4', 'rc5')")
p.write_text(t)
'''+source[b:]
exec(compile(source,'.traffic-20261006/apply.py','exec'))
