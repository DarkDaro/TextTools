# -*- coding: utf-8 -*-
r"""
core: rulebase — загрузка YAML-словарей правил (05.11).

Словари режима АНТИРЕШИМОСТЬ (data/resolve_db.yaml, data/pathos_db.yaml):

  rules:
    - cat: решимость       # категория отчёта (обязательно)
      level: hard          # hard — зачистка --clean; soft — только подсветка
      re: '\bрешимост\w*'  # регэксп (нижний регистр; регистр поиска не важен)
      word: решимость      # ИЛИ лемма: формы через core.morph.word_forms
      hint: "..."          # подсказка редактору (попадает в лог)
      fix: "..."           # автозамена; пусто — вырезание

Свой парсер не нужен: PyYAML уже в requirements.txt и используется
в проекте (phrase_check, obsidian_check). Валидация строгая, ошибки —
ValueError с именем файла и номером правила: словарь правится человеком
вручную, ругаться надо по-человечески. Регэкспы компилируются на
загрузке — битый паттерн ловится сразу, а не на полпути по хранилищу.
"""
import re
from dataclasses import dataclass
from pathlib import Path

LEVELS = ("hard", "soft")


@dataclass
class Rule:
    """Одно правило словаря: что искать и насколько это опасно."""
    cat: str              # категория для отчёта
    level: str            # hard | soft
    source: str           # исходник регэкспа (для замены в docx: '(?i)'+source)
    pattern: "re.Pattern" # скомпилировано с IGNORECASE
    hint: str = ""        # подсказка редактору
    fix: str = ""         # безопасная автозамена (пусто — вырезать)
    index: int = 0        # номер правила в файле (1-based), для сообщений


def _word_pattern(term):
    """Лемма -> регэксп всех форм (pymorphy3). Без него — точное слово."""
    from core import morph
    forms = sorted(morph.word_forms(term))
    if not forms:
        forms = [term.lower()]
    body = "|".join(re.escape(f) for f in forms)
    return r"\b(?:" + body + r")\b"


def load_rules(path):
    """Читает YAML-словарь, возвращает список Rule.

    ValueError на любую проблему — с именем файла и номером правила,
    чтобы правку словаря можно было починить с одного прочтения ошибки.
    """
    path = Path(path)
    if not path.exists():
        raise ValueError(f"Словарь не найден: {path}")
    try:
        import yaml  # PyYAML — зависимость проекта, импорт на месте
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ValueError(f"Словарь {path.name}: ошибка YAML — {e}") from e
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise ValueError(
            f"Словарь {path.name}: ожидается секция 'rules:' со списком правил")
    rules = []
    for i, item in enumerate(data["rules"], 1):
        where = f"Словарь {path.name}, правило {i}"
        if not isinstance(item, dict):
            raise ValueError(f"{where}: ожидается словарь с полями "
                             "cat / level / re|word")
        cat = str(item.get("cat", "") or "").strip()
        if not cat:
            raise ValueError(f"{where}: не заполнена категория (cat)")
        level = str(item.get("level", "hard") or "hard").strip().lower()
        if level not in LEVELS:
            raise ValueError(f"{where}: level должен быть hard или soft, "
                             f"а не «{level}»")
        src = str(item.get("re", "") or "").strip()
        word = str(item.get("word", "") or "").strip()
        if bool(src) == bool(word):
            raise ValueError(f"{where}: нужно ровно одно поле — re или word")
        if word:
            src = _word_pattern(word)
        try:
            pattern = re.compile(src, re.IGNORECASE)
        except re.error as e:
            raise ValueError(f"{where}: битый регэксп «{src}» — {e}") from e
        if pattern.match(""):
            raise ValueError(f"{where}: регэксп совпадает с пустой строкой — "
                             "зачистка зациклится")
        rules.append(Rule(
            cat=cat, level=level, source=src, pattern=pattern,
            hint=str(item.get("hint", "") or ""),
            fix=str(item.get("fix", "") or ""), index=i))
    if not rules:
        raise ValueError(f"Словарь {path.name}: ни одного правила")
    return rules
