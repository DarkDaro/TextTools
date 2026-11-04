"""
Тесты текстовых частей docx: колонтитулы должны участвовать в чтении
и замене наравне с телом. 05.11: фильтр текстовых частей вынесен в
единый генератор _iter_doc_parts (раньше дублировался в read_text и
replace_in_docx и мог разъехаться); легаси replace_in_docx_text
(пересоздание тела, потеря форматирования) удалён.

Запуск:  python -m pytest test/test_docx_parts.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from core import docx_io


def _make_docx_with_header_footer(path, body, header, footer):
    from docx import Document
    doc = Document()
    for p in body:
        doc.add_paragraph(p)
    hdr = doc.sections[0].header
    hdr.is_linked_to_previous = False
    hdr.paragraphs[0].text = header
    ftr = doc.sections[0].footer
    ftr.is_linked_to_previous = False
    ftr.paragraphs[0].text = footer
    doc.save(path)
    return path


def test_read_text_sees_header_footer(tmp_path):
    p = _make_docx_with_header_footer(
        tmp_path / "глава.docx",
        body=["Текст главы."],
        header="Шапка: еж", footer="Низ: еж")
    text = docx_io.read_text(p)
    assert "Шапка: еж" in text
    assert "Низ: еж" in text


def test_replace_reaches_header_footer(tmp_path):
    p = _make_docx_with_header_footer(
        tmp_path / "глава.docx",
        body=["Текст главы."],
        header="Шапка: еж", footer="Низ: еж")
    n, changed, _broken = docx_io.replace_in_docx(p, "еж", "ёж")
    assert n == 2
    assert changed == 1
    text = docx_io.read_text(p)
    assert "Шапка: ёж" in text
    assert "Низ: ёж" in text
    assert "Текст главы" in text  # тело не задето


def test_legacy_full_rewrite_removed():
    # replace_in_docx_text пересоздавал параграфы и молча терял
    # форматирование; с 04.11 в продакшене не вызывался — удалён,
    # чтобы никто случайно им не воспользовался
    assert not hasattr(docx_io, "replace_in_docx_text")
