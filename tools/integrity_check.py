"""
integrity_check — быстрая проверка целостности .md заметок (21.10).

Проверяет без анализа содержимого:
  - пустые файлы (0 байт)
  - битый UTF-8 (не декодируется)
  - незакрытый frontmatter (--- без пары в первых 50 строках)
  - отсутствие заголовка ## (строка, начинающаяся с '## ')

  python textools.py integrity --input <vault> [--out report.md]
      [--limit N] [--verbose]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.encoding import is_utf8

# 21.10: .git — железно (мусор в контекст), md_replace_backups — копии
# до правок, целостность оригиналов они не характеризуют
SKIP_DIRS = {".git", "md_replace_backups"}


def iter_md(root, limit):
    count = 0
    for p in sorted(Path(root).rglob("*.md")):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if limit is not None and count >= limit:
            return
        count += 1
        yield p


def check_file(path):
    """Список проблем одного файла (пусто = порядок)."""
    try:
        data = path.read_bytes()
    except (PermissionError, OSError):
        return []  # не читается — не наше дело, пропускаем молча
    if not data:
        return ["ПУСТОЙ ФАЙЛ"]
    if not is_utf8(path):
        return ["БИТЫЙ UTF-8"]
    text = data.decode("utf-8-sig")
    lines = text.split("\n")
    issues = []
    if lines[0].strip() == "---":
        if not any(l.strip() == "---" for l in lines[1:50]):
            issues.append("НЕЗАКРЫТЫЙ FRONTMATTER")
    if not any(l.startswith("## ") for l in lines):
        issues.append("НЕТ ЗАГОЛОВКА ##")
    return issues


def run(input_path, limit=None, verbose=False, out=None):
    root = Path(input_path)
    if root.is_file():
        files = [root]
    else:
        files = list(iter_md(root, limit))

    problems = []
    for p in files:
        for issue in check_file(p):
            problems.append((issue, p))

    print(f"Файлов проверено: {len(files)}")
    print(f"Проблем: {len(problems)}")
    if verbose and problems:
        for issue, p in problems[:40]:
            print(f"  {issue}: {p}")
        if len(problems) > 40:
            print(f"  ... ещё {len(problems) - 40}")

    if out:
        lines = ["# Integrity check", "",
                 f"Vault: {input_path}",
                 f"Файлов: {len(files)}", f"Проблем: {len(problems)}", ""]
        for issue, p in problems:
            lines.append(f"- {issue}: {p}")
        Path(out).write_text("\n".join(lines), encoding="utf-8")
        print(f"Отчёт: {out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Целостность .md: пустые, битый UTF-8, frontmatter, заголовки")
    ap.add_argument("--input", required=True, help="папка или один .md файл")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--out", help="файл отчёта")
    args = ap.parse_args(argv)
    return run(args.input, limit=args.limit, verbose=args.verbose, out=args.out)
