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


def _replace_in_paragraph(p, pattern, new):
    """01.10: кросс-run замена внутри параграфа с сохранением
    форматирования. Искомая строка, разорванная между run'ами (w:t),
    находится в склеенном тексте; заменяющий текст помещается в первый
    затронутый run, остальные части совпадения очищаются. Соседние run'ы
    не трогаются. Возвращает число замен (0 или 1 за проход)."""
    ts = [t for t in p.iter(W_NS + "t")]
    if not ts:
        return 0
    texts = [t.text or "" for t in ts]
    full = "".join(texts)
    m = pattern.search(full)
    if not m or m.start() == m.end():
        return 0
    start, end = m.span()
    spans = []
    pos = 0
    for txt in texts:
        spans.append((pos, pos + len(txt)))
        pos += len(txt)
    first = next(i for i, (s, e) in enumerate(spans) if s <= start < e)
    last = next(i for i, (s, e) in enumerate(spans) if s < end <= e)
    prefix = texts[first][:start - spans[first][0]]
    suffix = texts[last][end - spans[last][0]:]
    texts[first] = prefix + new + (suffix if first == last else "")
    for i in range(first + 1, last + 1):
        texts[i] = suffix if i == last else ""
    for t_el, txt in zip(ts, texts):
        if (t_el.text or "") != txt:
            t_el.text = txt
            if txt != txt.strip():
                # краевые пробелы без xml:space Word съест
                t_el.set(
                    "{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return 1


def replace_in_docx(path, old, new, is_regex=False, backup=True):
    """Замена old -> new в тексте docx.

    01.10: замена идёт по параграфам в склеенном тексте w:t — фраза,
    разорванная Word'ом между run'ами, теперь ЗАМЕНЯЕТСЯ (раньше
    пропускалась как broken). Форматирование сохраняется: правятся только
    затронутые w:t, первый получает новый текст, остальные части
    совпадения очищаются.

    Возвращает (замен_всего, файлов_изменено, пропусков_разорванных=0).
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
    for part in doc.part.package.iter_parts():
        name = str(part.partname)
        if "/word/" not in name or not any(k in name for k in DOC_PART_KEYWORDS):
            continue
        el = getattr(part, "_element", None)
        if el is None:
            continue
        for p in el.iter(W_NS + "p"):
            # цикл: после каждой замены текст меняется — ищем заново
            for _ in range(1000):  # защита от нулевой длины совпадений
                n = _replace_in_paragraph(p, pattern, new)
                if not n:
                    break
                total += n

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