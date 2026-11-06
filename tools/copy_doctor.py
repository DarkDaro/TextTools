# -*- coding: utf-8 -*-
"""
copy_doctor — поиск старых копий TextTools и ярлыков к ним (07.11).

  python textools.py copy-doctor [--fix] [--roots папка1;папка2]

Головная боль «GUI не обновляется» — старые копии проекта и ярлыки,
которые запускают именно их: неделю выглядит так, будто ничего не
меняется, хотя GitHub обновился. Врач сканирует типовые места
(Рабочий стол, Загрузки, Документы, меню «Пуск», корень профиля) и
находит: папки-копии TextTools и ярлыки .lnk к ним.

Копия считается СТАРОЙ, если её gui_ctk.pyw не содержит маркер версии
(APP_VERSION появился 05.11) — такую копию с --fix можно переименовать
в «<имя>_СТАРАЯ» (всё reversibly, файлы не удаляются). Ярлыки, ведущие
в старую папку, --fix складывает в подпапку «_старые_ярлыки_TextTools»
рядом — тоже reversibly. Актуальная копия (та, где лежит этот файл)
не трогается никогда.

Без --fix — только отчёт. На не-Windows скан просто ничего не находит.
"""
import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CURRENT = Path(__file__).resolve().parent.parent
MAX_DEPTH = 4
SKIP_PARTS = {".git", ".obsidian", ".trash", ".smart-env", "__pycache__",
              "archive", "reports", "logs", "md_replace_backups",
              "node_modules", ".venv", "venv"}
LNK_DIRS = ("Desktop", "AppData/Roaming/Microsoft/Windows/Start Menu",
            "AppData/Roaming/Microsoft/Windows/Recent")
COPY_DIRS = ("Desktop", "Downloads", "Documents", "")
LNK_RE = re.compile(r"[A-Zа-яA-Za-z]:\\[^<>\"|?*\x00-\x1f]{1,200}?"
                    r"(?:gui_ctk\.pyw|textools[^\\]*\.bat)", re.IGNORECASE)


def default_roots():
    home = Path.home()
    roots = []
    for rel in COPY_DIRS:
        p = home / rel
        if p.is_dir():
            roots.append(p)
    return roots


def default_lnk_roots():
    home = Path.home()
    roots = []
    for rel in LNK_DIRS:
        p = home / rel
        if p.is_dir():
            roots.append(p)
    return roots


def _is_old_copy(pyw_path):
    """True, если gui_ctk.pyw без маркера версии (копия до 05.11)."""
    try:
        return "APP_VERSION" not in pyw_path.read_text(encoding="utf-8",
                                                       errors="ignore")
    except OSError:
        return False


def find_copies(roots):
    """[(папка, статус)] — папки-копии TextTools. SKIP_PARTS и текущая
    копия (где живёт этот файл) исключаются."""
    found = []
    seen = set()
    for root in roots:
        base_depth = len(root.parts)
        for dirpath, dirnames, filenames in os.walk(root):
            p = Path(dirpath)
            if len(p.parts) - base_depth >= MAX_DEPTH:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames
                           if d not in SKIP_PARTS and not d.startswith(".")]
            if not any(n in ("gui_ctk.pyw", "textools_gui.bat")
                       for n in filenames):
                continue
            if p.resolve() == CURRENT or p.resolve() in seen:
                continue
            seen.add(p.resolve())
            pyw = p / "gui_ctk.pyw"
            if pyw.exists() and _is_old_copy(pyw):
                found.append((p, "старая (нет маркера версии)"))
            elif pyw.exists():
                found.append((p, "с маркером версии — сверить по заголовку окна"))
            else:
                found.append((p, "только .bat, без gui_ctk.pyw"))
    return found


def _lnk_target(path):
    """Грубое извлечение цели из .lnk (UTF-16LE строки в бинарнике).
    Возвращает путь или None."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    text = raw.decode("utf-16-le", errors="ignore")
    m = LNK_RE.search(text)
    return m.group(0) if m else None


def find_shortcuts(roots):
    """[(ярлык, цель)] — ярлыки с textools в имени."""
    out = []
    seen = set()
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            p = Path(dirpath)
            dirnames[:] = [d for d in dirnames
                           if d not in SKIP_PARTS and not d.startswith(".")]
            for name in filenames:
                if "textools" not in name.lower() or not name.lower().endswith(".lnk"):
                    continue
                lnk = p / name
                if lnk.resolve() in seen:
                    continue
                seen.add(lnk.resolve())
                out.append((lnk, _lnk_target(lnk)))
    return out


def run(fix=False, roots=None, lnk_roots=None):
    roots = [Path(r) for r in roots] if roots else default_roots()
    lnk_roots = [Path(r) for r in lnk_roots] if lnk_roots else default_lnk_roots()
    copies = find_copies(roots)
    lnks = find_shortcuts(lnk_roots)
    print(f"Актуальная копия (запускается сейчас): {CURRENT}")
    if not copies and not lnks:
        print("Старых копий и ярлыков TextTools не найдено — чисто.")
        return 0
    stale_dirs = set()
    print(f"\nПапки-копии TextTools: {len(copies)}")
    for p, status in copies:
        print(f"  {p} — {status}")
        if status.startswith("старая"):
            stale_dirs.add(p.resolve())
    moved_lnk = 0
    renamed = 0
    print(f"\nЯрлыки .lnk с textools в имени: {len(lnks)}")
    for lnk, target in lnks:
        tgt_dir = Path(target).parent if target else None
        stale = bool(tgt_dir and tgt_dir.resolve() in stale_dirs)
        if target:
            print(f"  {lnk} → {target}"
                  + ("  (ведёт в СТАРУЮ копию)" if stale else ""))
        else:
            print(f"  {lnk} → цель не распознана")
        if fix and stale:
            # reversibly: ярлык переезжает в подпапку рядом
            junk = lnk.parent / "_старые_ярлыки_TextTools"
            junk.mkdir(exist_ok=True)
            try:
                os.rename(lnk, junk / lnk.name)
                moved_lnk += 1
                print(f"    перемещён в {junk}")
            except OSError as e:
                print(f"    не удалось: {e}")
    if fix:
        for p in stale_dirs:
            new_name = p.parent / (p.name + "_СТАРАЯ")
            if new_name.exists():
                print(f"  {p}: «{new_name.name}» уже существует — пропущено")
                continue
            try:
                os.rename(p, new_name)
                renamed += 1
                print(f"  папка переименована: {p} → {new_name.name}")
            except OSError as e:
                print(f"  {p}: не удалось переименовать (файлы заняты?): {e}")
        print(f"\nГотово: папок переименовано {renamed}, "
              f"ярлыков убрано {moved_lnk}.")
    else:
        print("\nЭто только отчёт. Убрать мешающее: "
              "python textools.py copy-doctor --fix")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Поиск старых копий TextTools и ярлыков к ним")
    ap.add_argument("--fix", action="store_true",
                    help="переименовать старые папки в *_СТАРАЯ и убрать "
                         "ярлыки к ним (reversibly)")
    ap.add_argument("--roots", help="дополнительные папки для скана "
                                    "копий через «;»")
    ap.add_argument("--out", help="файл отчёта не пишется — вывод в лог")
    args = ap.parse_args(argv)
    roots = args.roots.split(";") if args.roots else None
    return run(fix=args.fix, roots=roots)


if __name__ == "__main__":
    sys.exit(main())
