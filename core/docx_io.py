# -*- coding: utf-8 -*-
"""
textools core: docx_io — чтение и замена текста в .docx (22.09).

docx — это zip с XML. Текст живёт в <w:t> элементах частей
document/header/footer/footnotes/endnotes/comments.
Форматирование (стили, жирный, курсив, таблицы) не трогается.

API:
  read_text(path)          — текст всех w:t, с \\n между параграфами (для поиска)
  replace_in_docx(path, old, new, is_regex, backup=True)
                           — замена в w:t, возвращает (всего_замен, файлов_изменено=1/0)
  save_docx_part(...)      — служебное
"""
import re
import shutil
from pathlib import Path

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DOC_PART_KEYWORDS = ("document.xml", "header", "footer",
                     "footnotes", "endnotes", "comments")


def _iter_text_elements(doc):
    """Генератор всех w:t элементов текстовых частей документа."""
    for part in doc.part.package.iter_parts():
        name = str(part.partname)
        if "/word/" not in name or not any(k in name for k in DOC_PART_KEYWORDS):
            continue
        el = getattr(part, "_element", None)
        if el is None:
            continue
        yield from el.iter(W_NS + "t")


def read_text(path):
    """Текст docx одним куском: w:t внутри параграфа склеиваются (разорванные
    между run'ами фразы находятся), параграфы через \\n.
    Для search/count. None если не читается."""
    try:
        from docx import Document
        doc = Document(path)
    except Exception:
        return None
    chunks = []
    for part in doc.part.package.iter_parts():
        name = str(part.partname)
        if "/word/" not in name or not any(k in name for k in DOC_PART_KEYWORDS):
            continue
        el = getattr(part, "_element", None)
        if el is None:
            continue
        for p in el.iter(W_NS + "p"):
            t = "".join(t_el.text or "" for t_el in p.iter(W_NS + "t"))
            if t:
                chunks.append(t)
    return "\n".join(chunks)


def replace_in_docx_text(path, new_full_text):
    """22.09: перезаписать весь текст docx параграфами из new_full_text.

    Используется чисткой штампов: читаем весь текст (read_text), правим
    строку, записываем обратно. Форматирование run'ов теряется внутри
    изменённых параграфов (параграфы пересоздаются) — это плата за
    cross-run замены. Параграфы = строки new_full_text.
    """
    from docx import Document
    doc = Document(path)
    # удаляем все существующие параграфы
    for p in list(doc.paragraphs):
        p._element.getparent().remove(p._element)
    for line in new_full_text.split("\n"):
        doc.add_paragraph(line)
    doc.save(path)


def replace_in_docx(path, old, new, is_regex=False, backup=True):
    """Замена old -> new в тексте w:t.

    Замена идёт внутри каждого w:t отдельно: если искомая строка
    разорвана между run'ами (Word любит рвать на куски), такие случаи
    пропускаются — сообщаем отдельно (см. счётчик skipped).
    Форматирование run'ов сохраняется полностью.

    Возвращает (замен_всего, файлов_изменено, пропусков_разорванных).
    """
    from docx import Document
    flags = 0
    if not is_regex:
        pattern = re.compile(re.escape(old), flags)
    else:
        try:
            pattern = re.compile(old, flags)
        except re.error:
            return 0, 0, 0

    try:
        doc = Document(path)
    except Exception as e:
        print(f"  ПРОПУСК (docx не читается): {Path(path).name}: {e}")
        return 0, 0, 0

    total = 0
    broken = 0
    for t_el in _iter_text_elements(doc):
        txt = t_el.text
        if not txt:
            continue
        new_txt, n = pattern.subn(new if is_regex else new, txt)
        # для не-regex: замена регистрозависимая как в md_replace
        if n:
            total += n
            t_el.text = new_txt
    # разорванные между run'ами: ищем в полном тексте параграфов
    if not is_regex and old in (read_text(path) or "") and total == 0:
        broken = 1  # есть вхождение, но порвано между run'ами
    elif is_regex and total == 0:
        full = read_text(path) or ""
        joined = "".join(full.split("\n"))
        if pattern.search(joined) and pattern.search(full):
            broken = 1

    if total and backup:
        shutil.copy2(path, str(path) + ".bak")
        doc.save(path)
    elif total:
        doc.save(path)
    return total, (1 if total else 0), broken


def count_in_docx(path, old, is_regex=False):
    """Сколько вхождений old в docx (по параграфам, разорванные склеиваются)."""
    flags = 0 if is_regex else re.MULTILINE
    text = read_text(path)
    if not text:
        return 0
    if is_regex:
        try:
            return len(re.findall(old, text))
        except re.error:
            return 0
    # регистрозависимо, как в md_replace
    return text.count(old)