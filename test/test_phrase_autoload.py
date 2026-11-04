"""
Тест автозагрузки постоянного словаря штампов (phrases.yaml).

05.11: фразы, добавленные кнопкой «запомнить» (add_phrase пишет в
tools/phrases.yaml), раньше молча не участвовали в поиске — файл
читался только с явным --custom. Теперь load_phrases() без аргументов
подхватывает постоянный словарь.

Запуск:  python -m pytest test/test_phrase_autoload.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools import phrase_check


def test_custom_path_still_works(tmp_path):
    f = tmp_path / "мой.yaml"
    f.write_text("- мармеладные бегемоты\n", encoding="utf-8")
    phrases = phrase_check.load_phrases(str(f))
    assert "мармеладные бегемоты" in phrases
    # встроенные никуда не делись
    assert "стоит отметить, что" in phrases


def test_builtin_without_file(tmp_path, monkeypatch):
    # файл словаря отсутствует — только встроенный список
    monkeypatch.setattr(phrase_check, "PHRASES_FILE",
                        tmp_path / "нет" / "phrases.yaml")
    phrases = phrase_check.load_phrases()
    assert phrases == phrase_check.BUILTIN_PHRASES


def test_repo_phrases_yaml_autoloaded():
    # постоянный словарь репозитория подхватывается без --custom;
    # в phrases.yaml репозитория записан «по сути дела»
    phrases = phrase_check.load_phrases()
    assert "по сути дела" in phrases


def test_bad_yaml_structure_skipped(tmp_path, monkeypatch, capsys):
    # файл-словарь вместо списка — предупреждение, поиск не падает
    f = tmp_path / "phrases.yaml"
    f.write_text("словарь: {а: б}\n", encoding="utf-8")
    monkeypatch.setattr(phrase_check, "PHRASES_FILE", f)
    phrases = phrase_check.load_phrases()
    assert phrases == phrase_check.BUILTIN_PHRASES
    assert "ПРЕДУПРЕЖДЕНИЕ" in capsys.readouterr().out
