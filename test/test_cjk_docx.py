"""
Тесты docx-поддержки find_cjk: docx больше не «бинарник».

05.11: главы в docx раньше молча пропускались («Пропущено бинарных: 1»),
проверки на иероглифы и мойбейк не было вовсе — writer получал ложное
«ЧИСТО». Теперь текст читается через core.docx_io (python-docx),
номер строки в отчёте = номер параграфа docx.

Запуск:  python -m pytest test/test_cjk_docx.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from find_cjk import DEFAULT_EXT, main, scan_file


def _make_docx(path, paras):
    from docx import Document
    doc = Document()
    for p in paras:
        doc.add_paragraph(p)
    doc.save(path)
    return path


def test_docx_with_cjk_found(tmp_path):
    p = _make_docx(tmp_path / "глава.docx", [
        "Эрика шла по коридору.",
        "Мусор от модели: привет， мир！测试 ＡＢＣ",
        "Лика взяла книгу.",
    ])
    findings, err = scan_file(p)
    assert err is None
    ranges = {f["range"] for f in findings}
    assert "Китайские иероглифы (CJK Unified)" in ranges
    assert "Fullwidth формы" in ranges
    # номер строки = номер параграфа docx
    line2 = [f for f in findings if f["line"] == 2]
    assert "测" in {f["char"] for f in line2}
    assert line2[0]["context"].startswith("Мусор от модели")


def test_clean_docx_is_silent(tmp_path):
    p = _make_docx(tmp_path / "чисто.docx", [
        "Эрика посмотрела на Кайдзо.",
        "— Ты уверен? — спросила она.",
    ])
    findings, err = scan_file(p)
    assert findings == [] and err is None


def test_broken_docx_reported_not_skipped(tmp_path):
    # битый zip — явная ошибка в отчёте, а не молчаливый «бинарник»
    p = tmp_path / "битый.docx"
    p.write_bytes(b"PK\x03\x04 " + "обрезанный мусор".encode("utf-8"))
    findings, err = scan_file(p)
    assert findings == []
    assert err is not None and err.startswith("не читается")


def test_docx_in_default_extensions():
    # 05.11: папка с docx попадает в дефолтный прогон без --ext
    assert ".docx" in DEFAULT_EXT


def test_main_scans_docx_folder(tmp_path):
    _make_docx(tmp_path / "а.docx", ["текст 测试"])
    (tmp_path / "б.txt").write_text("чисто\n", encoding="utf-8")
    rep = tmp_path / "rep.json"
    rc = main([str(tmp_path), "--quiet", "--json", str(rep)])
    assert rc == 1
    data = json.loads(rep.read_text(encoding="utf-8"))
    assert set(data["results"]) == {"а.docx"}  # txt чист, docx нашёлся
