from pathlib import Path
p=Path('tools/racecraft_validation.py');s=p.read_text()
s=s.replace('import racecraft_learning_memory\n','')
s=s.replace('import hashlib','import hashlib\nimport racecraft_learning_memory',1)
p.write_text(s)
