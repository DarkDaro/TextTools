"""Перенос личных скриптов в external/ — разовая миграция.

06.11: внешние инструменты (эмодзи-чистка, md-replace, поиск
персонажей, refile, clean_text) раньше лежали вне репозитория, и
после клонирования их кнопки GUI не работали. Теперь они едут вместе
с программой в папке external/, автопоиск проверяет её первой
(wrappers.SCRIPT_CANDIDATES).

Скрипт находит инструменты тем же поиском, что и GUI, копирует их
в external/ вместе с соседями по папке (.py/.md/.yaml/.json/.txt —
без bak/log и без подпапок) и в конце сверяет, что все пять копий
на месте и проходят проверку подписи.

Запуск из корня репозитория:  python tools/bundle_external.py
Повторный запуск просто перезаписывает external/ свежими копиями.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wrappers import _looks_like_script, find_scripts  # noqa: E402

# ключ -> (папка в external/, копировать соседей из исходной папки)
# соседи нужны, если скрипт тянет рядом лежащие модули или данные
TARGETS = {
    "emoji_cleaner": ("external/emoji-cleaner", True,
                      "external/emoji-cleaner/clean.py"),
    "md_replace": ("external/md-replace", True,
                   "external/md-replace/md_replace.py"),
    "char_search": ("external/md-replace", True,
                    "external/md-replace/char_search.py"),
    "refile": ("external", False, "external/refile.py"),
    "clean_text": ("external/herodata", False,
                   "external/herodata/clean_text_files.py"),
}

COPY_EXT = {".py", ".md", ".yaml", ".yml", ".json", ".txt"}
SKIP_EXT = {".bak", ".log", ".tmp", ".pyc"}

# 06.11: md_replace и char_search живут в одной папке — копируем её один раз
_copied_dirs = set()


def copy_with_siblings(src, dst_dir, label=""):
    """Файл и разрешённые соседи из его папки (без подпапок)."""
    if dst_dir in _copied_dirs:
        print(f"  папка уже скопирована ({label})")
        return
    _copied_dirs.add(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    for f in sorted(src.parent.iterdir()):
        if not f.is_file() or f.name.startswith((".", "~$")):
            continue
        if f.suffix.lower() not in COPY_EXT or f.suffix.lower() in SKIP_EXT:
            continue
        shutil.copy2(f, dst_dir / f.name)
        size_kb = f.stat().st_size / 1024
        print(f"  {(dst_dir / f.name).relative_to(ROOT)} "
              f"({size_kb:.1f} КБ)")


def main():
    found = find_scripts()
    if not found:
        print("Автопоиск не нашёл ни одного скрипта. Запусти из папки "
              "репозитория или задай TEXTOOLS_SCRIPTS_DIR.")
        return 1
    for key, (rel, _with_sib, _main) in TARGETS.items():
        src = found.get(key)
        print(f"{key}: " + (src if src else "НЕ НАЙДЕН — скопируй вручную"))
        if src:
            dst = ROOT / rel
            if _with_sib:
                copy_with_siblings(Path(src), dst, label=key)
            else:
                dst.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst / Path(src).name)
                print(f"  {rel}/{Path(src).name}")
    # сверка: каждая ожидаемая копия существует и похожа на инструмент
    print("\nПроверка external/:")
    ok = 0
    for key, (_rel, _sib, main_file) in TARGETS.items():
        p = ROOT / main_file
        if p.is_file() and _looks_like_script(key, p):
            print(f"  {key}: ок ({main_file})")
            ok += 1
        else:
            print(f"  {key}: файла нет или он не похож на инструмент "
                  f"({main_file})")
    print(f"\nИтого: {ok} из {len(TARGETS)}. Дальше вручную: "
          "git add external/ && git commit")
    return 0 if ok == len(TARGETS) else 1


if __name__ == "__main__":
    sys.exit(main())
