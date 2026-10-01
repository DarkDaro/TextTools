# -*- coding: utf-8 -*-
"""
core: morph — падежные формы имён через pymorphy3 (01.10).

Если pymorphy3 не установлен, всё деградирует мягко: word_forms
возвращает только сам термин (поиск ведётся как раньше).

Эвристика имён: формы матчатся в тексте только с заглавной буквы —
иначе «Лика» (персонаж) совпадёт с бытовым «лик» через общую лемму.
"""
try:
    import re

    import pymorphy3
    AVAILABLE = True
except Exception:
    AVAILABLE = False

_analyzer = None
MIN_LEN = 3

# границы слова: кириллица + латиница (дефис внутри имени разрешён словом
# вне проверки — имя может содержать дефис, но границы смотрят по буквам)
_WORD_EDGE = r"(?<![А-ЯЁа-яёA-Za-z])"
_WORD_EDGE_END = r"(?![А-ЯЁа-яёA-Za-z])"


def _esc_yo(s):
    """01.10: экранирование с ё/е-классами: «е»/«ё» (в любом регистре)
    превращаются в [ЕЁеё] — паттерн находит оба написания."""
    return "".join("[ЕЁеё]" if ch in "еёЕЁ" else re.escape(ch) for ch in s)


def combine_patterns(groups):
    """01.10: groups = [(ключ, [patterns])] -> (комбинированный regex | None,
    {имя_группы: ключ}). Совпадение атрибутируется по m.lastgroup — одна
    прогонка finditer по строке вместо суммы по всем паттернам."""
    branches, gmap = [], {}
    for i, (key, pats) in enumerate(groups):
        if not pats:
            continue
        g = f"g{i}"
        gmap[g] = key
        branches.append(f"(?P<{g}>" + "|".join(p.pattern for p in pats) + ")")
    if not branches:
        return None, gmap
    return re.compile("|".join(branches)), gmap


def term_patterns(terms, expand=True):
    """Паттерны поиска списка терминов: точные — регистронезависимо,
    падежные формы — только с заглавной (эвристика имён, 01.10),
    ё/е эквивалентны. Возвращает список re.Pattern."""
    pats = []
    covered = set()
    for t in terms:
        tl = t.lower()
        if tl in covered:
            continue
        covered.add(tl)
        pats.append(re.compile(
            _WORD_EDGE + _esc_yo(t) + _WORD_EDGE_END, re.IGNORECASE))
    if expand and AVAILABLE:
        for t in terms:
            for f in sorted(word_forms(t)):
                fl = f.lower()
                if fl in covered:
                    continue
                covered.add(fl)
                if " " in f:
                    # составные («Мастер Кайдзо») — регистронезависимо
                    pats.append(re.compile(
                        _WORD_EDGE + _esc_yo(f) + _WORD_EDGE_END,
                        re.IGNORECASE))
                else:
                    # одиночные — только с заглавной (эвристика имён:
                    # бытовое «лик» в нижнем регистре не считается «Ликой»)
                    pats.append(re.compile(
                        _WORD_EDGE + _esc_yo(f.capitalize())
                        + _WORD_EDGE_END))
    return pats


def analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = pymorphy3.MorphAnalyzer()
    return _analyzer


def _forms_of(word):
    low = word.lower()
    if not AVAILABLE:
        return {low}
    try:
        parses = analyzer().parse(low)
    except Exception:
        return {low}
    if not parses:
        return {low}
    # 01.10: склоняем только слова в именительном падеже (слово = лемма).
    # Косвенные формы («Эрики» от «Эрик»-мужское) не расширяем — иначе
    # появляется мусор вроде «эрик»/«эриком»; их формы покрывает базовое слово
    best = None
    for p in parses:
        if "nomn" in p.tag.grammemes and p.normal_form == low:
            best = p
            break
    if best is None:
        return {low}
    forms = {low}
    for case in ("nomn", "gent", "datv", "accs", "ablt", "loct"):
        try:
            inf = best.inflect({case, "sing"})
        except Exception:
            inf = None
        if inf and inf.word and inf.word.isalpha() and len(inf.word) >= MIN_LEN:
            forms.add(inf.word)
    return forms


def word_forms(term):
    """Падежные формы термина. Для составного («Мастер Кайдзо») склоняется
    последнее слово, первые остаются как есть. Регистр нижний, сам термин
    включён. Без pymorphy3 — {термин}."""
    term = term.strip().lower()
    if not term:
        return set()
    words = term.split()
    if len(words) == 1:
        return _forms_of(words[0])
    out = set()
    for f in _forms_of(words[-1]):
        out.add(" ".join([*words[:-1], f]))
    return out or {term}
