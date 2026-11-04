# -*- coding: utf-8 -*-
"""
separator_clean — чистка мусорных разделителей в .md/.txt/.docx.

  python separator_clean.py --input <папка или файл> [--fix]
      [--symbols СИМВОЛЫ] [--min-run N] [--max-blank N] [--out отчёт.md]

Убирает строки, целиком состоящие из повторяющихся символов-разделителей:
«/////», «*****», «======», «———», «* * *» и т.п. Это авторские отбойники
сцен, к самому тексту они отношения не имеют.

Строка считается разделителем, если состоит из ОДНОГО символа набора
--symbols, повторённого --min-run раз и больше; пробелы между ними
допускаются («* * *», «— — —»).

Не трогается:
  • frontmatter .md (блок --- ... --- в начале файла);
  • блоки кода ``` и ~~~ вместе с ограждениями;
  • заголовки из решёток «####» — символа «#» в наборе по умолчанию нет;
  • таблицы («|---|---|» — не одна чистая серия), списки, цитаты;
  • всё, где символ повторяется меньше --min-run раз.

Нюанс markdown: строка «===» или «---» сразу под текстом — это заголовок
(setext), одиночная «---» — горизонтальная линия. В рукописях это почти
всегда рукописный разделитель, поэтому убирается; заголовки лучше
оформлять решётками.

На месте убранного разделителя остаётся пустая строка (между абзацами —
--max-blank); если разделитель стоял вплотную к абзацам, между ними
вставляется пустая строка, текст не склеивается.

docx: убираются абзацы-разделители в теле документа; форматирование
(жирный, курсив, стили) не затрагивается. Таблицы и колонтитулы не трогаются.

По умолчанию dry-run (ничего не меняет). С --fix правит файлы, создавая
<имя>.bak рядом. .bak, .git, отчёты не трогаются.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.report import write_report
from core import text_parser as tp

SKIP_DIRS = {".git", ".obsidian", ".trash", "reports", "__pycache__",
             "md_replace_backups", ".smart-env"}  # бэкапы не чистим
EXTS = (".md", ".txt", ".docx")

# Символы-разделители по умолчанию. «#» не входит: серия решёток — это
# заголовок markdown. «~» не входит: «~~~» — ограждение кода.
DEFAULT_SYMBOLS = "*/=~-_+%&@•·—–§"


def _junk_re(symbols):
    """Регулярка строки-разделителя: один символ набора, повторённый
    с необязательными одиночными пробелами («*****», «* * *», «———»)."""
    return re.compile("^([{}])( *\\1)*$".format(re.escape(symbols)))


def _is_junk(line, junk, min_run):
    """Чистая строка-разделитель из одного повторяющегося символа?"""
    s = line.strip()
    if len(s) < min_run:
        return False
    m = junk.match(s)
    return bool(m) and s.count(m.group(1)) >= min_run


def clean_text(text, symbols=DEFAULT_SYMBOLS, min_run=3, max_blank=1,
               frontmatter=False):
    """Возвращает (новый_текст, кол-во_убранных_строк-разделителей).

    frontmatter=True защищает блок --- ... --- в начале файла (.md).
    Блоки кода не трогаются. Пустые строки в месте убранного разделителя
    схлопываются до max_blank; между абзацами, оставшимися вплотную,
    вставляется пустая строка.
    """
    if not text:
        return text, 0
    min_run = max(1, int(min_run))
    max_blank = max(0, int(max_blank))
    junk = _junk_re(symbols)
    lines = text.split("\n")

    flags = []  # True — строка-разделитель, убирается
    in_fence = False
    fence_marker = None
    # frontmatter: только строго «---» первой строкой, закрытие — тоже «---»
    in_fm = bool(frontmatter) and lines[0].strip() == "---"
    for idx, line in enumerate(lines):
        s = line.strip()
        if in_fm:
            flags.append(False)
            # закрывает не первая строка, а последующий «---»
            if idx > 0 and s == "---":
                in_fm = False
            continue
        if s.startswith(("```", "~~~")):
            # вход/выход из блока кода — строка не трогается
            if not in_fence:
                in_fence, fence_marker = True, s[:3]
            elif s.startswith(fence_marker):
                in_fence, fence_marker = False, None
            flags.append(False)
            continue
        if in_fence:
            flags.append(False)
            continue
        flags.append(_is_junk(line, junk, min_run))

    out = []
    removed = 0
    i, n = 0, len(lines)
    while i < n:
        if not flags[i]:
            out.append(lines[i])
            i += 1
            continue
        j = i
        while j < n and flags[j]:
            j += 1
        removed += j - i
        # пустые строки перед разделителем (уже добавлены в out)
        tb = 0
        while tb < len(out) and out[-1 - tb] == "":
            tb += 1
        # пустые строки сразу после блока разделителей
        k = j
        while k < n and lines[k] == "":
            k += 1
        has_after = k < n and lines[k].strip() != ""
        # абзацы по обе стороны вплотную — вставляем пустую строку,
        # чтобы текст не склеился; иначе схлопываем стык до max_blank
        if tb < len(out) and has_after:
            keep = max_blank
        else:
            keep = min(max_blank, tb + (k - j))
        del out[len(out) - tb:]
        out.extend([""] * keep)
        i = k  # пустые строки после блока уже учтены

    if not removed:
        return text, 0
    while out and out[-1] == "":
        out.pop()
    if not out:
        return "", removed
    if text.endswith("\n"):
        out.append("")
    return "\n".join(out), removed


def collect(root):
    root = Path(root)
    if root.is_file():
        return [root] if root.suffix.lower() in EXTS else []
    files = []
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in EXTS:
            continue
        if set(f.parts) & SKIP_DIRS or f.name.endswith(".bak"):
            continue
        files.append(f)
    return files


def clean_docx(path, symbols, min_run, fix):
    """docx: убираем абзацы-разделители в теле документа.
    Форматирование сохраняется; таблицы и колонтитулы не трогаются."""
    try:
        from docx import Document
        doc = Document(path)
    except Exception as e:
        print(f"ПРОПУСК (docx не читается): {Path(path).name}: {e}")
        return 0
    junk = _junk_re(symbols)
    doomed = []
    for p in doc.paragraphs:
        if _is_junk(p.text, junk, min_run):
            doomed.append(p._p)
    if not doomed:
        return 0
    if fix:
        tp.backup_once(path)
        try:
            for el in doomed:
                el.getparent().remove(el)
            doc.save(path)
        except Exception as e:
            print(f"ПРОПУСК (не сохраняется, файл занят?): "
                  f"{Path(path).name}: {e}")
            return 0
    return len(doomed)


def run(input_path, symbols="", min_run=3, max_blank=1, fix=False, out=None):
    symbols = symbols or DEFAULT_SYMBOLS
    files = collect(input_path)
    if not files:
        print("Файлы .md/.txt/.docx не найдены.")
        return 1
    total_files = total_changes = 0
    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)
    for idx, f in enumerate(files, 1):
        if tp.stop_requested():  # мягкая остановка
            print("Остановлено пользователем.")
            break
        try:
            if f.suffix.lower() == ".docx":
                n = clean_docx(f, symbols, min_run, fix)
            else:
                raw = f.read_bytes()
                text = raw.decode("utf-8")
                crlf = "\r\n" in text
                new_text, n = clean_text(
                    text.replace("\r\n", "\n"), symbols, min_run, max_blank,
                    frontmatter=(f.suffix.lower() == ".md"))
                if n and fix:
                    tp.backup_once(f)
                    if crlf:
                        new_text = new_text.replace("\n", "\r\n")
                    with open(f, "w", encoding="utf-8", newline="") as fh:
                        fh.write(new_text)
        except (UnicodeDecodeError, PermissionError, OSError) as e:
            print(f"ПРОПУСК {f.name}: {e}")
            print(f"PROGRESS:{idx}/{total}", flush=True)
            continue
        print(f"PROGRESS:{idx}/{total}", flush=True)
        if n:
            total_files += 1
            total_changes += n
            print(f"{'[FIX] ' if fix else ''}{f}: разделителей {n}")
    print(f"\nИтого: файлов с разделителями {total_files}, "
          f"убрано строк {total_changes}")
    if not fix and total_changes:
        print("Режим dry-run — файлы НЕ изменены. Для правки: --fix")
    if out:
        write_report(out, f"# Separator clean\nФайлов: {total_files}, "
                          f"убрано строк-разделителей: {total_changes}\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Чистка мусорных разделителей (///// ***** ====== ———)")
    ap.add_argument("--input", required=True,
                    help="папка или файл .md/.txt/.docx")
    ap.add_argument("--fix", action="store_true",
                    help="реально править (с .bak)")
    ap.add_argument("--symbols", default="",
                    help="символы-разделители (по умолчанию «{}»)".format(
                        DEFAULT_SYMBOLS))
    ap.add_argument("--min-run", type=int, default=3,
                    help="минимальная серия символов (по умолчанию 3)")
    ap.add_argument("--max-blank", type=int, default=1,
                    help="пустых строк на месте разделителя (по умолчанию 1)")
    ap.add_argument("--out", help="файл отчёта")
    args = ap.parse_args(argv)
    if args.min_run < 1:
        ap.error("--min-run должен быть 1 и больше")
    if args.max_blank < 0:
        ap.error("--max-blank не может быть отрицательным")
    return run(args.input, symbols=args.symbols, min_run=args.min_run,
               max_blank=args.max_blank, fix=args.fix, out=args.out)


if __name__ == "__main__":
    sys.exit(main())
