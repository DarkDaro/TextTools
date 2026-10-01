"""
Обёртки над внешними скриптами.

Каждая функция собирает командную строку и возвращает её (список аргументов).
Запуск выполняет runner.py через subprocess, stdout перехватывается в GUI-лог.

Внешние скрипты НЕ изменяются — вызываются как есть.
md_replace / char_search при реальной записи требуют подтверждения:
GUI всегда передаёт --yes, подтверждением служит чекбокс «Применить изменения».
"""
from pathlib import Path

# Пути к внешним скриптам (переопределяются в настройках GUI)
DEFAULTS = {
    "emoji_cleaner": r"C:\AgentLetta\python-projects\emoji-cleaner\clean.py",
    "clean_text": r"C:\AgentLetta\scripts\clean_text_files.py",
    "md_replace": r"C:\AgentLetta\python-projects\md-replace\md_replace.py",
    "char_search": r"C:\AgentLetta\python-projects\md-replace\char_search.py",
    "refile": r"C:\AgentLetta\python-projects\refile.py",
}

TEXT_EXTS = ["md", "txt"]


def script_path(key):
    """18.09: путь к скрипту с учётом настроек GUI (script_<key> в конфиге).
    Пустое/несуществующее значение -> путь по умолчанию."""
    from gui_config import CFG
    custom = CFG.get(f"script_{key}")
    if custom and Path(custom).is_file():
        return custom
    return DEFAULTS[key]


def cmd_emoji_clean(paths, dry_run=True, backup=False, restore=False):
    """Чистка эмодзи/смайлов в txt/md/docx."""
    cmd = ["python", script_path("emoji_cleaner"), *paths]
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
    cmd = ["python", script_path("clean_text"), root]
    if apply:
        cmd.append("--fix")
    return cmd


def cmd_md_replace(vault, old, new, is_regex=False, subdir=None,
                   include=None, exclude=None, dry_run=True, no_backup=False):
    """Массовая замена в .md по vault."""
    cmd = ["python", script_path("md_replace"), old, new, "--vault", vault]
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
    cmd = ["python", script_path("md_replace"), "--find-bad", "--vault", vault]
    if subdir:
        cmd += ["--subdir", subdir]
    return cmd


def cmd_md_fix_encoding(vault, subdir=None, dry_run=True, no_backup=False):
    """Пересохранить файлы в UTF-8."""
    cmd = ["python", script_path("md_replace"), "--fix-encoding", "--vault", vault]
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
    cmd = ["python", script_path("md_replace"), "--strip-bad", "--vault", vault]
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
    cmd = ["python", script_path("char_search"), "--vault", vault]
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
    cmd = ["python", script_path("char_search"), "--vault", vault,
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
    cmd = ["python", script_path("refile"), pattern,
           "-r", replacement, "-d", directory]
    if exts:
        cmd += ["--exts", *exts]
    if exclude_dirs:
        cmd += ["--exclude-dirs", *exclude_dirs]
    if dry_run:
        cmd.append("--dry-run")
    return cmd