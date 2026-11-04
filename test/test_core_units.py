"""
Юнит-тесты ядра: парсер текста, кодировки, реестр имён, сканер vault,
docx-движок, отчёты. Фикстуры создаются на месте, внешних данных не нужно.

Запуск:  python -m pytest test/test_core_units.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from core import text_parser as tp
from core import encoding as enc
from core import name_registry as nr
from core import vault_scanner as vs
from core.report import write_report


# --- text_parser ---------------------------------------------------------

def test_norm_yo_keeps_length():
    assert tp.norm_yo("Ёлка, ёлка, ЕЁ") == "Елка, елка, ЕЕ"
    assert len(tp.norm_yo("ёжик через улицу")) == len("ёжик через улицу")


def test_iter_text_files_skips_service_dirs(tmp_path):
    (tmp_path / "заметка.md").write_text("текст", encoding="utf-8")
    for svc in (".obsidian", ".trash", ".git", "md_replace_backups"):
        d = tmp_path / svc
        d.mkdir()
        (d / "внутри.md").write_text("текст", encoding="utf-8")
    files = list(tp.iter_text_files(str(tmp_path)))
    assert [f.name for f in files] == ["заметка.md"]


def test_iter_text_files_limit_and_exts(tmp_path):
    for n in range(5):
        (tmp_path / f"ф{n}.md").write_text("т", encoding="utf-8")
    # limit=0/None — без ограничения; limit=2 — ровно два
    assert len(list(tp.iter_text_files(str(tmp_path), limit=2))) == 2
    assert len(list(tp.iter_text_files(str(tmp_path), limit=None))) == 5
    assert len(list(tp.iter_text_files(str(tmp_path), limit=0))) == 5


def test_iter_text_files_guards(tmp_path):
    try:
        list(tp.iter_text_files(""))
        assert False, "пустой путь должен давать ValueError"
    except ValueError:
        pass
    try:
        list(tp.iter_text_files(str(tmp_path / "нет_такой")))
        assert False, "несуществующий путь должен давать ValueError"
    except ValueError:
        pass


def test_find_name_candidates_skips_stoplist():
    text = "Эрика шла по улице. Однако в городе было тихо."
    known = {"эрика"}
    cand = tp.find_name_candidates(text, known=known)
    assert "Эрика" not in cand
    assert "Однако" not in cand


# --- encoding ------------------------------------------------------------

def test_detect_cp1251_and_koi8():
    text = "привет, мир, это тестовая русская строка для проверки кодировки"
    assert enc.detect(text.encode("cp1251")) == "cp1251"
    assert enc.detect(text.encode("koi8-r")) == "koi8-r"


def test_detect_empty_and_ascii():
    assert enc.detect(b"") == "utf-8"
    assert enc.detect(b"plain ascii text") in ("utf-8", "ascii")


def test_is_utf8_and_read_any(tmp_path):
    good = tmp_path / "хорошо.md"
    good.write_text("привет", encoding="utf-8")
    bad = tmp_path / "старый.md"
    bad.write_text("привет", encoding="cp1251")
    assert enc.is_utf8(good) is True
    assert enc.is_utf8(bad) is False
    text, detected = enc.read_any(bad)
    assert text == "привет"
    assert detected == "cp1251"


# --- name_registry -------------------------------------------------------

def test_registry_load_missing_and_invalid(tmp_path):
    assert nr.load_registry(tmp_path / "нет.yaml") == []
    bad = tmp_path / "сломан.yaml"
    bad.write_text("{не список: а словарь}", encoding="utf-8")
    assert nr.load_registry(bad) == []


def test_registry_roundtrip_and_normalization(tmp_path):
    src = tmp_path / "реестр.yaml"
    src.write_text(
        "- имя: Эрика\n  формы: [Эрика, 5]\n- имя: Кай\n", encoding="utf-8")
    chars = nr.load_registry(src)
    assert [c["имя"] for c in chars] == ["Эрика", "Кай"]
    assert chars[0]["формы"] == ["Эрика", "5"]  # элементы приведены к str
    out = tmp_path / "sub" / "копия.yaml"
    nr.save_registry(out, chars)
    assert nr.load_registry(out) == chars


def test_known_forms_and_first_names():
    chars = [{"имя": "Мастер Кайдзо", "формы": ["Кайдзо"], "старое": [],
              "старое_опасное": [], "опечатки": []}]
    forms = nr.known_forms(chars)
    assert "кайдзо" in forms and "мастер кайдзо" in forms
    assert nr.known_first_names(chars) == {"мастер"}


# --- vault_scanner -------------------------------------------------------

def test_is_resolved_names_and_paths():
    # контракт: цели приходят уже в нижнем регистре (как из _clean_link)
    basenames = {"глава"}
    relpaths = {"сцены/начало"}
    attachments = {"картинка.png"}
    assert vs.is_resolved("глава", basenames, relpaths, attachments)
    assert vs.is_resolved("сцены/начало", basenames, relpaths, attachments)
    assert vs.is_resolved("картинка.png", basenames, relpaths, attachments)
    assert not vs.is_resolved("нет", basenames, relpaths, attachments)
    assert vs.is_resolved("путь/глава", basenames, relpaths, attachments)


def test_clean_link_strips_alias_and_anchor():
    assert vs._clean_link("путь/имя#глава|алияс") == "путь/имя"
    assert vs._clean_link("Имя.md") == "имя"


def test_scan_vault_counts_and_links(tmp_path):
    (tmp_path / "A.md").write_text("## А\n\n[[Б]] и [текст](Б.md)\n",
                                   encoding="utf-8")
    (tmp_path / "Б.md").write_text("## Б\n", encoding="utf-8")
    notes, basenames, relpaths, attachments = vs.scan_vault(str(tmp_path))
    assert len(notes) == 2
    a = next(n for n in notes if n.rel == "A.md")
    assert "б" in a.links            # вики
    assert ("б", "Б.md") in a.md_links  # markdown


# --- docx_io -------------------------------------------------------------

def _make_docx(path, text_paras):
    from docx import Document
    doc = Document()
    for p in text_paras:
        doc.add_paragraph(p)
    doc.save(path)


def test_docx_read_count_replace(tmp_path):
    from core import docx_io
    p = tmp_path / "книга.docx"
    _make_docx(p, ["Первый абзац про Кая.", "Второй абзац."])
    assert "Первый абзац" in docx_io.read_text(p)
    assert docx_io.count_in_docx(p, "абзац") == 2
    n, changed, broken = docx_io.replace_in_docx(p, "Кая", "Эрики",
                                                 backup=False)
    assert n == 1 and changed == 1 and broken == 0
    text = docx_io.read_text(p)
    assert "Эрики" in text and "Кая" not in text


def test_docx_split_runs_replaced(tmp_path):
    # фраза, разорванная Word'ом между run'ами, находится и заменяется
    from docx import Document
    from core import docx_io
    p = tmp_path / "рваный.docx"
    doc = Document()
    par = doc.add_paragraph()
    par.add_run("Стоит от")
    par.add_run("метить, что")
    doc.save(p)
    assert docx_io.count_in_docx(p, "Стоит отметить") == 1
    n, changed, _broken = docx_io.replace_in_docx(
        p, "Стоит отметить, что", "", backup=False)
    assert n == 1 and changed == 1
    doc2 = Document(p)
    assert "".join(t.text or "" for t in doc2.paragraphs[0]._p.iter(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
    ) == ""


# --- report --------------------------------------------------------------

def test_write_report_roundtrip(tmp_path):
    p = tmp_path / "отчёты" / "вложено" / "rep.md"
    write_report(p, "содержимое")
    assert p.read_text(encoding="utf-8") == "содержимое"
