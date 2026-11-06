# -*- coding: utf-8 -*-
r"""
antiresolve — режим «АНТИРЕШИМОСТЬ» (05.11): поиск, лог и зачистка
запрещённой лексики и пафосных штампов в .md/.txt/.docx.

Этапы (по памятке романа «История Даро. Проект Восход»):
  1. Поиск    — словари data/resolve_db.yaml (лексика памятки) и
                data/pathos_db.yaml (антипафос); формат — core.rulebase
  2. Лог      — reports/antiresolve.log (текстовик, дописывается по прогонам)
  3. Зачистка — --clean: вырезание hard-вхождений с .bak-бэкапами;
                docx правится через core.docx_io (форматирование
                сохраняется), md/txt — перезапись текста
  4. Контроль — повторный прогон, «осталось» дописывается в лог

Без --clean ничего не правится (поиск + лог + отчёт). soft-правила не
вырезаются никогда — только подсветка с подсказкой редактору. Код
возврата: 0 — чисто, 1 — есть hard-находки (после зачистки — остались),
2 — ошибка путей/словарей.

Использование:
  python tools/antiresolve.py --input <папка/файл>            — поиск+лог
  python tools/antiresolve.py --input <...> --clean           — зачистка
  python tools/antiresolve.py --input <...> --out -           — отчёт в stdout
  python tools/antiresolve.py --input <...> --json -          — сводка в stdout
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import text_parser as tp  # noqa: E402
from core.report import write_json, write_report  # noqa: E402
from core.rulebase import load_rules  # noqa: E402

HERE = Path(__file__).resolve().parent
DEFAULT_RESOLVE_DB = HERE.parent / "data" / "resolve_db.yaml"
DEFAULT_PATHOS_DB = HERE.parent / "data" / "pathos_db.yaml"

CTX = 40  # символов контекста вокруг вхождения


def _context(text, start, end, width=CTX):
    """Контекст вхождения ±width, переводы строк спрямлены."""
    a = max(0, start - width)
    b = min(len(text), end + width)
    frag = text[a:b].replace("\n", " ").strip()
    return ("…" if a > 0 else "") + frag + ("…" if b < len(text) else "")


def scan_text(text, rules):
    """Совпадения [(правило, начало, конец)] по тексту, отсортированы
    по позиции. Правила работают в порядке словаря: вхождение,
    пересекающееся с уже найденным (более конкретная фраза раньше
    в словаре), пропускается — «с решимостью» не даёт второго
    срабатывания корневого правила «решимост*». Нулевые совпадения
    пропускаются."""
    out = []
    taken = []
    for rule in rules:
        for m in rule.pattern.finditer(text):
            s, e = m.start(), m.end()
            if s == e:
                continue
            if any(not (e <= a or s >= b) for a, b in taken):
                continue
            out.append((rule, s, e))
            taken.append((s, e))
    out.sort(key=lambda t: (t[1], t[2]))
    return out


def scan_file(path, rules):
    """Находки одного файла: список dict. Файл не читается — None.
    Для docx «строка» — номер абзаца (read_text склеивает w:t по
    параграфам, разорванные между run'ами фразы находятся)."""
    text = tp.read_text(path)
    if not text:
        return None
    unit = "абз." if path.suffix.lower() == ".docx" else "стр."
    found = []
    for rule, s, e in scan_text(text, rules):
        found.append({
            "файл": str(path),
            "строка": text.count("\n", 0, s) + 1,
            "единица": unit,
            "категория": rule.cat,
            "жёсткость": rule.level,
            "фрагмент": text[s:e],
            "контекст": _context(text, s, e),
            "подсказка": rule.hint,
        })
    return found


def _cut_pattern(rule):
    """Регэксп вырезания: вхождение с прилегающими пробелами.

    Переводы строк не трогаются — абзацы не склеиваются. Хвостовые
    пробелы забираются только перед пунктуацией/концом строки, иначе
    вырезание «с решимостью» в «Она с решимостью посмотрела» склеивает
    слова («Онапосмотрела») или оставляет пробел перед точкой."""
    return re.compile(
        r"[ \t]*(?:" + rule.source + r")(?:[ \t]*(?=[\n.,!?;:…—)»\"]|$))?",
        re.IGNORECASE)


def clean_text_file(path, rules):
    """Зачистка md/txt: вырезает hard-вхождения (или заменяет на fix).
    .bak создаётся один раз — оригинал не затирается повторными прогонами.
    Возвращает число правок."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        text = tp.read_text(path)
    if not text:
        return 0
    total = 0
    for rule in rules:
        if rule.level != "hard":
            continue
        repl = rule.fix
        # lambda: replacement без интерпретации \1 и прочих регэксп-символов
        text, n = _cut_pattern(rule).subn(lambda _m: repl, text)
        total += n
    if total:
        tp.backup_once(path)
        path.write_text(text, encoding="utf-8")
    return total


def clean_docx_file(path, rules):
    """Зачистка docx: кросс-run замена с сохранением форматирования
    (core.docx_io), .bak создаётся внутри при первой правке.
    Возвращает число правок."""
    from core import docx_io
    total = 0
    for rule in rules:
        if rule.level != "hard":
            continue
        pat = (r"(?i)[ \t]*(?:" + rule.source
               + r")(?:[ \t]*(?=[\n.,!?;:…—)»\"]|$))?")
        n, _changed, _br = docx_io.replace_in_docx(
            path, pat, rule.fix, is_regex=True, backup=True)
        total += n
    return total


def _counts(findings):
    """hard/soft и словарь по категориям «категория/жёсткость»."""
    hard = sum(1 for it in findings if it["жёсткость"] == "hard")
    cats = {}
    for it in findings:
        key = f"{it['категория']}/{it['жёсткость']}"
        cats[key] = cats.get(key, 0) + 1
    return {"всего": len(findings), "hard": hard, "soft": len(findings) - hard,
            "по_категориям": dict(sorted(cats.items(),
                                         key=lambda kv: (-kv[1], kv[0])))}


def build_report(source, n_files, unread, findings, cleaned, leftover):
    """Отчёт .md (--out). Одинаково работает для сухого прогона и зачистки."""
    c = _counts(findings)
    L = ["# АНТИРЕШИМОСТЬ — отчёт", "",
         f"Источник: {source} (файлов: {n_files}"
         + (f", не читается: {unread}" if unread else "") + ")", ""]
    by_file = {}
    for it in findings:
        by_file.setdefault(it["файл"], []).append(it)
    for fname, items in by_file.items():
        L.append(f"## {fname}")
        for it in items:
            L.append(f"- {it['строка']} ({it['единица']}): "
                     f"[{it['категория']}/{it['жёсткость']}] "
                     f"«{it['фрагмент']}» {it['контекст']}")
            if it["подсказка"]:
                L.append(f"  - подсказка: {it['подсказка']}")
        L.append("")
    L.append("## Сводка по категориям")
    if c["по_категориям"]:
        for key, n in c["по_категориям"].items():
            L.append(f"- {key}: {n}")
    else:
        L.append("- чисто")
    L.append("")
    L.append(f"Итого: находок {c['всего']} — hard {c['hard']}, soft {c['soft']}.")
    if cleaned is not None:
        L.append(f"Зачистка: правок {cleaned['правок']}, "
                 f"файлов изменено {cleaned['файлов']}.")
    if leftover is not None:
        L.append(f"Контрольный прогон: осталось hard {leftover['hard']}, "
                 f"soft {leftover['soft']}.")
    return "\n".join(L) + "\n"


def build_log_entry(source, n_files, findings, cleaned, leftover):
    """Блок лога-текстовика: дописывается в reports/antiresolve.log,
    история прогонов накапливается."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c = _counts(findings)
    L = [f"=== АНТИРЕШИМОСТЬ {now} | источник: {source} | "
         f"файлов: {n_files} | зачистка: {'да' if cleaned is not None else 'нет'} ==="]
    by_file = {}
    for it in findings:
        by_file.setdefault(it["файл"], []).append(it)
    for fname, items in by_file.items():
        L.append(f"--- {fname}")
        for it in items:
            line = (f"  {it['строка']} ({it['единица']}): "
                    f"[{it['категория']}/{it['жёсткость']}] "
                    f"«{it['фрагмент']}» {it['контекст']}")
            if it["подсказка"]:
                line += f"  → {it['подсказка']}"
            L.append(line)
    tail = f"=== Итого: {c['всего']} — hard {c['hard']} / soft {c['soft']}"
    if cleaned is not None:
        tail += (f" | зачистка: правок {cleaned['правок']} "
                 f"в {cleaned['файлов']} файлах")
    if leftover is not None:
        tail += (f" | контрольный прогон: осталось hard {leftover['hard']} "
                 f"/ soft {leftover['soft']}")
    tail += " ==="
    L.append(tail)
    L.append("")
    return "\n".join(L) + "\n"


def run(input_path, resolve_db="", pathos_db="", clean=False,
        log_path="", out="", quiet=False, collect=False):
    """Полный прогон: поиск → лог → (зачистка) → контроль.
    Возвращает (код_возврата, путь_лога, сводка).
    collect=True — в сводку добавляется «находки»: полный список dict
    (нужно репетиции чистки в check-all --plan; без collect сводка
    компактна, как раньше)."""
    rules = load_rules(resolve_db or DEFAULT_RESOLVE_DB)
    rules += load_rules(pathos_db or DEFAULT_PATHOS_DB)
    root = tp.check_root(input_path)
    files = list(tp.iter_text_files(root, exts=tp.ANALYSIS_EXTS))  # 07.11: + html

    findings = []
    unread = 0
    cleaned = None
    leftover = None
    hard_rules = [r for r in rules if r.level == "hard"] if clean else []

    for f in files:
        found = scan_file(f, rules)
        if found is None:
            unread += 1
            continue
        findings.extend(found)
        if clean:
            if f.suffix.lower() == ".docx":
                n = clean_docx_file(f, hard_rules)
            else:
                n = clean_text_file(f, hard_rules)
            if n:
                cleaned = cleaned or {"правок": 0, "файлов": 0}
                cleaned["правок"] += n
                cleaned["файлов"] += 1

    if clean:
        # этап 4: контрольный прогон по фактическому состоянию файлов
        leftover = {"hard": 0, "soft": 0}
        for f in files:
            found = scan_file(f, rules) or []
            for it in found:
                leftover[it["жёсткость"]] += 1

    log_file = Path(log_path) if log_path else Path("reports") / "antiresolve.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(build_log_entry(str(root), len(files), findings,
                                 cleaned, leftover))

    report = build_report(str(root), len(files), unread, findings,
                          cleaned, leftover)
    if out:
        write_report(out, report)
    elif not quiet:
        # quiet: при --json stdout принадлежит JSON-сводке
        print(report, end="")

    c = _counts(findings)
    summary = {"файлов": len(files), "не_читается": unread, **c,
               "зачистка": cleaned, "осталось": leftover,
               "лог": str(log_file)}
    if collect:
        summary["находки"] = findings
    rc = 1 if (leftover["hard"] if leftover else c["hard"]) > 0 else 0
    return rc, str(log_file), summary


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="antiresolve",
        description="АНТИРЕШИМОСТЬ: поиск, лог и зачистка запрещённой "
                    "лексики и пафоса (памятка романа)")
    ap.add_argument("--input", required=True, help="папка или файл")
    ap.add_argument("--resolve-db", default="",
                    help="словарь лексики памятки (по умолчанию "
                         "data/resolve_db.yaml)")
    ap.add_argument("--pathos-db", default="",
                    help="словарь антипафоса (по умолчанию "
                         "data/pathos_db.yaml)")
    ap.add_argument("--clean", action="store_true",
                    help="зачистка: вырезать hard-вхождения (с .bak)")
    ap.add_argument("--log", default="",
                    help="файл лога (по умолчанию reports/antiresolve.log, "
                         "дописывается)")
    ap.add_argument("--out", default="",
                    help="отчёт .md («-» — в stdout)")
    ap.add_argument("--json", dest="json_out", nargs="?", const="-",
                    default="",
                    help="сводка в JSON («-» — в stdout)")
    args = ap.parse_args(argv)

    try:
        rc, log_file, summary = run(
            args.input, resolve_db=args.resolve_db, pathos_db=args.pathos_db,
            clean=args.clean, log_path=args.log, out=args.out,
            quiet=bool(args.json_out))
    except ValueError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 2
    print(f"Лог: {log_file}", file=sys.stderr)
    if args.json_out:
        write_json(args.json_out, summary)
    return rc


if __name__ == "__main__":
    sys.exit(main())
