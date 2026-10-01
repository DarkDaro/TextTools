# -*- coding: utf-8 -*-
"""
registry_merge — добавление кандидатов из YAML registry-builder'а в реестр (01.10).

До сих пор найденных кандидатов приходилось копировать в characters.yaml
вручную. Здесь: отчёт «что будет добавлено» и по --add дописывание
в реестр (с .bak-бэкапом). Существующие имена/формы не дублируются.

Использование:
  python registry_merge.py --candidates candidates.yaml --registry characters.yaml
  python registry_merge.py --candidates candidates.yaml --registry characters.yaml --add
  python registry_merge.py --candidates candidates.yaml --registry characters.yaml --names Эрика,Кайдзо
"""
import argparse
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import name_registry as nr


def plan(candidates_path, registry_path, names=None):
    """(новые записи, пропущенные). Кандидаты, чьи имена/формы ещё не в реестре."""
    cand = nr.load_registry(candidates_path)
    chars = nr.load_registry(registry_path)
    known = nr.known_forms(chars)
    existing = {c["имя"].lower() for c in chars}
    want = {n.strip().lower() for n in (names or []) if n.strip()}
    new, skipped = [], []
    for c in cand:
        nm = c["имя"]
        if want and nm.lower() not in want:
            continue
        if nm.lower() in existing or nm.lower() in known:
            skipped.append((nm, "уже в реестре"))
            continue
        forms = [w for w in c.get("формы", []) if w.lower() not in known]
        new.append({"имя": nm, "формы": forms or [nm],
                    "старое": [], "старое_опасное": [], "опечатки": []})
    return new, skipped


def run(candidates_path, registry_path, names=None, add=False, out=None):
    if not Path(candidates_path).exists():
        print(f"Файл кандидатов не найден: {candidates_path}")
        return 1
    if not Path(registry_path).exists():
        print(f"Реестр не найден: {registry_path}")
        return 1
    new, skipped = plan(candidates_path, registry_path, names)
    print(f"Кандидатов к добавлению: {len(new)}, пропущено: {len(skipped)}")
    for nm, why in skipped:
        print(f"  [пропуск] {nm}: {why}")
    for c in new:
        print(f"  + {c['имя']}: {', '.join(c['формы'][:6])}"
              + ("…" if len(c["формы"]) > 6 else ""))
    if not new:
        print("Добавлять нечего.")
        return 0
    if not add:
        print("\nРЕЖИМ ОТЧЁТА — реестр не изменён. Для добавления: --add / галочка.")
        return 0
    p = Path(registry_path)
    shutil.copy2(p, str(p) + ".bak")
    chars = nr.load_registry(registry_path)
    chars.extend(new)
    nr.save_registry(registry_path, chars)
    print(f"\nДобавлено {len(new)} в {registry_path} (бэкап: {p}.bak)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Добавление кандидатов в реестр персонажей")
    ap.add_argument("--candidates", required=True, help="YAML кандидатов")
    ap.add_argument("--registry", required=True, help="YAML реестра")
    ap.add_argument("--names", help="добавить только эти имена (через запятую)")
    ap.add_argument("--add", action="store_true", help="реально дописать (с .bak)")
    ap.add_argument("--out", help="отчёт в .md")
    args = ap.parse_args(argv)
    names = [n for n in (args.names or "").split(",") if n.strip()] or None
    return run(args.candidates, args.registry, names=names, add=args.add,
               out=args.out)


if __name__ == "__main__":
    sys.exit(main())
