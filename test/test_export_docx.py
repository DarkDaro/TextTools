"""
Тесты export-docx: экспорт главы .md → .docx для беты (BACKLOG №4).

Проверяется содержимое через core.docx_io.read_text и стили через
python-docx (стили Heading/List Bullet, жирные runs).

Запуск:  python -m pytest test/test_export_docx.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import docx_io
from docx import Document
from tools import export_docx

MD = """---
title: Глава 1
tags: [роман]
---

# Глава первая

Мира **открыла дверь** и *замерла*. Она посмотрела на [[Мастер Кайдзо|мастера]].

> Цитата в рамке.

- первый пункт
- второй пункт

1. шаг раз
2. шаг два

---

## Раздел

    код внутри код-блока

Диалог начинается с тире.
"""


def test_file_export_content_and_styles(tmp_path):
    src = tmp_path / "глава.md"
    src.write_text(MD, encoding="utf-8")
    dst = tmp_path / "глава.docx"
    rc = export_docx.run(str(src), str(dst))
    assert rc == 0
    assert dst.exists()
    text = docx_io.read_text(dst)
    # frontmatter в docx не попал
    assert "title: Глава 1" not in text
    # контент на месте, вики-ссылка превратилась в алиас
    assert "Мира открыла дверь" in text
    assert "мастера" in text and "[[" not in text
    assert "Диалог начинается с тире." in text
    # стили: заголовки и список
    doc = Document(str(dst))
    styles = [p.style.name for p in doc.paragraphs]
    assert "Heading 1" in styles
    assert "Heading 2" in styles
    assert "List Bullet" in styles
    assert "Quote" in styles
    # жирный run
    bold = [r.text for p in doc.paragraphs for r in p.runs if r.bold]
    assert any("открыла дверь" in t for t in bold)


def test_export_no_overwrite_without_force(tmp_path):
    src = tmp_path / "глава.md"
    src.write_text("# Т\n\nТекст.\n", encoding="utf-8")
    dst = tmp_path / "глава.docx"
    assert export_docx.run(str(src), str(dst)) == 0
    first = dst.read_bytes()
    rc = export_docx.run(str(src), str(dst))
    assert rc == 2  # без --force перезапись запрещена
    assert dst.read_bytes() == first
    assert export_docx.run(str(src), str(dst), force=True) == 0


def test_dir_export_keeps_structure(tmp_path):
    (tmp_path / "глава1.md").write_text("# Г1\n\nТекст.\n", encoding="utf-8")
    sub = tmp_path / "часть2"
    sub.mkdir()
    (sub / "глава2.md").write_text("# Г2\n\nТекст.\n", encoding="utf-8")
    out = tmp_path / "docx"
    rc = export_docx.run(str(tmp_path), str(out))
    assert rc == 0
    assert (out / "глава1.docx").exists()
    assert (out / "часть2" / "глава2.docx").exists()


def test_dir_export_skips_existing(tmp_path):
    (tmp_path / "а.md").write_text("# А\n\nТекст.\n", encoding="utf-8")
    (tmp_path / "б.md").write_text("# Б\n\nТекст.\n", encoding="utf-8")
    out = tmp_path / "docx"
    out.mkdir()
    (out / "а.docx").write_text("старый файл", encoding="utf-8")
    rc = export_docx.run(str(tmp_path), str(out))
    assert rc == 0
    # существующий не тронут, новый сделан
    assert (out / "а.docx").read_text(encoding="utf-8") == "старый файл"
    assert (out / "б.docx").exists()


def test_non_md_input_rejected(tmp_path):
    f = tmp_path / "заметка.txt"
    f.write_text("Текст.", encoding="utf-8")
    assert export_docx.run(str(f), str(tmp_path / "з.docx")) == 2


def test_cli_wiring(tmp_path):
    src = tmp_path / "глава.md"
    src.write_text("# Заголовок\n\nАбзац с **жирным**.\n", encoding="utf-8")
    dst = tmp_path / "глава.docx"
    r = subprocess.run(
        [sys.executable, "textools.py", "export-docx",
         "--input", str(src), "--out", str(dst)],
        cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0
    assert "Экспортировано" in r.stdout
    assert "Абзац с жирным." in docx_io.read_text(dst)


def test_cli_help_visible():
    r = subprocess.run(
        [sys.executable, "textools.py", "--help"],
        cwd=ROOT, capture_output=True, text=True)
    assert "export-docx" in r.stdout
