# -*- coding: utf-8 -*-
"""
backup_restore — обзор и восстановление из бэкапов (01.10).

Собирает все <файл>.bak рядом с оригиналами и снимки в папках
md_replace_backups/<timestamp>/; по --restore возвращает прежнее
содержимое. .bak при восстановлении сохраняется, поверх текущего файла
сначала кладётся его копия (<имя>.pre-restore.bak) — ничего не теряется.

Использование:
  python backup_restore.py --input <папка>               — обзор
  python backup_restore.py --input <папка> --restore     — восстановить всё
  python backup_restore.py --input <папка> --file a.md   — только один файл
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import text_parser as tp

BAK_SUFFIX = ".bak"


def find_backups(root, only=None):
    """[(тип, бэкап, оригинал)] — .bak рядом и последние снимки
    из md_replace_backups. only — имя файла без пути для фильтра."""
    root = Path(root)
    out = []
    files = list(root.rglob("*")) if root.is_dir() else [root]
    for f in files:
        if not f.is_file():
            continue
        if set(f.parts) & {".git", ".obsidian"}:
            continue
        # 1) .bak рядом с оригиналом (в т.ч. .pre-restore.bak)
        if f.name.endswith(BAK_SUFFIX):
            orig = Path(str(f)[:-len(BAK_SUFFIX)])
            if orig.exists() and (only is None or orig.name == only):
                out.append((".bak", f, orig))
    # 2) md_replace_backups: самый свежий снимок для каждого файла
    snaps = {}
    for f in files:
        if not f.is_file() or "md_replace_backups" not in f.parts:
            continue
        if only is not None and f.name != only:
            continue
        rel_parts = f.parts[f.parts.index("md_replace_backups") + 2:]
        key = "/".join(rel_parts)
        ts = f.parts[f.parts.index("md_replace_backups") + 1]
        if key not in snaps or ts > snaps[key][0]:
            snaps[key] = (ts, f)
    for ts, f in sorted(snaps.items()):
        # оригинал: корень входа + хвост rel-пути после <timestamp>/
        tail = Path(*f.parts[f.parts.index("md_replace_backups") + 2:])
        orig = root / tail
        if orig.exists():
            out.append(("снимок", f, orig))
    return out


def run(input_path, restore=False, only=None):
    if tp.stop_requested():
        print("Остановлено пользователем.")
        return 0
    pairs = find_backups(input_path, only)
    print(f"РЕЖИМ: {'ВОССТАНОВЛЕНИЕ' if restore else 'ТОЛЬКО ОБЗОР'}")
    print(f"Бэкапов найдено: {len(pairs)}")
    for kind, bak, orig in pairs[:40]:
        print(f"  [{kind}] {orig.name}  <-  {bak}")
    if len(pairs) > 40:
        print(f"  ... ещё {len(pairs) - 40}")
    if not pairs:
        print("Бэкапов нет — восстанавливать нечего.")
        return 0
    if not restore:
        print("\nРЕЖИМ ОБЗОРА — файлы не изменены. Для восстановления: --restore / галочка.")
        return 0

    n = 0
    for kind, bak, orig in pairs:
        if tp.stop_requested():
            print("Остановлено пользователем.")
            break
        # текущая версия сохраняется — откат отката всегда возможен
        pre = Path(str(orig) + ".pre-restore.bak")
        if not pre.exists():
            shutil.copy2(orig, pre)
        shutil.copy2(bak, orig)
        n += 1
        print(f"  [восстановлен] {orig}  ({kind}: {bak.name})")
    print(f"\nВосстановлено файлов: {n}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Обзор и восстановление из .bak и md_replace_backups")
    ap.add_argument("--input", required=True, help="папка хранилища")
    ap.add_argument("--restore", action="store_true",
                    help="восстановить (текущие версии сохраняются как .pre-restore.bak)")
    ap.add_argument("--file", help="восстановить только этот файл (по имени)")
    args = ap.parse_args(argv)
    return run(args.input, restore=args.restore, only=args.file)


if __name__ == "__main__":
    sys.exit(main())
