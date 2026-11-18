# -*- coding: utf-8 -*-
"""
Юнит-тесты style_report для двуязычия (docs/LOC_PLAN.md):
англ. служебные слова не считаются стилистическим повтором,
--lang у CLI, русское поведение не меняется.

Запуск: python -m pytest test/test_style_lang_units.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from tools import style_report as sr  # noqa: E402


def test_english_function_words_not_repeats():
    # «was/that/the» рядом — не стилистическая проблема для en
    text = ("She said that it was the door that was closed. "
            "It was the old key that was lost.")
    hits = sr.scan_repeats(text, window=5, stopwords=sr._stopwords("en"))
    assert all(h[0] not in ("was", "that", "the", "it") for h in hits)


def test_english_real_repeat_found():
    text = ("Verin opened the door. Verin looked back. Verin stepped in.")
    hits = sr.scan_repeats(text, window=5, stopwords=sr._stopwords("en"))
    assert any(h[0] == "verin" for h in hits)


def test_russian_repeats_unchanged():
    text = ("Эрика шла по коридору. Эрика остановилась у двери. "
            "Эрика молчала.")
    hits = sr.scan_repeats(text, window=5, stopwords=sr._stopwords("ru"))
    assert any(h[0] == "эрика" for h in hits)


def test_russian_function_words_still_filtered():
    text = ("Он видел этот дом. Этот дом горел. "
            "Который дом он выбрал, тот и запомнил.")
    hits = sr.scan_repeats(text, window=6, stopwords=sr._stopwords("ru"))
    assert all(h[0] not in ("этот", "который", "дом-дом") for h in hits
               if h[0] in ("этот", "который"))
    assert not any(h[0] in ("этот", "который") for h in hits)


def test_stopwords_default_matches_ru_union():
    # по умолчанию (None) — прежний объединённый набор
    assert sr._stopwords(None) is sr.STOPWORDS
    assert sr._stopwords("ru") is sr.STOPWORDS
    assert "which" in sr._stopwords("en")
    assert "который" not in sr._stopwords("en")
