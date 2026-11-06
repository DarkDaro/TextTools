# refile.py — массовое редактирование файлов по регулярным выражениям
# Использовать: python refile.py <pattern> -r <replacement> --exts py js md
# 22.09: .docx по умолчанию НЕ обрабатывается (это zip-бинарник) —
# только при явном --exts docx, и тогда замена идёт через docx-модуль textools.

import re
import os
import sys
from pathlib import Path

# 22.09: docx-поддержка через общий модуль textools (если рядом)
_SCRIPT_DIR = Path(__file__).resolve().parent
for _cand in (_SCRIPT_DIR / "textools",):
    if str(_cand) not in sys.path and _cand.is_dir():
        sys.path.insert(0, str(_cand))
try:
    from core import docx_io
except ImportError:
    docx_io = None

DOCX_WARN = (
    "  ВНИМАНИЕ: --exts docx подключает docx-обработку. Замена идёт по тексту "
    "w:t, форматирование сохраняется, .bak создаётся автоматически.")


def batch_replace(
    root_dir=".",
    pattern=r".*",
    replacement="",
    include_extensions=None,  # set("py", "js", "md") or None = all files
    exclude_dirs=None,        # set(".git", "node_modules"), default: gitignored dirs
    dry_run=False,
):
    """Массовая замена по regex в файлах директории рекурсивно.

    22.09: без --exts обрабатываются все ТЕКСТОВЫЕ файлы; .docx —
    только если явно указан в --exts (иначе пропускается как бинарник)."""

    if include_extensions is None:
        include_exts = set()  # no filter by default
    else:
        include_exts = {e.lower().lstrip(".") for e in include_extensions}
    docx_allowed = "docx" in include_exts

    exclude_dirs = exclude_dirs or {".git", "node_modules", ".venv", "__pycache__"}

    root = Path(root_dir)
    changed_files = []

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue

        # skip directories we don't want to enter
        rel_parts = [p.lower() for p in file_path.parts]
        if any(part in exclude_dirs for part in rel_parts):
            continue

        ext = file_path.suffix.lstrip(".").lower()
        if include_exts and ext not in include_exts:
            continue

        # 22.09: docx только при явном --exts docx
        if ext == "docx":
            if not docx_allowed:
                continue
            if docx_io is None:
                print(f"  ПРОПУСК {file_path.name}: docx-модуль textools не найден")
                continue
            try:
                count, _ch, _b = docx_io.replace_in_docx(
                    file_path, pattern, replacement, is_regex=True,
                    backup=not dry_run)
            except Exception as e:
                print(f"  Ошибка docx {file_path.name}: {e}")
                continue
            if count > 0:
                changed_files.append((str(file_path), count))
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue  # binary / no access

        new_content, count = re.subn(pattern, replacement, content)

        if count > 0:
            changed_files.append((str(file_path), count))

            if not dry_run:
                file_path.write_text(new_content, encoding="utf-8")

    return changed_files


def batch_search(
    root_dir=".",
    pattern=r".*",
    include_extensions=None,
    exclude_dirs=None,
):
    """Найти все совпадения в файлах (без замены)."""

    if include_extensions is None:
        include_exts = set()
    else:
        include_exts = {e.lower().lstrip(".") for e in include_extensions}
    docx_allowed = "docx" in include_exts

    exclude_dirs = exclude_dirs or {".git", "node_modules", ".venv", "__pycache__"}

    root = Path(root_dir)
    results = []  # [(file, matches)]

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue

        rel_parts = [p.lower() for p in file_path.parts]
        if any(part in exclude_dirs for part in rel_parts):
            continue

        ext = file_path.suffix.lstrip(".").lower()
        if include_exts and ext not in include_exts:
            continue

        # 22.09: docx только при явном --exts docx
        if ext == "docx":
            if not docx_allowed:
                continue
            if docx_io is None:
                continue
            try:
                text = docx_io.read_text(file_path)
            except Exception:
                continue
            if text:
                matches = re.findall(pattern, text)
                if matches:
                    results.append((str(file_path), matches))
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        matches = re.findall(pattern, content)
        if matches:
            results.append((str(file_path), matches))

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Массовое редактирование файлов по regex")
    parser.add_argument("pattern", help="Regex-паттерн")
    parser.add_argument("-r", "--replacement", default="", help="Чем заменить (по умолчанию убрать)")
    parser.add_argument("-d", "--dir", default=".", help="Директория для рекурсии")
    parser.add_argument("--exts", nargs="+", help="Расширения файлов: py js md txt (docx — только явно)")
    parser.add_argument("--exclude-dirs", nargs="+", default=[".git", "node_modules"])
    parser.add_argument("--dry-run", action="store_true", help="Только показать что изменится")

    args = parser.parse_args()

    print(f"🔍 Паттерн: {args.pattern}")
    print(f"   Замена на: {repr(args.replacement)}")
    print(f"   Директория: {args.dir}\n")
    # 22.09: предупреждение при явном docx
    if args.exts and "docx" in {e.lower().lstrip(".") for e in args.exts}:
        print(DOCX_WARN + "\n")

    if args.dry_run:
        print("РЕЖИМ: DRY-RUN (файлы не изменены)")
        changed = batch_replace(
            root_dir=args.dir,
            pattern=args.pattern,
            replacement=args.replacement,
            include_extensions=args.exts,
            exclude_dirs=set(args.exclude_dirs),
            dry_run=True,
        )
        print(f"📁 Изменено файлов: {len(changed)}")
        for path, count in changed:
            print(f"   {path} ({count} совпадений)")
    else:
        print("РЕЖИМ: РЕАЛЬНАЯ ЗАМЕНА")
        changed = batch_replace(
            root_dir=args.dir,
            pattern=args.pattern,
            replacement=args.replacement,
            include_extensions=args.exts,
            exclude_dirs=set(args.exclude_dirs),
        )
        print(f"✅ Изменено файлов: {len(changed)}")
        for path, count in changed:
            print(f"   {path} ({count} совпадений)")

    # поиск тоже можно вызвать
    # results = batch_search(root_dir=args.dir, pattern=args.pattern)
