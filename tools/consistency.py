"""
02_consistency — проверка консистентности имён по реестру.
Ищет: текущие формы (ОК), старые (заменить), опасные (вручную), опечатки.
Выводит только сводку; детали по --verbose или в файл --out.

Использование:
  python textools.py consistency --input <файл/папка> --registry characters.yaml
      [--limit N] [--verbose] [--out report.md]
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import morph
from core import name_registry as nr
from core import text_parser as tp


def count_occurrences(text, terms):
    """{термин: [(файл, строка, фрагмент)]} по границам слов."""
    res = {t: [] for t in terms}
    for i, line in enumerate(text.splitlines(), 1):
        for t in terms:
            if re.search(r"(?<![А-ЯЁа-яёA-Za-z-])" + re.escape(t)
                         + r"(?![А-ЯЁа-яёA-Za-z])", line):
                res[t].append((i, line.strip()[:100]))
    return res


def run(input_path, registry_path, limit=None, verbose=False, out=None):
    chars = nr.load_registry(registry_path)
    if not chars:
        print(f"Реестр пуст или не найден: {registry_path}")
        return 1

    # собираем все термины заранее, сканируем файлы один раз
    all_terms = set()
    for c in chars:
        for fld in nr.FIELDS[1:]:
            all_terms.update(c[fld])
    # регистронезависимо: ищем точные строки как в реестре;
    # для скорости приводим строки файлов к lower и ищем lower-термины
    terms_lower = sorted({t.lower() for t in all_terms},
                         key=lambda s: -len(s))  # длинные первыми

    totals = {c["имя"]: {"ок": 0, "старое": 0, "опасное": 0, "опечатки": 0}
              for c in chars}
    details = []  # для отчёта

    # 01.10: паттерны собираются один раз; точные термины — регистро-
    # независимо, падежные формы (pymorphy3) — только с заглавной буквы
    # (эвристика имён: бытовое «лик» в нижнем регистре не считается «Ликой»)
    patmap = {}
    for c in chars:
        for fld in ("формы", "старое", "старое_опасное", "опечатки"):
            expand = fld != "старое_опасное"  # опасное — явные формы, не расширяем
            patmap[(c["имя"], fld)] = morph.term_patterns(c[fld], expand=expand)

    files_n = 0
    for path in tp.iter_text_files(input_path, limit=limit):
        if tp.stop_requested():
            print("Остановлено пользователем.")
            break
        text = tp.read_text(path)
        if not text:
            continue
        files_n += 1
        lines = text.splitlines()
        for c in chars:
            for fld, key in (("формы", "ок"), ("старое", "старое"),
                             ("старое_опасное", "опасное"),
                             ("опечатки", "опечатки")):
                hits = []
                pats = patmap[(c["имя"], fld)]
                for i, ln in enumerate(lines, 1):
                    n = sum(len(pat.findall(ln)) for pat in pats)
                    for _ in range(n):
                        hits.append((path, i, ln[:100]))
                if hits:
                    totals[c["имя"]][key] += len(hits)
                    details.extend((c["имя"], key, h) for h in hits)

    print(f"Файлов: {files_n}, персонажей в реестре: {len(chars)}")
    print()
    print(f"{'Персонаж':<25} {'ОК':>6} {'стар.':>6} {'ОПАСН':>6} {'опечат':>7}")
    problems = 0
    for c in chars:
        t = totals[c["имя"]]
        mark = " <-- ПРОВЕРИТЬ" if (t["старое"] or t["опасное"] or t["опечатки"]) else ""
        if mark:
            problems += 1
        print(f"{c['имя'][:24]:<25} {t['ок']:>6} {t['старое']:>6} "
              f"{t['опасное']:>6} {t['опечатки']:>7}{mark}")
    print()
    print("Проблемных персонажей:", problems)

    if verbose:
        for name, key, (path, line_no, line) in details[:50]:
            print(f"  [{key}] {name} | {path.name}:L{line_no}: {line.strip()}")
        if len(details) > 50:
            print(f"  ... ещё {len(details) - 50}")

    if out:
        lines = [f"# Consistency report — {Path(input_path)}", ""]
        for c in chars:
            t = totals[c["имя"]]
            lines.append(f"## {c['имя']}")
            lines.append(f"ОК: {t['ок']}, старое: {t['старое']}, "
                         f"опасное: {t['опасное']}, опечатки: {t['опечатки']}")
            for name2, key, (path, line_no, line) in details:
                if name2 == c["имя"] and key != "ок":
                    lines.append(f"- [{key}] {path.name}:L{line_no}: {line.strip()}")
            lines.append("")
        Path(out).write_text("\n".join(lines), encoding="utf-8")
        print(f"Отчёт: {out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Проверка имён по реестру (старые/опасные/опечатки)")
    ap.add_argument("--input", required=True, help="файл или папка .md/.txt/.docx")
    ap.add_argument("--registry", required=True, help="YAML реестр")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--out", help="файл отчёта (.md)")
    args = ap.parse_args(argv)
    return run(args.input, args.registry, limit=args.limit,
               verbose=args.verbose, out=args.out)