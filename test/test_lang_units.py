# -*- coding: utf-8 -*-
"""
Юнит-тесты core/lang: цепочка источников языка (аргумент > env >
конфиг > «ru»), нормализация, две оси (text_lang / ui_lang).

Запуск: python -m pytest test/test_lang_units.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from core import lang  # noqa: E402
import gui_config  # noqa: E402


def _no_env(monkeypatch):
    monkeypatch.delenv("TEXTOOLS_LANG", raising=False)


def test_default_is_ru(monkeypatch, tmp_path):
    _no_env(monkeypatch)
    monkeypatch.setattr(gui_config, "CONFIG_FILE",
                        tmp_path / "absent.json")
    assert lang.get_text_lang() == "ru"
    assert lang.get_ui_lang() == "ru"
    assert not lang.is_en(lang.get_text_lang())


def test_explicit_argument_wins(monkeypatch, tmp_path):
    _no_env(monkeypatch)
    monkeypatch.setattr(gui_config, "CONFIG_FILE", tmp_path / "x.json")
    # даже при env и конфиге с «en» явный аргумент сильнее
    monkeypatch.setenv("TEXTOOLS_LANG", "en")
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"text_lang": "en"}), encoding="utf-8")
    monkeypatch.setattr(gui_config, "CONFIG_FILE", cfg)
    assert lang.get_text_lang("ru") == "ru"


def test_env_overrides_config(monkeypatch, tmp_path):
    _no_env(monkeypatch)
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"text_lang": "ru"}), encoding="utf-8")
    monkeypatch.setattr(gui_config, "CONFIG_FILE", cfg)
    assert lang.get_text_lang() == "ru"
    monkeypatch.setenv("TEXTOOLS_LANG", "en")
    assert lang.get_text_lang() == "en"


def test_config_key_read(monkeypatch, tmp_path):
    _no_env(monkeypatch)
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"text_lang": "en", "ui_lang": "ru"}),
                   encoding="utf-8")
    monkeypatch.setattr(gui_config, "CONFIG_FILE", cfg)
    assert lang.get_text_lang() == "en"
    assert lang.get_ui_lang() == "ru"  # оси независимы


def test_normalization(monkeypatch, tmp_path):
    _no_env(monkeypatch)
    monkeypatch.setattr(gui_config, "CONFIG_FILE", tmp_path / "x.json")
    assert lang.get_text_lang(" EN ") == "en"
    assert lang.get_text_lang("Ru") == "ru"
    monkeypatch.setenv("TEXTOOLS_LANG", "  EN ")
    assert lang.get_text_lang() == "en"


def test_bad_values_fall_back_to_ru(monkeypatch, tmp_path):
    _no_env(monkeypatch)
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"text_lang": "de", "ui_lang": 42}),
                   encoding="utf-8")
    monkeypatch.setattr(gui_config, "CONFIG_FILE", cfg)
    assert lang.get_text_lang() == "ru"
    assert lang.get_ui_lang() == "ru"
    monkeypatch.setenv("TEXTOOLS_LANG", "fr")
    assert lang.get_text_lang() == "ru"


def test_broken_config_degrades_to_ru(monkeypatch, tmp_path):
    _no_env(monkeypatch)
    cfg = tmp_path / "cfg.json"
    cfg.write_text("{битый json", encoding="utf-8")
    monkeypatch.setattr(gui_config, "CONFIG_FILE", cfg)
    assert lang.get_text_lang() == "ru"


def test_is_en():
    assert lang.is_en("en") and lang.is_en("EN")
    assert not lang.is_en("ru") and not lang.is_en(None)
