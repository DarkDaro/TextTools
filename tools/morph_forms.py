# -*- coding: utf-8 -*-
"""
morph_forms — подсказка падежных форм для реестра персонажей (01.10).

Сравнивает формы в реестре с падежными формами pymorphy3 и показывает
недостающие. По --fill дописывает их в реестр (с .bak-бэкапом).

Использование:
  python morph_forms.py --registry characters.yaml            — отчёт
  python morph_forms.py --registry characters.yaml --fill     — дописать
  python textools.py forms --registry characters.yaml
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import morph
from core import name_registry as nr


def suggestions(chars):
    """{имя: {поле: [недостающие формы]}} по всем полям, кроме опасных."""
    out = {}
    for c in chars:
        existing = {c["имя"].lower()}
        for fld in nr.FIELDS[1:]:
            existing |= {w.lower() for w in c[fld]}
        per = {}
        for fld in ("формы", "старое", "опечатки"):
            missing = set()
            for w in c[fld]:
                missing |= {f for f in morph.word_forms(w)
                            if f.lower() not in existing}
            if missing:
                per[fld] = sorted(missing)
                existing |= {m.lower() for m in missing}
        if per:
            out[c["имя"]] = per
    return out


def run(registry_path, fill=False, out=None):
    if not morph.AVAILABLE:
        print("pymorphy3 не установлен: pip install pymorphy3")
        return 1
    chars = nr.load_registry(registry_path)
    if not chars:
        print(f"Реестр пуст или не найден: {registry_path}")
        return 1
    print(f"pymorphy3: подключён. Реестр: {registry_path}\n")
    sug = suggestions(chars)
    if not sug:
        print("Все падежные формы уже в реестре.")
        return 0
    total = 0
    for name, per in sug.items():
        print(f"{name}:")
        for fld, missing in per.items():
            print(f"  {fld}: {', '.join(missing)}")
            total += len(missing)
    print(f"\nНедостающих форм: {total}")

    if out:
        lines = [f"# Недостающие падежные формы — {registry_path}", ""]
        for name, per in sug.items():
            lines.append(f"## {name}")
            for fld, missing in per.items():
                lines.append(f"- {fld}: {', '.join(missing)}")
            lines.append("")
        Path(out).write_text("\n".join(lines), encoding="utf-8")
        print(f"Отчёт: {out}")

    if fill:
        p = Path(registry_path)
        shutil.copy2(p, str(p) + ".bak")
        for c in chars:
            per = sug.get(c["имя"], {})
            for fld, missing in per.items():
                seen = {w.lower() for w in c[fld]}
                for m in missing:
                    if m.lower() not in seen:
                        c[fld].append(m.capitalize()
                                      if fld == "формы" else m)
                        seen.add(m.lower())
        nr.save_registry(registry_path, chars)
        print(f"Реестр дополнен (бэкап: {p}.bak)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Недостающие падежные формы реестра (pymorphy3)")
    ap.add_argument("--registry", required=True, help="YAML реестр")
    ap.add_argument("--fill", action="store_true",
                    help="дописать формы в реестр (с .bak)")
    ap.add_argument("--out", help="отчёт в .md")
    args = ap.parse_args(argv)
    return run(args.registry, fill=args.fill, out=args.out)


if __name__ == "__main__":
    sys.exit(main())
