"""
Юнит-тесты словаря ё/е-аудита: yo_dict.yaml полностью заменяет
встроенный, битые пары отбрасываются, имена из реестра дают
е->ё-пары, границы слов не задевают чужие формы.

Запуск:  python -m pytest test/test_yo_dict_units.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools import yo_audit


def test_builtin_by_default(tmp_path):
    d = yo_audit.load_dict(str(tmp_path / "нет.yaml"))
    assert d == yo_audit.BUILTIN


def test_custom_dict_replaces_fully(tmp_path):
    f = tmp_path / "yo_dict.yaml"
    f.write_text("словарные:\n  - желоб|жёлоб\n", encoding="utf-8")
    d = yo_audit.load_dict(str(f))
    # категория заменена, остальная пуста — полного слияния нет
    assert d["словарные"] == [("желоб", "жёлоб")]
    assert d["омографы"] == []


def test_bad_pairs_dropped(tmp_path):
    f = tmp_path / "yo_dict.yaml"
    # «|пусто» намеренно не используем: "|" в начале значения — это
    # block-scalar YAML, файл не распарсится вовсе
    f.write_text("омографы:\n  - все|всё\n  - без черты\n  - два|три|четыре\n",
                 encoding="utf-8")
    d = yo_audit.load_dict(str(f))
    assert d["омографы"] == [("все", "всё")]
    assert d["словарные"] == []  # файла категории нет — полная замена


def test_broken_yaml_falls_back(tmp_path, capsys):
    f = tmp_path / "yo_dict.yaml"
    f.write_text("словарные: [разорванная\n  структура\n", encoding="utf-8")
    d = yo_audit.load_dict(str(f))
    assert d == yo_audit.BUILTIN
    assert "не прочитан" in capsys.readouterr().out


def test_name_pairs_from_registry():
    chars = [{"имя": "Семён", "формы": ["Семёна", "Мастер"]},
             {"имя": "Тёрн", "формы": []}]
    pairs = yo_audit.name_pairs(chars)
    assert ("Семен", "Семён") in pairs
    assert ("Семена", "Семёна") in pairs
    # «Мастер» без ё — мимо; дублей е-варианта нет
    assert all(p[1] != "Мастер" for p in pairs)
    assert len(pairs) == len({p[0].lower() for p in pairs})


def test_word_pattern_bounds():
    # тире внутри формы допустимо: е-написание «все-таки» ловится
    rx = yo_audit._word_pattern("все")
    assert rx.search("все-таки")
    assert rx.search("Все шло хорошо")
    # внутри другого слова — нет
    assert not yo_audit._word_pattern("шел").search("шелест")
    assert not rx.search("всего")
