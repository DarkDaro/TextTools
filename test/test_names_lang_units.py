# -*- coding: utf-8 -*-
"""
Юнит-тесты cast_list / registry_builder для двуязычия
(docs/LOC_PLAN.md): английские регэкспы имён, строгий фильтр
титулов для en, --lang у CLI.

Запуск: python -m pytest test/test_names_lang_units.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools import cast_list as cl  # noqa: E402
from tools import registry_builder as rb  # noqa: E402


def test_cast_english_names():
    text = ("The Captain called John Blackthorn over. "
            "John waited. Then the Captain left.")
    single, pairs = cl.scan_text(text, lang="en")
    assert "John" in single and "Blackthorn" in single
    # титул и месяц с заглавной в середине — не имена
    assert "Captain" not in single
    assert "John Blackthorn" in pairs


def test_cast_english_dash_name():
    single, _ = cl.scan_text(
        "Anne-Marie smiled and Anne-Marie waved.", lang="en")
    assert single.get("Anne-Marie") == 2


def test_cast_russian_unchanged():
    text = "Эрика Волкова вышла из дома. Эрика остановилась у двери."
    single, pairs = cl.scan_text(text, lang="ru")
    assert single.get("Эрика") == 2
    assert single.get("Волкова") == 1
    assert "Эрика Волкова" in pairs


def test_cast_russian_default_lang_stops():
    # для ru стоп-слова отсеиваются только вне середины предложения
    text = "Ну и мастер этот Иван пришёл."
    single, _ = cl.scan_text(text, lang="ru")
    assert "Иван" in single
    assert "мастер" not in single


def test_registry_builder_english(tmp_path, capsys):
    src = tmp_path / "story.md"
    src.write_text(
        "The captain called John Blackthorn over. "
        "The door closed behind John Blackthorn.", encoding="utf-8")
    out = tmp_path / "cand.yaml"
    rb.run(str(src), out=str(out), min_count=1, lang="en")
    data = out.read_text(encoding="utf-8")
    assert "blackthorn" in data
    assert "john blackthorn" in data


def test_registry_builder_russian_unchanged(tmp_path, capsys):
    src = tmp_path / "story.md"
    # «Эрика» в середине предложения — кандидат; в начале — нет
    src.write_text("У двери Эрика остановилась. Эрика молчала.",
                   encoding="utf-8")
    out = tmp_path / "cand.yaml"
    rb.run(str(src), out=str(out), min_count=1, lang="ru")
    data = out.read_text(encoding="utf-8")
    assert "эрика" in data
