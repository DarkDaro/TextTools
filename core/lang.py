# -*- coding: utf-8 -*-
"""
core: lang — откуда инструменты берут язык (18.11, docs/LOC_PLAN.md).

Языка два: «ru» и «en». Оси две, ключи конфига разные:
  text_lang — язык текстов (правила обработки),
  ui_lang   — язык интерфейса (строки окна).

Цепочка источников, первый источник выигрывает:
  1. явный аргумент функции (--lang в командной строке);
  2. переменная окружения TEXTOOLS_LANG — для тестов и CI;
  3. ключ gui_config.json — выбор на вкладке «Настройки»;
  4. по умолчанию «ru»: поведение прежних версий не меняется.

Файл конфига читается напрямую и только на чтение: core не пишет
настройки и не держит кэш — правка на «Настройках» видна следующему
запуску инструмента сразу. Любая беда (нет файла, битый JSON, чужое
значение) молча деградирует в «ru».
"""
import json
import os

LANGS = ("ru", "en")


def _norm(value):
    """'EN', ' en ' -> 'en'; всё прочее -> None."""
    if isinstance(value, str):
        v = value.strip().lower()
        if v in LANGS:
            return v
    return None


def _from_config(key):
    try:
        from gui_config import CONFIG_FILE
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return _norm(data.get(key))
    except Exception:
        return None


def get_lang(explicit=None, key="text_lang"):
    """Язык по цепочке: аргумент > TEXTOOLS_LANG > конфиг > «ru».

    explicit — то, что пришло с --lang (None или «ru»/«en»,
    регистр и пробелы прощаются). key — «text_lang» или «ui_lang».
    """
    for v in (explicit, os.environ.get("TEXTOOLS_LANG"), _from_config(key)):
        v = _norm(v)
        if v:
            return v
    return "ru"


def get_text_lang(explicit=None):
    """Язык текстов — то, что передают инструменты обработки."""
    return get_lang(explicit, "text_lang")


def get_ui_lang(explicit=None):
    """Язык интерфейса — то, что читает core.i18n."""
    return get_lang(explicit, "ui_lang")


def is_en(lang):
    """Мелкая удобная проверка для разветвлений правил."""
    return _norm(lang) == "en"
