"""
Обёртки над внешними скриптами.

Каждая функция собирает командную строку и возвращает её (список аргументов).
Запуск выполняет Runner (gui_ctk) через subprocess, stdout перехватывается
в GUI-лог.

Внешние скрипты НЕ изменяются — вызываются как есть.
md_replace / char_search при реальной записи требуют подтверждения:
GUI всегда передаёт --yes, подтверждением служит чекбокс «Применить изменения».
"""
from pathlib import Path
import os
import sys

# 25.10: базовые пути к внешним скриптам. Абсолютные пути в коде не
# хранятся: ищем знакомые раскладки рядом с проектом и в каталогах
# пользователя. Найденное подставляется в пустые поля настроек.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOME_ROOT = Path.home()

# Относительные пути от одной из базовых папок. Порядок важен:
# сначала специфичные для проекта каталоги, потом общие имена.
SCRIPT_CANDIDATES = {
    "emoji_cleaner": (
        "emoji-cleaner/clean.py",
        "emoji_cleaner/clean.py",
        "emoji-cleaner.py",
    ),
    "clean_text": (
        "scripts/Archive/herodata/clean_text_files.py",
        "herodata/clean_text_files.py",
        "clean_text_files.py",
        "clean-text/clean_text_files.py",
    ),
    "md_replace": (
        "md-replace/md_replace.py",
        "md_replace/md_replace.py",
        "md_replace.py",
    ),
    "char_search": (
        "md-replace/char_search.py",
        "md_replace/char_search.py",
        "char_search.py",
    ),
    "refile": (
        "refile.py",
        "refile/refile.py",
    ),
}

# 25.10: недостаточно проверить имя файла. Одноимённый чужой скрипт в
# домашнем каталоге не должен попасть в автопоиск: сверяем заметные
# строки конкретного инструмента. Ручной путь в настройках не проверяется.
SCRIPT_SIGNATURES = {
    "emoji_cleaner": ("эмодзи", "--restore"),
    "clean_text": ("clean_text_files", "китайских"),
    "md_replace": ("Массовая автозамена", "--dry-run"),
    "char_search": ("Поиск персонажей", "--vault"),
    "refile": ("массовое редактирование", "--exts"),
}


def _looks_like_script(key, path):
    """Проверить, что файл похож на нужный инструмент по его строкам."""
    markers = SCRIPT_SIGNATURES.get(key, ())
    try:
        text = Path(path).read_text(encoding="utf-8",
                                     errors="replace")[:16384].lower()
    except OSError:
        return False
    return bool(markers) and all(marker.lower() in text for marker in markers)


def _script_roots(root=None):
    """Папки, в которых ищем скрипты. root задаёт только одну папку."""
    if root is not None:
        return [Path(root)]
    roots = []
    env = os.environ.get("TEXTOOLS_SCRIPTS_DIR", "").strip()
    if env:
        roots.append(Path(env))
    roots.extend([
        PROJECT_ROOT,
        PROJECT_ROOT.parent,
        PROJECT_ROOT.parent.parent,
        HOME_ROOT / "python-projects",
        HOME_ROOT / "projects",
        Path.cwd(),
    ])
    # без дублей, сохраняя порядок
    seen = set()
    out = []
    for p in roots:
        try:
            key = str(p.resolve()).lower()
        except Exception:
            key = str(p).lower()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def find_scripts(root=None):
    """{ключ: путь} для найденных внешних скриптов. root — только эта папка."""
    found = {}
    for base in _script_roots(root):
        for key, relatives in SCRIPT_CANDIDATES.items():
            if key in found:
                continue
            for rel in relatives:
                p = base / rel
                if p.is_file() and _looks_like_script(key, p):
                    found[key] = str(p)
                    break
    return found


# 25.10: не кэшируем на импорте. Кэш сбрасывается при смене
# TEXTOOLS_SCRIPTS_DIR или рабочей папки, иначе новый путь находился бы
# только после перезапуска GUI.
_default_cache = None
_default_key = None


def default_scripts():
    """Найденные скрипты с кэшем, зависящим от окружения и cwd."""
    global _default_cache, _default_key
    key = (os.environ.get("TEXTOOLS_SCRIPTS_DIR", "").strip(),
           str(Path.cwd()))
    if _default_cache is None or key != _default_key:
        _default_cache = find_scripts()
        _default_key = key
    return _default_cache


TEXT_EXTS = ["md", "txt"]


def script_preset():
    """Текущий пресет: auto / manual / off. Старые конфиги = auto."""
    from gui_config import CFG
    value = str(CFG.get("script_preset", "auto") or "auto").strip().lower()
    return value if value in ("auto", "manual", "off") else "auto"


def script_source(key):
    """Откуда взят путь: custom / auto / ""."""
    from gui_config import CFG
    custom = str(CFG.get(f"script_{key}", "") or "").strip()
    if custom and Path(custom).is_file():
        return "custom"
    default = default_scripts().get(key, "")
    if default and Path(default).is_file():
        return "auto"
    if find_scripts().get(key):
        return "auto"
    return ""


def script_path(key):
    """Путь к внешнему скрипту: настройка -> автопоиск -> "".
    Пресет off отключает внешние скрипты целиком."""
    from gui_config import CFG
    if script_preset() == "off":
        return ""
    custom = str(CFG.get(f"script_{key}", "") or "").strip()
    if custom and Path(custom).is_file():
        return custom
    default = default_scripts().get(key, "")
    if default and Path(default).is_file():
        return default
    return find_scripts().get(key, "")


def cmd_emoji_clean(paths, dry_run=True, backup=False, restore=False):
    """Чистка эмодзи/смайлов в txt/md/docx."""
    cmd = [sys.executable, script_path("emoji_cleaner"), *paths]
    if restore:
        cmd.append("--restore")
    else:
        if dry_run:
            cmd.append("--dry-run")
        if backup:
            cmd.append("--backup")
    return cmd


def cmd_clean_text(root, apply=False):
    """Чистка мусора/CJK в txt/md (whitelist)."""
    cmd = [sys.executable, script_path("clean_text"), root]
    if apply:
        cmd.append("--fix")
    return cmd


def cmd_md_replace(vault, old, new, is_regex=False, subdir=None,
                   include=None, exclude=None, dry_run=True, no_backup=False):
    """Массовая замена в .md по vault."""
    cmd = [sys.executable, script_path("md_replace"), old, new, "--vault", vault]
    if is_regex:
        cmd.append("--regex")
    if subdir:
        cmd += ["--subdir", subdir]
    for inc in (include or []):
        cmd += ["--include", inc]
    for exc in (exclude or []):
        cmd += ["--exclude", exc]
    if dry_run:
        cmd.append("--dry-run")
    if no_backup:
        cmd.append("--no-backup")
    cmd.append("--yes")
    return cmd


def cmd_md_find_bad(vault, subdir=None):
    """Найти проблемные unicode-символы."""
    cmd = [sys.executable, script_path("md_replace"), "--find-bad", "--vault", vault]
    if subdir:
        cmd += ["--subdir", subdir]
    return cmd


def cmd_md_fix_encoding(vault, subdir=None, dry_run=True, no_backup=False):
    """Пересохранить файлы в UTF-8."""
    cmd = [sys.executable, script_path("md_replace"), "--fix-encoding", "--vault", vault]
    if subdir:
        cmd += ["--subdir", subdir]
    if dry_run:
        cmd.append("--dry-run")
    if no_backup:
        cmd.append("--no-backup")
    cmd.append("--yes")
    return cmd


def cmd_md_strip_bad(vault, subdir=None, dry_run=True, no_backup=False):
    """Вырезать мусорные unicode-символы."""
    cmd = [sys.executable, script_path("md_replace"), "--strip-bad", "--vault", vault]
    if subdir:
        cmd += ["--subdir", subdir]
    if dry_run:
        cmd.append("--dry-run")
    if no_backup:
        cmd.append("--no-backup")
    cmd.append("--yes")
    return cmd


def cmd_char_search(vault, char=None, fix=False, dry_run=True, no_backup=False):
    """Проверка/исправление имён персонажей по characters.yaml."""
    cmd = [sys.executable, script_path("char_search"), "--vault", vault]
    if char:
        cmd.append(char)
    if fix:
        cmd.append("--fix")
        if dry_run:
            cmd.append("--dry-run")
        if no_backup:
            cmd.append("--no-backup")
        cmd.append("--yes")
    return cmd


def cmd_char_fix_word(vault, bad, good, dry_run=True, no_backup=False):
    """22.09: точечная замена одного слова (--fix-word) без реестра."""
    cmd = [sys.executable, script_path("char_search"), "--vault", vault,
           "--fix-word", bad, good]
    if dry_run:
        cmd.append("--dry-run")
    if no_backup:
        cmd.append("--no-backup")
    cmd.append("--yes")
    return cmd


def cmd_refile(directory, pattern, replacement="", exts=None,
               exclude_dirs=None, dry_run=True):
    """Массовая regex-замена по папке."""
    cmd = [sys.executable, script_path("refile"), pattern,
           "-r", replacement, "-d", directory]
    if exts:
        cmd += ["--exts", *exts]
    if exclude_dirs:
        cmd += ["--exclude-dirs", *exclude_dirs]
    if dry_run:
        cmd.append("--dry-run")
    return cmd