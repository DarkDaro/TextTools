"""
Массовая автозамена в .md/.txt/.docx файлах (22.09: добавлены .txt и .docx)
Находит и заменяет текст по всем файлам хранилища
Полезно: переименовал персонажа -- заменил везде разом

Функции:
  - Обычный поиск и замена текста
  - Regex-поиск и замена
  - Режим --dry-run (показать что заменится, не трогать файлы)
  - Подтверждение перед заменой
  - Бэкап файлов перед изменением
  - Фильтр по папке/имени файла
  - Сводка: сколько файлов, сколько замен
  - .docx: правится только текст (w:t), форматирование сохраняется
"""

import os
import re
import sys
import shutil
import time
from pathlib import Path

# 22.09: docx-поддержка через общий модуль textools (если рядом)
_SCRIPT_DIR = Path(__file__).resolve().parent
for _cand in (_SCRIPT_DIR.parent / "textools",):
    if str(_cand) not in sys.path and _cand.is_dir():
        sys.path.insert(0, str(_cand))
try:
    from core import docx_io
except ImportError:
    docx_io = None  # docx будет пропущен с предупреждением

TEXT_EXTS = (".md", ".txt", ".docx")


# --- Настройки -----------------------------------------------------------

DEFAULT_VAULT = r"C:\Users\Dario\Documents\DaroObsidian\Daro Coding"
BACKUP_DIR = "md_replace_backups"


# --- Утилиты ---------------------------------------------------------------

def format_size(bytes_size):
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    else:
        return f"{bytes_size / (1024 * 1024):.1f} MB"


def count_matches(text, pattern, is_regex):
    """Считает количество совпадений в тексте"""
    if is_regex:
        return len(re.findall(pattern, text))
    else:
        return text.count(pattern)


def collect_files(search_root, include=None, exclude=None):
    """22.09: сбор .md/.txt/.docx файлов с фильтрами include/exclude и
    пропуском служебных папок. Замена повторявшегося rglob('*.md') в 4 местах."""
    files = []
    for ext in TEXT_EXTS:
        files.extend(search_root.rglob("*" + ext))
    if include:
        inc_patterns = [p.lower() for p in include]
        files = [f for f in files
                 if any(p in f.name.lower() for p in inc_patterns)]
    if exclude:
        exc_patterns = [p.lower() for p in exclude]
        files = [f for f in files
                 if not any(p in f.name.lower() for p in exc_patterns)]
    # Служебные папки
    files = [f for f in files
             if ".obsidian" not in f.parts and "md_replace_backups" not in f.parts
             and not f.name.endswith(".bak")]
    return sorted(files)


def find_in_file(filepath, pattern, is_regex):
    """Ищет совпадения в файле, возвращает список (строка, номер, текст_строки)
    22.09: docx читается через docx_io (по параграфам)."""
    if filepath.suffix.lower() == ".docx":
        if docx_io is None:
            return []
        content = docx_io.read_text(filepath)
        if content is None:
            return []
    else:
        try:
            content = filepath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            return []

    results = []
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        if is_regex:
            if re.search(pattern, line):
                results.append((i, line))
        else:
            if pattern in line:
                results.append((i, line))
    return results


def replace_in_text(text, old, new, is_regex):
    """Заменяет текст, возвращает (новый_текст, количество_замен)"""
    if is_regex:
        new_text, count = re.subn(old, new, text)
    else:
        count = text.count(old)
        new_text = text.replace(old, new)
    return new_text, count


# --- Основная логика --------------------------------------------------------

def scan_vault(vault_path, pattern, is_regex=False, subdir=None,
               include=None, exclude=None):
    """Сканирует vault, находит файлы с совпадениями"""
    vault = Path(vault_path)
    if not vault.exists():
        print(f"Папка не найдена: {vault_path}")
        return []

    # Стартовая папка
    if subdir:
        search_root = vault / subdir
        if not search_root.exists():
            print(f"Подпапка не найдена: {subdir}")
            return []
    else:
        search_root = vault

    # Собираем .md/.txt/.docx файлы (22.09)
    md_files = collect_files(search_root, include, exclude)

    # Ищем совпадения
    matches = []
    for filepath in md_files:
        results = find_in_file(filepath, pattern, is_regex)
        if results:
            matches.append((filepath, results))

    return matches


def replace_in_vault(vault_path, old, new, is_regex=False, subdir=None,
                     include=None, exclude=None, dry_run=False,
                     no_backup=False, yes=False):
    """Массовая замена по vault"""
    print(f"Vault: {vault_path}")
    if subdir:
        print(f"Папка: {subdir}")
    print(f"Поиск: {old}")
    if is_regex:
        print("Режим: regex")
    print(f"Замена: {new}")
    if dry_run:
        print("[DRY-RUN] Файлы не изменяются")
    print()

    # Скан
    matches = scan_vault(vault_path, old, is_regex, subdir, include, exclude)

    if not matches:
        print("Совпадений не найдено.")
        return

    # Считаем общее количество
    # 22.09: счёт через ту же функцию, что и реальная замена
    # (раньше считались строки, число расходилось с итогом замен)
    total_files = len(matches)
    total_replacements = 0
    for filepath, results in matches:
        try:
            # 22.09: docx — счёт через docx_io, не через read_text (utf-8 падает)
            if filepath.suffix.lower() == ".docx":
                if docx_io is not None:
                    total_replacements += docx_io.count_in_docx(
                        filepath, old, is_regex=is_regex)
                continue
            content = filepath.read_text(encoding="utf-8")
            _, count = replace_in_text(content, old, new, is_regex)
            total_replacements += count
        except Exception:
            pass

    # Показываем результаты
    print(f"Найдено: {total_files} файлов, {total_replacements} замен")
    print()

    # Показываем первые совпадения
    max_show = 20
    shown = 0
    for filepath, results in matches:
        if shown >= max_show:
            remaining = total_files - shown
            print(f"  ... и ещё {remaining} файлов")
            break
        rel_path = filepath.relative_to(vault_path)
        print(f"  {rel_path} ({len(results)} совпадений)")
        for line_num, line_text in results[:3]:
            # Подсвечиваем совпадение
            trimmed = line_text.strip()
            if len(trimmed) > 100:
                trimmed = trimmed[:100] + "..."
            # Убираем символы которые не может напечатать консоль Windows
            safe = trimmed.encode("cp1251", errors="replace").decode("cp1251")
            print(f"    L{line_num}: {safe}")
        if len(results) > 3:
            print(f"    ... ещё {len(results) - 3} совпадений")
        shown += 1

    print()

    # Подтверждение
    if not dry_run:
        if not yes:
            answer = input(f"Заменить в {total_files} файлах? [y/N]: ").strip().lower()
            if answer not in ("y", "yes", "д", "да"):
                print("Отменено.")
                return

    # Бэкап
    if not dry_run and not no_backup:
        backup_path = Path(vault_path) / BACKUP_DIR / time.strftime("%Y-%m-%d_%H-%M-%S")
        backup_path.mkdir(parents=True, exist_ok=True)
        print(f"Бэкап: {backup_path}")

    # Замена
    replaced_files = 0
    replaced_count = 0
    errors = 0

    for filepath, results in matches:
        try:
            # 22.09: docx — через docx_io (замена в w:t, форматирование цело)
            if filepath.suffix.lower() == ".docx" and docx_io is not None:
                if dry_run:
                    count = docx_io.count_in_docx(filepath, old, is_regex)
                    replaced_files += 1
                    replaced_count += count
                    continue
                if not no_backup:
                    rel = filepath.relative_to(vault_path)
                    backup_file = backup_path / rel
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(filepath, backup_file)
                count, _changed, broken = docx_io.replace_in_docx(
                    filepath, old, new, is_regex, backup=False)
                replaced_files += _changed
                replaced_count += count
                continue

            content = filepath.read_text(encoding="utf-8")
            new_content, count = replace_in_text(content, old, new, is_regex)

            if dry_run:
                replaced_files += 1
                replaced_count += count
                continue

            # Бэкап файла
            if not no_backup:
                rel = filepath.relative_to(vault_path)
                backup_file = backup_path / rel
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(filepath, backup_file)

            # Запись
            filepath.write_text(new_content, encoding="utf-8")
            replaced_files += 1
            replaced_count += count

        except Exception as e:
            errors += 1
            print(f"  Ошибка: {filepath.name}: {e}")

    # Сводка
    print()
    print("=" * 50)
    if dry_run:
        print("DRY-RUN (файлы не изменены)")
    print(f"Файлов: {replaced_files}")
    print(f"Замен: {replaced_count}")
    if errors:
        print(f"Ошибок: {errors}")
    if not dry_run and not no_backup:
        print(f"Бэкап: {backup_path}")
    print("=" * 50)


# --- Поиск мусора ---------------------------------------------------------

BAD_UNICODE_RANGES = [
    # Китайские иероглифы (часто появляются при битой кодировке)
    ("\u4e00-\u9fff", "китайские иероглифы CJK"),
    ("\u3400-\u4dbf", "китайские иероглифы CJK-A"),
    # Японские катакана/хирагана
    ("\u3040-\u309f", "хирагана"),
    ("\u30a0-\u30ff", "катакана"),
    # Корейские
    ("\uac00-\ud7af", "корейские слоги"),
    # Управляющие символы (кроме \n \r \t)
    ("\u0000-\u0008", "управляющие символы 0x00-0x08"),
    ("\u000b-\u000c", "управляющие символы 0x0B-0x0C"),
    ("\u000e-\u001f", "управляющие символы 0x0E-0x1F"),
    ("\u007f-\u009f", "DEL и управляющие 0x7F-0x9F"),
    # Заменители (surrogate pairs не должны быть в тексте)
    ("\ud800-\udfff", "суррогатные символы"),
    # Примечание: приватная зона (U+E000-U+F8FF) НЕ включена --
    # ChatGPT использует её для иконок, это нормально
]


def find_bad_unicode(vault_path, subdir=None, include=None, exclude=None):
    """Ищет файлы с мусорными Unicode-символами"""
    vault = Path(vault_path)
    if not vault.exists():
        print(f"Папка не найдена: {vault_path}")
        return

    if subdir:
        search_root = vault / subdir
        if not search_root.exists():
            print(f"Подпапка не найдена: {subdir}")
            return
    else:
        search_root = vault

    # 22.09: .md/.txt/.docx
    md_files = collect_files(search_root, include, exclude)

    print(f"Сканирую {len(md_files)} файлов на мусорные символы...")
    print()

    total_bad_files = 0

    for range_spec, label in BAD_UNICODE_RANGES:
        pattern = f"[{range_spec}]"
        matches = scan_vault(vault_path, pattern, is_regex=True,
                             subdir=subdir, include=include, exclude=exclude)
        if matches:
            total = 0
            for f, _ in matches:
                if f.suffix.lower() == ".docx" and docx_io is not None:
                    total += docx_io.count_in_docx(f, pattern, True)
                else:
                    total += count_matches(f.read_text(encoding="utf-8"),
                                           pattern, True)
            print(f"  {label}: {len(matches)} файлов, {total} символов")
            for filepath, results in matches[:5]:
                rel = filepath.relative_to(vault_path)
                print(f"    {rel}")
            if len(matches) > 5:
                print(f"    ... ещё {len(matches) - 5} файлов")
            total_bad_files += len(matches)

    # Файлы с ошибками чтения (битая кодировка)
    # 22.09: docx — zip, UTF-8 проверка неприменима (ложные срабатывания)
    bad_encoding = []
    for filepath in md_files:
        if filepath.suffix.lower() == ".docx":
            continue
        try:
            filepath.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            bad_encoding.append(filepath)

    if bad_encoding:
        print(f"\n  Битая кодировка (не UTF-8): {len(bad_encoding)} файлов")
        for filepath in bad_encoding[:10]:
            rel = filepath.relative_to(vault_path)
            print(f"    {rel}")
        if len(bad_encoding) > 10:
            print(f"    ... ещё {len(bad_encoding) - 10} файлов")
        total_bad_files += len(bad_encoding)

    print()
    if total_bad_files == 0:
        print("Всё чисто! Мусорных символов не найдено.")
    else:
        print(f"Всего проблемных файлов: {total_bad_files}")


# --- Вырезание мусорных символов ------------------------------------------

def strip_bad_unicode(vault_path, subdir=None, include=None, exclude=None,
                      dry_run=False, no_backup=False, yes=False,
                      replace_with=""):
    """Находит и вырезает мусорные Unicode-символы из файлов"""
    vault = Path(vault_path)
    if not vault.exists():
        print(f"Папка не найдена: {vault_path}")
        return

    if subdir:
        search_root = vault / subdir
        if not search_root.exists():
            print(f"Подпапка не найдена: {subdir}")
            return
    else:
        search_root = vault

    # 22.09: .md/.txt/.docx
    md_files = collect_files(search_root, include, exclude)

    print(f"Сканирую {len(md_files)} файлов на мусорные символы...")
    print()

    # Строим regex из всех плохих диапазонов
    bad_pattern = ""
    for range_spec, label in BAD_UNICODE_RANGES:
        bad_pattern += range_spec
    if bad_pattern:
        bad_pattern = f"[{bad_pattern}]"
    else:
        print("Нет диапазонов для проверки.")
        return

    # Ищем файлы с мусором
    dirty_files = []
    for filepath in md_files:
        try:
            # 22.09: docx через docx_io
            if filepath.suffix.lower() == ".docx":
                if docx_io is None:
                    continue
                content = docx_io.read_text(filepath)
                if content is None:
                    continue
            else:
                content = filepath.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        matches = re.findall(bad_pattern, content)
        if matches:
            dirty_files.append((filepath, len(matches)))

    if not dirty_files:
        print("Всё чисто! Мусорных символов не найдено.")
        return

    total_chars = sum(c for _, c in dirty_files)
    print(f"Найдено: {len(dirty_files)} файлов, {total_chars} мусорных символов")
    print()

    for filepath, count in dirty_files[:20]:
        rel = filepath.relative_to(vault_path)
        print(f"  {rel} ({count} символов)")
    if len(dirty_files) > 20:
        print(f"  ... ещё {len(dirty_files) - 20} файлов")

    print()

    # Подтверждение
    if not dry_run:
        if not yes:
            answer = input(f"Вырезать мусорные символы из {len(dirty_files)} файлов? [y/N]: ").strip().lower()
            if answer not in ("y", "yes", "д", "да"):
                print("Отменено.")
                return

    # Бэкап
    if not dry_run and not no_backup:
        backup_path = Path(vault_path) / BACKUP_DIR / time.strftime("%Y-%m-%d_%H-%M-%S")
        backup_path.mkdir(parents=True, exist_ok=True)
        print(f"Бэкап: {backup_path}")

    # Вырезаем
    fixed = 0
    removed = 0
    errors = 0

    for filepath, _ in dirty_files:
        try:
            # 22.09: docx — чтение и запись через docx_io
            if filepath.suffix.lower() == ".docx":
                if docx_io is None:
                    continue
                content = docx_io.read_text(filepath)
                if content is None:
                    continue
                new_content = re.sub(bad_pattern, replace_with, content)
                removed_count = len(content) - len(new_content)
                if dry_run:
                    fixed += 1
                    removed += removed_count
                    continue
                if not no_backup:
                    rel = filepath.relative_to(vault_path)
                    backup_file = backup_path / rel
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(filepath, backup_file)
                # docx: вырезание мусора идёт по w:t построчно
                _n, _ch, _b = docx_io.replace_in_docx(
                    filepath, bad_pattern, replace_with, is_regex=True,
                    backup=False)
                fixed += _ch
                removed += removed_count if _ch else 0
                continue

            content = filepath.read_text(encoding="utf-8")
            new_content = re.sub(bad_pattern, replace_with, content)
            removed_count = len(content) - len(new_content) + len(replace_with) * (len(content) - len(new_content.replace(replace_with, "")) if replace_with else 0)

            if dry_run:
                fixed += 1
                removed += removed_count
                continue

            if not no_backup:
                rel = filepath.relative_to(vault_path)
                backup_file = backup_path / rel
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(filepath, backup_file)

            filepath.write_text(new_content, encoding="utf-8")
            fixed += 1
            removed += removed_count

        except Exception as e:
            errors += 1
            rel = filepath.relative_to(vault_path)
            print(f"  Ошибка: {rel}: {e}")

    # Сводка
    print()
    print("=" * 50)
    if dry_run:
        print("DRY-RUN (файлы не изменены)")
    print(f"Обработано: {fixed} файлов")
    print(f"Удалено символов: {removed}")
    if errors:
        print(f"Ошибок: {errors}")
    if not dry_run and not no_backup and dirty_files:
        print(f"Бэкап: {backup_path}")
    print("=" * 50)


# --- Исправление кодировки -------------------------------------------------

# Кодировки для попытки чтения (в порядке приоритета)
ENCODINGS_TO_TRY = [
    "utf-8",
    "windows-1251",   # русский Windows
    "cp1251",          # то же самое, алиас
    "koi8-r",          # русский Linux старый
    "iso-8859-5",      # русский ISO
    "mac_cyrillic",    # русский Mac
    "latin-1",         # никогда не падает (читает любой байт)
]


def detect_encoding(filepath):
    """
    Определяет кодировку файла.
    Возвращает (encoding, confidence) или (None, None).
    """
    raw = filepath.read_bytes()

    # 1. Пробуем chardet (если установлен)
    try:
        import chardet
        result = chardet.detect(raw)
        if result["confidence"] > 0.7:
            return result["encoding"], result["confidence"]
    except ImportError:
        pass

    # 2. Пробуем UTF-8 с BOM
    if raw[:3] == b"\xef\xbb\xbf":
        return "utf-8-sig", 1.0

    # 3. Пробуем читать как UTF-8
    try:
        raw.decode("utf-8")
        return "utf-8", 0.9
    except UnicodeDecodeError:
        pass

    # 4-5. koi8-r vs windows-1251 — честное сравнение (22.09, синтетика:
    # каждый в другом даёт «валидную» кириллицу, порядок не спасает).
    # Дискриминатор: частые русские БИГРАМЫ (ст, ен, о и т.п.) — настоящий
    # русский текст в правильной кодировке даёт много реальных биграм,
    # в неправильной — редкие/невозможные сочетания.
    RU_BIGRAMS = ("ст", "но", "то", "на", "ен", "ов", "ни", "ра", "во", "ко",
                  "ро", "ли", "ла", "от", "по", "ос", "ер", "да", "ы ", "ем",
                  "пр", "ы", "ом", "ть", "ай", "и ", " и", " в", "не", "что")
    RU_TRIGRAMS = ("ста", "ени", "тов", "ать", "стр", "про", " что", "что ",
                   "вне", "тся", "ась", "ый ", "кий")

    def _score(text):
        """(кириллица%, биграмы на 1000 симв., мусор%, доля_букв+пробелов%)."""
        if not text:
            return 0.0, 0.0, 1.0, 0.0
        n = len(text)
        cyr = sum(1 for c in text if "\u0400" <= c <= "\u04FF")
        junk = sum(1 for c in text if ord(c) < 32 and c not in "\n\r\t")
        alpha = sum(1 for c in text if c.isalpha() or c in " .,!?:;-'\"\n\r\t")
        low = text.lower()
        bi = sum(low.count(b) for b in RU_BIGRAMS)
        tri = sum(low.count(t) for t in RU_TRIGRAMS)
        return cyr / n, (bi + 2 * tri) * 1000 / max(n, 1), junk / n, alpha / n

    best = (None, 0.0, 0.0, 1.0)  # (имя, биграмы, кириллица, мусор)
    for enc in ("koi8-r", "windows-1251"):
        try:
            text = raw.decode(enc)
            cyr, bi, junk, alpha = _score(text)
            # 22.09: гибридные файлы (utf8+cp1251) отбраковка — в нормальном
            # тексте 85%+ букв и пробелов; гибрид даёт кучу знаков посреди слов
            if cyr > 0.30 and junk < 0.02 and bi > 20 and alpha > 0.85:
                if bi > best[1]:
                    best = (enc, bi, cyr, junk)
        except Exception:
            pass

    if best[0]:
        return best[0], 0.8
    return None, 0


def fix_encoding(vault_path, subdir=None, include=None, exclude=None,
                 dry_run=False, no_backup=False, yes=False):
    """Находит файлы с битой кодировкой и пересохраняет как UTF-8"""
    vault = Path(vault_path)
    if not vault.exists():
        print(f"Папка не найдена: {vault_path}")
        return

    if subdir:
        search_root = vault / subdir
        if not search_root.exists():
            print(f"Подпапка не найдена: {subdir}")
            return
    else:
        search_root = vault

    # 22.09: .md/.txt (docx — это zip, кодировка файла неприменима)
    md_files = collect_files(search_root, include, exclude)
    docx_skipped = sum(1 for f in md_files if f.suffix.lower() == ".docx")
    md_files = [f for f in md_files if f.suffix.lower() != ".docx"]
    if docx_skipped:
        print(f"  docx пропущены: {docx_skipped} (кодировка файла неприменима к zip)")

    print(f"Сканирую {len(md_files)} файлов на проблемы с кодировкой...")
    print()

    # 1. Файлы которые не читаются как UTF-8
    bad_files = []
    for filepath in md_files:
        try:
            filepath.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            bad_files.append(filepath)

    # 2. Файлы с мусорными Unicode-символами (прочитались как UTF-8, но криво)
    for range_spec, label in BAD_UNICODE_RANGES:
        pattern = f"[{range_spec}]"
        matches = scan_vault(vault_path, pattern, is_regex=True,
                             subdir=subdir, include=include, exclude=exclude)
        for filepath, _ in matches:
            if filepath not in bad_files:
                bad_files.append(filepath)

    if not bad_files:
        print("Всё чисто! Проблем с кодировкой не найдено.")
        return

    print(f"Проблемных файлов: {len(bad_files)}")
    print()

    # Определяем кодировку каждого
    fixable = []
    not_fixable = []

    for filepath in bad_files:
        encoding, confidence = detect_encoding(filepath)
        rel = filepath.relative_to(vault_path)
        if encoding and encoding.lower() not in ("utf-8", "utf-8-sig"):
            fixable.append((filepath, encoding, confidence))
            print(f"  {rel}")
            print(f"    кодировка: {encoding} (уверенность: {confidence:.0%})")
        elif encoding and encoding.lower() in ("utf-8", "utf-8-sig"):
            # UTF-8 но с мусором -- возможно двойная конвертация
            not_fixable.append((filepath, "UTF-8 с мусором"))
            print(f"  {rel}")
            print(f"    UTF-8 но содержит мусорные символы (нужен ручной разбор)")
        else:
            not_fixable.append((filepath, "не определена"))
            print(f"  {rel}")
            print(f"    кодировка не определена")

    print()
    print(f"Можно исправить: {len(fixable)}")
    print(f"Нужен ручной разбор: {len(not_fixable)}")

    if not fixable:
        return

    # Подтверждение
    if not dry_run:
        if not yes:
            answer = input(f"\nПересохранить {len(fixable)} файлов как UTF-8? [y/N]: ").strip().lower()
            if answer not in ("y", "yes", "д", "да"):
                print("Отменено.")
                return

    # Бэкап
    if not dry_run and not no_backup:
        backup_path = Path(vault_path) / BACKUP_DIR / time.strftime("%Y-%m-%d_%H-%M-%S")
        backup_path.mkdir(parents=True, exist_ok=True)
        print(f"Бэкап: {backup_path}")

    # Исправляем
    fixed = 0
    errors = 0

    for filepath, encoding, confidence in fixable:
        try:
            content = filepath.read_text(encoding=encoding)

            if dry_run:
                fixed += 1
                continue

            # Бэкап
            if not no_backup:
                rel = filepath.relative_to(vault_path)
                backup_file = backup_path / rel
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(filepath, backup_file)

            # Пересохраняем как UTF-8
            filepath.write_text(content, encoding="utf-8")
            fixed += 1

        except Exception as e:
            errors += 1
            rel = filepath.relative_to(vault_path)
            print(f"  Ошибка: {rel}: {e}")

    # Сводка
    print()
    print("=" * 50)
    if dry_run:
        print("DRY-RUN (файлы не изменены)")
    print(f"Исправлено: {fixed}")
    if errors:
        print(f"Ошибок: {errors}")
    if not_fixable:
        print(f"Нужен ручной разбор: {len(not_fixable)}")
    if not dry_run and not no_backup and fixable:
        print(f"Бэкап: {backup_path}")
    print("=" * 50)


# --- CLI -----------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Массовая автозамена в .md/.txt/.docx файлах (Obsidian)")
        print()
        print("Использование:")
        print("  python md_replace.py <старый_текст> <новый_текст>")
        print("  python md_replace.py --regex <паттерн> <замена>")
        print()
        print("Параметры:")
        print("  --vault <путь>       -- путь к vault (по умолчанию: Daro Coding)")
        print("  --subdir <папка>     -- искать только в подпапке")
        print("  --include <текст>    -- только файлы с таким именем (можно несколько)")
        print("  --exclude <текст>    -- исключить файлы с таким именем")
        print("  --regex              -- режим regex")
        print("  --find-bad           -- найти мусорные символы (иероглифы, битая кодировка)")
        print("  --strip-bad          -- вырезать мусорные символы из файлов")
        print("  --fix-encoding       -- найти и пересохранить файлы с битой кодировкой как UTF-8 (md/txt)")
        print("  --dry-run            -- показать что заменится, не трогать файлы")
        print("  --no-backup          -- не создавать бэкап")
        print("  --yes / -y           -- без подтверждения")
        print()
        print("Примеры:")
        print("  python md_replace.py 'Иван' 'Пётр' --dry-run")
        print("  python md_replace.py 'Иван' 'Пётр' --subdir 'Книга'")
        print("  python md_replace.py --regex '\\d{2}\\.\\d{2}\\.\\d{4}' 'ДАТА' --dry-run")
        print("  python md_replace.py --find-bad")
        print("  python md_replace.py --find-bad --subdir 'ChatGPT'")
        print("  python md_replace.py --fix-encoding --dry-run")
        print("  python md_replace.py --fix-encoding --subdir 'ChatGPT' -y")
        print("  python md_replace.py --strip-bad --dry-run")
        print("  python md_replace.py --strip-bad --subdir 'ChatGPT' -y")
        sys.exit(1)

    # Парсим аргументы
    args = sys.argv[1:]
    old_text = None
    new_text = None
    vault_path = DEFAULT_VAULT
    is_regex = False
    subdir = None
    include = []
    exclude = []
    dry_run = False
    no_backup = False
    yes = False
    find_bad = False
    fix_encoding_flag = False
    strip_bad = False

    i = 0
    positional = []
    while i < len(args):
        if args[i] == "--vault":
            i += 1
            if i < len(args):
                vault_path = args[i]
        elif args[i] == "--subdir":
            i += 1
            if i < len(args):
                subdir = args[i]
        elif args[i] == "--include":
            i += 1
            if i < len(args):
                include.append(args[i])
        elif args[i] == "--exclude":
            i += 1
            if i < len(args):
                exclude.append(args[i])
        elif args[i] == "--regex":
            is_regex = True
        elif args[i] == "--find-bad":
            find_bad = True
        elif args[i] == "--fix-encoding":
            fix_encoding_flag = True
        elif args[i] == "--strip-bad":
            strip_bad = True
        elif args[i] == "--dry-run":
            dry_run = True
        elif args[i] == "--no-backup":
            no_backup = True
        elif args[i] in ("--yes", "-y"):
            yes = True
        else:
            positional.append(args[i])
        i += 1

    if find_bad:
        find_bad_unicode(vault_path, subdir=subdir,
                         include=include or None, exclude=exclude or None)
        sys.exit(0)

    if fix_encoding_flag:
        fix_encoding(vault_path, subdir=subdir,
                     include=include or None, exclude=exclude or None,
                     dry_run=dry_run, no_backup=no_backup, yes=yes)
        sys.exit(0)

    if strip_bad:
        strip_bad_unicode(vault_path, subdir=subdir,
                         include=include or None, exclude=exclude or None,
                         dry_run=dry_run, no_backup=no_backup, yes=yes)
        sys.exit(0)

    if len(positional) < 2:
        print("Нужно указать: <старый_текст> <новый_текст>")
        sys.exit(1)

    old_text = positional[0]
    new_text = positional[1]

    replace_in_vault(
        vault_path, old_text, new_text,
        is_regex=is_regex, subdir=subdir,
        include=include or None, exclude=exclude or None,
        dry_run=dry_run, no_backup=no_backup, yes=yes
    )
