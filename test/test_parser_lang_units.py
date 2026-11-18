# -*- coding: utf-8 -*-
"""
Юнит-тесты text_parser для двуязычия (docs/LOC_PLAN.md):
англ. стоп-лист, параметр lang у find_name_candidates/find_bigrams,
обратная совместимость прежних вызовов без lang.

Запуск: python -m pytest test/test_parser_lang_units.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from core import text_parser as tp  # noqa: E402


def test_stoplist_union_backcompat():
    # прежнее имя STOPLIST — объединение: старые подписчики не меняются
    assert tp.STOPLIST == tp.STOPLIST_RU | tp.STOPLIST_EN
    assert "эрика" not in tp.STOPLIST
    assert tp.stoplist(None) is tp.STOPLIST
    assert tp.stoplist("ru") is tp.STOPLIST
    assert tp.stoplist("en") is tp.STOPLIST_EN


def test_russian_candidates_unchanged():
    text = ("Реплика продолжилась, Эрика молчала. "
            "Он посмотрел на Мастера Кайдзо.")
    cands = tp.find_name_candidates(text)
    assert "эрика" in cands
    # без lang стоп-слово «мастер» по-прежнему отсеивается
    assert "мастер" not in cands


def test_english_candidate_found():
    text = "The door opened and Verin stepped inside. He waited."
    cands = tp.find_name_candidates(text, lang="en")
    assert "verin" in cands


def test_english_stopwords_filtered():
    text = ("She turned around and Will smiled. "
            "The Doctor raised an eyebrow. Captain says no.")
    cands = tp.find_name_candidates(text, lang="en")
    # will, doctor, captain — служебные/титулы, не имена
    for w in ("will", "doctor", "captain"):
        assert w not in cands


def test_lang_en_ignores_capitalized_stopwords():
    # всё предложение из «стоповых» слов не даёт кандидатов
    text = "Then It Was Just Nothing. Maybe There Still Is Something."
    assert tp.find_name_candidates(text, lang="en") == []


def test_known_excluded_norm_yo():
    # ё/е — одна буква: известная «елёна» (в нижнем регистре, как из
    # реестра) гасит и кандидата «Елена»
    text = "Пришла Елена внутрь и села у стены."
    cands = tp.find_name_candidates(text, known={"елёна"})
    assert "елена" not in cands


def test_bigrams_english():
    text = "The captain called John Blackthorn over. Doctor, he said."
    bg = tp.find_bigrams(text, lang="en")
    assert "john blackthorn" in bg


def test_bigrams_russian_unchanged():
    # «мастер» — стоп-слово, для проверки биграмма берётся без него
    text = "Пришла Эрика Волкова и села у стены."
    assert "эрика волкова" in tp.find_bigrams(text)


def test_first_word_of_sentence_skipped_both_langs():
    # первое слово предложения всегда пропускается — это не кандидат
    assert tp.find_name_candidates("Verin waited. Then the door opened.",
                                   lang="en") == []
