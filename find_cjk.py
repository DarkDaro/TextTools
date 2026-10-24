#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""find_cjk.py — поиск иероглифов (CJK), мойбейка и порчи кодировки в текстовых документах.

Задача: от языковых моделей (в частности DeepSeek) в тексты пробиваются китайские
символы. Для кода сайта есть Node-версия (C:/AgentLetta/scripts/find-cjk.js),
эта — для текстовых документов и метафайлов: .md, .txt и подобных.

Запуск:
    python find_cjk.py <путь>                # папка или файл
    python find_cjk.py <путь> --ext .md,.txt # только эти расширения
    python find_cjk.py <путь> --json out.json
    python find_cjk.py <путь> --quiet        # только итог, без деталей

Код возврата: 0 — чисто, 1 — есть находки, 2 — путь не найден.
Только чтение. Ничего не меняет и не исправляет.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.text_parser import stop_requested

# Диапазоны, которых не должно быть в текстах проекта.
# Порядок важен: сначала иероглифы (частая проблема), потом мойбейк.
PATTERNS: list[tuple[str, re.Pattern[str], bool]] = [
    # (название, регулярка, пропускать_в_начале_файла)
    ("Китайские иероглифы (CJK Unified)", re.compile(r"[\u4e00-\u9fff]"), False),
    ("Китайские иероглифы (CJK Ext A)", re.compile(r"[\u3400-\u4dbf]"), False),
    ("Китайские иероглифы (CJK Compat)", re.compile(r"[\uf900-\ufaff]"), False),
    ("Китайская пунктуация", re.compile(r"[\u3000-\u303f]"), False),
    ("Fullwidth формы", re.compile(r"[\uff00-\uffef]"), False),
    ("Хирагана (японская азбука)", re.compile(r"[\u3040-\u309f]"), False),
    ("Катакана (японская азбука)", re.compile(r"[\u30a0-\u30ff]"), False),
    ("Хангыль (корейская азбука)", re.compile(r"[\uac00-\ud7af]"), False),
    ("Хангыль Jamo", re.compile(r"[\u1100-\u11ff]"), False),
    ("Иврит", re.compile(r"[\u0590-\u05ff]"), False),
    ("Арабский", re.compile(r"[\u0600-\u06ff]"), False),
    ("Тайский", re.compile(r"[\u0e00-\u0e7f]"), False),
    # Мойбейк: UTF-8, прочитанный как latin-1 или cp1251
    ("Мойбейк (UTF-8 как latin-1)", re.compile(r"[ÐÑÂÃ][\u0080-\u00bf]"), False),
    ("Мойбейк (UTF-8 как cp1251)", re.compile(r"â€[\u0090-\u00bf\u2018-\u2122]"), False),
    # Невидимые управляющие
    ("Невидимые управляющие символы", re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f]"), False),
    # BOM: в начале файла это норма для UTF-8, внутри текста — мусор
    ("BOM внутри текста", re.compile(r"\ufeff"), True),
]

# Расширения по умолчанию — именно текстовые документы, не код сайта
DEFAULT_EXT = (
    ".md", ".markdown", ".txt", ".text", ".rst",
    ".json", ".yaml", ".yml", ".ini", ".toml", ".csv",
)

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".idea",
             ".vscode", ".obsidian", ".trash", ".smart-env",
             "md_replace_backups", "reports"}


def is_binary(data: bytes) -> bool:
    """Грубая, но надёжная проверка: нулевой байт = бинарник."""
    return b"\x00" in data[:8192]


def code_points(ch: str) -> str:
    """U+XXXX для каждого символа строки."""
    return " ".join(f"U+{ord(c):04X}" for c in ch)


def scan_file(path: Path) -> tuple[list[dict], str | None]:
    """Сканирует один файл. Возвращает (находки, ошибка)."""
    try:
        data = path.read_bytes()
    except OSError as e:
        return [], f"не читается: {e.strerror}"

    if is_binary(data):
        return [], "binary"

    findings: list[dict] = []
    seen: set[tuple[int, str]] = set()

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        # Файл не в UTF-8 — это отдельная находка, важная сама по себе
        findings.append({
            "line": data[:e.start].count(b"\n") + 1,
            "column": 0,
            "char": "",
            "codepoints": "",
            "range": "ФАЙЛ НЕ В UTF-8",
            "context": f"ошибка декодирования на байте {e.start}: {e.reason}",
        })
        # всё равно пробуем cp1251, чтобы показать содержимое
        try:
            text = data.decode("cp1251")
        except UnicodeDecodeError:
            return findings, None

    for line_no, line in enumerate(text.splitlines(), start=1):
        for name, pattern, skip_first in PATTERNS:
            for m in pattern.finditer(line):
                # BOM в самом начале файла — норма
                if skip_first and line_no == 1 and m.start() == 0:
                    continue
                key = (line_no, name)
                if key in seen:
                    continue
                seen.add(key)
                findings.append({
                    "line": line_no,
                    "column": m.start() + 1,
                    "char": m.group(0),
                    "codepoints": code_points(m.group(0)),
                    "range": name,
                    "context": line.strip()[:140],
                })
                if len(findings) > 500:
                    return findings, "обрезано на 500 находках"

    return findings, None


def walk(root: Path):
    """Обходит папку или обрабатывает один файл."""
    if root.is_file():
        yield root
        return
    for entry in root.rglob("*"):
        # 24.10: служебные папки считаем относительно корня: явно
        # указанная папка reports/ не должна пропадать целиком
        if any(part in SKIP_DIRS for part in entry.relative_to(root).parts):
            continue
        if entry.is_file():
            yield entry


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Поиск иероглифов (CJK), мойбейка и порчи кодировки в текстовых документах",
    )
    parser.add_argument("path", nargs="?", default=".", help="папка или файл (по умолчанию текущая)")
    parser.add_argument("--ext", default="", help="расширения через запятую, например .md,.txt")
    parser.add_argument("--json", dest="json_out", default="", help="сохранить полный отчёт в JSON")
    parser.add_argument("--quiet", action="store_true", help="только итог, без деталей")
    # 24.10: argv — чтобы вызывать из textools.py без подмены sys.argv
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        print(f"Путь не найден: {root}", file=sys.stderr)
        return 2

    if args.ext:
        exts = tuple(e.strip().lower() if e.startswith(".") else "." + e.strip().lower()
                     for e in args.ext.split(",") if e.strip())
    elif root.is_file():
        # явно указанный файл проверяем в любом расширении
        exts = ()
    else:
        exts = DEFAULT_EXT

    print(f"Сканирую: {root}")
    print(f"Расширения: {', '.join(exts) if exts else 'любые'}")
    print()

    files = [p for p in walk(root) if not exts or p.suffix.lower() in exts]
    total = len(files)
    if total:
        print(f"PROGRESS:0/{total}", flush=True)

    total_files = 0
    skipped = 0
    truncated: list[str] = []
    results: dict[str, list[dict]] = {}
    errors: list[str] = []
    stopped = False

    for idx, path in enumerate(files, 1):
        # 24.10: мягкая остановка из GUI (stop.flag) — между файлами
        if stop_requested():
            stopped = True
            print("Остановлено пользователем.", flush=True)
            break
        findings, err = scan_file(path)
        if err == "binary":
            skipped += 1
            print(f"PROGRESS:{idx}/{total}", flush=True)
            continue
        if err and err.startswith("не читается"):
            errors.append(f"{path}: {err}")
            print(f"PROGRESS:{idx}/{total}", flush=True)
            continue
        if err and err.startswith("обрезано"):
            truncated.append(str(path))
        total_files += 1
        if findings:
            rel = path.name if root.is_file() else str(path.relative_to(root))
            results[rel] = findings
        print(f"PROGRESS:{idx}/{total}", flush=True)

    print(f"Просканировано файлов: {total_files}")
    if skipped:
        print(f"Пропущено бинарных: {skipped}")
    if truncated:
        print(f"Обрезано на 500 находках: {len(truncated)} файлов")
        for t in truncated[:5]:
            print(f"  {t}")
    if errors:
        print(f"Ошибок чтения: {len(errors)}")
        for e in errors[:5]:
            print(f"  {e}")

    total_findings = sum(len(v) for v in results.values())

    def write_json(payload: dict) -> None:
        out = Path(args.json_out)
        if out.parent and not out.parent.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                       encoding="utf-8")

    if not results:
        print()
        if stopped:
            print("Прогон прерван: обработано %d из %d файлов." % (total_files, total))
        else:
            print("ЧИСТО — иероглифов и порчи кодировки не найдено")
        if args.json_out:
            write_json({"root": str(root), "scanned": total_files,
                        "stopped": stopped, "findings": []})
        return 0

    print()
    print(f"НАЙДЕНО: {total_findings} вхождений в {len(results)} файлах")

    if not args.quiet:
        print()
        for rel in sorted(results, key=lambda r: -len(results[r])):
            items = results[rel]
            print(f"{rel}  — {len(items)} шт.")
            for f in items[:10]:
                print(f"  стр.{f['line']:>5}:{f['column']:<4} {f['range']}")
                if f["char"]:
                    print(f"       символ: {f['char']!r}  {f['codepoints']}")
                print(f"       контекст: {f['context']}")
            if len(items) > 10:
                print(f"  ... ещё {len(items) - 10}")
            print()

    if args.json_out:
        report = {
            "root": str(root),
            "scanned": total_files,
            "total": total_findings,
            "files": len(results),
            "stopped": stopped,
            "results": results,
        }
        write_json(report)
        print(f"Полный отчёт: {args.json_out}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
