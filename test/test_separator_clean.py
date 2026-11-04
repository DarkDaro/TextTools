"""
Тесты separator_clean — чистки мусорных разделителей.

Проверяются: уборка серий «/////», «*****», «======», «———», «* * *»;
порог --min-run; защита frontmatter и код-блоков; таблицы, списки и
заголовки не трогаются; стыки абзацев не склеиваются; dry-run и --fix
с .bak; docx.

Запуск:  python -m pytest test/test_separator_clean.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools import separator_clean as sc


def test_removes_plain_runs():
    text = "Абзац один.\n\n/////\n\nАбзац два.\n\n*****\n\nАбзац три."
    new, n = sc.clean_text(text)
    assert n == 2
    assert new == "Абзац один.\n\nАбзац два.\n\nАбзац три."


def test_removes_spaced_runs_and_dashes():
    text = "А.\n\n* * *\n\nБ.\n\n———\n\nВ.\n\n=====\n\nГ."
    new, n = sc.clean_text(text)
    assert n == 3
    assert new == "А.\n\nБ.\n\nВ.\n\nГ."


def test_min_run_threshold():
    # «--» (2 символа) при min_run=3 остаётся
    text = "А — Б.\n\n--\n\nВ."
    new, n = sc.clean_text(text, min_run=3)
    assert n == 0
    assert new == text


def test_frontmatter_protected_md():
    text = "---\nзаголовок: Глава\n---\n\nТекст.\n\n/////\n\nЕщё текст."
    new, n = sc.clean_text(text, frontmatter=True)
    assert n == 1
    assert new.startswith("---\nзаголовок: Глава\n---\n")
    assert "/////" not in new


def test_code_fence_protected():
    text = "Текст.\n\n```\n/////\nне код-разделитель\n```\n\n~~~~\n*****\n~~~~"
    new, n = sc.clean_text(text)
    assert n == 0
    assert new == text


def test_table_and_list_untouched():
    text = "| Колонка | Ещё |\n|---|---|\n| а | б |\n\n- пункт списка\n\n> цитата"
    new, n = sc.clean_text(text)
    assert n == 0
    assert new == text


def test_hash_heading_untouched():
    text = "#### Глава пятая\n\nТекст."
    new, n = sc.clean_text(text)
    assert n == 0
    assert new == text


def test_setext_underline_removed():
    # «====» под строкой — setext-заголовок; в рукописи это отбойник
    text = "Глава первая\n=====\n\nТекст."
    new, n = sc.clean_text(text)
    assert n == 1
    assert new == "Глава первая\n\nТекст."


def test_junction_without_blanks_no_glue():
    text = "Абзац.\n/////\nАбзац."
    new, n = sc.clean_text(text)
    assert n == 1
    assert new == "Абзац.\n\nАбзац."


def test_junction_blanks_collapsed():
    text = "Абзац.\n\n\n/////\n\n\n\nАбзац."
    new, n = sc.clean_text(text, max_blank=1)
    assert n == 1
    assert new == "Абзац.\n\nАбзац."


def test_no_changes_returns_original():
    text = "Просто текст,\nничего лишнего.\n"
    new, n = sc.clean_text(text)
    assert n == 0
    assert new == text


def test_idempotent():
    text = "А.\n\n/////\n\nБ.\n"
    once, n1 = sc.clean_text(text)
    assert n1 == 1
    twice, n2 = sc.clean_text(once)
    assert n2 == 0
    assert twice == once


def test_cli_fix_and_bak(tmp_path):
    f = tmp_path / "глава.md"
    f.write_text("Абзац.\n\n/////\n\nАбзац.\n", encoding="utf-8")
    rc = sc.main(["--input", str(tmp_path), "--fix"])
    assert rc == 0
    assert "/////" not in f.read_text(encoding="utf-8")
    assert Path(str(f) + ".bak").exists()


def test_cli_dry_run_untouched(tmp_path):
    f = tmp_path / "глава.txt"
    original = "Абзац.\n\n*****\n\nАбзац.\n"
    f.write_text(original, encoding="utf-8")
    report = tmp_path / "rep" / "отчёт.md"
    rc = sc.main(["--input", str(tmp_path), "--out", str(report)])
    assert rc == 0
    assert f.read_text(encoding="utf-8") == original
    assert report.exists()


def test_docx_paragraph_removed(tmp_path):
    from docx import Document
    p = tmp_path / "книга.docx"
    doc = Document()
    doc.add_paragraph("Абзац первый.")
    doc.add_paragraph("/////")
    doc.add_paragraph("Абзац второй.")
    doc.save(p)
    rc = sc.main(["--input", str(p), "--fix"])
    assert rc == 0
    after = Document(p)
    texts = [par.text for par in after.paragraphs]
    assert texts == ["Абзац первый.", "Абзац второй."]
    assert Path(str(p) + ".bak").exists()


def test_custom_symbols():
    text = "А.\n\n@@@\n\nБ."
    new, n = sc.clean_text(text, symbols="@", min_run=3)
    assert n == 1
    assert new == "А.\n\nБ."
    # «#» вне набора по умолчанию (решётки — заголовки) не трогается
    text2 = "А.\n\n###\n\nБ."
    new2, n2 = sc.clean_text(text2)
    assert n2 == 0
    assert new2 == text2
