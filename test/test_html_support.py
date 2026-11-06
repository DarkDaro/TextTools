"""
Тесты поддержки .html в аналитических инструментах (07.11).

Контракт: html читается как ТЕКСТ страницы (теги, <script>/<style>,
комментарии и сущности уходят) в статистике, стиле, штампах, эхо и
АНТИРЕШИМОСТИ. Правящие инструменты (типографика, чистка, разделители)
html не читают — разметку незачем править как прозу.

Запуск:  python -m pytest test/test_html_support.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from core import text_parser as tp
from tools import text_stats

PAGE = """<!doctype html>
<html><head><title>Страница</title>
<style>body { color: red; } /* Да,нет мусор */</style>
<script>var x = "А.С.Пушкин код";</script>
</head>
<body><!-- комментарий -->
<h1>Заголовок сайта</h1>
<p>Он ушёл.Свет погас — да,нет.</p>
<p>Ещё &laquo;текст&raquo; и 1941-1945.</p>
</body></html>"""


def test_html_to_text_strips_markup():
    text = tp.html_to_text(PAGE)
    assert "<" not in text and ">" not in text
    assert "Да,нет мусор" not in text      # внутри <style>
    assert "А.С.Пушкин код" not in text    # внутри <script>
    assert "комментарий" not in text       # HTML-комментарий
    assert "Он ушёл.Свет погас" in text
    assert "«текст»" in text               # сущности раскрываются
    assert "1941-1945" in text


def test_read_text_html():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "page.html"
        f.write_text(PAGE, encoding="utf-8")
        text = tp.read_text(f)
        assert "Заголовок сайта" in text
        assert "<p>" not in text


def test_iter_text_files_includes_html():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "a.md").write_text("Заметка.", encoding="utf-8")
        (Path(tmp) / "b.html").write_text(PAGE, encoding="utf-8")
        files = list(tp.iter_text_files(tmp, exts=tp.ANALYSIS_EXTS))
        names = {f.name for f in files}
        assert names == {"a.md", "b.html"}


def test_stats_and_echo_see_html():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "page.html").write_text(
            "<p>Он шёл и шёл. Он шёл долго.</p>", encoding="utf-8")
        files = list(tp.iter_text_files(tmp, exts=tp.ANALYSIS_EXTS))
        assert len(files) == 1
        text = tp.read_text(files[0])
        st = text_stats.analyze_text(text)
        assert st["words"] > 0


def test_writing_tools_do_not_touch_html():
    from tools import separator_clean, typography, whitespace_clean
    for mod in (typography, whitespace_clean, separator_clean):
        assert not any(e in mod.EXTS for e in (".html", ".htm"))


def test_bad_html_never_crashes():
    assert tp.html_to_text("") == ""
    assert tp.html_to_text("просто текст без разметки") == \
        "просто текст без разметки"
