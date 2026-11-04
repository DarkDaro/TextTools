"""
Юнит-тесты text_stats: подсчёт слов/предложений, доля диалогов,
слова-паразиты (регистр, ё=е, спецсимволы из parasites.yaml).

Раньше у статистики не было прямых тестов — поведение менялось
молча (например, re.escape для «(как бы)» появилось только 04.11).

Запуск:  python -m pytest test/test_text_stats_units.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools import text_stats as ts


def test_words_and_sentences():
    st = ts.analyze_text("Эрика шла по коридору. Мастер ждал у двери!\n"
                         "Лика кивнула?")
    assert st["words"] == 10
    assert st["sents"] == 3
    assert st["avg_sent"] == round(10 / 3, 1)


def test_empty_text_is_safe():
    st = ts.analyze_text("")
    assert st["words"] == 0 and st["sents"] == 0
    assert st["avg_sent"] == 0.0 and st["dialog_share"] == 0.0
    assert st["parasites"] == {}


def test_dialog_share():
    st = ts.analyze_text("— Пойдём, — сказал Кайдзо.\n— Куда?\n"
                         "Они вышли из ангара.")
    # 3 непустых строки, 2 диалоговых
    assert st["dialog_share"] == round(100 * 2 / 3, 1)


def test_dialog_dash_needs_word():
    # тире без слова — не реплика
    st = ts.analyze_text("—\nПусто.")
    assert st["dialog_share"] == 0.0


def test_parasites_case_and_yo():
    st = ts.analyze_text("По сути дела он знал. ПО СУТИ ДЕЛА — снова.",
                         parasites=["по сути дела"])
    # регистр не важен; счётчик паразита — 2
    assert st["parasites"].get("по сути дела", (0, 0))[0] == 2


def test_parasites_custom_list_and_word_bounds():
    # «дела» не должно сработать внутри «подела»
    st = ts.analyze_text("Он поделил дела. Дела сделаны.",
                         parasites=["дела"])
    assert st["parasites"]["дела"][0] == 2


def test_parasites_yaml_override(tmp_path, monkeypatch):
    f = tmp_path / "parasites.yaml"
    f.write_text('- просто космос\n', encoding="utf-8")
    monkeypatch.setattr(ts, "PARASITE_FILE", f)
    assert ts.load_parasites() == ["просто космос"]


def test_parasites_yaml_bad_structure_fallback(tmp_path, monkeypatch,
                                               capsys):
    f = tmp_path / "parasites.yaml"
    f.write_text("список: [нет]\n", encoding="utf-8")
    monkeypatch.setattr(ts, "PARASITE_FILE", f)
    assert ts.load_parasites() is ts.PARASITES
    assert "ПРЕДУПРЕЖДЕНИЕ" in capsys.readouterr().out


def test_hyphenated_words_counted():
    st = ts.analyze_text("Светло-серый костюм.")
    assert st["words"] == 2  # «светло-серый» + «костюм»
