# -*- coding: utf-8 -*-
"""
Юнит-тесты core/i18n: tr() по ключу и языку интерфейса,
незнакомый ключ не роняет окно, словарь пополняется.

Запуск: python -m pytest test/test_i18n_units.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from core import i18n  # noqa: E402
from core.lang import get_ui_lang  # noqa: E402


def test_tr_russian_default(monkeypatch, tmp_path):
    monkeypatch.delenv("TEXTOOLS_LANG", raising=False)
    monkeypatch.setattr("gui_config.CONFIG_FILE", tmp_path / "x.json")
    assert i18n.tr("settings.lang.section") == "Язык"


def test_tr_english_by_config(monkeypatch, tmp_path):
    import json
    import gui_config
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"ui_lang": "en"}), encoding="utf-8")
    monkeypatch.setattr(gui_config, "CONFIG_FILE", cfg)
    monkeypatch.delenv("TEXTOOLS_LANG", raising=False)
    assert i18n.tr("settings.lang.section") == "Language"
    assert i18n.tr("settings.lang.text") == "Text language:"


def test_tr_explicit_lang_wins(monkeypatch):
    monkeypatch.setenv("TEXTOOLS_LANG", "en")
    assert i18n.tr("settings.lang.text", lang="ru") == "Язык текстов:"


def test_unknown_key_returns_itself():
    assert i18n.tr("tab.gone.missing") == "tab.gone.missing"


def test_add_and_tr():
    i18n.add("test.hello", "Привет", "Hello")
    assert i18n.tr("test.hello", lang="ru") == "Привет"
    assert i18n.tr("test.hello", lang="en") == "Hello"


def test_ui_lang_resolution(monkeypatch, tmp_path):
    monkeypatch.delenv("TEXTOOLS_LANG", raising=False)
    monkeypatch.setattr("gui_config.CONFIG_FILE", tmp_path / "x.json")
    assert get_ui_lang() == "ru"
    monkeypatch.setenv("TEXTOOLS_LANG", "en")
    assert get_ui_lang() == "en"
    # тр() подхватывает env без явного lang
    assert i18n.tr("settings.lang.section") == "Language"


def test_missing_lang_variant_falls_back(monkeypatch):
    i18n.STRINGS["test.partial"] = {"ru": "Только русский"}
    monkeypatch.setenv("TEXTOOLS_LANG", "en")
    assert i18n.tr("test.partial") == "Только русский"
    del i18n.STRINGS["test.partial"]
