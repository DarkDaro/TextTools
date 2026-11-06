"""
Поиск персонажей по заметкам Obsidian (.md/.txt/.docx — 22.09)
Читает реестр из characters.yaml, сканирует vault, показывает:
  - текущие имена (ОК)
  - старые имена (надо заменить!)
  - опечатки (надо исправить!)

Использование:
  python char_search.py                     -- проверить всех персонажей
  python char_search.py Эрика               -- проверить конкретного
  python char_search.py --vault <путь>      -- другое хранилище
  python char_search.py --fix               -- заменить старые имена на текущие
"""

import re
import sys
import time
import shutil
from pathlib import Path

# 22.09: docx-поддержка через общий модуль textools
_SCRIPT_DIR = Path(__file__).resolve().parent
for _cand in (_SCRIPT_DIR.parent / "textools",):
    if str(_cand) not in sys.path and _cand.is_dir():
        sys.path.insert(0, str(_cand))
try:
    from core import docx_io
except ImportError:
    docx_io = None

TEXT_EXTS = (".md", ".txt", ".docx")

try:
    import yaml
except ImportError:
    print("Нужна библиотека pyyaml: pip install pyyaml")
    sys.exit(1)


# --- Настройки -----------------------------------------------------------

DEFAULT_VAULT = r"C:\Users\Dario\Documents\DaroObsidian\Daro Coding"
CHARACTERS_FILE = Path(__file__).parent / "characters.yaml"
BACKUP_DIR = "md_replace_backups"


# --- Поиск ---------------------------------------------------------------

def scan_vault(vault_path, search_terms, subdir=None):
    """Ищет список терминов в vault, возвращает {термин: [(файл, строка, номер)]}"""
    vault = Path(vault_path)
    if not vault.exists():
        print(f"Папка не найдена: {vault_path}")
        return {}

    search_root = vault / subdir if subdir else vault
    if subdir and not search_root.exists():
        print(f"Подпапка не найдена: {subdir}")
        return {}

    # 22.09: .md/.txt/.docx
    files = []
    for ext in TEXT_EXTS:
        files.extend(search_root.rglob("*" + ext))
    files = [f for f in sorted(files) if ".obsidian" not in f.parts
             and BACKUP_DIR not in f.parts and not f.name.endswith(".bak")]

    results = {term: [] for term in search_terms}

    for filepath in files:
        # 22.09: docx через docx_io
        if filepath.suffix.lower() == ".docx":
            if docx_io is None:
                continue
            text = docx_io.read_text(filepath)
            if text is None:
                continue
        else:
            try:
                text = filepath.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            for term in search_terms:
                if term in line:
                    results[term].append((filepath, line.strip(), i))

    return results


def search_character(vault_path, char, subdir=None):
    """Ищет одного персонажа по всем категориям"""
    name = char["имя"]
    forms = char.get("формы", [])
    old = char.get("старое", [])
    old_danger = char.get("старое_опасное", [])
    typos = char.get("опечатки", [])

    # Собираем все поисковые термины
    all_terms = list(set(forms + old + old_danger + typos))
    if not all_terms:
        return

    results = scan_vault(vault_path, all_terms, subdir)

    # Считаем
    current_count = sum(len(results.get(f, [])) for f in forms)
    old_count = sum(len(results.get(f, [])) for f in old)
    danger_count = sum(len(results.get(f, [])) for f in old_danger)
    typo_count = sum(len(results.get(t, [])) for t in typos)

    # Вывод
    has_problems = old_count > 0 or danger_count > 0 or typo_count > 0
    status = "ПРОБЛЕМЫ" if has_problems else "OK"
    print(f"\n{'=' * 50}")
    print(f"  {name}  [{status}]")
    print(f"{'=' * 50}")

    # Текущие формы
    if current_count > 0:
        print(f"\n  Текущее имя: {current_count} упоминаний")
        for f in forms:
            hits = results.get(f, [])
            if hits:
                print(f"    {f}: {len(hits)}")

    # Старые имена (безопасные)
    if old_count > 0:
        print(f"\n  СТАРОЕ ИМЯ: {old_count} упоминаний (надо заменить!)")
        for f in old:
            hits = results.get(f, [])
            if hits:
                print(f"    {f}: {len(hits)}")
                for filepath, line, num in hits[:5]:
                    rel = filepath.relative_to(vault_path)
                    safe = line.encode("cp1251", errors="replace").decode("cp1251")
                    if len(safe) > 80:
                        safe = safe[:80] + "..."
                    print(f"      {rel}:L{num}: {safe}")
                if len(hits) > 5:
                    print(f"      ... ещё {len(hits) - 5}")

    # Опасные формы (совпадают с другими персонажами)
    if danger_count > 0:
        print(f"\n  ОПАСНЫЕ ФОРМЫ: {danger_count} упоминаний (проверить вручную!)")
        for f in old_danger:
            hits = results.get(f, [])
            if hits:
                print(f"    {f}: {len(hits)} -- может быть от другого персонажа")
                for filepath, line, num in hits[:10]:
                    rel = filepath.relative_to(vault_path)
                    safe = line.encode("cp1251", errors="replace").decode("cp1251")
                    if len(safe) > 80:
                        safe = safe[:80] + "..."
                    print(f"      {rel}:L{num}: {safe}")
                if len(hits) > 10:
                    print(f"      ... ещё {len(hits) - 10}")

    # Опечатки
    if typo_count > 0:
        print(f"\n  ОПЕЧАТКИ: {typo_count} упоминаний (надо исправить!)")
        for t in typos:
            hits = results.get(t, [])
            if hits:
                print(f"    {t}: {len(hits)}")
                for filepath, line, num in hits[:5]:
                    rel = filepath.relative_to(vault_path)
                    safe = line.encode("cp1251", errors="replace").decode("cp1251")
                    if len(safe) > 80:
                        safe = safe[:80] + "..."
                    print(f"      {rel}:L{num}: {safe}")
                if len(hits) > 5:
                    print(f"      ... ещё {len(hits) - 5}")

    if current_count == 0 and old_count == 0 and danger_count == 0 and typo_count == 0:
        print("  Не найден в хранилище.")

    return {"current": current_count, "old": old_count, "danger": danger_count,
            "typos": typo_count,
            "old_results": {f: results.get(f, []) for f in old},
            "danger_results": {f: results.get(f, []) for f in old_danger},
            "typo_results": {t: results.get(t, []) for t in typos}}


def fix_word(vault_path, bad, good, subdir=None, dry_run=False,
             no_backup=False, yes=False):
    """22.09: точечная замена одного слова (опечатка/старое имя) без реестра.
    Ничего лишнего не трогает — только данное слово на данную замену."""
    vault = Path(vault_path)
    if not vault.exists():
        print(f"Папка не найдена: {vault_path}")
        return
    results = scan_vault(vault_path, [bad], subdir)
    hits = results.get(bad, [])
    if not hits:
        print(f"  «{bad}» не найдено — замен не нужно.")
        return
    files = sorted({str(f) for f, _, _ in hits})
    n_hits = len(hits)
    print(f"  «{bad}» -> «{good}»: {len(hits)} вхождений в {len(files)} файлах")
    for f in files:
        print(f"    {f}")
    if dry_run:
        print("  DRY-RUN — ничего не изменено.")
        return
    if not yes:
        answer = input("  Заменить? [y/N]: ").strip().lower()
        if answer not in ("y", "yes", "д", "да"):
            print("  Отменено.")
            return
    backup_path = None
    if not no_backup:
        backup_path = vault / BACKUP_DIR / time.strftime("%Y-%m-%d_%H-%M-%S")
        backup_path.mkdir(parents=True, exist_ok=True)
        print(f"  Бэкап: {backup_path}")
    fixed = 0
    for fp in [Path(f) for f in files]:
        try:
            if fp.suffix.lower() == ".docx":
                if docx_io is None:
                    continue
                if not no_backup:
                    rel = fp.relative_to(vault)
                    bf = backup_path / rel
                    bf.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(fp, bf)
                docx_io.replace_in_docx(fp, bad, good, is_regex=False,
                                        backup=False)
                fixed += 1
                continue
            if not no_backup:
                rel = fp.relative_to(vault)
                bf = backup_path / rel
                bf.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(fp, bf)
            content = fp.read_text(encoding="utf-8")
            fp.write_text(content.replace(bad, good), encoding="utf-8")
            fixed += 1
        except Exception as e:
            print(f"  Ошибка: {fp.name}: {e}")
    print(f"  Заменено файлов: {fixed}")


def fix_character(vault_path, char, subdir=None, dry_run=False,
                  no_backup=False, yes=False):
    """Заменяет старые имена и опечатки на текущие"""
    name = char["имя"]
    forms = char.get("формы", [])
    old = char.get("старое", [])
    typos = char.get("опечатки", [])

    if not old and not typos:
        print(f"  {name}: нечего исправлять")
        return

    # Сначала ищем что менять
    search_data = search_character(vault_path, char, subdir)
    if not search_data:
        return

    if search_data["old"] == 0 and search_data["typos"] == 0:
        return

    # Определяем замену: старое -> текущее (им. падеж), опечатка -> правильное
    replacements = []
    for old_form in old:
        if search_data["old_results"].get(old_form):
            # Заменяем старую форму на форму текущего имени с тем же падежом
            # Простой подход: заменяем на имя в им. падеже
            # TODO: можно добавить маппинг падежей
            replacements.append((old_form, name))
    for typo in typos:
        if search_data["typo_results"].get(typo):
            # Заменяем опечатку на правильное написание
            # Ищем правильную форму (ближайшую по длине)
            correct = forms[0] if forms else name
            for f in forms:
                if len(f) == len(typo):
                    correct = f
                    break
            replacements.append((typo, correct))

    total = 0
    for old_form, new_form in replacements:
        all_terms = [old_form]
        results = scan_vault(vault_path, all_terms, subdir)
        total += len(results.get(old_form, []))

    if total == 0:
        return

    print(f"\n  Замена для {name}:")
    for old_form, new_form in replacements:
        print(f"    {old_form} -> {new_form}")

    # Подтверждение
    if not dry_run:
        if not yes:
            answer = input(f"  Заменить? [y/N]: ").strip().lower()
            if answer not in ("y", "yes", "д", "да"):
                print("  Отменено.")
                return

    # Бэкап
    if not dry_run and not no_backup:
        backup_path = Path(vault_path) / BACKUP_DIR / time.strftime("%Y-%m-%d_%H-%M-%S")
        backup_path.mkdir(parents=True, exist_ok=True)
        print(f"  Бэкап: {backup_path}")

    # Замена
    fixed = 0
    for old_form, new_form in replacements:
        all_terms = [old_form]
        results = scan_vault(vault_path, all_terms, subdir)
        hits = results.get(old_form, [])
        for filepath, _, _ in hits:
            try:
                # 22.09: docx — замена через docx_io (форматирование цело)
                if filepath.suffix.lower() == ".docx":
                    if docx_io is None:
                        continue
                    if dry_run:
                        fixed += 1
                        continue
                    if not no_backup:
                        rel = filepath.relative_to(vault_path)
                        backup_file = backup_path / rel
                        backup_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(filepath, backup_file)
                    docx_io.replace_in_docx(filepath, old_form, new_form,
                                            is_regex=False, backup=False)
                    fixed += 1
                    continue

                content = filepath.read_text(encoding="utf-8")
                if dry_run:
                    fixed += 1
                    continue
                if not no_backup:
                    rel = filepath.relative_to(vault_path)
                    backup_file = backup_path / rel
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(filepath, backup_file)
                new_content = content.replace(old_form, new_form)
                filepath.write_text(new_content, encoding="utf-8")
                fixed += 1
            except Exception as e:
                print(f"  Ошибка: {filepath.name}: {e}")

    print(f"\n  Заменено: {fixed}")
    if not dry_run and not no_backup and fixed > 0:
        print(f"  Бэкап: {backup_path}")


# --- CLI -----------------------------------------------------------------

if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv or len(sys.argv) < 2:
        # 22.09: нормальный --help (раньше флаг проглатывался и запускался
        # полный скан дефолтного хранилища)
        print("Поиск персонажей по заметкам Obsidian")
        print()
        print("Использование:")
        print("  python char_search.py                          -- проверить всех")
        print("  python char_search.py Эрика                    -- проверить конкретного")
        print("  python char_search.py --fix Эрика              -- заменить старые имена")
        print("  python char_search.py --fix --dry-run          -- показать что заменится")
        print("  python char_search.py --fix-word <плохо> <верно>")
        print("                                       -- точечная замена одного слова")
        print("                                          (опечатка/старое имя), без реестра")
        print("  python char_search.py --vault <путь>           -- другое хранилище")
        print("  python char_search.py --all-vaults             -- все хранилища")
        print("Опции: --subdir <путь> | --dry-run | --no-backup | --yes (-y)")
        print()
        print("Реестр персонажей: characters.yaml")
        sys.exit(0)

    # Парсим аргументы
    args = sys.argv[1:]
    vault_path = DEFAULT_VAULT
    subdir = None
    char_name = None
    fix = False
    dry_run = False
    no_backup = False
    yes = False
    all_vaults = False
    fix_word_args = None  # 22.09: (bad, good)

    # 22.09: --fix-word <плохо> <верно> — пер-словный фикс, парсим отдельно
    if "--fix-word" in args:
        j = args.index("--fix-word")
        try:
            rest = [a for a in args[j + 1:] if not a.startswith("--")]
            if len(rest) < 2:
                print("--fix-word требует два аргумента: <плохо> <верно>")
                sys.exit(1)
            fix_word_args = (rest[0], rest[1])
        except IndexError:
            print("--fix-word требует два аргумента: <плохо> <верно>")
            sys.exit(1)
        # убираем из общего парсера
        del args[j:j + 3]

    i = 0
    while i < len(args):
        if args[i] == "--vault":
            i += 1
            if i < len(args):
                vault_path = args[i]
        elif args[i] == "--subdir":
            i += 1
            if i < len(args):
                subdir = args[i]
        elif args[i] == "--fix":
            fix = True
        elif args[i] == "--dry-run":
            dry_run = True
        elif args[i] == "--no-backup":
            no_backup = True
        elif args[i] in ("--yes", "-y"):
            yes = True
        elif args[i] == "--all-vaults":
            all_vaults = True
        elif not args[i].startswith("--"):
            char_name = args[i]
        i += 1

    # 22.09: --fix-word — точечный фикс без реестра (реестр не нужен)
    if fix_word_args:
        bad, good = fix_word_args
        # 22.09: --all-vaults работает и для fix-word
        vaults = [vault_path]
        if all_vaults:
            vaults = [
                r"C:\Users\Dario\Documents\DaroObsidian\Daro Coding",
                r"C:\Users\Dario\Documents\DaroObsidian\Chatcd",
                r"C:\Users\Dario\Documents\DaroObsidian\ChatGPT_ChatsDaro",
            ]
        for vault in vaults:
            vault_name = Path(vault).name
            print(f"\n  [{vault_name}]")
            fix_word(vault, bad, good, subdir=subdir, dry_run=dry_run,
                     no_backup=no_backup, yes=yes)
        sys.exit(0)

    # Загружаем реестр
    if not CHARACTERS_FILE.exists():
        print(f"Реестр не найден: {CHARACTERS_FILE}")
        print("Создайте characters.yaml рядом со скриптом.")
        sys.exit(1)

    with open(CHARACTERS_FILE, "r", encoding="utf-8") as f:
        characters = yaml.safe_load(f)

    if not characters:
        print("Реестр пуст.")
        sys.exit(1)

    # Фильтруем по имени
    if char_name:
        characters = [c for c in characters if char_name in c["имя"]]
        if not characters:
            print(f"Персонаж '{char_name}' не найден в реестре.")
            sys.exit(1)

    # Хранилища
    vaults = [vault_path]
    if all_vaults:
        vaults = [
            r"C:\Users\Dario\Documents\DaroObsidian\Daro Coding",
            r"C:\Users\Dario\Documents\DaroObsidian\Chatcd",
            r"C:\Users\Dario\Documents\DaroObsidian\ChatGPT_ChatsDaro",
        ]

    # Запуск
    for vault in vaults:
        vault_name = Path(vault).name
        print(f"\n{'#' * 50}")
        print(f"  Хранилище: {vault_name}")
        print(f"{'#' * 50}")

        for char in characters:
            if fix:
                fix_character(vault, char, subdir=subdir,
                              dry_run=dry_run, no_backup=no_backup, yes=yes)
            else:
                search_character(vault, char, subdir=subdir)

    # Сводка
    if not fix:
        print(f"\n{'#' * 50}")
        print("  Сводка")
        print(f"{'#' * 50}")
        for char in characters:
            name = char["имя"]
            old = char.get("старое", [])
            typos = char.get("опечатки", [])
            if old or typos:
                print(f"  {name}: есть старые имена или опечатки для проверки")
            else:
                print(f"  {name}: OK")
