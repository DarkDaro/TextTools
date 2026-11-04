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
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def run(input_path, limit=None, exit_zero=False, json_out=None):
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
        return _run(input_path, limit, exit_zero, json_out, _real_stdout)
    finally:
        sys.stdout = _real_stdout


def _run(input_path, limit=None, exit_zero=False, json_out=None,
         out_stream=None):
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
        _rc, _log, ar_summary = antiresolve.run(
            input_path, clean=False, quiet=True,
            log_path=str(tmp / "antiresolve.log"))
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
    if serious and not exit_zero:
        return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Профиль «проверить всё»")
    ap.add_argument("--input", required=True, help="папка vault")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--exit-zero", action="store_true",
                    help="код 0, даже если есть серьёзные находки (для GUI)")
    ap.add_argument("--json", dest="json_out",
                    help="сохранить сводку всех проверок в JSON "
                         "(«-» — в stdout)")
    args = ap.parse_args(argv)
    return run(args.input, limit=args.limit, exit_zero=args.exit_zero,
               json_out=args.json_out)


if __name__ == "__main__":
    sys.exit(main())
