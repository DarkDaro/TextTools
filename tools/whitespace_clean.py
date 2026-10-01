# -*- coding: utf-8 -*-
"""
whitespace_clean — умная чистка пробелов и пустых строк в .md/.txt/.docx.

  python whitespace_clean.py --input <папка или файл> [--fix]
      [--max-blank N] [--keep-breaks] [--out report.md]

Что делает (вне блоков кода ```):
  1. Убирает пробелы/табы в конце каждой строки.
  2. Сжимает серии пустых строк до --max-blank (по умолчанию 1).
  3. Убирает пустые строки в начале файла, в конце оставляет один \n.

docx: правится только текст параграфов (w:t) — тело, таблицы, сноски,
колонтитулы. Форматирование (жирный, курсив, стили) не трогается.

По умолчанию dry-run (ничего не меняет). С --fix — правит файлы,
создавая <имя>.bak рядом. .bak, .git, отчёты не трогаются.
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import text_parser as tp

SKIP_DIRS = {".git", ".obsidian", ".trash", "reports", "__pycache__"}
EXTS = (".md", ".txt", ".docx")
FENCE_RE = ("```", "~~~")


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


def clean_text(text, max_blank=1, keep_breaks=False):
    """Возвращает (новый_текст, кол-во_правок). Блоки кода не трогаем."""
    # 18.09: подсчёт честный — правка = убранные хвостовые пробелы +
    # РАЗНИЦА пустых строк до/после (без артефактов split)
    if not text:
        return text, 0
    lines = text.split("\n")
    out = []
    ws_changes = 0
    in_fence = False
    fence_marker = None
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(FENCE_RE):
            # вход/выход из блока кода — строку не правим
            if not in_fence:
                in_fence, fence_marker = True, stripped[:3]
            elif stripped.startswith(fence_marker):
                in_fence, fence_marker = False, None
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        # 1. пробелы в конце строки
        r = line.rstrip()
        if keep_breaks and line.endswith("  ") and r:
            r = r + "  "  # markdown-перенос из двух пробелов — сохраняем
        if r != line:
            ws_changes += 1
        # 22.09: табы → пробел, двойные пробелы внутри схлопнуть
        # 01.10: с keep_breaks хвостовой markdown-перенос "  " сохраняется
        # (раньше схлопывание уничтожало его)
        if "\t" in r or "  " in r:
            fixed = r.replace("\t", " ")
            if keep_breaks and fixed.endswith("  ") and fixed.rstrip():
                body = fixed[:-2]
                while "  " in body:
                    body = body.replace("  ", " ")
                fixed = body + "  "
            else:
                while "  " in fixed:
                    fixed = fixed.replace("  ", " ")
            if fixed != r:
                ws_changes += 1
            out.append(fixed)
        else:
            out.append(r)
    # 2-3. пустые строки: сжатие серий до max_blank, чистка начала и конца
    # 18.09: подсчёт правок — только реально убранные пустые строки.
    # Финальный \n файла — норма, в подсчёт не входит.
    before_blanks = out.count("")
    if text.endswith("\n") and out and out[-1] == "":
        before_blanks -= 1  # хвостовой артефакт split — не пустая строка
    result = []
    blank_run = 0
    for line in out:
        if line == "":
            blank_run += 1
            if blank_run > max_blank:  # 18.09: оставляем ровно max_blank пустых
                continue
        else:
            blank_run = 0
        result.append(line)
    while result and result[0] == "":
        result.pop(0)
    # хвостовой артефакт split от завершающего \n убираем бесплатно
    if text.endswith("\n") and result and result[-1] == "":
        result.pop()
    while result and result[-1] == "":
        result.pop()
    after_blanks = result.count("")
    if result:
        result.append("")  # один \n в конце файла (не в подсчёт)
    blank_changes = before_blanks - after_blanks
    return "\n".join(result), ws_changes + blank_changes


def run(input_path, max_blank=1, keep_breaks=False, fix=False, out=None):
    files = collect(input_path)
    if not files:
        print("Файлы .md/.txt/.docx не найдены.")
        return 1
    total_files = total_changes = 0
    total = len(files)
    print(f"PROGRESS:0/{total}", flush=True)
    for idx, f in enumerate(files, 1):
        if tp.stop_requested():  # 01.10: мягкая остановка
            print("Остановлено пользователем.")
            break
        try:
            if f.suffix.lower() == ".docx":
                n = clean_docx(f, max_blank, keep_breaks, fix)
            else:
                text = f.read_text(encoding="utf-8")
                new_text, n = clean_text(text, max_blank, keep_breaks)
                if n and fix:
                    shutil.copy2(f, str(f) + ".bak")
                    f.write_text(new_text, encoding="utf-8")
        except (UnicodeDecodeError, PermissionError, OSError) as e:
            print(f"ПРОПУСК {f.name}: {e}")
            print(f"PROGRESS:{idx}/{total}", flush=True)
            continue
        print(f"PROGRESS:{idx}/{total}", flush=True)
        if n:
            total_files += 1
            total_changes += n
            print(f"{'[FIX] ' if fix else ''}{f}: правок {n}")
    print(f"\nИтого: файлов с проблемами {total_files}, правок {total_changes}")
    if not fix and total_changes:
        print("Режим dry-run — файлы НЕ изменены. Для правки: --fix")
    if out:
        Path(out).write_text(
            f"# Whitespace clean\nФайлов: {total_files}, правок: {total_changes}\n",
            encoding="utf-8")
    return 0


# --- docx (18.09) ---

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
# части документа с текстом (тело, сноски, колонтитулы, комментарии, текстбоксы)
DOC_PART_KEYWORDS = (
    "document.xml", "header", "footer", "footnotes", "endnotes", "comments")


def clean_docx(path, max_blank, keep_breaks, fix):
    """Чистка docx: только текст w:t. Форматирование полностью сохраняется.
    Пустые строки в docx — это пустые параграфы, сжимаем их серии."""
    from docx import Document

    doc = Document(path)
    total = 0
    for part in doc.part.package.iter_parts():
        name = str(part.partname)
        if "/word/" not in name or not any(k in name for k in DOC_PART_KEYWORDS):
            continue
        el = getattr(part, "_element", None)
        if el is None:
            continue
        # 1) хвостовые пробелы внутри каждого w:t
        for t_el in el.iter(W_NS + "t"):
            txt = t_el.text
            if not txt:
                continue
            r = txt.rstrip()
            if keep_breaks and txt.endswith("  ") and r:
                r = r + "  "  # markdown-перенос не актуален в docx, но не мешает
            # 22.09: табы → пробел и схлопывание двойных пробелов внутри w:t
            if "\t" in r or "  " in r:
                fixed = r.replace("\t", " ")
                while "  " in fixed:
                    fixed = fixed.replace("  ", " ")
                if fixed != r:
                    r = fixed
                    total += 1
            if r != txt:
                t_el.text = r
                if r != r.strip():
                    # краевые пробелы без xml:space Word съест
                    t_el.set(
                        "{http://www.w3.org/XML/1998/namespace}space", "preserve")
                total += 1
        # 2) пустые параграфы: серии сжимаем до max_blank
        total += _compress_blank_paras(el, max_blank)
        # 3) хвостовые таб-элементы в конце параграфов
        total += _strip_trailing_tabs(el)
    if total and fix:
        shutil.copy2(path, str(path) + ".bak")
        doc.save(path)
    return total


def _compress_blank_paras(el, max_blank):
    """Сжатие серий пустых параграфов в одной части документа.
    Пустой параграф = все w:t пустые/отсутствуют. Возвращает кол-во удалённых."""
    body = el.find(W_NS + "body") if el.tag.endswith("}document") else None
    container = body if body is not None else el
    paras = [c for c in container.iter() if c.tag == W_NS + "p"]
    if not paras:
        return 0

    def is_blank(p):
        texts = [t.text or "" for t in p.iter(W_NS + "t")]
        return not any(s.strip() for s in texts)

    removed = 0
    run_len = 0
    to_remove = []
    for p in paras:
        if is_blank(p):
            run_len += 1
            if run_len > max_blank:
                to_remove.append(p)
        else:
            run_len = 0
    for p in to_remove:
        parent = p.getparent()
        if parent is not None:
            parent.remove(p)
            removed += 1
    return removed


def _strip_trailing_tabs(el):
    """18.09: хвостовые пустые run'ы с одним w:tab в конце параграфа — мусор
    (в docx таб это элемент <w:tab/>, не текст). Удаляем такие run'ы."""
    n = 0
    body = el.find(W_NS + "body") if el.tag.endswith("}document") else None
    container = body if body is not None else el
    for p in container.iter(W_NS + "p"):
        runs = [r for r in p if r.tag == W_NS + "r"]
        for r in reversed(runs):
            children = [c.tag for c in r]
            # run состоит ТОЛЬКО из таба (без текста) — хвостовой мусор
            if children == [W_NS + "tab"]:
                # таб значим, только если после него есть текст в параграфе
                has_text_after = any(
                    c.tag == W_NS + "r" and c is not r and
                    any((t.text or "").strip() for t in c.iter(W_NS + "t"))
                    for c in list(p)[list(p).index(r) + 1:])
                if not has_text_after:
                    p.remove(r)
                    n += 1
            else:
                break  # наткнулись на содержательный run — стоп
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description="Умная чистка пробелов и пустых строк")
    ap.add_argument("--input", required=True, help="папка или файл .md/.txt/.docx")
    ap.add_argument("--fix", action="store_true", help="реально править (с .bak)")
    ap.add_argument("--max-blank", type=int, default=1,
                    help="максимум пустых строк между абзацами (по умолчанию 1)")
    ap.add_argument("--keep-breaks", action="store_true",
                    help="сохранять два пробела в конце строки (markdown-перенос)")
    ap.add_argument("--out", help="файл отчёта")
    args = ap.parse_args(argv)
    return run(args.input, max_blank=args.max_blank,
               keep_breaks=args.keep_breaks, fix=args.fix, out=args.out)


if __name__ == "__main__":
    sys.exit(main())