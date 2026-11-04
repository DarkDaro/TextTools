"""
Тесты docx/txt в merge-finder: главы в Word раньше выпадали из поиска
дубликатов совсем — scan_vault собирает только .md.

05.11: txt/docx добавляются отдельным сборщиком (_extra_text_notes),
вики-граф Obsidian не трогается; «глава.md» и «глава.docx» рядом — не
кандидаты на слияние (ключ stem+суффикс), а два «глава.docx» в разных
папках — кандидаты.

Запуск:  python -m pytest test/test_merge_docx.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools import merge_finder


def _make_docx(path, paras):
    from docx import Document
    doc = Document()
    for p in paras:
        doc.add_paragraph(p)
    doc.save(path)
    return path


_TEXT = ("Эрика шла по длинному коридору старой обсерватории. "
         "Мастер Кайдзо ждал у двери и молчал, как всегда перед вылетом. "
         "Лика взяла книгу со стола и кивнула.")


def test_duplicate_docx_content_found(tmp_path):
    (tmp_path / "копия").mkdir()
    _make_docx(tmp_path / "глава_01.docx", [_TEXT])
    _make_docx(tmp_path / "копия" / "глава_01_копия.docx", [_TEXT])
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        merge_finder.run(str(tmp_path))
    out = buf.getvalue()
    assert "Дубликатов по содержимому: 1 групп" in out
    assert "(+2 txt/docx)" in out


def test_docx_and_md_same_stem_not_merge_candidates(tmp_path):
    # заметка и её Word-исходник рядом — НЕ дубликат имён
    (tmp_path / "глава.md").write_text("## Глава\n\nТекст.\n",
                                       encoding="utf-8")
    _make_docx(tmp_path / "глава.docx", ["Текст главы."])
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        merge_finder.run(str(tmp_path))
    assert "Одинаковых имён в разных папках: 0 групп" in \
        buf.getvalue()


def test_duplicate_docx_names_in_folders_found(tmp_path):
    (tmp_path / "черновик").mkdir()
    (tmp_path / "финал").mkdir()
    _make_docx(tmp_path / "черновик" / "глава.docx", ["А."])
    _make_docx(tmp_path / "финал" / "глава.docx", ["Б."])
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        merge_finder.run(str(tmp_path))
    # имена файлов печатаются только с --verbose/--out; в stdout — счётчики
    assert "Одинаковых имён в разных папках: 1 групп" in buf.getvalue()
    # крошечные файлы не должны давать ложных «близких дубликатов»
    assert "Близких дубликатов (>= 70%): 0 пар" in buf.getvalue()


def test_broken_docx_does_not_crash_run(tmp_path):
    _make_docx(tmp_path / "ок.docx", [_TEXT])
    (tmp_path / "битый.docx").write_bytes(
        b"PK\x03\x04 " + "мусор".encode("utf-8"))
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = merge_finder.run(str(tmp_path))
    assert rc == 0
    assert "(+2 txt/docx)" in buf.getvalue()


def test_json_includes_docx_dups(tmp_path):
    import json
    _make_docx(tmp_path / "а.docx", [_TEXT])
    (tmp_path / "б").mkdir(exist_ok=True)
    _make_docx(tmp_path / "б" / "в.docx", [_TEXT])
    rep = tmp_path / "rep.json"
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        merge_finder.run(str(tmp_path), json_out=str(rep))
    data = json.loads(rep.read_text(encoding="utf-8"))
    files = [f for g in data["dup_content"] for f in g["files"]]
    assert "а.docx" in files and "б/в.docx" in files
