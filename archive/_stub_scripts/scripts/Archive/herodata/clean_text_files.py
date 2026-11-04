# stub-заглушка clean_text_files: clean_text_files, китайских
import re, sys
from pathlib import Path
args = sys.argv[1:]
fix = "--fix" in args
targets = []
for a in args:
    if a.startswith("--"):
        continue
    p = Path(a)
    if p.is_file():
        targets.append(p)
    elif p.is_dir():
        targets += [f for f in sorted(p.rglob("*"))
                    if f.is_file() and f.suffix in (".txt", ".md")]
for f in targets:
    t = f.read_text(encoding="utf-8")
    if fix:
        f.write_text(re.sub(r"[\u4e00-\u9fff]+", "", t), encoding="utf-8")
    else:
        print("DRY-RUN", f)
