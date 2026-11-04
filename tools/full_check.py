# -*- coding: utf-8 -*-
"""
full_check — профиль «проверить всё»: шесть проверок одним прогоном.

  python full_check.py --input <vault> [--limit N] [--json отчёт.json]

Порядок: obsidian-check → иероглифы/кодировки (cjk) → целостность →
дубликаты (merge-finder) → штампы ИИ (phrase-check, скан) →
АНТИРЕШИМОСТЬ (скан, без зачистки). Каждый шаг работает в режиме
«только чтение», никаких --fix; находки не правятся, а суммируются.
05.11: штампы и АНТИРЕШИМОСТЬ добавлены в скан-режиме — writer видит
объём стилистической правки сразу, не запуская инструменты по одному.
Лог АНТИРЕШИМОСТИ пишется во временный файл и не трогает reports/.

Итог: «серьёзные» находки (ERROR валидатора Obsidian, иероглифы,
проблемы целостности) дают код 1. Дубликаты, штампы и АНТИРЕШИМОСТЬ —
совет для ручного разбора, на код не влияют. --exit-zero всегда
возвращает 0.

JSON (--json) — агрегат всех шести проверок:
{"tool": "check-all", "input", "serious", "checks": {имя: {...}}}.

05.11 (--out, BACKLOG №5): человеческая md-сводка в файл — журнал
проекта: «проверено тогда-то, найдено то-то» приложить к главе.
«--out -» печатает md в stdout.

05.11 (--plan, BACKLOG №2): «репетиция чистки» — единый план
стилистической правки ДО всякой правки: штампы (фраза → замена,
файл, сколько раз) и hard-вхождения АНТИРЕШИМОСТИ (что будет
вырезано, файл). Ничего не правится — только план.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def run(input_path, limit=None, exit_zero=False, json_out=None, out=None,
        plan=None):
    if not Path(input_path).exists():
        print(f"Путь не найден: {input_path}", file=sys.stderr)
        return 2
    # 05.11: «--json -» — stdout целиком под JSON; весь человеческий
    # вывод (включая вывод вложенных проверок) уходит в stderr —
    # конвейеры (jq и т.п.) получают чистый JSON без примесей
    to_stdout = str(json_out).strip() == "-"
    _real_stdout = sys.stdout
    if to_stdout:
        sys.stdout = sys.stderr
    try:
        return _run(input_path, limit, exit_zero, json_out, _real_stdout,
                    out=out, plan=plan)
    finally:
        sys.stdout = _real_stdout


def _run(input_path, limit=None, exit_zero=False, json_out=None,
         out_stream=None, out=None, plan=None):
    from tools import obsidian_check, integrity_check, merge_finder
    from tools import phrase_check, antiresolve
    from find_cjk import main as cjk_main

    checks = {}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        print("=" * 32)
        print("1/6 Валидатор Obsidian (obsidian-check)", flush=True)
        j1 = tmp / "obsidian.json"
        obsidian_check.run(input_path, limit=limit, exit_zero=True,
                           json_out=str(j1))
        checks["obsidian-check"] = json.loads(
            j1.read_text(encoding="utf-8"))

        print("=" * 32)
        print("2/6 Иероглифы и порча кодировки (cjk)", flush=True)
        j2 = tmp / "cjk.json"
        cjk_main([str(input_path), "--quiet", "--exit-zero",
                  "--json", str(j2)])
        checks["cjk"] = json.loads(j2.read_text(encoding="utf-8"))

        print("=" * 32)
        print("3/6 Целостность заметок (integrity)", flush=True)
        j3 = tmp / "integrity.json"
        integrity_check.run(input_path, limit=limit, json_out=str(j3))
        checks["integrity"] = json.loads(j3.read_text(encoding="utf-8"))

        print("=" * 32)
        print("4/6 Дубликаты (merge-finder)", flush=True)
        j4 = tmp / "merge.json"
        merge_finder.run(input_path, limit=limit, json_out=str(j4))
        checks["merge-finder"] = json.loads(j4.read_text(encoding="utf-8"))

        print("=" * 32)
        print("5/6 Штампы ИИ-текста (phrase-check, скан)", flush=True)
        j5 = tmp / "phrase.json"
        phrase_check.run(input_path, limit=limit, json_out=str(j5))
        checks["phrase-check"] = json.loads(
            j5.read_text(encoding="utf-8"))

        print("=" * 32)
        print("6/6 АНТИРЕШИМОСТЬ (скан, без зачистки)", flush=True)
        # quiet: отчёт не печатается; лог — во временный файл, reports/
        # не трогается; clean=False — только поиск
        # collect: для --plan нужны сами находки (файл, строка, фрагмент)
        _rc, _log, ar_summary = antiresolve.run(
            input_path, clean=False, quiet=True,
            log_path=str(tmp / "antiresolve.log"), collect=bool(plan))
        checks["antiresolve"] = ar_summary

    findings = checks["obsidian-check"]["findings"]
    obs_err = sum(1 for f in findings if f["severity"] == "ERROR")
    cjk_n = sum(len(v) for v in checks["cjk"].get("results", {}).values())
    integrity_n = len(checks["integrity"]["problems"])
    merge_n = (len(checks["merge-finder"]["dup_content"])
               + len(checks["merge-finder"]["dup_names"]))
    near_n = len(checks["merge-finder"]["near"])
    phrase_n = checks["phrase-check"].get("total", 0)
    ar_n = checks["antiresolve"].get("всего", 0)
    ar_hard = checks["antiresolve"].get("hard", 0)
    serious = bool(obs_err or cjk_n or integrity_n)

    print("=" * 32)
    print("СВОДКА «проверить всё»:")
    print(f"  obsidian-check: {obs_err} ERROR, "
          f"{len(findings) - obs_err} прочих замечаний")
    print(f"  иероглифы/кодировки: {cjk_n} вхождений")
    print(f"  целостность: {integrity_n} проблем")
    print(f"  дубликаты: {merge_n} групп, {near_n} близких пар "
          f"(на усмотрение)")
    print(f"  штампы ИИ: {phrase_n} вхождений (на усмотрение)")
    print(f"  АНТИРЕШИМОСТЬ: {ar_n} вхождений, из них {ar_hard} hard "
          f"(на усмотрение)")
    if serious:
        print("Итог: есть серьёзные замечания — детали в разделах выше.")
    else:
        print("Итог: серьёзных замечаний нет.")
    if json_out:
        from core.report import write_json
        payload = {
            "tool": "check-all",
            "input": str(input_path),
            "serious": serious,
            "checks": checks,
        }
        if str(json_out).strip() == "-":
            # 05.11: печать в сохранённый stdout (при «-» он освобождён
            # от человеческого вывода) — без строки «JSON-отчёт: -» после
            print(json.dumps(payload, ensure_ascii=False, indent=2),
                  file=out_stream)
        else:
            write_json(json_out, payload)
            print(f"JSON-отчёт: {json_out}")
    if out:
        # 05.11 (BACKLOG №5): md-сводка в журнал проекта
        from core.report import write_report
        write_report(out, build_md(input_path, checks, serious))
        print(f"md-отчёт: {out}")
    if plan:
        # 05.11 (BACKLOG №2): репетиция чистки — ничего не правится
        from core.report import write_report
        write_report(plan, build_plan(input_path, checks))
        print(f"План чистки (ничего не правилось): {plan}")
    if serious and not exit_zero:
        return 1
    return 0


def _md_section(lines, title, rows, empty="не найдено", limit=40):
    """Секция md-отчёта: заголовок + строки; пустая секция — честное
    «не найдено», а не пропуск. rows — готовые md-строки (с «- »)."""
    lines.append(f"## {title}")
    if rows:
        lines.extend(rows[:limit])
        if len(rows) > limit:
            lines.append(f"- ... ещё {len(rows) - limit}")
    else:
        lines.append(f"- {empty}.")
    lines.append("")


def build_md(input_path, checks, serious):
    """05.11 (BACKLOG №5): человекочитаемая md-сводка шести проверок
    для журнала проекта. Только компоновка уже собранных данных."""
    from datetime import datetime
    findings = checks["obsidian-check"]["findings"]
    obs_err = [f for f in findings if f["severity"] == "ERROR"]
    obs_other = len(findings) - len(obs_err)
    cjk_results = checks["cjk"].get("results", {})
    cjk_n = sum(len(v) for v in cjk_results.values())
    problems = checks["integrity"]["problems"]
    dup_content = checks["merge-finder"]["dup_content"]
    dup_names = checks["merge-finder"]["dup_names"]
    near = checks["merge-finder"]["near"]
    ph = checks["phrase-check"]
    ph_hits = ph.get("hits", {})
    ar = checks["antiresolve"]

    L = ["# Проверить всё — сводка", "",
         f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
         f"Источник: {input_path}", "",
         "| Проверка | Итог |",
         "|---|---|",
         f"| obsidian-check | {len(obs_err)} ERROR, {obs_other} прочих |",
         f"| иероглифы/кодировки | {cjk_n} вхождений |",
         f"| целостность | {len(problems)} проблем |",
         f"| дубликаты | {len(dup_content) + len(dup_names)} групп, "
         f"{len(near)} близких пар |",
         f"| штампы ИИ | {ph.get('total', 0)} вхождений |",
         f"| АНТИРЕШИМОСТЬ | {ar.get('всего', 0)} вхождений, "
         f"hard {ar.get('hard', 0)} |",
         "",
         "Серьёзные замечания: "
         + ("есть — раздел «Серьёзное» ниже." if serious else "нет."),
         ""]

    _md_section(L, "obsidian-check — ERROR",
                [f"- [{f['code']}] {f['file']} — {f['message']}"
                 for f in obs_err])
    _md_section(L, "Иероглифы и порча кодировки",
                [f"- {rel}: {len(items)} вхожд. "
                 f"({', '.join(sorted({i.get('range', '?') for i in items}))})"
                 for rel, items in sorted(cjk_results.items(),
                                          key=lambda kv: -len(kv[1]))])
    _md_section(L, "Целостность заметок",
                [f"- {p['file']} — {p['issue']}" for p in problems])

    merge_rows = []
    for g in dup_content:
        merge_rows.append(f"- по содержимому [{g['hash']}]: "
                          + ", ".join(g["files"]))
    for g in dup_names:
        merge_rows.append(f"- по имени «{g['name']}{g['ext']}»: "
                          + ", ".join(g["files"]))
    for pair in near:
        merge_rows.append(f"- близкая пара: {pair['a']} ↔ {pair['b']} "
                          f"(схожесть {pair['jaccard']})")
    _md_section(L, "Дубликаты (на усмотрение)", merge_rows, limit=15)

    ph_rows = []
    for phrase, lst in sorted(ph_hits.items(),
                              key=lambda kv: -sum(c["count"]
                                                  for c in kv[1])):
        s = sum(c["count"] for c in lst)
        ph_rows.append(f"- «{phrase}» — {s} вхожд., "
                       f"{len(lst)} файл(ов)")
    _md_section(L, f"Штампы ИИ (всего {ph.get('total', 0)})",
                ph_rows, empty="штампов не найдено — текст чистый",
                limit=20)

    _md_section(L, "АНТИРЕШИМОСТЬ (на усмотрение)",
                [f"- {cat}: {n}"
                 for cat, n in ar.get("по_категориям", {}).items()],
                empty="находок нет")
    return "\n".join(L) + "\n"


def build_plan(input_path, checks):
    """05.11 (BACKLOG №2): «репетиция чистки» — единый план правок
    штампов и АНТИРЕШИМОСТИ до всякой правки. Пишущие инструменты
    (phrase-check --clean, antiresolve --clean) запускаются по одному и
    вслепую; один план показывает весь объём и порядок работы."""
    from datetime import datetime
    ph_hits = checks["phrase-check"].get("hits", {})
    ph_total = checks["phrase-check"].get("total", 0)
    from tools.phrase_check import load_clean_map
    mapping = load_clean_map()
    ar = checks["antiresolve"]
    ar_items = ar.get("находки", [])
    ar_hard = [it for it in ar_items if it["жёсткость"] == "hard"]
    ar_soft_n = ar.get("soft", 0)

    L = ["# Репетиция чистки — план правок", "",
         f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
         f"Источник: {input_path}", "",
         "Ничего не правится: это план. Правки делают "
         "«phrase-check --clean» и «antiresolve --clean» — оба с бэкапами.",
         ""]

    # --- штампы: фраза → замена/удаление, файл, сколько раз
    L.append(f"## Штампы: {ph_total} вхождений, {len(ph_hits)} видов")
    L.append("")
    if ph_hits:
        L.append("| Штамп | Действие | Файл | Раз |")
        L.append("|---|---|---|---|")
        for phrase, lst in sorted(ph_hits.items(),
                                  key=lambda kv: -sum(c["count"]
                                                      for c in kv[1])):
            # hits[phrase] — список {"file": путь, "count": n}
            repl = mapping.get(phrase)
            if repl is None:
                action = "в словаре замен нет — править вручную"
            elif repl == "":
                action = "удалить"
            else:
                action = f"→ «{repl}»"
            for entry in lst:
                L.append(f"| {phrase} | {action} | {entry['file']} "
                         f"| {entry['count']} |")
    else:
        L.append("- штампов не найдено — чистить нечего.")
    L.append("")

    # --- АНТИРЕШИМОСТЬ: hard будет вырезан зачисткой, soft — нет
    L.append(f"## АНТИРЕШИМОСТЬ: hard — {len(ar_hard)} "
             "(будет вырезано при зачистке)")
    L.append("")
    if ar_hard:
        for it in ar_hard:
            hint = f" → {it['подсказка']}" if it["подсказка"] else ""
            L.append(f"- {it['файл']}:{it['строка']} — "
                     f"[{it['категория']}] «{it['фрагмент']}»{hint}")
    else:
        L.append("- hard-вхождений нет.")
    L.append("")
    L.append(f"## АНТИРЕШИМОСТЬ: soft — {ar_soft_n} "
             "(не вырезается, решение за автором)")
    L.append("")
    if ar.get("по_категориям"):
        for cat, n in ar["по_категориям"].items():
            if "/soft" in cat:
                L.append(f"- {cat}: {n}")
    else:
        L.append("- soft-вхождений нет.")
    L.append("")

    L.append("## Порядок работы")
    L.append("")
    L.append("1. Не-UTF8 файлы (если целостность их нашла) — сначала "
             "«utf8 --fix», иначе чистка их пропускает.")
    L.append("2. «antiresolve --clean» — вырезает hard-вхождения выше.")
    L.append("3. «phrase-check --clean --yes» — заменяет штампы по "
             "словарю замен (столбец «Действие»).")
    L.append("4. soft-вхождения и штампы вне словаря — вручную, по "
             "контексту.")
    L.append("5. Повторный «check-all» — сверить, что стало чисто.")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Профиль «проверить всё»")
    ap.add_argument("--input", required=True, help="папка vault")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--exit-zero", action="store_true",
                    help="код 0, даже если есть серьёзные находки (для GUI)")
    ap.add_argument("--json", dest="json_out",
                    help="сохранить сводку всех проверок в JSON "
                         "(«-» — в stdout)")
    ap.add_argument("--out",
                    help="человекочитаемая md-сводка в файл "
                         "(«-» — в stdout)")
    ap.add_argument("--plan",
                    help="репетиция чистки: план правок штампов и "
                         "АНТИРЕШИМОСТИ в .md (ничего не правится)")
    args = ap.parse_args(argv)
    return run(args.input, limit=args.limit, exit_zero=args.exit_zero,
               json_out=args.json_out, out=args.out, plan=args.plan)


if __name__ == "__main__":
    sys.exit(main())
