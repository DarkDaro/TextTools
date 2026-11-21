# -*- coding: utf-8 -*-
"""
meta_check — проверка метафайлов проекта (команда meta-check, 21.11).

Повышение из рабочего скрипта песочницы check_docs.py: раз метафайлы
ведутся руками, они должны сами уметь доказывать свою целостность —
как doctor делает это для программы.

Проверяет (только чтение):
1. README.md и README.en.md: языковой блок, версия из textools.py,
   счётчик подкоманд и тестов, ссылки на метафайлы, скрин Помодоро;
2. локальные ссылки из обоих README ведут на существующие файлы;
3. GUI_GUIDE.md: 17 разделов верхнего уровня, ключевые подразделы,
   хоткей Ctrl+8; MANUAL.md и карта CLI↔GUI — раздел «Помодоро»;
4. TECH_DEBT.md: разделы TD совпадают с таблицей, статусы определены;
5. счётчик тестов сверяется с фактическим числом, которое отдаёт
   pytest --collect-only (если pytest недоступен — проверка
   пропускается с предупреждением, это не провал).

Код выхода: 0 — всё сходится, 1 — есть провалы.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# старые версии, которых в README быть не должно
OLD_VERSIONS = ("1.9.0", "1.8.5", "1.8.4", "1.8.3", "1.6.0")


def _plural(n, one, few, many):
    """1 подкоманда / 2–4 подкоманды / 5+ подкоманд — по-русски."""
    if n % 100 == 11 or n % 10 == 1 and n % 100 != 11:
        return f"{n} {one}"
    if n % 100 not in (12, 13, 14) and n % 10 in (2, 3, 4):
        return f"{n} {few}"
    return f"{n} {many}"


def _plural_tests(n):
    return _plural(n, "тест", "теста", "тестов")


def _cli_names():
    """Имена и число подкоманд CLI — из живого textools.py --help:
    argparse сам печатает список choices, это единственная правда.
    None — CLI не поднялся, сверку пропускаем."""
    try:
        r = subprocess.run(
            [sys.executable, str(ROOT / "textools.py"), "--help"],
            cwd=ROOT, capture_output=True, text=True, timeout=60)
        m = re.search(r"\{([a-z0-9-]+(?:,[a-z0-9-]+)+)\}", r.stdout)
        if not m:
            return None
        names = m.group(1).split(",")
        src = (ROOT / "textools.py").read_text(encoding="utf-8")
        n_alias = len(re.findall(r"aliases=\[", src))
        return len(names) - n_alias, len(names)
    except Exception:
        return None


def _collect_test_count():
    """Сколько тестов видит pytest (None — не удалось посчитать)."""
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "test/", "--collect-only", "-q"],
            cwd=ROOT, capture_output=True, text=True, timeout=120)
        m = re.search(r"(\d+) tests? collected", r.stdout)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def run_checks():
    """(failures, строки отчёта) — печатью занимается main()."""
    failures = []

    def check(lines, cond, ok_msg, err_msg):
        if cond:
            lines.append(f"  ok: {ok_msg}")
        else:
            failures.append(err_msg)
            lines.append(f"  ПРОВАЛ: {err_msg}")

    lines = []

    def md_files(md_path):
        text = md_path.read_text(encoding="utf-8")
        return text, re.findall(r"\]\(([^)#\s]+)\)", text)

    _tt = (ROOT / "textools.py").read_text(encoding="utf-8")
    _m = re.search(r'__version__\s*=\s*"(.+?)"', _tt)
    cur_ver = _m.group(1) if _m else "?"

    lines.append("== README.md ==")
    ru_text, ru_links = md_files(ROOT / "README.md")
    check(lines, "**Русский**" in ru_text and "[English](README.en.md)" in ru_text,
          "языковой блок на месте", "нет языкового блока в README.md")
    check(lines, f"Версия {cur_ver}" in ru_text, f"версия {cur_ver}",
          f"в README.md не {cur_ver}")
    for old in OLD_VERSIONS:
        check(lines, f"Версия {old}" not in ru_text, f"старой версии {old} нет",
              f"в README.md осталось «Версия {old}»")
    check(lines, "[TECH_DEBT.md](TECH_DEBT.md)" in ru_text,
          "ссылка на TECH_DEBT.md", "в README.md нет ссылки на TECH_DEBT.md")
    check(lines, "update.bat" in ru_text and "canonical.txt" in ru_text,
          "патник и canonical.txt описаны",
          "в README.md нет патника/canonical.txt")
    check(lines, "окно на восемь вкладок" in ru_text, "восемь вкладок",
          "в README.md не восемь вкладок")
    check(lines, "**Помодоро**" in ru_text, "вкладка «Помодоро» в списке",
          "в README.md нет вкладки «Помодоро»")
    check(lines, "Ctrl+1…8" in ru_text, "Ctrl+1…8", "в README.md не Ctrl+1…8")
    check(lines, "light-pomodoro.png" in ru_text, "скрин Помодоро",
          "в README.md нет скрина Помодоро")

    lines.append("== README.en.md ==")
    en_text, en_links = md_files(ROOT / "README.en.md")
    check(lines, "[Русский](README.md)" in en_text and "**English**" in en_text,
          "языковой блок на месте", "нет языкового блока в README.en.md")
    check(lines, f"Version {cur_ver}" in en_text, f"версия {cur_ver}",
          f"в README.en.md не {cur_ver}")
    for old in ("1.9.0", "1.8.5", "1.8.4"):
        check(lines, f"Version {old}" not in en_text, f"старой версии {old} нет",
              f"в README.en.md осталось «Version {old}»")
    check(lines, "eight tabs" in en_text, "eight tabs",
          "в README.en.md нет eight tabs")
    check(lines, "**Pomodoro (Помодоро)**" in en_text, "Pomodoro в списке вкладок",
          "в README.en.md нет Pomodoro в списке вкладок")
    check(lines, "Ctrl+1…8" in en_text, "Ctrl+1…8", "в README.en.md не Ctrl+1…8")
    check(lines, "[TECH_DEBT.md](TECH_DEBT.md)" in en_text,
          "ссылка на TECH_DEBT.md", "в README.en.md нет ссылки на TECH_DEBT.md")

    lines.append("== счётчик тестов ==")
    n_tests = _collect_test_count()
    if n_tests is None:
        lines.append("  предупреждение: pytest не отдал число тестов — "
                     "сверка счётчика пропущена")
    else:
        s = _plural_tests(n_tests)
        check(lines, s in ru_text, f"README.md: «{s}»",
              f"в README.md не «{s}» (фактически pytest собирает {n_tests})")
        check(lines, f"{n_tests} tests" in en_text, f"README.en.md: «{n_tests} tests»",
              f"в README.en.md не «{n_tests} tests»")

    lines.append("== счётчик подкоманд CLI ==")
    cli = _cli_names()
    if cli is None:
        lines.append("  предупреждение: textools.py --help не поднялся — "
                     "сверка числа подкоманд пропущена")
    else:
        n_sub, n_names = cli
        s_ru = _plural(n_sub, "подкоманда", "подкоманды", "подкоманд")
        # README переносит строки внутри фразы — сверяем по «сложенному»
        # тексту без переносов
        ru_flat = re.sub(r"\s+", " ", ru_text)
        check(lines, s_ru in ru_flat, f"README.md: «{s_ru}»",
              f"в README.md не «{s_ru}» (фактически {n_sub}, имён {n_names})")
        check(lines, f"{n_sub} CLI subcommands" in en_text,
              f"README.en.md: «{n_sub} CLI subcommands»",
              f"в README.en.md не «{n_sub} CLI subcommands»")

    lines.append("== ссылки на локальные файлы ==")
    for link in sorted(set(ru_links + en_links)):
        check(lines, (ROOT / link).exists(), link, f"битая ссылка на {link}")

    lines.append("== GUI_GUIDE.md, MANUAL.md, карта CLI↔GUI ==")
    guide = (ROOT / "GUI_GUIDE.md").read_text(encoding="utf-8")
    manual = (ROOT / "MANUAL.md").read_text(encoding="utf-8")
    map_text = (ROOT / "docs/CLI_GUI_MAP.md").read_text(encoding="utf-8")
    check(lines, "## 10. Вкладка «Помодоро»" in guide,
          "раздел 10 Помодоро в GUIDE", "в GUI_GUIDE.md нет раздела «Помодоро»")
    check(lines, "## 11. Вкладка «Настройки»" in guide, "Настройки — раздел 11",
          "в GUI_GUIDE.md «Настройки» не раздел 11")
    check(lines, "## 12. Вкладка «Журнал»" in guide, "Журнал — раздел 12",
          "в GUI_GUIDE.md «Журнал» не раздел 12")
    check(lines, "## 17. Словарь простыми словами" in guide,
          "Словарь — раздел 17", "в GUI_GUIDE.md «Словарь» не раздел 17")
    check(lines, "| `Ctrl+8` | Вкладка «Журнал» |" in guide, "Ctrl+8 в таблице",
          "в таблице хоткеев GUIDE нет Ctrl+8")
    check(lines, "### Вкладка «Помодоро»" in manual, "Помодоро в MANUAL",
          "в MANUAL.md нет раздела «Помодоро»")
    check(lines, "## Помодоро" in map_text, "Помодоро в карте CLI↔GUI",
          "в docs/CLI_GUI_MAP.md нет раздела «Помодоро»")
    check(lines, "core/pomodoro.py" in map_text, "движок в карте",
          "в карте CLI↔GUI не указан core/pomodoro.py")
    for n in range(1, 18):
        if not re.search(rf"^## {n}\. ", guide, re.M):
            check(lines, False, f"GUIDE: раздел {n}",
                  f"в GUI_GUIDE.md нет заголовка «## {n}.»")
    check(lines, len(re.findall(r"^## \d+\. ", guide, re.M)) == 17,
          "17 разделов GUIDE", "в GUI_GUIDE.md не 17 разделов верхнего уровня")

    lines.append("== TECH_DEBT.md ==")
    td_text = (ROOT / "TECH_DEBT.md").read_text(encoding="utf-8")
    ids = re.findall(r"^## (TD-\d+)", td_text, re.M)
    table_ids = set(re.findall(r"^\| (TD-\d+) \|", td_text, re.M))
    check(lines, len(ids) == len(set(ids)), f"{len(ids)} уникальных разделов TD",
          "дубликаты TD-разделов в TECH_DEBT.md")
    check(lines, set(ids) == table_ids, "таблица и разделы совпадают",
          f"таблица и разделы не совпадают: {sorted(set(ids) ^ table_ids)}")
    for st in ("открыт", "закрыт", "ждёт решения", "в работе"):
        check(lines, st in td_text, f"статус «{st}» определён",
              f"статус «{st}» не определён")

    return failures, lines


def main(opts=None):
    failures, lines = run_checks()
    for line in lines:
        print(line)
    print()
    if failures:
        print(f"ИТОГ: {len(failures)} провал(ов)")
        for f in failures:
            print(f" - {f}")
        return 1
    print("ИТОГ: все проверки зелёные")
    return 0


if __name__ == "__main__":  # прямой запуск: python tools/meta_check.py
    sys.exit(main())
