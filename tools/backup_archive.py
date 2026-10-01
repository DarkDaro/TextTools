# -*- coding: utf-8 -*-
"""
backup_archive — авто-архивация старых бэкапов (01.10, СЛ6).

Бэкапы (.bak рядом с файлами и папки md_replace_backups/<timestamp>/)
старше N дней ПЕРЕНОСЯТСЯ (не удаляются!) в централизованное хранилище
textools/archive/backups/<имя-источника>/ с сохранением относительной
структуры. Ничего не перезаписывается: при конфликте имён добавляется
суффикс времени.

Использование:
  python backup_archive.py --input <папка>                  — обзор
  python backup_archive.py --input <папка> --days 30 --move — перенести
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import text_parser as tp

ARCHIVE_ROOT = Path(__file__).resolve().parent.parent / "archive" / "backups"


def collect_old(root, days):
    """[(путь, возраст_дней)] — бэкапы старше N дней."""
    cutoff = time.time() - days * 86400
    out = []
    root = Path(root)
    files = list(root.rglob("*")) if root.is_dir() else []
    for f in files:
        if not f.is_file():
            continue
        if set(f.parts) & {".git", ".obsidian"}:
            continue
        is_bak = f.name.endswith(".bak")
        in_snap = "md_replace_backups" in f.parts
        if not (is_bak or in_snap):
            continue
        try:
            mtime = f.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            out.append((f, round((time.time() - mtime) / 86400, 1)))
    return out


def _unique(dest):
    """Путь, которого ещё нет (конфликт — суффикс времени, без перезаписи)."""
    if not dest.exists():
        return dest
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return dest.with_name(f"{dest.stem}.{stamp}{dest.suffix}")


def run(input_path, days=30, move=False):
    if tp.stop_requested():
        return 0
    old = collect_old(input_path, days)
    root = Path(input_path)
    print(f"РЕЖИМ: {'ПЕРЕНОС В АРХИВ' if move else 'ТОЛЬКО ОБЗОР'}")
    print(f"Бэкапов старше {days} дн.: {len(old)} (хранилище: {ARCHIVE_ROOT})")
    src_name = root.name or "vault"
    for f, age in old[:40]:
        print(f"  [{age:>6} дн.] {f}")
    if len(old) > 40:
        print(f"  ... ещё {len(old) - 40}")
    if not old:
        print("Старых бэкапов нет — архивировать нечего.")
        return 0
    if not move:
        print("\nРЕЖИМ ОБЗОРА — ничего не перенесено. Для переноса: --move / галочка.")
        return 0

    n = 0
    for f, _age in old:
        if tp.stop_requested():
            print("Остановлено пользователем.")
            break
        # сохраняем относительную структуру внутри источника
        rel = f.relative_to(root) if root.is_dir() else Path(f.name)
        # .bak лежит рядом с оригиналом; снимки — внутри md_replace_backups
        if root.is_file():
            rel = Path(f.name)
        dest = _unique(ARCHIVE_ROOT / src_name / rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), str(dest))  # перенос, не удаление
        n += 1
        print(f"  [архивирован] {f.name} -> {dest}")
    # пустые папки-обёртки снимков остаются на месте (ничего не удаляем)
    print(f"\nПеренесено в архив: {n}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Архивация старых бэкапов (перенос в archive/backups)")
    ap.add_argument("--input", required=True, help="папка хранилища")
    ap.add_argument("--days", type=int, default=30,
                    help="возраст в днях (по умолчанию 30)")
    ap.add_argument("--move", action="store_true",
                    help="перенести в архив (иначе только обзор)")
    args = ap.parse_args(argv)
    return run(args.input, days=args.days, move=args.move)


if __name__ == "__main__":
    sys.exit(main())
