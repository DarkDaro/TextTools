# -*- coding: utf-8 -*-
"""
full_check — профиль «проверить всё»: четыре проверки одним прогоном.

  python full_check.py --input <vault> [--limit N] [--json отчёт.json]

Порядок: obsidian-check → иероглифы/кодировки (cjk) → целостность →
дубликаты (merge-finder). Каждый шаг работает в режиме «только чтение»,
никаких --fix; находки не правятся, а суммируются.

Итог: «серьёзные» находки (ERROR валидатора Obsidian, иероглифы,
проблемы целостности) дают код 1. Дубликаты — совет для ручного
разбора, на код не влияют. --exit-zero всегда возвращает 0.

JSON (--json) — агрегат всех четырёх проверок:
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
    from tools import obsidian_check, integrity_check, merge_finder
    from find_cjk import main as cjk_main

    checks = {}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        print("=" * 32)
        print("1/4 Валидатор Obsidian (obsidian-check)", flush=True)
        j1 = tmp / "obsidian.json"
        obsidian_check.run(input_path, limit=limit, exit_zero=True,
                           json_out=str(j1))
        checks["obsidian-check"] = json.loads(
            j1.read_text(encoding="utf-8"))

        print("=" * 32)
        print("2/4 Иероглифы и порча кодировки (cjk)", flush=True)
        j2 = tmp / "cjk.json"
        cjk_main([str(input_path), "--quiet", "--exit-zero",
                  "--json", str(j2)])
        checks["cjk"] = json.loads(j2.read_text(encoding="utf-8"))

        print("=" * 32)
        print("3/4 Целостность заметок (integrity)", flush=True)
        j3 = tmp / "integrity.json"
        integrity_check.run(input_path, limit=limit, json_out=str(j3))
        checks["integrity"] = json.loads(j3.read_text(encoding="utf-8"))

        print("=" * 32)
        print("4/4 Дубликаты (merge-finder)", flush=True)
        j4 = tmp / "merge.json"
        merge_finder.run(input_path, limit=limit, json_out=str(j4))
        checks["merge-finder"] = json.loads(j4.read_text(encoding="utf-8"))

    findings = checks["obsidian-check"]["findings"]
    obs_err = sum(1 for f in findings if f["severity"] == "ERROR")
    cjk_n = sum(len(v) for v in checks["cjk"].get("results", {}).values())
    integrity_n = len(checks["integrity"]["problems"])
    merge_n = (len(checks["merge-finder"]["dup_content"])
               + len(checks["merge-finder"]["dup_names"]))
    near_n = len(checks["merge-finder"]["near"])
    serious = bool(obs_err or cjk_n or integrity_n)

    print("=" * 32)
    print("СВОДКА «проверить всё»:")
    print(f"  obsidian-check: {obs_err} ERROR, "
          f"{len(findings) - obs_err} прочих замечаний")
    print(f"  иероглифы/кодировки: {cjk_n} вхождений")
    print(f"  целостность: {integrity_n} проблем")
    print(f"  дубликаты: {merge_n} групп, {near_n} близких пар "
          f"(на усмотрение)")
    if serious:
        print("Итог: есть серьёзные замечания — детали в разделах выше.")
    else:
        print("Итог: серьёзных замечаний нет.")
    if json_out:
        from core.report import write_json
        write_json(json_out, {
            "tool": "check-all",
            "input": str(input_path),
            "serious": serious,
            "checks": checks,
        })
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
