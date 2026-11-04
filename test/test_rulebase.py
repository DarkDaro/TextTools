# -*- coding: utf-8 -*-
"""Тесты загрузчика YAML-словарей правил (core.rulebase)."""
from pathlib import Path

import pytest

from core.rulebase import load_rules

VALID = r"""rules:
  - cat: решимость
    level: hard
    re: '\bрешимост\w*'
    hint: "действие вместо оценки"
  - cat: надежда
    level: soft
    word: надежда
"""


def write_yaml(tmp_path, text, name="db.yaml"):
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    return f


def test_load_valid(tmp_path):
    rules = load_rules(write_yaml(tmp_path, VALID))
    assert [r.cat for r in rules] == ["решимость", "надежда"]
    assert rules[0].level == "hard"
    assert rules[1].level == "soft"
    assert rules[0].hint == "действие вместо оценки"
    # регистр поиска не важен
    assert rules[0].pattern.search("Она с Решимостью шагнула")
    assert rules[0].pattern.search("решимостью")


def test_word_rule_forms(tmp_path):
    """word: разворачивается в формы (pymorphy3), падежи ловятся."""
    from core import morph
    f = write_yaml(tmp_path, "rules:\n  - cat: эпитет\n    word: непоколебимый\n")
    rules = load_rules(f)
    if morph.AVAILABLE:
        assert rules[0].pattern.search("он был непоколебимым")
    else:
        assert rules[0].pattern.search("непоколебимый")


def test_missing_cat(tmp_path):
    f = write_yaml(tmp_path, "rules:\n  - level: hard\n    re: 'x'\n")
    with pytest.raises(ValueError, match="категория"):
        load_rules(f)


def test_both_re_and_word(tmp_path):
    f = write_yaml(tmp_path, "rules:\n  - cat: a\n    re: 'x'\n    word: y\n")
    with pytest.raises(ValueError, match="ровно одно"):
        load_rules(f)


def test_neither_re_nor_word(tmp_path):
    f = write_yaml(tmp_path, "rules:\n  - cat: a\n    hint: пусто\n")
    with pytest.raises(ValueError, match="ровно одно"):
        load_rules(f)


def test_bad_regex(tmp_path):
    f = write_yaml(tmp_path, "rules:\n  - cat: a\n    re: '(unclosed'\n")
    with pytest.raises(ValueError, match="регэксп"):
        load_rules(f)


def test_bad_level(tmp_path):
    f = write_yaml(tmp_path,
                   "rules:\n  - cat: a\n    level: strict\n    re: 'x'\n")
    with pytest.raises(ValueError, match="hard или soft"):
        load_rules(f)


def test_empty_rules(tmp_path):
    f = write_yaml(tmp_path, "rules: []\n")
    with pytest.raises(ValueError, match="ни одного"):
        load_rules(f)


def test_wrong_structure(tmp_path):
    f = write_yaml(tmp_path, "- просто список\n")
    with pytest.raises(ValueError, match="rules"):
        load_rules(f)


def test_not_found():
    with pytest.raises(ValueError, match="не найден"):
        load_rules("/nonexistent/db.yaml")


def test_empty_match_guard(tmp_path):
    """Регэксп, совпадающий с пустотой, отвергается — иначе --clean
    зациклится на нулевых заменах."""
    f = write_yaml(tmp_path, "rules:\n  - cat: a\n    re: 'x?'\n")
    with pytest.raises(ValueError, match="зациклится"):
        load_rules(f)


def test_real_dictionaries_load():
    """Штатные словари валидны, непусты, категории заполнены."""
    root = Path(__file__).resolve().parent.parent
    for name in ("resolve_db.yaml", "pathos_db.yaml"):
        rules = load_rules(root / "data" / name)
        assert len(rules) >= 10, name
        assert all(r.cat for r in rules), name
