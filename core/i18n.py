# -*- coding: utf-8 -*-
"""
core: i18n — подмена строк интерфейса (18.11, docs/LOC_PLAN.md).

Разметку окна не трогаем: вкладки, кнопки, горячие клавиши — как
спроектированы. Подменяются только строки: каждый переводимый текст
живёт в STRINGS под ключом в двух вариантах («ru»/«en»), и tr(key)
возвращает вариант по ui_lang из настроек.

Правила пайплайна перевода вкладок:
  1. строка уходит в STRINGS, в разметке остаётся tr("ключ");
  2. вкладка = коммит = её GUI-тест (сначала Настройки, дальше по
     списку в LOC_PLAN.md);
  3. ключи именуются «tab.что»: settings.help, pomo.start и т.д.

tr() читает язык на каждый вызов — правка на «Настройках» видна
следующему окну без перезапуска. Незнакомый ключ возвращается сам
собой (это диагностика: пропущенный ключ сразу виден в окне).
"""
from core.lang import get_ui_lang

# Словарь строк. Наполняется по мере перевода вкладок; на старте
# здесь живут строки раздела «Язык» вкладки «Настройки» — пилот.
STRINGS = {
    "settings.lang.section": {
        "ru": "Язык",
        "en": "Language",
    },
    "settings.lang.text": {
        "ru": "Язык текстов:",
        "en": "Text language:",
    },
    "settings.lang.ui": {
        "ru": "Язык интерфейса:",
        "en": "Interface language:",
    },
    "settings.lang.hint": {
        "ru": "Язык текстов — по каким правилам работают скрипты: "
              "стоп-слова, слова-паразиты, словари штампов, поиск имён. "
              "Язык интерфейса — подмена строк окна (перевод вкладок "
              "идёт по плану docs/LOC_PLAN.md). Выбор сохраняется "
              "сразу; инструменты подхватят его при следующем запуске.",
        "en": "Text language — the rules the scripts apply: stop words, "
              "parasites, cliche dictionaries, name search. Interface "
              "language — the strings of this window (tabs are "
              "translated step by step, see docs/LOC_PLAN.md). The "
              "choice is saved at once; tools pick it up on the next run.",
    },
}


def add(key, ru, en):
    """Пополнить словарь (для тестов и будущих вкладок)."""
    STRINGS[key] = {"ru": ru, "en": en}


def tr(key, lang=None):
    """Строка по ключу и языку интерфейса. Нет ключа — вернётся сам
    ключ (бросать исключение нельзя: окно должно открыться всегда)."""
    item = STRINGS.get(key)
    if not item:
        return key
    if lang is None:
        lang = get_ui_lang()
    return item.get(lang) or item.get("ru") or key
