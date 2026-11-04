"""
Тесты docx-правок ё/е-аудита: витрина показывала находки в Word,
а «Применить» молча пропускала их («только .md/.txt»).

05.11: замена идёт пословно по отмеченным формам во всём документе
(как в phrase_check), кросс-run с сохранением форматирования, регистр
первой буквы сохраняется, границы слов защищают («Ежевика» не задевается
при правке «еж»).

Запуск:  python -m pytest test/test_yo_docx.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from core import docx_io
from tools import yo_audit


def _make_docx(path, paras):
    from docx import Document
    doc = Document()
    for p in paras:
        doc.add_paragraph(p)
    doc.save(path)
    return path


def test_docx_clean_replaces_with_case(tmp_path):
    p = _make_docx(tmp_path / "глава.docx", [
        "Еж шёл в лес.",
        "Вот еж колючий.",
    ])
    lines, n = yo_audit._clean_docx(p, [("еж", "ёж", 2)],
                                    "2026-11-05_test")
    assert n == 2
    text = docx_io.read_text(p)
    assert "Ёж шёл" in text
    assert "ёж колючий" in text


def test_docx_clean_respects_word_bounds(tmp_path):
    p = _make_docx(tmp_path / "глава.docx", [
        "Ежевика росла у реки. Еж шёл мимо.",
    ])
    _, n = yo_audit._clean_docx(p, [("еж", "ёж", 1)], "t")
    assert n == 1
    assert "Ежевика" in docx_io.read_text(p)


def test_docx_clean_backup_created(tmp_path):
    p = _make_docx(tmp_path / "глава.docx", ["еж в лесу."])
    yo_audit._clean_docx(p, [("еж", "ёж", 1)], "2026-11-05_x")
    bak = p.parent / "md_replace_backups" / "2026-11-05_x" / "глава.docx"
    assert bak.exists()
    # бэкап — оригинал (е-написание до правки)
    assert "еж" in (docx_io.read_text(bak) or "")


def test_docx_clean_broken_file_skipped(tmp_path):
    p = tmp_path / "битый.docx"
    p.write_bytes(b"PK\x03\x04 " + "мусор".encode("utf-8"))
    lines, n = yo_audit._clean_docx(p, [("еж", "ёж", 1)], "t")
    assert n == 0
    assert any(s.startswith("[ПРОПУСК]") for s in lines)


def test_clean_selection_routes_docx(tmp_path):
    # сквозной вызов: docx больше не «только .md/.txt»
    p = _make_docx(tmp_path / "глава.docx", ["еж сидел под елью."])
    res = yo_audit.clean_selection({str(p): [("еж", "ёж", 1)]})
    assert any("[Ё]" in s for s in res)
    assert "ёж" in docx_io.read_text(p)
