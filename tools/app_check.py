"""
app_check — самопроверка целостности приложения (команда doctor).

Свежая копия репозитория должна работать «из коробки». Проверка идёт
только чтением, ничего на диск не пишется:

1. ключевые файлы: CLI, GUI-модули, find_cjk, requirements.txt,
   pyproject.toml, LICENSE;
2. папки: core, tools, wrappers, data, external, test;
3. словари движков: tools/phrases*.yaml, tools/parasites.yaml, data/
   (yo_dict.yaml и gui_config.example.json — опциональные: их нет —
   предупреждение, не провал);
4. зависимости Python: yaml, docx, customtkinter, pymorphy3,
   charset_normalizer; tkinterdnd2 — опциональна (drag&drop);
5. внешние скрипты: автопоиск wrappers (external/ проверяется первым),
   ожидание — 5 из 5; при провале — подсказка про bundle_external.py;
6. версии: textools.__version__ совпадает с верхней записью CHANGELOG.md;
7. CLI поднимается: `python textools.py --help` отрабатывает без ошибки.

Код выхода: 0 — всё цело, 1 — есть провалы (предупреждения не считаются).
"""
from pathlib import Path
import argparse
import importlib
import json
import re
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "textools.py", "gui_ctk.pyw", "widgets_ctk.py", "review_dialog.py",
    "tabs_writers.py", "tabs_names.py", "tabs_vault.py", "tabs_clean.py",
    "tabs_replace.py", "tabs_settings.py", "find_cjk.py",
    "requirements.txt", "pyproject.toml", "LICENSE", "README.md",
    "tools/phrases.yaml", "tools/phrases_clean.yaml", "tools/parasites.yaml",
    "data/resolve_db.yaml", "data/pathos_db.yaml",
    "data/name_alerts.yaml", "data/SOURCES.md",
]

# отсутствие не ломает программу
OPTIONAL_FILES = ["tools/yo_dict.yaml", "gui_config.example.json"]

REQUIRED_DIRS = ["core", "tools", "wrappers", "data", "external", "test"]

REQUIRED_DEPS = ["yaml", "docx", "customtkinter", "pymorphy3",
                 "charset_normalizer"]
# только drag&drop путей в GUI
OPTIONAL_DEPS = ["tkinterdnd2"]

EXPECTED_SCRIPTS = 5

MARKS = {"ok": "ok", "warn": "предупреждение", "fail": "ПРОВАЛ"}


def _app_version():
    """Версия из textools.__version__ ("" — не удалось прочитать)."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        import textools
        return str(textools.__version__)
    except Exception:
        return ""


def run_checks():
    """[(статус, проверка, деталь)] — ok / warn / fail."""
    res = []

    def add(status, name, detail=""):
        res.append((status, name, detail))

    for rel in REQUIRED_FILES:
        p = PROJECT_ROOT / rel
        add("ok" if p.is_file() else "fail", f"файл {rel}",
            "на месте" if p.is_file() else "отсутствует")

    for rel in OPTIONAL_FILES:
        p = PROJECT_ROOT / rel
        add("ok" if p.is_file() else "warn",
            f"файл {rel} (опциональный)",
            "на месте" if p.is_file() else "нет — обойдётся встроенным")

    for rel in REQUIRED_DIRS:
        p = PROJECT_ROOT / rel
        add("ok" if p.is_dir() else "fail", f"папка {rel}",
            "на месте" if p.is_dir() else "отсутствует")

    for mod in REQUIRED_DEPS:
        try:
            importlib.import_module(mod)
            add("ok", f"зависимость {mod}", "импортируется")
        except Exception as e:
            add("fail", f"зависимость {mod}", f"не импортируется: {e}")

    for mod in OPTIONAL_DEPS:
        try:
            importlib.import_module(mod)
            add("ok", f"зависимость {mod} (опциональная)", "импортируется")
        except Exception:
            add("warn", f"зависимость {mod} (опциональная)",
                "нет — drag&drop в полях не работает")

    # внешние скрипты: автопоиск, external/ первым
    try:
        from wrappers import SCRIPT_CANDIDATES, find_scripts
        found = find_scripts()
        missing = sorted(set(SCRIPT_CANDIDATES) - set(found))
        if not missing:
            add("ok", "внешние скрипты",
                f"{len(found)} из {len(SCRIPT_CANDIDATES)} найдены "
                f"автопоиском")
        else:
            add("fail", "внешние скрипты",
                "не найдены: " + ", ".join(missing) +
                "; запустите tools/bundle_external.py в папке с личными "
                "копиями или задайте пути вручную на «Настройках»")
    except Exception as e:
        add("fail", "внешние скрипты", f"обёртки не импортировались: {e}")

    # версии textools.py и CHANGELOG.md согласованы
    app_version = _app_version()
    try:
        changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(
            encoding="utf-8")
        m = re.search(r"^## .*— версия (\S+)", changelog, re.M)
        doc_version = m.group(1) if m else ""
        if not app_version:
            add("fail", "версия", "textools.py не читается")
        elif not doc_version:
            add("warn", "версия",
                "в CHANGELOG.md нет строки «— версия X» в верхней записи")
        elif doc_version == app_version:
            add("ok", "версия",
                f"textools.py и CHANGELOG.md согласованы: {app_version}")
        else:
            add("fail", "версия",
                f"textools.py: {app_version}, CHANGELOG.md: {doc_version} "
                f"— рассинхрон")
    except Exception as e:
        add("fail", "версия", f"не проверить: {e}")

    # CLI поднимается
    try:
        r = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "textools.py"), "--help"],
            capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            add("ok", "CLI", "textools.py --help отрабатывает")
        else:
            add("fail", "CLI", f"--help вернул код {r.returncode}")
    except Exception as e:
        add("fail", "CLI", f"запуск не удался: {e}")

    return res


def main(opts=None):
    ap = argparse.ArgumentParser(
        description="целостность приложения: файлы, зависимости, "
                    "внешние скрипты, версии (только чтение)")
    ap.add_argument("--json", dest="json_out",
                    help="отчёт в JSON («-» — в stdout)")
    args = ap.parse_args(opts if opts is not None else [])

    res = run_checks()
    fails = [x for x in res if x[0] == "fail"]
    warns = [x for x in res if x[0] == "warn"]

    # при «-» stdout целиком под JSON, человеческий отчёт — в stderr
    out = sys.stderr if args.json_out == "-" else sys.stdout

    if args.json_out:
        doc = {
            "ok": not fails,
            "version": _app_version(),
            "problems": len(fails),
            "warnings": len(warns),
            "checks": [{"status": s, "check": n, "detail": d}
                       for s, n, d in res],
        }
        text = json.dumps(doc, ensure_ascii=False, indent=2)
        if args.json_out == "-":
            print(text)
        else:
            Path(args.json_out).write_text(text, encoding="utf-8")
            print(f"JSON-отчёт: {args.json_out}")

    for s, n, d in res:
        print(f"{MARKS[s]:<14} {n}" + (f" — {d}" if d else ""), file=out)
    print(f"\nЦелостность приложения: {len(res)} проверок, "
          f"провалов: {len(fails)}, предупреждений: {len(warns)}.",
          file=out)
    if fails:
        print("Копия неполная — см. провалы выше.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # прямой запуск: python tools/app_check.py
    sys.exit(main())
