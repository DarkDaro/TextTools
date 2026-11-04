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
    из md_replace_backups. only — имя файла без пути для фильтра.

    04.11: снимки писателей лежат в <папка оригинала>/md_replace_backups/
    <штамп>/ — плоское имя или вложенный rel-путь. Оригинал определяется
    от родителя папки снимков, а не от корня входа: раньше снимок для
    vault/sub/a.md восстанавливался в vault/a.md, затирая чужую заметку.
    """
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
        idx = f.parts.index("md_replace_backups")
        ts = f.parts[idx + 1]
        key = "/".join(f.parts[idx + 2:])
        if key not in snaps or ts > snaps[key][0]:
            snaps[key] = (ts, f)
    for key, (ts, f) in sorted(snaps.items()):
        # основной кандидат: снимок лежит рядом с оригиналом (оба
        # писателя — phrase_check и yo_audit — кладут папку снимков
        # в ту же папку, где файл). Запасной — вложенная раскладка
        # от корня входа, на случай сторонних снимков.
        idx = f.parts.index("md_replace_backups")
        tail = Path(*f.parts[idx + 2:])
        orig = f.parent.parent.parent / f.name
        if not orig.exists():
            alt = root / tail
            orig = alt if alt.exists() else None
        if orig is not None:
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
    fails = 0
    for kind, bak, orig in pairs:
        if tp.stop_requested():
            print("Остановлено пользователем.")
            break
        try:
            # текущая версия сохраняется — откат отката всегда возможен
            pre = Path(str(orig) + ".pre-restore.bak")
            if not pre.exists():
                shutil.copy2(orig, pre)
            # 04.11: занятый файл (редактор, синхронизация) не роняет
            # прогон — остальные восстанавливаются
            shutil.copy2(bak, orig)
        except (PermissionError, OSError) as e:
            fails += 1
            print(f"  [ПРОПУСК] {orig}: {e}")
            continue
        n += 1
        print(f"  [восстановлен] {orig}  ({kind}: {bak.name})")
    print(f"\nВосстановлено файлов: {n}" +
          (f", пропущено {fails}" if fails else ""))
    return 1 if fails else 0


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
