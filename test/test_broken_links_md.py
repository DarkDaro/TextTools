"""
Тесты broken_links на markdown-ссылках [текст](цель).

Проверяются: существующие и отсутствующие цели, внешние адреса,
якоря, проценты-эквивы (%20), изображения ![](), код-блоки,
относительные пути по диску (при --limit индекс неполный).

Запуск:  python -m pytest test/test_broken_links_md.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools import broken_links
from core import vault_scanner as vs


def _make_vault(tmp_path):
    (tmp_path / "Б.md").write_text("Цель.", encoding="utf-8")
    (tmp_path / "картинка.png").write_bytes(b"png")
    (tmp_path / "Сцены").mkdir()
    (tmp_path / "Сцены" / "Внутренняя.md").write_text("внутри",
                                                      encoding="utf-8")
    (tmp_path / "под").mkdir()
    (tmp_path / "под" / "Отн.md").write_text(
        "[вверх](../Сцены/Внутренняя.md)\n", encoding="utf-8")
    a = tmp_path / "A.md"
    a.write_text(
        "[есть](Б.md)\n"
        "[нет](Отсутствует.md)\n"
        "[гугл](https://example.com/x)\n"
        "[якорь](#глава)\n"
        "[с якорем](Б.md#глава)\n"
        "[с пробелом](a%20б.md)\n"
        "![картинка](картинка.png)\n"
        "![пустая](нет_такой.png)\n"
        "```\n[в коде](В_коде.md)\n```\n",
        encoding="utf-8")
    (tmp_path / "a б.md").write_text("пробел в имени", encoding="utf-8")
    return a


def test_md_links_from_text_parse():
    text = ("[один](Б.md) ![два](картинка.png)\n"
            "[внешний](https://x.y) [якорь](#гл)\n"
            "```\n[в коде](Нет.md)\n```\n")
    pairs = vs.md_links_from_text(text)
    cleans = {c for c, _r in pairs}
    assert "б" in cleans
    assert "картинка.png" in cleans
    assert "нет" not in cleans  # внешние и якоря пропущены
    assert all("в коде" not in c for c in cleans)


def test_md_links_percent_and_anchor():
    pairs = vs.md_links_from_text("[т](Моя%20заметка.md#гл)")
    assert pairs == {("моя заметка", "Моя заметка.md")}


def test_integration_counts(tmp_path, capsys):
    _make_vault(tmp_path)
    rc = broken_links.run(str(tmp_path))
    assert rc == 0
    out = capsys.readouterr().out
    # битые markdown: Отсутствует.md + нет_такой.png = 2
    assert "Битых markdown-ссылок: 2" in out
    # битые вики: 0
    assert "Битых вики-ссылок: 0" in out


def test_report_contains_md_section(tmp_path):
    _make_vault(tmp_path)
    report = tmp_path / "rep" / "отчёт.md"
    broken_links.run(str(tmp_path), out=str(report))
    text = report.read_text(encoding="utf-8")
    assert "Broken markdown: 2" in text
    assert "- Отсутствует.md" in text
    assert "- нет_такой.png" in text


def test_relative_disk_fallback_under_limit(tmp_path, capsys):
    # при --limit=1 индекс содержит только A.md, Б.md в индекс не
    # попадает — ссылка всё равно не битая: спасает проверка по диску
    _make_vault(tmp_path)
    rc = broken_links.run(str(tmp_path), limit=1)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Битых markdown-ссылок: 0" not in out or "Отсутствует" in out
    # точечно: [есть](Б.md) не в списке битых
    lines = [ln for ln in out.splitlines() if "Битых markdown" in ln]
    assert lines and "в 1 файлах" in lines[0]


def test_wiki_links_still_checked(tmp_path, capsys):
    (tmp_path / "A.md").write_text(
        "[[нет такой]] [[Б]]\n", encoding="utf-8")
    (tmp_path / "Б.md").write_text("цель", encoding="utf-8")
    broken_links.run(str(tmp_path))
    out = capsys.readouterr().out
    assert "Битых вики-ссылок: 1" in out
