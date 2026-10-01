# -*- coding: utf-8 -*-
"""
character_matrix — матрица упоминаний персонажей по файлам (01.10).

Где и сколько раз упоминается каждый персонаж реестра (текущие формы +
падежные через pymorphy3). Для сюжета: «персонаж исчезает после главы N».

Использование:
  python textools.py matrix --input <тексты> --registry characters.yaml
      [--out report.md] [--limit N] [--verbose]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import morph
from core import name_registry as nr
from core import text_parser as tp


def run(input_path, registry_path, limit=None, verbose=False, out=None):
    chars = nr.load_registry(registry_path)
    if not chars:
        print(f"Реестр пуст или не найден: {registry_path}")
        return 1

    # 02.10 (СЛ7): один комбинированный паттерн на всех персонажей —
    # одна прогонка finditer по строке; атрибуция по named-группе
    groups = [(c["имя"],
               morph.term_patterns([c["имя"]] + list(c["формы"]), expand=True))
              for c in chars]
    combined, gmap = morph.combine_patterns(groups)

    counts = {c["имя"]: {} for c in chars}  # имя -> {файл: кол-во}
    files = list(tp.iter_text_files(input_path, limit=limit))
    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)
    files_n = 0
    for path in files:
        if tp.stop_requested():
            print("Остановлено пользователем.")
            break
        files_n += 1
        print(f"PROGRESS:{files_n}/{total}", flush=True)
        text = tp.read_text(path)
        if not text:
            continue
        if combined is None:
            continue
        for ln in text.splitlines():
            for m in combined.finditer(ln):
                name = gmap[m.lastgroup]
                key = str(path)
                counts[name][key] = counts[name].get(key, 0) + 1

    print(f"Файлов: {files_n}, персонажей: {len(chars)}\n")
    for c in chars:
        name = c["имя"]
        per = counts[name]
        total = sum(per.values())
        mark = "" if total else "  (не встречается)"
        print(f"{name}: всего {total}{mark}")
        for f, n in sorted(per.items(), key=lambda kv: -kv[1]):
            print(f"    {n:>4}  {f}")

    if out:
        lines = [f"# Матрица упоминаний — {input_path}", ""]
        for c in chars:
            name = c["имя"]
            lines.append(f"## {name} (всего {sum(counts[name].values())})")
            for f, n in sorted(counts[name].items(), key=lambda kv: -kv[1]):
                lines.append(f"- {n} — {f}")
            if not counts[name]:
                lines.append("- не встречается")
            lines.append("")
        Path(out).write_text("\n".join(lines), encoding="utf-8")
        print(f"\nОтчёт: {out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Матрица «персонаж × файл» по реестру")
    ap.add_argument("--input", required=True, help="файл или папка")
    ap.add_argument("--registry", required=True, help="YAML реестр")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--out", help="отчёт в .md")
    args = ap.parse_args(argv)
    return run(args.input, args.registry, limit=args.limit,
               verbose=args.verbose, out=args.out)


if __name__ == "__main__":
    sys.exit(main())
